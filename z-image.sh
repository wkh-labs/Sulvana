#!/usr/bin/env bash
set -euo pipefail

app=/home/tanchjim/Documents/Codex/ai-workspace
model_dir="$app/models/Z-Image-Turbo"
runner="$app/z-image-runner/sd-cli"
prompt=${1:-}
if [[ -z "$prompt" ]]; then
  echo 'Usage: z-image.sh "Describe the image you want" [output.png]' >&2
  exit 2
fi
if [[ ! -x "$runner" ]]; then
  echo "Image runner not found: $runner" >&2
  exit 1
fi

denoiser="$model_dir/z-image-turbo-Q4_K_M.gguf"
encoder="$model_dir/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
vae="$model_dir/vae.safetensors"
for spec in \
  "$denoiser:5017613376" \
  "$encoder:2497281120" \
  "$vae:167666902"; do
  file=${spec%:*}
  expected=${spec##*:}
  if [[ ! -f "$file" ]] || (( $(stat -c %s "$file") != expected )); then
    echo "Missing or incomplete model file: $file" >&2
    exit 1
  fi
done

mkdir -p "$app/runs/z-image"
output=${2:-"$app/runs/z-image/$(date +%Y%m%d-%H%M%S).png"}
width=${Z_WIDTH:-768}
height=${Z_HEIGHT:-768}

exec "$runner" \
  --diffusion-model "$denoiser" \
  --llm "$encoder" \
  --vae "$vae" \
  --backend 'diffusion=vulkan0,te=cpu,vae=cpu' \
  --offload-to-cpu \
  --diffusion-fa \
  --vae-tiling \
  --steps 9 \
  --cfg-scale 1 \
  --sampling-method euler \
  --seed -1 \
  --width "$width" \
  --height "$height" \
  --prompt "$prompt" \
  --output "$output"
