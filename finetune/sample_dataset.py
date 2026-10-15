#!/usr/bin/env python3
"""Take a reproducible random subset of a dataset, keeping each source's share.

Used to fit a fine-tune into a time budget (for example 5 hours) without using every conversation:

    .venv/bin/python finetune/sample_dataset.py datasets/khmer-full/train.jsonl \
        datasets/khmer-mimo/train.jsonl --count 9000

Records are grouped by meta.source; every group keeps its share of the total. The same input,
count and seed always give the same subset. A small manifest is written next to the output.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="input JSONL (the documented dataset format)")
    parser.add_argument("output", help="output JSONL; must be under datasets/")
    parser.add_argument("--count", type=int, required=True, help="number of conversations to keep")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source, output = common.workspace_path(args.source), common.workspace_path(args.output)
    if not output.resolve().is_relative_to((common.WORKSPACE / "datasets").resolve()):
        raise SystemExit("Write datasets under datasets/.")
    records, errors, _warnings = common.read_jsonl(source)
    if errors:
        raise SystemExit(f"{source} is not a valid dataset ({len(errors)} problems); run validate_dataset.py first.")
    if not 1 <= args.count <= len(records):
        raise SystemExit(f"--count must be between 1 and {len(records)}.")

    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["meta"] or {}).get("source", "unknown")].append(record)
    rng = random.Random(args.seed)
    chosen: list[dict] = []
    remaining = args.count
    names = sorted(groups)
    for index, name in enumerate(names):
        share = remaining if index == len(names) - 1 else round(args.count * len(groups[name]) / len(records))
        share = min(share, len(groups[name]), remaining)
        chosen += rng.sample(groups[name], share)
        remaining -= share
    rng.shuffle(chosen)

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        for record in chosen:
            item = {"messages": record["messages"], **({"meta": record["meta"]} if record["meta"] else {})}
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    manifest = {
        "source": str(source), "source_sha256": common.sha256_file(source), "source_conversations": len(records),
        "count": len(chosen), "seed": args.seed, "output_sha256": common.sha256_file(output),
        "by_source": {name: sum(1 for r in chosen if (r["meta"] or {}).get("source", "unknown") == name) for name in names},
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
