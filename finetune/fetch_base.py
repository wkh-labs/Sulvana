#!/usr/bin/env python3
"""Download the pinned trainable Dolphin checkpoint. Without --yes this only prints the plan.

This is the only script in the workflow that may use the network.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

SMALL_FILES = ["config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
               "special_tokens_map.json", "model.safetensors.index.json", "README.md"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.add_argument("--yes", action="store_true", help="actually download (otherwise: dry run)")
    parser.add_argument("--metadata-only", action="store_true", help="only the ~17 MB of config and tokenizer files")
    args = parser.parse_args()
    # Stay offline until the user has confirmed with --yes.
    common.setup_environment(offline=not args.yes)
    config = common.load_config(args.config)
    base = config["base_model"]
    status = common.weights_status(config)
    wanted = SMALL_FILES if args.metadata_only else SMALL_FILES + list(base["weight_files"])
    needed = 0 if args.metadata_only else status["total_bytes"] - status["present_bytes"]
    cache = Path(__import__("os").environ["HF_HOME"]) / "hub"
    free = shutil.disk_usage(cache if cache.exists() else common.WORKSPACE).free

    print(f"Repository : https://huggingface.co/{base['repo_id']}")
    print(f"Revision   : {base['revision']} (pinned)")
    print(f"License    : {base['license']} (Llama 3.1 Community License) - fine-tuned from {base['upstream_base']}")
    print(f"Destination: {cache}")
    for name, item in status["files"].items():
        if not args.metadata_only:
            print(f"  {item['expected_bytes'] / 1e9:6.2f} GB  {name}  {'already complete' if item['complete'] else 'to download'}")
    print("  ~0.02 GB  config, tokenizer and model card files")
    print(f"To download: {needed / 1e9:.2f} GB   |   free disk: {free / 1e9:.0f} GB")
    if needed and free < needed * 1.1:
        raise SystemExit("Not enough free disk space for this download.")
    if not args.yes:
        print("\nDry run: nothing was downloaded. Re-run with --yes to download.")
        return 0

    from huggingface_hub import snapshot_download

    path = snapshot_download(base["repo_id"], revision=base["revision"], allow_patterns=wanted)
    print(f"\nSnapshot: {path}")
    if args.metadata_only:
        return 0
    status = common.weights_status(config)
    if not status["complete"]:
        print("Download finished but these files are incomplete: " + ", ".join(status["missing"]))
        print("Run the same command again; the download resumes.")
        return 1
    print("All weight files are present with the expected sizes. Next: finetune/verify_base.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
