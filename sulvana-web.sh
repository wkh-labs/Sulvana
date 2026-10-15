#!/usr/bin/env bash
set -euo pipefail
APP=/home/tanchjim/Documents/Codex/ai-workspace
cd "$APP"
exec python -u "$APP/sulvana_web.py"
