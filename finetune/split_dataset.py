#!/usr/bin/env python3
"""Split a validated dataset into train and validation files, deterministically.

Each conversation is assigned by a hash of its content and the seed. Re-running, re-ordering
or appending lines therefore never moves an existing conversation to the other split, and
exact duplicates always land together (no leakage into validation).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

common.setup_environment(offline=True)

from validate_dataset import print_report, validate  # noqa: E402


def rank(messages: list[dict], seed: int) -> float:
    digest = hashlib.sha256(f"{seed}:{common.conversation_key(messages)}".encode()).hexdigest()
    return int(digest[:16], 16) / 16**16


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--min-val", type=int, default=1, help="smallest validation set to accept")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    if not 0 < args.val_fraction < 1:
        raise SystemExit("--val-fraction must be between 0 and 1")
    config = common.load_config(args.config)
    source = Path(args.input).resolve() if Path(args.input).exists() else common.workspace_path(args.input)
    out_dir = Path(args.out_dir).resolve() if Path(args.out_dir).is_absolute() else common.workspace_path(args.out_dir)
    report = validate(source, config)
    if report["errors"]:
        print_report(report)
        raise SystemExit("Refusing to split an invalid dataset.")
    if out_dir.resolve() == source.parent.resolve() and source.name in {"train.jsonl", "val.jsonl"}:
        raise SystemExit("The split would overwrite its own input; choose another --out-dir.")
    records, _, _ = common.read_jsonl(source)
    ranks: dict[str, float] = {}
    for record in records:
        ranks[common.conversation_key(record["messages"])] = rank(record["messages"], args.seed)
    if len(ranks) < 2:
        raise SystemExit("At least two distinct conversations are needed for a train/validation split.")
    validation = {key for key, value in ranks.items() if value < args.val_fraction}
    # Small datasets can hash to an empty (or complete) validation set: move the lowest-ranked ones.
    ordered = sorted(ranks, key=ranks.get)
    wanted = min(max(args.min_val, 1), len(ordered) - 1)
    if len(validation) < wanted:
        validation = set(ordered[:wanted])
    if len(validation) >= len(ordered):
        validation = set(ordered[: len(ordered) - 1])
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = {"train": [], "val": []}
    for record in records:
        row = {"messages": record["messages"]}
        if record.get("meta") is not None:
            row["meta"] = record["meta"]
        parts["val" if common.conversation_key(record["messages"]) in validation else "train"].append(row)
    manifest = {"source": str(source), "source_sha256": report["sha256"], "seed": args.seed, "val_fraction": args.val_fraction,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "files": {}}
    for name, rows in parts.items():
        target = out_dir / f"{name}.jsonl"
        target.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        manifest["files"][name] = {"path": str(target), "conversations": len(rows), "sha256": common.sha256_file(target)}
        print(f"{name:5s} {len(rows):6d} conversations -> {target}")
    (out_dir / "split-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
