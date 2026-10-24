#!/usr/bin/env bash
set -euo pipefail

# Compatibility name retained for the command used during base-model testing.
exec "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/qwen-chat.sh" "$@"
