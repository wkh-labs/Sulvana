#!/usr/bin/env python3
"""Convert common dataset shapes into the chat JSONL format this pipeline trains on.

  alpaca    {"instruction": ..., "input": ..., "output": ...}        (JSON array or JSONL)
  sharegpt  {"conversations": [{"from": "human"|"gpt"|"system", "value": ...}, ...]}
  pairs     translation pairs, e.g. {"en": ..., "km": ...} or a two-column TSV

Records that break the format rules are skipped and counted, never repaired silently.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

SHAREGPT_ROLES = {"human": "user", "user": "user", "gpt": "assistant", "assistant": "assistant", "system": "system"}
# Khmer-first translation prompts: "Please translate into Khmer:" / "Please translate into English:"
TO_KHMER, TO_ENGLISH = "សូមបកប្រែជាភាសាខ្មែរ៖ {text}", "សូមបកប្រែជាភាសាអង់គ្លេស៖ {text}"


def load_rows(path: Path) -> list:
    if path.suffix.lower() in {".tsv", ".csv"}:
        with open(path, newline="", encoding="utf-8") as handle:
            return list(csv.reader(handle, delimiter="\t" if path.suffix.lower() == ".tsv" else ","))
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    if text.lstrip().startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def clean(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def convert(row, args) -> list[list[dict]]:
    """One source row -> zero or more conversations."""
    if args.format == "alpaca":
        question = clean(row.get("instruction"))
        if clean(row.get("input")):
            question += "\n\n" + clean(row.get("input"))
        return [[{"role": "user", "content": question}, {"role": "assistant", "content": clean(row.get("output"))}]]
    if args.format == "sharegpt":
        turns = row.get("conversations") or row.get("messages") or []
        return [[{"role": SHAREGPT_ROLES.get(turn.get("from") or turn.get("role"), "?"), "content": clean(turn.get("value") or turn.get("content"))} for turn in turns]]
    english, khmer = (clean(row[0]), clean(row[1])) if isinstance(row, list) else (clean(row.get(args.english_key)), clean(row.get(args.khmer_key)))
    made = []
    if args.direction in {"to-khmer", "both"}:
        made.append([{"role": "user", "content": TO_KHMER.format(text=english)}, {"role": "assistant", "content": khmer}])
    if args.direction in {"to-english", "both"}:
        made.append([{"role": "user", "content": TO_ENGLISH.format(text=khmer)}, {"role": "assistant", "content": english}])
    return made


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True, help="chat JSONL to write, e.g. datasets/khmer/all.jsonl")
    parser.add_argument("--format", required=True, choices=["alpaca", "sharegpt", "pairs"])
    parser.add_argument("--english-key", default="en")
    parser.add_argument("--khmer-key", default="km")
    parser.add_argument("--direction", default="both", choices=["to-khmer", "to-english", "both"], help="for --format pairs")
    parser.add_argument("--system-prompt-file", default=None, help="prepend this text as the system message of every conversation")
    parser.add_argument("--source-name", default=None, help='recorded in each record\'s "meta" (where the data came from)')
    parser.add_argument("--max-records", type=int, default=None)
    args = parser.parse_args()
    source, target = common.workspace_path(args.input), common.workspace_path(args.output)
    if target.resolve() == source.resolve():
        raise SystemExit("--output must not be the input file")
    system = common.workspace_path(args.system_prompt_file).read_text(encoding="utf-8").strip() if args.system_prompt_file else ""
    written, skipped, seen, reasons = 0, 0, set(), {}
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        for row in load_rows(source):
            try:
                conversations = convert(row, args)
            except (AttributeError, IndexError, TypeError):
                conversations = [[]]
            for messages in conversations:
                if system and messages and messages[0]["role"] != "system":
                    messages = [{"role": "system", "content": system}, *messages]
                problems = common.check_messages(messages)
                key = common.conversation_key(messages) if not problems else None
                if problems or key in seen:
                    skipped += 1
                    reason = "duplicate" if not problems else problems[0].split(" has ")[-1].split(": ")[-1]
                    reasons[reason] = reasons.get(reason, 0) + 1
                    continue
                seen.add(key)
                record = {"messages": messages}
                if args.source_name:
                    record["meta"] = {"source": args.source_name}
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
                if args.max_records and written >= args.max_records:
                    break
            if args.max_records and written >= args.max_records:
                break
    print(f"wrote {written} conversations to {target}; skipped {skipped}")
    for reason, count in sorted(reasons.items(), key=lambda item: -item[1])[:8]:
        print(f"  skipped {count}: {reason}")
    print(f"next: .venv/bin/python finetune/validate_dataset.py {args.output}")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
