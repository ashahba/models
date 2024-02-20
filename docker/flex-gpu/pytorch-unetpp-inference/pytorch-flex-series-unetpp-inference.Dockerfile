# Copyright (c) 2023 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ARG PYT_BASE_IMAGE="intel/intel-extension-for-pytorch"
ARG PYT_BASE_TAG="2.1.10-xpu-pip-base"

FROM ${PYT_BASE_IMAGE}:${PYT_BASE_TAG}

WORKDIR /workspace/pytorch-flex-series-unetpp-inference/models

ENV DEBIAN_FRONTEND=noninteractive

COPY models_v2/pytorch/unetpp/inference/gpu .
COPY models_v2/common common

RUN python -m pip install -r requirements.txt 

RUN python -m pip install pretrainedmodels==0.7.4 \
        efficientnet-pytorch==0.7.1 \
        timm==0.4.12 \
        segmentation-models-pytorch 

COPY LICENSE license/LICENSE
COPY third_party license/third_party
