#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 COMMAND [ARGUMENT ...]" >&2
  exit 2
fi

if [[ "$(cat /sys/class/power_supply/ACAD/online 2>/dev/null || echo 0)" != "1" ]]; then
  echo "Refusing a sustained AI run while the main AC adapter is disconnected." >&2
  exit 1
fi

power_profile() {
  /usr/bin/python3 /usr/bin/powerprofilesctl "$@"
}

previous_profile="$(power_profile get)"
restore_profile() {
  power_profile set "$previous_profile" >/dev/null 2>&1 || true
}
trap restore_profile EXIT INT TERM

power_profile set performance
source "/home/tanchjim/Documents/Codex/ai-workspace/activate-ai.sh"

set +e
"$@"
command_status=$?
set -e

restore_profile
trap - EXIT INT TERM
exit "$command_status"
