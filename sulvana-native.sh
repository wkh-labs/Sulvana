#!/usr/bin/env bash
# Starts Sulvana: the local engine (sulvana_web.py) if it is not running yet, then the app window.
#   sulvana          open Sulvana
#   sulvana stop     stop the engine and free the GPU memory it holds
set -euo pipefail

SULVANA_APP="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
SULVANA_ORIGIN=http://127.0.0.1:8766
SULVANA_URL="$SULVANA_ORIGIN/api/status"
SULVANA_UI="$SULVANA_APP/sulvana-ui"
SULVANA_ELECTRON_APP="$SULVANA_APP/electron-ui"
SULVANA_JAVA="$SULVANA_APP/.runtime/java/bin/java"
SULVANA_JAVAFX="$SULVANA_APP/.runtime/javafx/javafx-sdk-25.0.4/lib"
SULVANA_SOURCE="$SULVANA_APP/java-ui/src/SulvanaDesktop.java"
SULVANA_CLASS="$SULVANA_APP/java-ui/build/SulvanaDesktop.class"
PID_FILE="$SULVANA_APP/.runtime/sulvana-web.pid"
ENGINE_VARS=(SULVANA_BASE SULVANA_CONTEXT SULVANA_GPU_HEADROOM_MB SULVANA_LORA_ADAPTER SULVANA_LORA_SCALE SULVANA_LORA_KHMER SULVANA_LORA_OTHER SULVANA_KHMER_ADAPTER)

# systemd user services keep the engine running after this script exits; without them (some
# distributions, containers, WSL) the engine is started in the background instead.
use_systemd() { command -v systemd-run >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; }
engine_status() { curl --silent --max-time 2 "$SULVANA_URL" 2>/dev/null || true; }
engine_running() {
  if use_systemd && systemctl --user is-active --quiet sulvana-web.service; then return 0; fi
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

stop_engine() {
  if use_systemd; then systemctl --user stop sulvana-web.service 2>/dev/null || true; fi
  if [[ -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
}

if [[ "${1:-}" == "stop" ]]; then
  stop_engine
  echo "Sulvana's engine is stopped and its GPU memory is free. Run 'sulvana' to start it again."
  exit 0
fi

# The window: Electron (Chromium) when it is available, otherwise a Chromium-family browser in app
# mode, otherwise the default browser. The older JavaFX window cannot shape Khmer text, so it is
# only used when asked for with SULVANA_SHELL=javafx.
SULVANA_ELECTRON="$(command -v electron || true)"
[[ -z "$SULVANA_ELECTRON" && -x "$SULVANA_ELECTRON_APP/node_modules/.bin/electron" ]] && SULVANA_ELECTRON="$SULVANA_ELECTRON_APP/node_modules/.bin/electron"
case "${SULVANA_SHELL:-auto}" in
  javafx) shell_kind=javafx ;;
  browser) shell_kind=browser ;;
  *) if [[ -n "$SULVANA_ELECTRON" && -f "$SULVANA_ELECTRON_APP/main.js" ]]; then shell_kind=electron; else shell_kind=browser; fi ;;
esac

if [[ "$shell_kind" == "javafx" ]]; then
  if [[ ! -x "$SULVANA_JAVA" ]]; then
    echo "SULVANA_SHELL=javafx needs the Java runtime in .runtime/java; opening Sulvana in the browser instead." >&2
    shell_kind=browser
  elif [[ ! -f "$SULVANA_CLASS" || "$SULVANA_SOURCE" -nt "$SULVANA_CLASS" ]]; then
    mkdir -p "$SULVANA_APP/java-ui/build"
    "$SULVANA_APP/.runtime/java/bin/javac" --module-path "$SULVANA_JAVAFX" \
      --add-modules javafx.controls,javafx.web \
      -d "$SULVANA_APP/java-ui/build" "$SULVANA_SOURCE"
  fi
fi

# Rebuild the web UI when its sources are newer than the served bundle (development convenience).
if [[ -d "$SULVANA_UI/node_modules" ]] && command -v npm >/dev/null 2>&1; then
  if [[ ! -f "$SULVANA_UI/dist/index.html" || -n "$(find "$SULVANA_UI/src" "$SULVANA_UI/index.html" -newer "$SULVANA_UI/dist/index.html" -print -quit)" ]]; then
    (cd "$SULVANA_UI" && npm run build >/dev/null 2>&1) || echo "Sulvana's interface could not be rebuilt; using the existing build." >&2
  fi
fi
if [[ ! -f "$SULVANA_UI/dist/index.html" ]]; then
  echo "Sulvana's interface has not been built yet. Run ./install.sh in $SULVANA_APP first." >&2
  exit 1
fi

start_engine() {
  if ! engine_running; then
    mkdir -p "$SULVANA_APP/.runtime"
    if use_systemd; then
      local env_args=()
      for var in "${ENGINE_VARS[@]}"; do
        if [[ -n "${!var:-}" ]]; then
          env_args+=("--setenv=$var=${!var}")
        fi
      done
      systemd-run --user --collect --unit=sulvana-web \
        "${env_args[@]}" \
        "$SULVANA_APP/sulvana-web.sh" >/dev/null
    else
      setsid nohup "$SULVANA_APP/sulvana-web.sh" >"$SULVANA_APP/.runtime/sulvana-web.log" 2>&1 < /dev/null &
      echo $! > "$PID_FILE"
    fi
  fi
  for attempt in {1..90}; do
    [[ "$(engine_status)" == *'"state"'* ]] && return 0
    sleep 1
  done
  return 1
}

running_overrides=()
for var in "${ENGINE_VARS[@]}"; do
  [[ -n "${!var:-}" ]] && running_overrides+=("$var")
done
if [[ ${#running_overrides[@]} -gt 0 ]] && engine_running; then
  echo "Sulvana's engine is already running, so ${running_overrides[*]} are ignored." >&2
  echo "Run 'sulvana stop' first to apply new environment settings." >&2
fi

status="$(engine_status)"
if [[ "$status" != *'"state"'* ]]; then
  start_engine || { echo "Sulvana's local engine could not start. Run ./install.sh --check in $SULVANA_APP to see what is missing." >&2; exit 1; }
  status="$(engine_status)"
fi

# A fatal engine never recovers by itself. Replace the whole service (this also clears any
# leftover model process) instead of opening a window onto a dead engine.
if [[ "$status" == *'"state": "fatal"'* || "$status" == *'"state":"fatal"'* ]]; then
  stop_engine
  start_engine || { echo "Sulvana's local engine could not start." >&2; exit 1; }
fi

uid="$(id -u)"
window_environment=(
  DISPLAY="${DISPLAY:-:0}" WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"
  XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$uid}"
  DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$uid/bus}"
  XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-}"
)

# Start the window detached, so closing the terminal does not close Sulvana.
launch() {
  if use_systemd; then
    systemd-run --user --collect --unit="sulvana-window-$$" env "${window_environment[@]}" "$@" >/dev/null
  else
    setsid nohup env "${window_environment[@]}" "$@" >/dev/null 2>&1 < /dev/null &
  fi
}

case "$shell_kind" in
  electron)
    # First use of this window: carry over the conversations saved by the JavaFX window.
    if [[ ! -d "$SULVANA_APP/.runtime/sulvana-electron" && -d "$SULVANA_APP/.runtime/java" ]]; then
      python3 "$SULVANA_ELECTRON_APP/export_javafx_history.py" >/dev/null 2>&1 || true
    fi
    launch "$SULVANA_ELECTRON" --ozone-platform-hint=auto "$SULVANA_ELECTRON_APP"
    ;;
  javafx)
    launch "$SULVANA_JAVA" --enable-native-access=javafx.graphics,javafx.web \
      --module-path "$SULVANA_JAVAFX" --add-modules javafx.controls,javafx.web \
      -cp "$SULVANA_APP/java-ui/build" SulvanaDesktop
    ;;
  *)
    for browser in chromium chromium-browser google-chrome-stable google-chrome brave-browser brave microsoft-edge-stable vivaldi-stable; do
      if command -v "$browser" >/dev/null 2>&1; then
        launch "$browser" --app="$SULVANA_ORIGIN/" --class=Sulvana
        exit 0
      fi
    done
    if command -v xdg-open >/dev/null 2>&1; then
      launch xdg-open "$SULVANA_ORIGIN/"
    else
      echo "Sulvana is running. Open $SULVANA_ORIGIN in your browser."
    fi
    ;;
esac
