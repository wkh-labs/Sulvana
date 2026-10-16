#!/usr/bin/env python3
"""Build the v2 Khmer training mix for MiMo: quality data only, no machine-translated Alpaca.

Sources (whatever exists when this runs):
  - datasets/khmer-gemini/raw.jsonl     Gemini-written Khmer with worked answers
  - datasets/khmer-cloud/raw.jsonl      the first 20 hand-checked Gemini examples
  - datasets/feedback/corrections.jsonl answers approved or corrected in Sulvana (👍 / ✏️)
  - ALT English–Khmer pairs from datasets/khmer-full/ (human translations), capped so that
    translation is at most about 40% of the mix

Writes datasets/khmer-v2/{train,val}.jsonl and a manifest. Run: .venv/bin/python finetune/mix_khmer_v2.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

DATA = common.WORKSPACE / "datasets"


def load(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records, errors, _ = common.read_jsonl(path)
    if errors:
        print(f"skipping {len(errors)} invalid lines in {path.name}")
    return [{"messages": r["messages"], "meta": r["meta"] or {}} for r in records]


def main() -> int:
    rng = random.Random(42)
    gemini = load(DATA / "khmer-gemini/raw.jsonl") + load(DATA / "khmer-cloud/raw.jsonl")
    feedback = load(DATA / "feedback/corrections.jsonl")
    alt = [r for r in load(DATA / "khmer-full/train.jsonl") if "alt" in r["meta"].get("source", "")]
    quality = gemini + feedback
    if len(quality) < 100:
        raise SystemExit(f"Only {len(quality)} quality examples; generate more Gemini data first.")
    rng.shuffle(gemini)
    held = max(20, len(gemini) // 20)                     # 5% of the Gemini data for validation
    val_quality, train_gemini = gemini[:held], gemini[held:]
    alt_cap = max(400, int(len(train_gemini + feedback) * 0.67))   # translation <= ~40% of training
    rng.shuffle(alt)
    train = train_gemini + feedback * 2 + alt[:alt_cap]   # human corrections count double
    val = val_quality + alt[alt_cap:alt_cap + max(10, held // 3)]
    rng.shuffle(train)
    out = DATA / "khmer-v2"
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("val", val)):
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps({"messages": row["messages"], "meta": row["meta"]}, ensure_ascii=False) + "\n")
    manifest = {"train": len(train), "val": len(val), "gemini": len(train_gemini), "gemini_val": held,
                "feedback": len(feedback), "alt": min(alt_cap, len(alt)), "seed": 42}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
