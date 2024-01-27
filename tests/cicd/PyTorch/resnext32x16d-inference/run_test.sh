#!/bin/bash
set -e

echo "Setup PyTorch Test Enviroment for ResNext32x16d Inference"

PRECISION=$1
SCRIPT=$2
OUTPUT_DIR=${OUTPUT_DIR-"$(pwd)/tests/cicd/output/PyTorch/resnext32x16d-inference/${SCRIPT}/${PRECISION}"}
WORKSPACE=$3
is_lkg_drop=$4
DATASET=$5

# Create the output directory in case it doesn't already exist
mkdir -p ${OUTPUT_DIR}

if [[ "${is_lkg_drop}" == "true" ]]; then
  source ${WORKSPACE}/pytorch_setup/bin/activate pytorch
fi

export LD_PRELOAD="${WORKSPACE}/jemalloc/lib/libjemalloc.so":"${WORKSPACE}/tcmalloc/lib/libtcmalloc.so":"/usr/local/lib/libiomp5.so":$LD_PRELOAD 
export MALLOC_CONF="oversize_threshold:1,background_thread:true,metadata_thp:auto,dirty_decay_ms:9000000000,muzzy_decay_ms:9000000000"
export DNNL_MAX_CPU_ISA=AVX512_CORE_AMX

# Run script
OUTPUT_DIR=${OUTPUT_DIR} DATASET_DIR=${DATASET} PRECISION=${PRECISION} ./quickstart/image_recognition/pytorch/resnext-32x16d/inference/cpu/${SCRIPT}
