#!/usr/bin/env python3
"""Copy the conversations saved by Sulvana's JavaFX window to where the Electron window imports them.

Read-only on the old store. Run by the launcher the first time the Electron window is used.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
OLD = APP / ".runtime" / "sulvana-webview" / "localstorage" / "http_127.0.0.1_8766.localstorage"
NEW = APP / ".runtime" / "sulvana-electron" / "javafx-history.json"
KEY = "sulvana.desktop.v1"


def main() -> int:
    if NEW.exists() or NEW.with_name(NEW.name + ".imported").exists() or not OLD.is_file():
        return 0
    try:
        database = sqlite3.connect(f"file:{OLD}?mode=ro", uri=True)
        row = database.execute("SELECT value FROM ItemTable WHERE key = ?", (KEY,)).fetchone()
        database.close()
    except sqlite3.Error as error:
        print(f"Could not read the previous chat history: {error}", file=sys.stderr)
        return 0
    if not row:
        return 0
    text = row[0].decode("utf-16-le") if isinstance(row[0], bytes) else str(row[0])
    try:
        saved = json.loads(text)
    except json.JSONDecodeError:
        return 0
    NEW.parent.mkdir(parents=True, exist_ok=True)
    NEW.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    print(f"Carried over {len(saved.get('conversations', []))} conversations from the previous window.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
