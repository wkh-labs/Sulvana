#!/usr/bin/env python3
"""Compare the original base checkpoint with the same checkpoint plus a trained adapter.

Loads the base once, then measures both on the validation file: loss and perplexity over
assistant tokens, and side-by-side greedy answers for a few validation prompts.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

common.setup_environment(offline=True)

from train import SMOKE_BANNER, dataset_entry, preflight, write_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--config", default=None, help="only used to locate the runs folder; settings come from the run itself")
    parser.add_argument("--val-file", default=None, help="default: the validation file the run was trained with")
    parser.add_argument("--samples", type=int, default=5, help="validation prompts to answer with both models")
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--force", action="store_true", help="skip the free-VRAM check")
    args = parser.parse_args()

    run_dir = common.run_directory(common.load_config(args.config), args.run_name)
    adapter_dir = run_dir / "adapter"
    if not (run_dir / "run.json").is_file() or not (adapter_dir / "adapter_config.json").is_file():
        raise SystemExit(f"No finished adapter in {run_dir}. Train (or resume) the run first.")
    manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    session = manifest["sessions"][-1]
    config, smoke = session["config"], bool(manifest.get("smoke"))
    lineage = json.loads((adapter_dir / "LINEAGE.json").read_text(encoding="utf-8"))
    for key in ("repo_id", "revision"):
        if lineage["base_model"][key] != config["base_model"][key]:
            raise SystemExit("The adapter was trained from a different base checkpoint than this run's config names; refusing to compare.")
    val_file = args.val_file or (session["data"].get("val") or {}).get("path")
    if not val_file:
        raise SystemExit("This run has no validation file; pass --val-file.")
    if not smoke:
        preflight(config, args.force)
    else:
        print(SMOKE_BANNER)

    import torch
    from peft import PeftModel

    tokenizer = common.load_tokenizer(config)
    val_path = common.workspace_path(val_file)
    examples, val_info = dataset_entry(val_path, config, tokenizer)
    records, _, _ = common.read_jsonl(val_path)
    model, load_info = common.load_base(config, tokenizer, smoke)
    model = PeftModel.from_pretrained(model, str(adapter_dir))
    model.eval()
    model.config.use_cache = True
    on_gpu = torch.cuda.is_available()
    device = torch.device("cuda:0" if on_gpu else "cpu")
    collate = common.Collator(tokenizer.pad_token_id)
    stops = sorted({tokenizer.eos_token_id, *([model.config.eos_token_id] if isinstance(model.config.eos_token_id, int) else model.config.eos_token_id or [])})

    def measure() -> dict:
        loss_sum, tokens = 0.0, 0
        for example in examples:
            batch = {key: value.to(device) for key, value in collate([example]).items()}
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=on_gpu):
                total, count = common.supervised_loss(model, batch, reduction="sum")
            loss_sum, tokens = loss_sum + float(total), tokens + count
        mean = loss_sum / max(1, tokens)
        return {"loss": round(mean, 5), "perplexity": round(math.exp(min(mean, 50)), 3), "supervised_tokens": tokens, "conversations": len(examples)}

    def answer(messages: list[dict]) -> str:
        prompt = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True,
                                               **(config["data"].get("chat_template_kwargs") or {}))
        encoded = tokenizer(prompt, add_special_tokens=True, return_tensors="pt").to(device)
        if tokenizer.bos_token_id is not None and int((encoded["input_ids"] == tokenizer.bos_token_id).sum()) != 1:
            raise ValueError("Expected exactly one BOS token in the generation prompt.")
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=on_gpu):
            output = model.generate(**encoded, max_new_tokens=args.max_new_tokens, do_sample=False, temperature=None, top_p=None,
                                    eos_token_id=stops, pad_token_id=tokenizer.pad_token_id)
        return tokenizer.decode(output[0][encoded["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    chosen = [common.with_system_prompt(record["messages"], config) for record in records[: max(0, args.samples)]]
    started = time.perf_counter()
    with model.disable_adapter():
        base_metrics = measure()
        base_answers = [answer(messages) for messages in chosen]
    tuned_metrics = measure()
    tuned_answers = [answer(messages) for messages in chosen]

    result = {
        "run_name": args.run_name, "smoke_test": smoke, "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_model": manifest["base_model"], "adapter": str(adapter_dir), "validation": val_info,
        "base": base_metrics, "with_adapter": tuned_metrics,
        "loss_change": round(tuned_metrics["loss"] - base_metrics["loss"], 5),
        "seconds": round(time.perf_counter() - started, 1), "model_load": load_info,
        "vram_peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3) if on_gpu else None,
    }
    (run_dir / "eval.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f"# Evaluation samples: {args.run_name}", ""]
    if smoke:
        lines += ["**Pipeline smoke test on a random tiny model: the text below is expected to be gibberish.**", ""]
    lines += [f"Base: `{manifest['base_model']['repo_id']}` @ `{manifest['base_model']['revision'][:12]}` · greedy decoding, up to {args.max_new_tokens} new tokens.", "",
              f"| | loss (assistant tokens) | perplexity |", "|---|---|---|",
              f"| original base | {base_metrics['loss']} | {base_metrics['perplexity']} |",
              f"| base + adapter | {tuned_metrics['loss']} | {tuned_metrics['perplexity']} |", ""]
    for number, (messages, before, after) in enumerate(zip(chosen, base_answers, tuned_answers), 1):
        lines += [f"## Sample {number}", ""]
        lines += [f"**{message['role']}:** {message['content']}\n" for message in messages[:-1]]
        lines += ["**Reference answer:**", "", messages[-1]["content"], "", "**Original base:**", "", before or "(empty)", "",
                  "**Base + adapter:**", "", after or "(empty)", ""]
    (run_dir / "eval-samples.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest.setdefault("evaluations", []).append({key: result[key] for key in ("evaluated_at", "base", "with_adapter", "loss_change")} | {"validation_sha256": val_info["sha256"]})
    write_manifest(run_dir, manifest)

    print(f"validation: {val_info['conversations']} conversations, {base_metrics['supervised_tokens']} assistant tokens")
    print(f"original base   loss {base_metrics['loss']:.4f}  perplexity {base_metrics['perplexity']}")
    print(f"base + adapter  loss {tuned_metrics['loss']:.4f}  perplexity {tuned_metrics['perplexity']}   (change {result['loss_change']:+.4f})")
    print(f"written: {run_dir / 'eval.json'} and {run_dir / 'eval-samples.md'}")
    if smoke:
        print(SMOKE_BANNER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
