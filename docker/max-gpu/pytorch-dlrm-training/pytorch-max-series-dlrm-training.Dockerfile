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
ARG PYT_BASE_TAG="2.1.10-xpu"

FROM ${PYT_BASE_IMAGE}:${PYT_BASE_TAG}

USER root

WORKDIR /workspace/pytorch-max-series-dlrm-training
    
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        numactl \
        intel-oneapi-ccl=2021.11.2-5 \
        intel-oneapi-mpi-devel=2021.11.0-49493 && \
    rm -rf /var/lib/apt/lists/*

COPY models/recommendation/pytorch/torchrec_dlrm/training/gpu models/recommendation/pytorch/torchrec_dlrm/training/gpu
COPY quickstart/recommendation/pytorch/torchrec_dlrm/training/gpu/multi_card_distributed_train.sh quickstart/multi_card_distributed_train.sh 

RUN cd models/recommendation/pytorch/torchrec_dlrm/training/gpu && \
    pip install -r requirements.txt && \
    cd -
RUN pip install -e git+https://github.com/mlperf/logging#egg=mlperf-logging

COPY LICENSE licenses/LICENSE
COPY third_party licenses/third_party

ENV LD_LIBRARY_PATH=/opt/intel/oneapi/ccl/2021.11/lib/:/opt/intel/oneapi/mpi/2021.11/opt/mpi/libfabric/lib:/opt/intel/oneapi/mpi/2021.11/lib:$LD_LIBRARY_PATH
ENV LIBRARY_PATH=/opt/intel/oneapi/mpi/2021.11/lib:/opt/intel/oneapi/ccl/2021.11/lib/
ENV PATH=/opt/intel/oneapi/mpi/2021.11/opt/mpi/libfabric/bin:/opt/intel/oneapi/mpi/2021.11/bin:$PATH
ENV CCL_ROOT=/opt/intel/oneapi/ccl/2021.11
ENV I_MPI_ROOT=/opt/intel/oneapi/mpi/2021.11
ENV FI_PROVIDER_PATH=/opt/intel/oneapi/mpi/2021.11/opt/mpi/libfabric/lib/prov:/usr/lib/x86_64-linux-gnu/libfabric

USER $USER