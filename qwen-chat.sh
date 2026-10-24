#!/usr/bin/env bash
set -euo pipefail

APP="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
exec "$APP/run-performance.sh" \
  python "$APP/run-qwen-base.py" "$@"
