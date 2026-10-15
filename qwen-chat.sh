#!/usr/bin/env bash
set -euo pipefail

exec /home/tanchjim/Documents/Codex/ai-workspace/run-performance.sh \
  python /home/tanchjim/Documents/Codex/ai-workspace/run-qwen-base.py "$@"
