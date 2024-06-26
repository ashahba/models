#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2023 Intel Corporation
#
# AGPL-3.0 license


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from common.base_model_init import BaseModelInitializer
from common.base_model_init import set_env_var

import os
from argparse import ArgumentParser
import time


class ModelInitializer(BaseModelInitializer):
    """initialize mode and run benchmark"""

    def __init__(self, args, custom_args=[], platform_util=None):
        super(ModelInitializer, self).__init__(args, custom_args, platform_util)

        self.benchmark_command = ""
        if not platform_util:
            raise ValueError("Did not find any platform info.")

        # use default batch size if -1
        if self.args.batch_size == -1:
            self.args.batch_size = 128

        # set num_inter_threads and num_intra_threads
        self.set_num_inter_intra_threads()

        arg_parser = ArgumentParser(description='Parse args')

        arg_parser.add_argument("--warmup-steps", dest='warmup_steps',
                                type=int, default=10,
                                help="number of warmup steps")
        arg_parser.add_argument("--steps", dest='steps',
                                type=int, default=50,
                                help="number of steps")
        arg_parser.add_argument(
            '--kmp-blocktime', dest='kmp_blocktime',
            help='number of kmp block time',
            type=int, default=1)
        self.args = arg_parser.parse_args(self.custom_args, namespace=self.args)

        # Set KMP env vars, if they haven't already been set, but override the default KMP_BLOCKTIME value
        config_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
        self.set_kmp_vars(config_file_path, kmp_blocktime=str(self.args.kmp_blocktime))

        set_env_var("OMP_NUM_THREADS", self.args.num_intra_threads)

        if self.args.accuracy_only:
            script_file = ""
        elif self.args.benchmark_only:
            script_file = "detect.py"
        benchmark_script = os.path.join(
            self.args.intelai_models, self.args.mode, self.args.precision, script_file)

        self.benchmark_command = self.get_command_prefix(args.socket_id) + \
            self.python_exe + " " + benchmark_script

        if self.args.input_graph:
            self.benchmark_command += " --weights=" + self.args.input_graph

        # if the data location directory is not empty, then include the arg
        if self.args.data_location and os.listdir(self.args.data_location):
            self.benchmark_command += " --source=" + \
                                      self.args.data_location
        if self.args.benchmark_only:
            self.benchmark_command += " --dataset_size=500"
            self.benchmark_command += " --nosave"
        if self.args.accuracy_only:
            self.benchmark_command += " --accuracy-only"

        # if output results is enabled, generate a results file name and pass it to the inference script
        if self.args.output_results:
            self.results_filename = "{}_{}_{}_results_{}.txt".format(
                self.args.model_name, self.args.precision, self.args.mode,
                time.strftime("%Y%m%d_%H%M%S", time.gmtime()))
            self.results_file_path = os.path.join(self.args.output_dir, self.results_filename)
            self.benchmark_command += " --results-file-path {}".format(self.results_file_path)

    def run(self):
        if self.benchmark_command:
            self.run_command(self.benchmark_command)
            if self.args.output_results:
                print("Inference results file in the output directory: {}".format(self.results_filename))
