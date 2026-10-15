#!/usr/bin/env python3
"""Validate a chat dataset (JSONL) before it is split or used for training."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

common.setup_environment(offline=True)


def validate(path: Path, config: dict, tokenizer=None) -> dict:
    """Return a report with errors, warnings and token statistics for one dataset file."""
    if not path.is_file():
        return {"file": str(path), "errors": [f"file not found: {path}"], "warnings": [], "records": 0}
    records, errors, warnings = common.read_jsonl(path)
    report = {"file": str(path), "sha256": common.sha256_file(path), "records": len(records), "errors": errors, "warnings": warnings}
    if records and not errors:
        tokenizer = tokenizer or common.load_tokenizer(config)
        _, stats = common.build_examples(tokenizer, records, config)
        report["tokens"] = stats
        report["with_system_message"] = sum(record["messages"][0]["role"] == "system" for record in records)
        report["multi_turn"] = sum(sum(m["role"] == "assistant" for m in record["messages"]) > 1 for record in records)
        report["marked_synthetic"] = sum(bool((record.get("meta") or {}).get("synthetic")) for record in records)
        if stats["usable"] == 0:
            errors.append("no example survives tokenisation at this max_seq_length")
        if stats["truncated"]:
            warnings.append(f"{stats['truncated']} conversation(s) exceed {stats['max_seq_length']} tokens and would be truncated")
        dropped = stats["dropped_overlength"] + stats["dropped_no_labels"]
        if dropped:
            warnings.append(f"{dropped} conversation(s) would be dropped (too long, or nothing left to learn from after truncation)")
    return report


def print_report(report: dict, limit: int = 30) -> None:
    print(f"File: {report['file']}")
    for label in ("errors", "warnings"):
        for message in report[label][:limit]:
            print(f"  {label[:-1].upper()}: {message}")
        if len(report[label]) > limit:
            print(f"  … and {len(report[label]) - limit} more {label}")
    print(f"  conversations: {report['records']}   errors: {len(report['errors'])}   warnings: {len(report['warnings'])}")
    if "tokens" in report:
        tokens, lengths = report["tokens"], report["tokens"]["token_length"]
        print(f"  with system message: {report['with_system_message']}   multi-turn: {report['multi_turn']}   marked synthetic: {report['marked_synthetic']}")
        print(f"  token length  min {lengths['min']}  median {lengths['median']}  p90 {lengths['p90']}  p99 {lengths['p99']}  max {lengths['max']}  (limit {tokens['max_seq_length']})")
        print(f"  usable {tokens['usable']}  truncated {tokens['truncated']}  dropped {tokens['dropped_overlength'] + tokens['dropped_no_labels']}  supervised tokens {tokens['supervised_tokens']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--config", default=None)
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args()
    config = common.load_config(args.config, args.set)
    report = validate(common.workspace_path(args.file) if not Path(args.file).exists() else Path(args.file).resolve(), config)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)
    failed = bool(report["errors"]) or (args.strict and bool(report["warnings"]))
    print("INVALID" if failed else "VALID")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
