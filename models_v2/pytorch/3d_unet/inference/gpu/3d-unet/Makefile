# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
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

SHELL := /bin/bash

MAKEFILE_NAME := $(lastword $(MAKEFILE_LIST))
UNAME := $(shell whoami)
UID := $(shell id -u `whoami`)
GROUPNAME := $(shell id -gn `whoami`)
GROUPID := $(shell id -g `whoami`)

HOST_VOL ?= ${PWD}
CONTAINER_VOL ?= /workspace

BUILD_DIR := build
ifndef DOWNLOAD_DATA_DIR
	export DOWNLOAD_DATA_DIR := $(HOST_VOL)/$(BUILD_DIR)/MICCAI_BraTS_2019_Data_Training
endif
RAW_DATA_DIR := $(BUILD_DIR)/raw_data
PREPROCESSED_DATA_DIR := $(BUILD_DIR)/preprocessed_data
POSTPROCESSED_DATA_DIR := $(BUILD_DIR)/postprocessed_data
#MODEL_DIR := $(BUILD_DIR)/model
RESULT_DIR := $(BUILD_DIR)/result
MLPERF_CONF := $(BUILD_DIR)/mlperf.conf
PYTORCH_MODEL := $(RESULT_DIR)/fold_1.zip
#ONNX_MODEL := $(MODEL_DIR)/224_224_160.onnx
#ONNX_DYNAMIC_BS_MODEL := $(MODEL_DIR)/224_224_160_dynamic_bs.onnx
#TF_MODEL := $(MODEL_DIR)/224_224_160.pb
#OPENVINO_MODEL := $(MODEL_DIR)/brats_model_checkpoint_final_fold1_H224_W224_D160_C4.bin
#OPENVINO_MODEL_METADATA := $(MODEL_DIR)/brats_model_checkpoint_final_fold1_H224_W224_D160_C4.xml

# Env variables needed by nnUnet
export nnUNet_raw_data_base=$(RAW_DATA_DIR)
export nnUNet_preprocessed=$(PREPROCESSED_DATA_DIR)
export RESULTS_FOLDER=$(RESULT_DIR)

HAS_GPU := $(shell command -v nvidia-smi 2> /dev/null)

ifeq ($(HAS_GPU),)
	DOCKER_RUN_CMD := docker run
else
	# Handle different nvidia-docker version
	ifneq ($(wildcard /usr/bin/nvidia-docker),)
		DOCKER_RUN_CMD := nvidia-docker run
	else
		DOCKER_RUN_CMD := docker run --gpus=all
	endif
endif

.PHONY: setup
setup: check_download_data_dir create_directories
	@echo "Running basic setup..."
#	@if [ ! -e $(MLPERF_CONF) ]; then \
#		cp ../../../mlperf.conf $(MLPERF_CONF); \
#	fi
#	@$(MAKE) -f $(MAKEFILE_NAME) init_submodule
	@$(MAKE) -f $(MAKEFILE_NAME) download_model

.PHONY: check_download_data_dir
check_download_data_dir:
	@if [ ! -e $(DOWNLOAD_DATA_DIR) ]; then \
		echo "Please set environment variable DOWNLOAD_DATA_DIR to <path/to/MICCAI_BraTS_2019_Data_Training>" && false ; \
	fi

.PHONY: create_directories
create_directories:
	@if [ ! -e $(BUILD_DIR) ]; then \
		mkdir $(BUILD_DIR); \
	fi
	#@if [ ! -e $(MODEL_DIR) ]; then \
	#	mkdir $(MODEL_DIR); \
	#fi
	@if [ ! -e $(RESULT_DIR) ]; then \
		mkdir $(RESULT_DIR); \
	fi

#.PHONY: init_submodule
#init_submodule:
#	@echo "Initialize nnUnet submodule.."
#	@git submodule update --init nnUnet

.PHONY: download_model
download_model:
	@echo "Download models..."
	@$(MAKE) -f $(MAKEFILE_NAME) download_pytorch_model
#	@$(MAKE) -f $(MAKEFILE_NAME) download_onnx_model
#	@$(MAKE) -f $(MAKEFILE_NAME) download_tf_model
#	@$(MAKE) -f $(MAKEFILE_NAME) download_openvino_model

.PHONY: download_pytorch_model
download_pytorch_model: create_directories
	@echo "Downloading PyTorch model from Zenodo..."
	@if [ ! -e $(PYTORCH_MODEL) ]; then \
		wget -O $(PYTORCH_MODEL) https://zenodo.org/record/3904106/files/fold_1.zip?download=1; \
	fi
	@cd $(RESULT_DIR) && unzip -o fold_1.zip;

#.PHONY: download_onnx_model
#download_onnx_model: create_directories
#	@echo "Downloading ONNX model from Zenodo..."
#	@if [ ! -e $(ONNX_MODEL) ]; then \
#		wget -O $(ONNX_MODEL) https://zenodo.org/record/3928973/files/224_224_160.onnx?download=1; \
#	fi
#	@if [ ! -e $(ONNX_DYNAMIC_BS_MODEL) ]; then \
#		wget -O $(ONNX_DYNAMIC_BS_MODEL) https://zenodo.org/record/3928973/files/224_224_160_dyanmic_bs.onnx?download=1; \
#	fi
#
#.PHONY: download_tf_model
#download_tf_model: create_directories
#	@echo "Downloading TF model from Zenodo..."
#	@if [ ! -e $(TF_MODEL) ]; then \
#		wget -O $(TF_MODEL) https://zenodo.org/record/3928991/files/224_224_160.pb?download=1; \
#	fi
#
#.PHONY: download_openvino_model
#download_openvino_model: create_directories
#	@echo "Downloading OpenVINO model from Zenodo..."
#	@if [ ! -e $(OPENVINO_MODEL) ]; then \
#		wget -O $(OPENVINO_MODEL) https://zenodo.org/record/3929002/files/brats_model_checkpoint_final_fold1_H224_W224_D160_C4.bin?download=1; \
#	fi
#	@if [ ! -e $(OPENVINO_MODEL_METADATA) ]; then \
#		wget -O $(OPENVINO_MODEL_METADATA) https://zenodo.org/record/3929002/files/brats_model_checkpoint_final_fold1_H224_W224_D160_C4.xml?download=1; \
#	fi
#
#.PHONY: convert_onnx_model
#convert_onnx_model: download_pytorch_model
#	@echo "Converting PyTorch model to ONNX model..."
#	@if [ ! -e $(ONNX_MODEL) ]; then \
#		python3 unet_pytorch_to_onnx.py; \
#	fi
#
#.PHONY: convert_tf_model
#convert_tf_model: convert_onnx_model
#	@echo "Converting ONNX model to TF model..."
#	@if [ ! -e $(TF_MODEL) ]; then \
#		python3 unet_onnx_to_tf.py; \
#	fi
#
#.PHONY: build_docker
#build_docker:
#	@echo "Building docker image..."
#	@docker pull nvcr.io/nvidia/pytorch:20.03-py3
#	@docker build --build-arg GID=$(GROUPID) --build-arg UID=$(UID) --build-arg GROUP=$(GROUPNAME) --build-arg USER=$(UNAME) \
#	--build-arg http_proxy=$(HTTP_PROXY) --build-arg https_proxy=$(HTTPS_PROXY) --build-arg HTTPS_PROXY=$(HTTPS_PROXY) --build-arg HTTP_PROXY=$(HTTP_PROXY) \
#        --build-arg BASE_IMAGE=nvcr.io/nvidia/pytorch:20.03-py3 -t mlperf-inference-3d-unet -f Dockerfile .
#
#.PHONY: launch_docker
#launch_docker: check_download_data_dir
#	@mkdir -p $(POSTPROCESSED_DATA_DIR)
#	@echo "Launching docker container..."
#	@$(DOCKER_RUN_CMD) --rm -it -w $(CONTAINER_VOL) -v $(HOST_VOL):$(CONTAINER_VOL) -v ${HOME}:/mnt/${HOME} \
#		-v $(DOWNLOAD_DATA_DIR):/downloaded_data_dir \
#		--shm-size=1g --ulimit memlock=-1 --ulimit stack=67108864 \
#		-v /etc/timezone:/etc/timezone:ro -v /etc/localtime:/etc/localtime:ro \
#		--security-opt apparmor=unconfined --security-opt seccomp=unconfined \
#		--name mlperf-inference-3d-unet-$(UNAME) -h mlperf-inference-3d-unet-$(UNAME) --add-host mlperf-inference-3d-unet-$(UNAME):127.0.0.1 \
#		--user $(UID):$(GROUPID) --net host --device /dev/fuse --cap-add SYS_ADMIN $(DOCKER_ARGS) mlperf-inference-3d-unet
#
.PHONY: preprocess_data
preprocess_data: create_directories
	@echo "Restructuring raw data to $(RAW_DATA_DIR)..."
	@if [ ! -e $(RAW_DATA_DIR) ]; then \
		mkdir $(RAW_DATA_DIR); \
	fi
	@python3 Task043_BraTS_2019.py --downloaded_data_dir $(DOWNLOAD_DATA_DIR) 
	@echo "Preprocessing and saving preprocessed data to $(PREPROCESSED_DATA_DIR)..."
	@if [ ! -e $(PREPROCESSED_DATA_DIR) ]; then \
		mkdir $(PREPROCESSED_DATA_DIR); \
	fi
	@python3 preprocess.py --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --raw_data_dir $(RAW_DATA_DIR)/nnUNet_raw_data/Task043_BraTS2019/imagesTr --preprocessed_data_dir $(PREPROCESSED_DATA_DIR)

.PHONY: mkdir_postprocessed_data
mkdir_postprocessed_data:
	@if [ ! -e $(POSTPROCESSED_DATA_DIR) ]; then \
		mkdir -p $(POSTPROCESSED_DATA_DIR); \
	fi

.PHONY: run_pytorch_performance
run_pytorch_performance:
	@python3 run.py --backend=pytorch --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHONY: run_pytorch_accuracy
run_pytorch_accuracy: mkdir_postprocessed_data
	@python3 run.py --backend=pytorch --accuracy --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHONY: run_pytorch_performance_fp16
run_pytorch_performance_fp16:
	@python3 run.py --backend=pytorch --run_fp16 --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHONY: run_pytorch_accuracy_fp16
run_pytorch_accuracy_fp16: mkdir_postprocessed_data
	@python3 run.py --backend=pytorch --accuracy --run_fp16 --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHONY: run_pytorch_performance_int8
run_pytorch_performance_int8:
	@python3 run.py --backend pytorch --run_int8 --calib_iters 1 --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHONY: run_pytorch_accuracy_symm_u8
run_pytorch_accuracy_symm_u8: mkdir_postprocessed_data
	@python3 run.py --backend pytorch --accuracy --run_int8 --uint8 --calib_iters 1 --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHONY: run_pytorch_accuracy_symm_s8
run_pytorch_accuracy_symm_s8: mkdir_postprocessed_data
	@python3 run.py --backend pytorch --accuracy --run_int8 --calib_iters 1 --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHYONY: run_pytorch_accuracy_asymm_u8
run_pytorch_accuracy_asymm_u8: mkdir_postprocessed_data
	@python3 run.py --backend pytorch --accuracy --asymm --uint8 --run_int8 --calib_iters 1 --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHYONY: run_pytorch_accuracy_asymm_s8
run_pytorch_accuracy_asymm_s8: mkdir_postprocessed_data
	@python3 run.py --backend pytorch --accuracy --asymm --run_int8 --calib_iters 1 --model_dir $(RESULT_DIR)/nnUNet/3d_fullres/Task043_BraTS2019/nnUNetTrainerV2__nnUNetPlansv2.mlperf.1 --preprocessed_data_dir $(PREPROCESSED_DATA_DIR) --mlperf_conf $(BUILD_DIR)/mlperf.conf --build_dir $(BUILD_DIR)

.PHYONY: run_pytorch_accuracy_int8
run_pytorch_accuracy_int8:
	@$(MAKE) -f $(MAKEFILE_NAME) run_pytorch_accuracy_symm_s8

#.PHONY: run_onnxruntime_performance
#run_onnxruntime_performance:
#	@python3 run.py --backend=onnxruntime --model=build/model/224_224_160.onnx
#
#.PHONY: run_onnxruntime_accuracy
#run_onnxruntime_accuracy: mkdir_postprocessed_data
#	@python3 run.py --backend=onnxruntime --model=build/model/224_224_160.onnx --accuracy
#
#.PHONY: run_tf_performance
#run_tf_performance:
#	@python3 run.py --backend=tf --model=build/model/224_224_160.pb
#
#.PHONY: run_tf_accuracy
#run_tf_accuracy: mkdir_postprocessed_data
#	@python3 run.py --backend=tf --model=build/model/224_224_160.pb --accuracy
#
.PHONY: evaluate
evaluate:
	@python3 accuracy-brats.py

.PHONY: clean
clean:
	@rm -rf build
