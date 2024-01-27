# coding=utf-8
# Copyright 2019-present, the HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Training the distilled model.
Supported architectures include: BERT -> DistilBERT, RoBERTa -> DistilRoBERTa, GPT2 -> DistilGPT2.
"""
import argparse
import json
import os
import pickle
import shutil

import numpy
import numpy as np
import torch
from typing import Dict, List, Optional, Set, Tuple, Union

from distiller import Distiller
from lm_seqs_dataset import LmSeqsDataset
from transformers import (
    BertConfig,
    BertForMaskedLM,
    BertTokenizer,
    DistilBertConfig,
    DistilBertForMaskedLM,
    DistilBertTokenizer,
    GPT2Config,
    GPT2LMHeadModel,
    GPT2Tokenizer,
    RobertaConfig,
    RobertaForMaskedLM,
    RobertaTokenizer,
)
from transformers.modeling_outputs import MaskedLMOutput

from utils import git_log, init_gpu_params, logger, set_seed

class DistilBertForMaskedLM_Trace(DistilBertForMaskedLM):

    def __init__(self, config):
        super().__init__(config)

    def forward(
        self,
        input_ids: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        head_mask: Optional[torch.Tensor] = None,
        inputs_embeds: Optional[torch.Tensor] = None,
        labels: Optional[torch.LongTensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Tuple[torch.Tensor, ...]:
        r"""
        labels (`torch.LongTensor` of shape `(batch_size, sequence_length)`, *optional*):
            Labels for computing the masked language modeling loss. Indices should be in `[-100, 0, ...,
            config.vocab_size]` (see `input_ids` docstring) Tokens with indices set to `-100` are ignored (masked), the
            loss is only computed for the tokens with labels in `[0, ..., config.vocab_size]`.
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        dlbrt_output = self.distilbert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        hidden_states = dlbrt_output[0]  # (bs, seq_length, dim)
        prediction_logits = self.vocab_transform(hidden_states)  # (bs, seq_length, dim)
        prediction_logits = self.activation(prediction_logits)  # (bs, seq_length, dim)
        prediction_logits = self.vocab_layer_norm(prediction_logits)  # (bs, seq_length, dim)
        prediction_logits = self.vocab_projector(prediction_logits)  # (bs, seq_length, vocab_size)

        mlm_loss = None
        if labels is not None:
            mlm_loss = self.mlm_loss_fct(prediction_logits.view(-1, prediction_logits.size(-1)), labels.view(-1))

        if not return_dict:
            output = (prediction_logits,) + dlbrt_output[1:]
            return ((mlm_loss,) + output) if mlm_loss is not None else output

        if dlbrt_output.attentions == None:
            dlbrt_output.attentions = torch.empty((0))
        if mlm_loss == None:
            mlm_loss = torch.empty((0))
        return prediction_logits, dlbrt_output.hidden_states, dlbrt_output.attentions, mlm_loss

MODEL_CLASSES = {
    "distilbert": (DistilBertConfig, DistilBertForMaskedLM, DistilBertTokenizer),
    "distilbert_infer": (DistilBertConfig, DistilBertForMaskedLM_Trace, DistilBertTokenizer),
    "roberta": (RobertaConfig, RobertaForMaskedLM, RobertaTokenizer),
    "bert": (BertConfig, BertForMaskedLM, BertTokenizer),
    "gpt2": (GPT2Config, GPT2LMHeadModel, GPT2Tokenizer),
}

def sanity_checks(args):
    """
    A bunch of args sanity checks to perform even starting...
    """
    if args.run_mode == "train":
        assert (args.mlm and args.alpha_mlm > 0.0) or (not args.mlm and args.alpha_mlm == 0.0)
        assert (args.alpha_mlm > 0.0 and args.alpha_clm == 0.0) or (args.alpha_mlm == 0.0 and args.alpha_clm > 0.0)
        assert args.alpha_ce >= 0.0
        assert args.alpha_mlm >= 0.0
        assert args.alpha_clm >= 0.0
        assert args.alpha_mse >= 0.0
        assert args.alpha_cos >= 0.0
        assert args.alpha_ce + args.alpha_mlm + args.alpha_clm + args.alpha_mse + args.alpha_cos > 0.0
    if args.mlm:
        if args.run_mode == "train":
            assert os.path.isfile(args.token_counts)
        assert (args.student_type in ["roberta", "distilbert"]) and (args.teacher_type in ["roberta", "bert"])
    else:
        assert (args.student_type in ["gpt2"]) and (args.teacher_type in ["gpt2"])

    assert args.teacher_type == args.student_type or (
        args.student_type == "distilbert" and args.teacher_type == "bert"
    )
    assert os.path.isfile(args.student_config)
    if args.student_pretrained_weights is not None:
        assert os.path.isfile(args.student_pretrained_weights)

    if args.freeze_token_type_embds:
        assert args.student_type in ["roberta"]



def freeze_pos_embeddings(student, args):
    if args.student_type == "roberta":
        student.roberta.embeddings.position_embeddings.weight.requires_grad = False
    elif args.student_type == "gpt2":
        student.transformer.wpe.weight.requires_grad = False


def freeze_token_type_embeddings(student, args):
    if args.student_type == "roberta":
        student.roberta.embeddings.token_type_embeddings.weight.requires_grad = False


def main():
    parser = argparse.ArgumentParser(description="Training")
    parser.add_argument("--force", action="store_true", help="Overwrite dump_path if it already exists.")

    parser.add_argument(
        "--run_mode", choices=["train", "eval"], default="train", help="Runs mode(train, eval)."
    )

    parser.add_argument(
        "--run_dtype", choices=["FP32", "BF16", "FP16"], default="FP32", help="Data type (FP32, BF16, FP16)."
    )

    parser.add_argument(
        "--device", choices=["cpu", "cuda", "xpu"], default="cpu", help="The running device (cpu, cuda, xpu)."
    )

    parser.add_argument(
        "--amp",
        action="store_true",
        help="Whether to use mixed precision instead of 32-bit",
    )

    parser.add_argument(
        "--jit",
        action="store_true",
        help="Whether to use jit trace",
    )

    parser.add_argument(
        "--dump_path", type=str, default="./dump_path", help="The output directory (log, checkpoints, parameters, etc.)"
    )
    parser.add_argument(
        "--data_file",
        type=str,
        required=True,
        help="The binarized file (tokenized + tokens_to_ids) and grouped by sequence.",
    )

    parser.add_argument(
        "--student_type",
        type=str,
        choices=["distilbert", "roberta", "gpt2"],
        required=True,
        help="The student type (DistilBERT, RoBERTa).",
    )
    parser.add_argument("--student_config", type=str, required=True, help="Path to the student configuration.")
    parser.add_argument(
        "--student_pretrained_weights", default=None, type=str, help="Load student initialization checkpoint."
    )

    parser.add_argument(
        "--teacher_type", choices=["bert", "roberta", "gpt2"], required=True, help="Teacher type (BERT, RoBERTa)."
    )
    parser.add_argument("--teacher_name", type=str, required=True, help="The teacher model.")
    parser.add_argument("--student_name", type=str, required=True, help="The student model.")

    parser.add_argument("--temperature", default=2.0, type=float, help="Temperature for the softmax temperature.")
    parser.add_argument(
        "--alpha_ce", default=0.5, type=float, help="Linear weight for the distillation loss. Must be >=0."
    )
    parser.add_argument(
        "--alpha_mlm",
        default=0.0,
        type=float,
        help="Linear weight for the MLM loss. Must be >=0. Should be used in conjunction with `mlm` flag.",
    )
    parser.add_argument("--alpha_clm", default=0.5, type=float, help="Linear weight for the CLM loss. Must be >=0.")
    parser.add_argument("--alpha_mse", default=0.0, type=float, help="Linear weight of the MSE loss. Must be >=0.")
    parser.add_argument(
        "--alpha_cos", default=0.0, type=float, help="Linear weight of the cosine embedding loss. Must be >=0."
    )

    parser.add_argument(
        "--mlm", action="store_true", help="The LM step: MLM or CLM. If `mlm` is True, the MLM is used over CLM."
    )
    parser.add_argument(
        "--mlm_mask_prop",
        default=0.15,
        type=float,
        help="Proportion of tokens for which we need to make a prediction.",
    )
    parser.add_argument("--word_mask", default=0.8, type=float, help="Proportion of tokens to mask out.")
    parser.add_argument("--word_keep", default=0.1, type=float, help="Proportion of tokens to keep.")
    parser.add_argument("--word_rand", default=0.1, type=float, help="Proportion of tokens to randomly replace.")
    parser.add_argument(
        "--mlm_smoothing",
        default=0.7,
        type=float,
        help="Smoothing parameter to emphasize more rare tokens (see XLM, similar to word2vec).",
    )
    parser.add_argument("--token_counts", type=str, help="The token counts in the data_file for MLM.")

    parser.add_argument(
        "--restrict_ce_to_mask",
        action="store_true",
        help="If true, compute the distillation loss only the [MLM] prediction distribution.",
    )
    parser.add_argument(
        "--freeze_pos_embs",
        action="store_true",
        help="Freeze positional embeddings during distillation. For student_type in ['roberta', 'gpt2'] only.",
    )
    parser.add_argument(
        "--freeze_token_type_embds",
        action="store_true",
        help="Freeze token type embeddings during distillation if existent. For student_type in ['roberta'] only.",
    )

    parser.add_argument("--n_epoch", type=int, default=3, help="Number of pass on the whole dataset.")
    parser.add_argument("--batch_size", type=int, default=64, help="Batch size (for each process).")
    parser.add_argument("--num_iteration", type=int, default=-1, help="Iteration number.")
    parser.add_argument(
        "--group_by_size",
        action="store_false",
        help="If true, group sequences that have similar length into the same batch. Default is true.",
    )

    parser.add_argument("--max_predictions_per_seq",
                        default=76,
                        type=int,
                        help="The maximum total of masked tokens in input sequence")

    parser.add_argument(
        "--gradient_accumulation_steps",
        type=int,
        default=50,
        help="Gradient accumulation for larger training batches.",
    )
    parser.add_argument("--warmup_prop", default=0.05, type=float, help="Linear warmup proportion.")
    parser.add_argument("--weight_decay", default=0.0, type=float, help="Weight decay if we apply some.")
    parser.add_argument("--learning_rate", default=5e-4, type=float, help="The initial learning rate for Adam.")
    parser.add_argument("--adam_epsilon", default=1e-6, type=float, help="Epsilon for Adam optimizer.")
    parser.add_argument("--max_grad_norm", default=5.0, type=float, help="Max gradient norm.")
    parser.add_argument("--initializer_range", default=0.02, type=float, help="Random initialization range.")

    #parser.add_argument(
    #    "--fp16",
    #    action="store_true",
    #    help="Whether to use 16-bit (mixed) precision (through NVIDIA apex) instead of 32-bit",
    #)
    parser.add_argument(
        "--fp16_opt_level",
        type=str,
        default="O1",
        help=(
            "For fp16: Apex AMP optimization level selected in ['O0', 'O1', 'O2', and 'O3']."
            "See details at https://nvidia.github.io/apex/amp.html"
        ),
    )
    parser.add_argument("--n_gpu", type=int, default=1, help="Number of GPUs in the node.")
    parser.add_argument("--local_rank", type=int, default=-1, help="Distributed training - Local rank")
    parser.add_argument("--seed", type=int, default=56, help="Random seed")

    parser.add_argument("--log_interval", type=int, default=500, help="Tensorboard logging interval.")
    parser.add_argument("--checkpoint_interval", type=int, default=4000, help="Checkpoint interval.")
    args = parser.parse_args()
    sanity_checks(args)

    if args.device == "xpu":
        import intel_extension_for_pytorch

    # ARGS #
    init_gpu_params(args)
    set_seed(args)
    if args.is_master:
        if os.path.exists(args.dump_path):
            if not args.force:
                raise ValueError(
                    f"Serialization dir {args.dump_path} already exists, but you have not precised wheter to overwrite"
                    " itUse `--force` if you want to overwrite it"
                )
            else:
                shutil.rmtree(args.dump_path)

        pid = os.getpid()
        args.dump_path += str(pid)
        if not os.path.exists(args.dump_path):
            os.makedirs(args.dump_path)
        logger.info(f"Experiment will be dumped and logged in {args.dump_path}")

        # SAVE PARAMS #
        logger.info(f"Param: {args}")
        with open(os.path.join(args.dump_path, "parameters.json"), "w") as f:
            json.dump(vars(args), f, indent=4)
        #git_log(args.dump_path)

    if args.run_mode == "eval":
        student_config_class, student_model_class, _ = MODEL_CLASSES[args.student_type + "_infer"]
    else:
        student_config_class, student_model_class, _ = MODEL_CLASSES[args.student_type]
    teacher_config_class, teacher_model_class, teacher_tokenizer_class = MODEL_CLASSES[args.teacher_type]

    # TOKENIZER #
    tokenizer = teacher_tokenizer_class.from_pretrained(args.teacher_name)
    special_tok_ids = {}
    for tok_name, tok_symbol in tokenizer.special_tokens_map.items():
        idx = tokenizer.all_special_tokens.index(tok_symbol)
        special_tok_ids[tok_name] = tokenizer.all_special_ids[idx]
    logger.info(f"Special tokens {special_tok_ids}")
    args.special_tok_ids = special_tok_ids
    args.max_model_input_size = tokenizer.max_model_input_sizes[args.teacher_name]

    # DATA LOADER #
    logger.info(f"Loading data from {args.data_file}")

    if args.mlm and args.run_mode == "train":
        logger.info(f"Loading token counts from {args.token_counts} (already pre-computed)")
        with open(args.token_counts, "rb") as fp:
            counts = pickle.load(fp)

        token_probs = np.maximum(counts, 1) ** -args.mlm_smoothing
        for idx in special_tok_ids.values():
            token_probs[idx] = 0.0  # do not predict special tokens
        token_probs = torch.from_numpy(token_probs)
    else:
        token_probs = None

    # STUDENT #
    logger.info(f"Loading student config from {args.student_config}")
    stu_architecture_config = student_config_class.from_pretrained(args.student_config)
    stu_architecture_config.output_hidden_states = True

    if args.student_pretrained_weights is not None:
        logger.info(f"Loading pretrained weights from {args.student_pretrained_weights}")
        student = student_model_class.from_pretrained(args.student_pretrained_weights, config=stu_architecture_config)
    else:
        student = student_model_class.from_pretrained(args.student_name, config=stu_architecture_config)
        #student = student_model_class(stu_architecture_config)

    if args.n_gpu > 0 and args.device == "cuda":
        student.to(f"cuda:{args.local_rank}")
    elif args.n_gpu > 0 and args.device == "xpu": 
        student.to(args.device)
    logger.info("Student loaded.")

    # TEACHER #
    teacher = teacher_model_class.from_pretrained(args.teacher_name, output_hidden_states=True)
    if args.n_gpu > 0 and args.device == "cuda":
        teacher.to(f"cuda:{args.local_rank}")
    elif args.n_gpu > 0 and args.device == "xpu": 
        teacher.to(args.device)
    logger.info(f"Teacher loaded from {args.teacher_name}.")

    # FREEZING #
    if args.freeze_pos_embs:
        freeze_pos_embeddings(student, args)
    if args.freeze_token_type_embds:
        freeze_token_type_embeddings(student, args)

    # SANITY CHECKS #
    assert student.config.vocab_size == teacher.config.vocab_size
    assert student.config.hidden_size == teacher.config.hidden_size
    assert student.config.max_position_embeddings == teacher.config.max_position_embeddings
    if args.mlm and args.run_mode == "train":
        assert token_probs.size(0) == stu_architecture_config.vocab_size

    # DISTILLER #
    if args.device == "cuda":
        torch.cuda.empty_cache()
    elif args.device == "xpu":
        torch.xpu.empty_cache()
    distiller = Distiller(
        params=args, token_probs=token_probs, student=student, teacher=teacher
    )
    if args.run_mode == "train":
        distiller.train()
    elif args.run_mode == "eval":
        distiller.eval()
    logger.info("Let's go get some drinks.")


if __name__ == "__main__":
    main()
