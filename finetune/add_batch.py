#!/usr/bin/env python3
"""Accept a batch of hand-made or agent-made Khmer examples into datasets/khmer-gemini/raw.jsonl.

    .venv/bin/python finetune/add_batch.py datasets/khmer-gemini/batch.jsonl

The batch is JSON Lines, one example per line:
    {"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}],"meta":{"task":"cambodia_fact"}}

Every example goes through the same quality filters as finetune/generate_gemini.py (format, Khmer script,
no Thai/Lao, final-answer line for maths and logic, length, repetition, duplicates). Accepted examples
are appended to raw.jsonl, rejected ones to rejected.jsonl with the reason. The batch file is then emptied.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_gemini as gen  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    batch = Path(sys.argv[1])
    gen.OUT.mkdir(parents=True, exist_ok=True)
    raw, rejected = gen.OUT / "raw.jsonl", gen.OUT / "rejected.jsonl"
    seen = set()
    if raw.exists():
        for line in raw.read_text(encoding="utf-8").splitlines():
            seen.add(re.sub(r"\s+", "", json.loads(line)["messages"][0]["content"])[:200])
    kept = dropped = 0
    with open(raw, "a", encoding="utf-8") as good, open(rejected, "a", encoding="utf-8") as bad:
        for number, line in enumerate(batch.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                messages = item["messages"]
                user, answer = messages[0]["content"], messages[-1]["content"]
                task = str((item.get("meta") or {}).get("task", "conversation"))
            except (ValueError, KeyError, IndexError, TypeError):
                print(f"line {number}: not a valid example (expected the documented JSON format)")
                dropped += 1
                continue
            if len(messages) != 2 or messages[0].get("role") != "user" or messages[-1].get("role") != "assistant":
                reasons = ["must be exactly one user message then one assistant message"]
            else:
                reasons = gen.problems(user, answer, task, seen)
            record = {"messages": [{"role": "user", "content": user.strip()}, {"role": "assistant", "content": answer.strip()}],
                      "meta": {"source": "gemini:antigravity", "task": task, "synthetic": True}}
            if reasons:
                bad.write(json.dumps({**record, "rejected": reasons}, ensure_ascii=False) + "\n")
                print(f"line {number}: rejected ({'; '.join(reasons)})")
                dropped += 1
                continue
            good.write(json.dumps(record, ensure_ascii=False) + "\n")
            seen.add(re.sub(r"\s+", "", user)[:200])
            kept += 1
    batch.write_text("", encoding="utf-8")
    total = sum(1 for _ in raw.open(encoding="utf-8"))
    print(f"accepted {kept}, rejected {dropped}; raw.jsonl now has {total} examples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
