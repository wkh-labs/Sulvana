#!/usr/bin/env bash
set -euo pipefail

app=/home/tanchjim/Documents/Codex/ai-workspace
prompt=$(zenity --entry --title='Z-Image Turbo' \
  --text='Describe the image you want to create:' \
  --width=600) || exit 0
if [[ -z "${prompt//[[:space:]]/}" ]]; then
  zenity --warning --title='Z-Image Turbo' --text='Please enter a prompt.'
  exit 0
fi

mkdir -p "$app/runs/z-image"
stamp=$(date +%Y%m%d-%H%M%S)
output="$app/runs/z-image/$stamp.png"
log="$app/runs/z-image/$stamp.log"

if ("$app/z-image.sh" "$prompt" "$output" >"$log" 2>&1; echo 100) | \
  zenity --progress --pulsate --auto-close --no-cancel \
    --title='Z-Image Turbo' --text='Generating your image… This can take several minutes.' \
    --width=480; then
  if [[ -s "$output" ]]; then
    xdg-open "$output" >/dev/null 2>&1 &
    zenity --info --title='Image ready' --text="Saved to:\n$output" --width=500
  else
    zenity --error --title='Generation failed' \
      --text="No image was produced. Details are in:\n$log" --width=500
  fi
else
  zenity --error --title='Generation failed' \
    --text="Details are in:\n$log" --width=500
fi
