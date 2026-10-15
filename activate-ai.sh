#!/usr/bin/env bash

AI_WORKSPACE="/home/tanchjim/Documents/Codex/ai-workspace"

source "$AI_WORKSPACE/.venv/bin/activate"

export HF_HOME="$AI_WORKSPACE/.cache/huggingface"
export TORCH_HOME="$AI_WORKSPACE/.cache/torch"
export UV_CACHE_DIR="$AI_WORKSPACE/.uv-cache"
export HF_XET_HIGH_PERFORMANCE=1
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=true
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_MODULE_LOADING=LAZY
export PYTORCH_ALLOC_CONF="expandable_segments:True"

echo "AI environment active: $AI_WORKSPACE"
python --version

