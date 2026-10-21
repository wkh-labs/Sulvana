#!/usr/bin/env bash
set -euo pipefail
APP="${SULVANA_APP:-/home/tanchjim/Documents/Codex/ai-workspace}"
cd "$APP"
PYTHON="$APP/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || command -v python)"
fi
exec "$PYTHON" -u "$APP/sulvana_web.py"
