#!/usr/bin/env python3
"""Check, offline, that the pinned Hugging Face checkpoint and Sulvana's local GGUF are the same model."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

common.setup_environment(offline=True)

from gguf_meta import read_metadata  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.add_argument("--hash-gguf", action="store_true", help="also SHA-256 the 4.9 GB GGUF and compare it with the config")
    args = parser.parse_args()
    config = common.load_config(args.config)
    base = config["base_model"]
    gguf_path = common.workspace_path(base["local_gguf"])
    if not gguf_path.is_file():
        raise SystemExit(f"Local GGUF not found: {gguf_path}")
    if common.cached_file(config, "config.json") is None or common.cached_file(config, "tokenizer.json") is None:
        raise SystemExit(
            f"The small config/tokenizer files of {base['repo_id']} @ {base['revision'][:12]} are not in the local cache.\n"
            "Run:  .venv/bin/python finetune/fetch_base.py --metadata-only --yes   (about 17 MB)")
    gguf = read_metadata(gguf_path)
    hf = json.loads(common.cached_file(config, "config.json").read_text())
    tokenizer = common.load_tokenizer(config)
    vocabulary = [None] * len(tokenizer)
    for token, index in tokenizer.get_vocab().items():
        vocabulary[index] = token
    gguf_tokens = gguf.get("tokenizer.ggml.tokens", [])
    mismatched = sum(a != b for a, b in zip(gguf_tokens, vocabulary)) + abs(len(gguf_tokens) - len(vocabulary))
    card = common.cached_file(config, "README.md")
    card_text = card.read_text(encoding="utf-8") if card else ""

    rows = [  # (check, value from the GGUF, value from the Hugging Face revision, equal?)
        ("architecture", gguf.get("general.architecture"), hf.get("model_type"), gguf.get("general.architecture") == hf.get("model_type") == "llama"),
        ("layers", gguf.get("llama.block_count"), hf.get("num_hidden_layers"), None),
        ("hidden size", gguf.get("llama.embedding_length"), hf.get("hidden_size"), None),
        ("feed-forward size", gguf.get("llama.feed_forward_length"), hf.get("intermediate_size"), None),
        ("attention heads", gguf.get("llama.attention.head_count"), hf.get("num_attention_heads"), None),
        ("key/value heads", gguf.get("llama.attention.head_count_kv"), hf.get("num_key_value_heads"), None),
        ("vocabulary size", gguf.get("llama.vocab_size"), hf.get("vocab_size"), None),
        ("vocabulary entries", len(gguf_tokens), len(vocabulary), None),
        ("token-by-token mismatches", mismatched, 0, mismatched == 0),
        ("BOS token id", gguf.get("tokenizer.ggml.bos_token_id"), tokenizer.bos_token_id, None),
        ("EOS token id", gguf.get("tokenizer.ggml.eos_token_id"), tokenizer.eos_token_id, None),
        ("PAD token id", gguf.get("tokenizer.ggml.padding_token_id"), tokenizer.pad_token_id, None),
        ("chat template identical", len(gguf.get("tokenizer.chat_template", "")), len(tokenizer.chat_template), gguf.get("tokenizer.chat_template") == tokenizer.chat_template),
        ("license", gguf.get("general.license"), base["license"], gguf.get("general.license") == base["license"] and f"license: {base['license']}" in card_text),
        ("fine-tuned from", gguf.get("general.base_model.0.repo_url"), base["upstream_base"], str(gguf.get("general.base_model.0.repo_url", "")).endswith(base["upstream_base"]) and base["upstream_base"] in card_text),
    ]
    rows = [(name, left, right, left == right if equal is None else equal) for name, left, right, equal in rows]
    if args.hash_gguf:
        started = time.time()
        digest = common.sha256_file(gguf_path)
        rows.append((f"GGUF sha256 ({time.time() - started:.0f}s)", digest[:16] + "…", base["gguf_sha256"][:16] + "…", digest == base["gguf_sha256"]))

    print(f"GGUF        : {gguf_path}  ({gguf.get('general.name')})")
    print(f"Checkpoint  : {base['repo_id']} @ {base['revision']}\n")
    print(f"{'check':28s} {'GGUF':>22s} {'Hugging Face':>24s}   result")
    for name, left, right, passed in rows:
        print(f"{name:28s} {str(left)[-22:]:>22s} {str(right)[-24:]:>24s}   {'PASS' if passed else 'FAIL'}")
    weights = common.weights_status(config)
    print(f"\nTrainable weights in the local cache: {'complete' if weights['complete'] else 'NOT downloaded'} "
          f"({weights['present_bytes'] / 1e9:.2f} of {weights['total_bytes'] / 1e9:.2f} GB)")
    passed = all(row[3] for row in rows)
    report = {
        "passed": passed, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "gguf": {"path": str(gguf_path), "name": gguf.get("general.name"), "bytes": gguf_path.stat().st_size},
        "checkpoint": {"repo_id": base["repo_id"], "revision": base["revision"], "license": base["license"], "upstream_base": base["upstream_base"]},
        "checks": [{"check": name, "gguf": left, "hugging_face": right, "passed": ok} for name, left, right, ok in rows],
        "weights": weights,
    }
    target = common.runs_root(config) / "base-verification.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{'COMPATIBLE' if passed else 'MISMATCH'}: report written to {target}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
