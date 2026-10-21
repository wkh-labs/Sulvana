#!/usr/bin/env bash
set -euo pipefail

SULVANA_APP=/home/tanchjim/Documents/Codex/ai-workspace
SULVANA_URL=http://127.0.0.1:8766/api/status
SULVANA_UI="$SULVANA_APP/sulvana-ui"
SULVANA_ELECTRON_APP="$SULVANA_APP/electron-ui"
SULVANA_JAVA="$SULVANA_APP/.runtime/java/bin/java"
SULVANA_JAVAFX="$SULVANA_APP/.runtime/javafx/javafx-sdk-25.0.4/lib"
SULVANA_SOURCE="$SULVANA_APP/java-ui/src/SulvanaDesktop.java"
SULVANA_CLASS="$SULVANA_APP/java-ui/build/SulvanaDesktop.class"

# The window is an Electron (Chromium) shell by default, because the JavaFX WebView cannot
# shape Khmer text. Set SULVANA_SHELL=javafx to use the older JavaFX window instead.
SULVANA_ELECTRON="$(command -v electron || true)"
shell_kind=javafx
if [[ "${SULVANA_SHELL:-electron}" != "javafx" && -n "$SULVANA_ELECTRON" && -f "$SULVANA_ELECTRON_APP/main.js" ]]; then
  shell_kind=electron
fi

if [[ "$shell_kind" == "javafx" ]] && [[ ! -f "$SULVANA_CLASS" || "$SULVANA_SOURCE" -nt "$SULVANA_CLASS" ]]; then
  mkdir -p "$SULVANA_APP/java-ui/build"
  "$SULVANA_APP/.runtime/java/bin/javac" --module-path "$SULVANA_JAVAFX" \
    --add-modules javafx.controls,javafx.web \
    -d "$SULVANA_APP/java-ui/build" "$SULVANA_SOURCE"
fi

# Rebuild the web UI when its sources are newer than the served bundle (development convenience).
if [[ -d "$SULVANA_UI/node_modules" ]] && command -v npm >/dev/null 2>&1; then
  if [[ ! -f "$SULVANA_UI/dist/index.html" || -n "$(find "$SULVANA_UI/src" "$SULVANA_UI/index.html" -newer "$SULVANA_UI/dist/index.html" -print -quit)" ]]; then
    (cd "$SULVANA_UI" && npm run build >/dev/null 2>&1) || echo "Sulvana's interface could not be rebuilt; using the existing build." >&2
  fi
fi

engine_status() { curl --silent --max-time 2 "$SULVANA_URL" 2>/dev/null || true; }

start_engine() {
  if ! systemctl --user is-active --quiet sulvana-web.service; then
    local env_args=()
    for var in SULVANA_BASE SULVANA_CONTEXT SULVANA_GPU_HEADROOM_MB SULVANA_LORA_ADAPTER SULVANA_LORA_SCALE SULVANA_LORA_KHMER SULVANA_LORA_OTHER SULVANA_KHMER_ADAPTER; do
      if [[ -n "${!var:-}" ]]; then
        env_args+=("--setenv=$var=${!var}")
      fi
    done
    systemd-run --user --collect --unit=sulvana-web \
      "${env_args[@]}" \
      "$SULVANA_APP/sulvana-web.sh" >/dev/null
  fi
  for attempt in {1..90}; do
    [[ "$(engine_status)" == *'"state"'* ]] && return 0
    sleep 1
  done
  return 1
}

running_overrides=()
for var in SULVANA_BASE SULVANA_CONTEXT SULVANA_GPU_HEADROOM_MB SULVANA_LORA_ADAPTER SULVANA_LORA_SCALE SULVANA_LORA_KHMER SULVANA_LORA_OTHER SULVANA_KHMER_ADAPTER; do
  [[ -n "${!var:-}" ]] && running_overrides+=("$var")
done
if [[ ${#running_overrides[@]} -gt 0 ]] && systemctl --user is-active --quiet sulvana-web.service; then
  echo "Sulvana's engine is already running, so ${running_overrides[*]} are ignored." >&2
  echo "Run 'systemctl --user stop sulvana-web' first to apply new environment settings." >&2
fi

status="$(engine_status)"
if [[ "$status" != *'"state"'* ]]; then
  start_engine || { echo "Sulvana's local engine could not start." >&2; exit 1; }
  status="$(engine_status)"
fi

# A fatal engine never recovers by itself. Replace the whole service (this also clears any
# leftover model process) instead of opening a window onto a dead engine.
if [[ "$status" == *'"state": "fatal"'* || "$status" == *'"state":"fatal"'* ]]; then
  systemctl --user stop sulvana-web.service 2>/dev/null || true
  start_engine || { echo "Sulvana's local engine could not start." >&2; exit 1; }
fi

window_environment=(
  DISPLAY="${DISPLAY:-:0}" WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"
  XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
  DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/1000/bus}"
)

if [[ "$shell_kind" == "electron" ]]; then
  # First use of this window: carry over the conversations saved by the JavaFX window.
  if [[ ! -d "$SULVANA_APP/.runtime/sulvana-electron" ]]; then
    python3 "$SULVANA_ELECTRON_APP/export_javafx_history.py" >/dev/null 2>&1 || true
  fi
  systemd-run --user --collect --unit="sulvana-window-$$" \
    env "${window_environment[@]}" XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-}" \
    "$SULVANA_ELECTRON" --ozone-platform-hint=auto "$SULVANA_ELECTRON_APP" >/dev/null
else
  systemd-run --user --collect --unit="sulvana-window-$$" \
    env "${window_environment[@]}" \
    "$SULVANA_JAVA" --enable-native-access=javafx.graphics,javafx.web \
      --module-path "$SULVANA_JAVAFX" --add-modules javafx.controls,javafx.web \
      -cp "$SULVANA_APP/java-ui/build" SulvanaDesktop >/dev/null
fi
