#!/usr/bin/env bash
set -euo pipefail

APP=/home/tanchjim/Documents/Codex/ai-workspace
JAVA="$APP/.runtime/java/bin/java"
JAVAC="$APP/.runtime/java/bin/javac"
JAVAFX="$APP/.runtime/javafx/javafx-sdk-25.0.4/lib"
SOURCE="$APP/java-ui/src/QwenDesktopApp.java"
CLASS="$APP/java-ui/build/QwenDesktopApp.class"

if [[ ! -x "$JAVA" || ! -d "$JAVAFX" ]]; then
  echo "Local Java/JavaFX runtime is missing from $APP/.runtime" >&2
  exit 1
fi

if [[ ! -f "$CLASS" || "$SOURCE" -nt "$CLASS" ]]; then
  mkdir -p "$APP/java-ui/build"
  "$JAVAC" --module-path "$JAVAFX" --add-modules javafx.controls \
    -d "$APP/java-ui/build" "$SOURCE"
fi

exec "$JAVA" --enable-native-access=javafx.graphics -Dfile.encoding=UTF-8 \
  --module-path "$JAVAFX" \
  --add-modules javafx.controls -cp "$APP/java-ui/build" QwenDesktopApp
