#!/usr/bin/env bash
# share-logs.sh — watch the shared Sulvana live: every request (yours marked "local", your friends' marked
# "friend" with their IP address and country) and the Cloudflare tunnel's own messages.
#   ./share-logs.sh          requests and tunnel events (the app's status checks every few seconds are hidden)
#   ./share-logs.sh --all    everything, including the status checks
# Chat text is never logged, only its size and settings. Press Ctrl+C to stop watching (sharing keeps running).
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
FILTER='GET /api/status'
[[ "${1:-}" == "--all" ]] && FILTER='^$'
echo "Sharing: $(systemctl --user is-active sulvana-share 2>/dev/null)   Engine: $(systemctl --user is-active sulvana-web 2>/dev/null)"
echo "Link: $(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' .runtime/tunnel.log 2>/dev/null | head -1)"
echo "------------------------------------------------------------------------"
trap 'kill $(jobs -p) 2>/dev/null' INT TERM EXIT
journalctl --user -f -n 40 -o cat -u sulvana-web | grep --line-buffered -v -E "$FILTER" &
tail -n 5 -F .runtime/tunnel.log 2>/dev/null | grep --line-buffered -E "ERR|WRN|Registered|Unregistered|trycloudflare" \
  | sed -u 's/^/[tunnel] /' &
wait
