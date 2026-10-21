#!/usr/bin/env bash
# share.sh — Share Sulvana AI with your friend on Vercel while running on your laptop GPU
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

RUNTIME_DIR="$APP_DIR/.runtime"
BIN_DIR="$RUNTIME_DIR/bin"
CLOUDFLARED="$BIN_DIR/cloudflared"
TUNNEL_LOG="$RUNTIME_DIR/tunnel.log"
VERCEL_FILE="$RUNTIME_DIR/vercel-url.txt"
WEB_LOG="$RUNTIME_DIR/sulvana-web.log"

mkdir -p "$BIN_DIR"

# 1. Ensure Cloudflare Tunnel binary is available
if [[ ! -x "$CLOUDFLARED" ]]; then
  echo "Downloading Cloudflare quick-tunnel client (cloudflared)..."
  curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o "$CLOUDFLARED"
  chmod +x "$CLOUDFLARED"
fi

# 2. Retrieve secure remote access key
KEY=$(python3 -c "import sys; sys.path.insert(0, '$APP_DIR'); import sulvana_web; print(sulvana_web.get_remote_key())")
if [[ -z "$KEY" ]]; then
  echo "Error: Failed to generate or retrieve Sulvana remote access key."
  exit 1
fi

# 3. Handle Vercel URL
VERCEL_URL="${VERCEL_URL:-}"
if [[ $# -ge 1 && "$1" =~ ^https?:// ]]; then
  VERCEL_URL="$1"
  echo "$VERCEL_URL" > "$VERCEL_FILE"
elif [[ -z "$VERCEL_URL" && -f "$VERCEL_FILE" ]]; then
  VERCEL_URL="$(cat "$VERCEL_FILE" | tr -d ' \r\n')"
fi

# 4. Check if Sulvana Web server is running locally on port 8766
STARTED_WEB=0
if ! curl -s --max-time 1 http://127.0.0.1:8766/api/status >/dev/null 2>&1; then
  echo "Sulvana web server is not running. Starting it now..."
  ./sulvana-web.sh > "$WEB_LOG" 2>&1 &
  WEB_PID=$!
  STARTED_WEB=1
  for i in {1..30}; do
    if curl -s --max-time 1 http://127.0.0.1:8766/api/status >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
  if ! curl -s --max-time 1 http://127.0.0.1:8766/api/status >/dev/null 2>&1; then
    echo "Error: Sulvana web server failed to start. Check $WEB_LOG for details."
    exit 1
  fi
fi

# 5. Start Cloudflare Tunnel
echo "Opening Cloudflare tunnel to local port 8766..."
rm -f "$TUNNEL_LOG"
"$CLOUDFLARED" tunnel --protocol http2 --url http://127.0.0.1:8766 > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

CLEANED=0
cleanup() {
  if [[ "$CLEANED" -eq 1 ]]; then
    return
  fi
  CLEANED=1
  echo ""
  echo "Closing tunnel..."
  kill "$TUNNEL_PID" 2>/dev/null || true
  wait "$TUNNEL_PID" 2>/dev/null || true
  if [[ "$STARTED_WEB" -eq 1 && -n "${WEB_PID:-}" ]]; then
    echo "Stopping background web server..."
    kill "$WEB_PID" 2>/dev/null || true
  fi
  echo "Remote access disconnected."
}
trap cleanup INT TERM EXIT

# Wait for tunnel URL
TUNNEL_URL=""
for i in {1..50}; do
  if [[ -f "$TUNNEL_LOG" ]]; then
    TUNNEL_URL="$(grep -o -E 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -n 1 || true)"
    if [[ -n "$TUNNEL_URL" ]]; then
      break
    fi
  fi
  sleep 0.5
done

if [[ -z "$TUNNEL_URL" ]]; then
  echo "Error: Failed to obtain Cloudflare tunnel URL. Log output:"
  cat "$TUNNEL_LOG" 2>/dev/null || true
  exit 1
fi

echo ""
echo "========================================================================"
echo "               SULVANA AI — LAPTOP SHARING ACTIVE                       "
echo "========================================================================"
echo ""
echo "  [GPU Engine] Running locally on RTX 5070 (port 8766)"
echo "  [Tunnel URL] $TUNNEL_URL"
echo "  [Access Key] $KEY"
echo ""

if [[ -n "$VERCEL_URL" ]]; then
  CLEAN_VERCEL="${VERCEL_URL%/}"
  INVITE_LINK="${CLEAN_VERCEL}/?tunnel=${TUNNEL_URL}&key=${KEY}"
  echo "  ----------------------------------------------------------------------"
  echo "  FRIEND INVITE LINK (Send this to your friend):"
  echo ""
  echo "  $INVITE_LINK"
  echo ""
  if command -v qrencode >/dev/null 2>&1; then
    echo "  Scan QR code with your phone camera to open:"
    echo ""
    qrencode -t ANSIUTF8 "$INVITE_LINK"
    echo ""
  fi
  echo "  (Your friend opens this link in their browser on phone/laptop."
  echo "   It connects directly to your GPU without needing any setup!)"
  echo "  ----------------------------------------------------------------------"
else
  INVITE_PARAM="?tunnel=${TUNNEL_URL}&key=${KEY}"
  echo "  ----------------------------------------------------------------------"
  echo "  FRIEND INVITE PARAMETERS:"
  echo ""
  echo "  https://<your-vercel-app>.vercel.app/$INVITE_PARAM"
  echo ""
  echo "  Tip: Next time, pass your Vercel URL to generate the link automatically:"
  echo "       ./share.sh https://<your-vercel-app>.vercel.app"
  echo "  ----------------------------------------------------------------------"
fi

echo ""
echo "  Security Protections:"
echo "  • Only requests with the Access Key can reach your GPU."
echo "  • Coding mode and bash commands are strictly blocked for remote users."
echo "  • Your files and system settings are completely safe."
echo ""
echo "  Keep this terminal window open while your friend is chatting."
echo "  Press Ctrl+C at any time to close the tunnel and disconnect access."
echo "========================================================================"
echo ""

# Keep running until user terminates
wait "$TUNNEL_PID"
