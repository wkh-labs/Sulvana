#!/usr/bin/env bash
set -euo pipefail
APP="${SULVANA_APP:-$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)}"
cd "$APP"
PYTHON="$APP/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || command -v python)"
fi
exec "$PYTHON" -u "$APP/sulvana_web.py"
