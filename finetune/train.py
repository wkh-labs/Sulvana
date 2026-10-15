#!/usr/bin/env python3
"""QLoRA fine-tuning of Sulvana's base model (Dolphin 3.0 8B or MiMo-V2.6-Distill-Qwen-9B): resumable, logged, conservative for an 8 GB GPU.

Never downloads anything. A real run needs the checkpoint fetched first (finetune/fetch_base.py);
--smoke runs the same code path on a tiny random model to test the pipeline itself.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

common.setup_environment(offline=True)

from validate_dataset import print_report, validate  # noqa: E402

LOG = logging.getLogger("finetune")
SMOKE_BANNER = (
    "\n" + "=" * 78 + "\n"
    "SMOKE TEST: training a tiny RANDOMLY INITIALISED model, not the real base model.\n"
    "This only proves that the pipeline runs. The result has no language ability.\n"
    + "=" * 78
)


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def newest_checkpoint(run_dir: Path) -> Path | None:
    found = []
    for path in run_dir.glob("checkpoint-*"):
        step = path.name.rsplit("-", 1)[-1]
        if step.isdigit() and (path / "trainer_state.json").is_file():
            found.append((int(step), path))
    return max(found)[1] if found else None


def write_manifest(run_dir: Path, manifest: dict) -> None:
    temporary = run_dir / "run.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(run_dir / "run.json")


def dataset_entry(path: Path, config: dict, tokenizer) -> tuple[list[dict], dict]:
    report = validate(path, config, tokenizer)
    if report["errors"]:
        print_report(report)
        raise SystemExit(f"Dataset is invalid: {path}")
    records, _, _ = common.read_jsonl(path)
    examples, stats = common.build_examples(tokenizer, records, config)
    return examples, {"path": str(path), "sha256": report["sha256"], "conversations": len(records), "tokens": stats}


def preflight(config: dict, force: bool) -> None:
    """Fail early, before anything heavy is loaded, with instructions instead of a stack trace."""
    status = common.weights_status(config)
    if not status["complete"]:
        print(common.missing_weights_message(config, status))
        sys.exit(2)
    gpu = common.gpu_summary()
    if not gpu["available"]:
        print("CUDA is not available. Activate the workspace environment (source activate-ai.sh) and check nvidia-smi.")
        sys.exit(2)
    needed = float(config["memory"]["min_free_vram_gib"])
    if gpu["free_gib"] < needed and not force:
        apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader"],
                              capture_output=True, text=True, check=False).stdout.strip()
        print(f"Only {gpu['free_gib']:.2f} GiB of VRAM is free; this configuration wants at least {needed:.1f} GiB.\n"
              f"Processes using the GPU:\n{apps or '  (none reported)'}\n"
              "Sulvana keeps Dolphin loaded (about 4.8 GB) while its service runs; stop it with:\n"
              "  systemctl --user stop sulvana-web\n"
              "Closing other GPU-accelerated apps frees more. Use --force to try anyway.")
        sys.exit(3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True, help="outputs go to runs/finetune/<run-name>/")
    parser.add_argument("--config", default=None, help=f"default: {common.DEFAULT_CONFIG.name}")
    parser.add_argument("--train-file", default=None)
    parser.add_argument("--val-file", default=None)
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override a config value, e.g. training.learning_rate=1e-4")
    parser.add_argument("--max-steps", type=int, default=None, help="stop after this many optimiser steps (overrides epochs)")
    parser.add_argument("--resume", action="store_true", help="continue from the newest checkpoint of this run")
    parser.add_argument("--overwrite", action="store_true", help="delete an existing run of this name and start again")
    parser.add_argument("--force", action="store_true", help="skip the free-VRAM check")
    parser.add_argument("--smoke", action="store_true", help="pipeline test on a tiny random model (no 16 GB checkpoint needed)")
    # Test hook: behave as if the run was interrupted right after the checkpoint at this step.
    parser.add_argument("--stop-after", type=int, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.resume and args.overwrite:
        raise SystemExit("Use either --resume or --overwrite, not both.")

    config = common.load_config(args.config, args.set)
    run_dir = common.run_directory(config, args.run_name)
    occupied = run_dir.exists() and any(run_dir.iterdir())
    manifest, resume_from = None, None
    if args.resume:
        resume_from = newest_checkpoint(run_dir)
        if resume_from is None or not (run_dir / "run.json").is_file():
            raise SystemExit(f"--resume: no checkpoint to continue from in {run_dir}")
        manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        if bool(manifest.get("smoke")) != args.smoke:
            raise SystemExit("--resume: this run was started " + ("with" if manifest.get("smoke") else "without") + " --smoke; resume it the same way.")
        # A resumed run keeps the settings it started with; only explicit --set values change them.
        previous = manifest["sessions"][-1]
        config = previous["config"]
        for item in args.set:
            key, raw = item.split("=", 1)
            common._set_nested(config, key.strip(), __import__("yaml").safe_load(raw))
        common.validate_config(config)
        args.max_steps = args.max_steps or previous.get("max_steps")
        args.train_file = args.train_file or previous["data"]["train"]["path"]
        args.val_file = args.val_file or (previous["data"].get("val") or {}).get("path")
    elif occupied:
        if not args.overwrite:
            raise SystemExit(f"{run_dir} already contains a run.\n"
                             "Use --resume to continue it, --overwrite to delete it and start again, or choose another --run-name.")
        if run_dir.resolve().parent != common.runs_root(config).resolve():
            raise SystemExit("Refusing to delete a directory outside the runs folder.")
        shutil.rmtree(run_dir)

    train_file = args.train_file or config["data"]["train_file"]
    val_file = args.val_file or config["data"]["val_file"]
    if not train_file:
        raise SystemExit("No training data: pass --train-file or set data.train_file in the config.")
    train_path, val_path = common.workspace_path(train_file), common.workspace_path(val_file) if val_file else None
    if not args.smoke:
        preflight(config, args.force)

    run_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
                        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(run_dir / "train.log", encoding="utf-8")])
    if args.smoke:
        LOG.info(SMOKE_BANNER)

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import Trainer, TrainerCallback, TrainingArguments

    base, training, lora = config["base_model"], config["training"], config["lora"]
    tokenizer = common.load_tokenizer(config)
    train_examples, train_info = dataset_entry(train_path, config, tokenizer)
    val_examples, val_info = dataset_entry(val_path, config, tokenizer) if val_path else ([], None)
    if not train_examples:
        raise SystemExit("No usable training example after tokenisation.")
    if manifest and manifest["sessions"][0]["data"]["train"]["sha256"] != train_info["sha256"] and not args.force:
        raise SystemExit("--resume: the training file changed since this run started. Start a new run, or pass --force to continue anyway.")
    LOG.info("train: %d conversations (%d usable, %d truncated) | val: %s", train_info["conversations"], len(train_examples),
             train_info["tokens"]["truncated"], f"{len(val_examples)} usable" if val_info else "none")

    model, load_info = common.load_base(config, tokenizer, args.smoke)
    modules = common.describe_modules(model)
    LOG.info("base loaded: %s | %d 4-bit layers | lm_head %s %s on %s | embeddings %s on %s", load_info["source"],
             modules["linear4bit_modules"], modules["lm_head_class"], modules["lm_head_dtype"], modules["lm_head_device"],
             modules["embeddings_dtype"], modules["embeddings_device"])

    # Prepared by hand instead of peft.prepare_model_for_kbit_training: that helper casts every
    # non-4-bit weight to FP32, which doubles the 128258-token embedding table and output head
    # (about +2.1 GB) and does not fit an 8 GB card. BF16 with autocast is stable without it.
    model.config.use_cache = False
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    if training["gradient_checkpointing"]:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(
        r=lora["r"], lora_alpha=lora["alpha"], lora_dropout=lora["dropout"], target_modules=list(lora["target_modules"]),
        bias=lora["bias"], task_type="CAUSAL_LM"))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters()) + (model.get_input_embeddings().weight.numel() if load_info["embeddings_in_system_ram"] else 0)
    if trainable == 0 or any(p.requires_grad and "lora_" not in name for name, p in model.named_parameters()):
        raise SystemExit("LoRA setup is wrong: expected only LoRA weights to be trainable.")
    LOG.info("trainable parameters: %s of %s (%.3f%%)", f"{trainable:,}", f"{total:,}", 100 * trainable / total)

    batch = training["per_device_train_batch_size"] * training["gradient_accumulation_steps"]
    steps_per_epoch = max(1, math.ceil(len(train_examples) / batch))
    planned = args.max_steps if args.max_steps else math.ceil(training["num_train_epochs"] * steps_per_epoch)
    warmup = min(max(0, planned - 1), math.ceil(float(training["warmup_ratio"]) * planned))
    on_gpu = torch.cuda.is_available()
    arguments = TrainingArguments(
        output_dir=str(run_dir),
        num_train_epochs=float(training["num_train_epochs"]),
        max_steps=args.max_steps or -1,
        per_device_train_batch_size=training["per_device_train_batch_size"],
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=training["gradient_accumulation_steps"],
        learning_rate=float(training["learning_rate"]),
        lr_scheduler_type=training["lr_scheduler"],
        warmup_steps=warmup,
        weight_decay=float(training["weight_decay"]),
        max_grad_norm=float(training["max_grad_norm"]),
        optim=training["optimizer"] if on_gpu else "adamw_torch",
        bf16=bool(training["bf16"]) and on_gpu,
        logging_strategy="steps", logging_steps=training["logging_steps"],
        eval_strategy="steps" if val_examples else "no", eval_steps=training["eval_steps"],
        save_strategy="steps", save_steps=training["save_steps"], save_total_limit=training["save_total_limit"],
        seed=training["seed"], data_seed=training["seed"],
        prediction_loss_only=True, remove_unused_columns=False, label_names=["labels"],
        dataloader_num_workers=0, dataloader_pin_memory=False, report_to="none",
        # With batches above 1, group conversations of similar length so little time goes to padding.
        train_sampling_strategy="group_by_length" if training.get("group_by_length") and training["per_device_train_batch_size"] > 1 else "random",
    )

    session = {
        "started_at": now(), "status": "running", "command": sys.argv, "resumed_from": str(resume_from) if resume_from else None,
        "config": common.frozen_copy(config), "data": {"train": train_info, "val": val_info},
        "libraries": common.library_versions(), "gpu": common.gpu_summary(),
        "model_load": {**{k: (v if isinstance(v, (str, bool, type(None))) else str(v)) for k, v in load_info.items()}, **modules},
        "trainable_parameters": trainable, "total_parameters": total,
        "planned_optimizer_steps": planned, "max_steps": args.max_steps, "warmup_steps": warmup, "effective_batch_size": batch,
    }
    if manifest is None:
        manifest = {
            "run_name": args.run_name, "smoke": bool(args.smoke), "created_at": now(), "run_dir": str(run_dir),
            "base_model": {key: base[key] for key in ("repo_id", "revision", "license", "upstream_base")},
            "inference_gguf": {"path": str(common.workspace_path(base["local_gguf"])), "sha256": base["gguf_sha256"]},
            "sessions": [],
        }
    manifest["sessions"].append(session)
    write_manifest(run_dir, manifest)

    class RunLogger(TrainerCallback):
        """Append every log event to metrics.jsonl and time the optimiser steps."""

        def __init__(self) -> None:
            self.step_seconds: list[float] = []
            self.losses: list[float] = []
            self.mark: float | None = None

        def on_step_begin(self, args_, state, control, **kwargs):
            self.mark = time.perf_counter()

        def on_step_end(self, args_, state, control, **kwargs):
            if self.mark is not None:
                self.step_seconds.append(time.perf_counter() - self.mark)

        def on_save(self, args_, state, control, **kwargs):
            if args.stop_after and state.global_step >= args.stop_after:
                raise KeyboardInterrupt

        def on_log(self, args_, state, control, logs=None, **kwargs):
            entry = {"time": now(), "step": state.global_step, **(logs or {})}
            if "loss" in entry:
                self.losses.append(float(entry["loss"]))
            if on_gpu:
                entry["vram_peak_allocated_gib"] = round(torch.cuda.max_memory_allocated() / 2**30, 3)
                entry["vram_peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 3)
            with open(run_dir / "metrics.jsonl", "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")
            shown = {key: value for key, value in entry.items() if key in ("loss", "eval_loss", "learning_rate", "epoch", "train_loss")}
            if shown:
                LOG.info("step %d %s", state.global_step, shown)

    class SupervisedTrainer(Trainer):
        """Trainer whose loss builds logits only where an assistant token is being predicted."""

        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            if num_items_in_batch is None:
                loss, _ = common.supervised_loss(model, inputs)
            else:
                # While accumulating gradients the Trainer passes the number of supervised tokens in the
                # whole accumulated batch and expects the loss to be normalised by it.
                total, _ = common.supervised_loss(model, inputs, reduction="sum")
                loss = total / torch.as_tensor(num_items_in_batch, device=total.device)
            return (loss, {"loss": loss}) if return_outputs else loss

    class ThermalGuard(TrainerCallback):
        """Keep the GPU under a temperature ceiling: pause when it is reached, continue once it has cooled.

        Checked after every conversation (not only every optimiser step), so the ceiling holds
        to within a second or two of work. Optional pacing adds a short rest after each
        conversation to run cooler at the cost of speed.
        """

        def __init__(self, settings: dict) -> None:
            self.limit = float(settings.get("max_gpu_temp_c") or 0)
            self.resume = float(settings.get("resume_gpu_temp_c") or max(0.0, self.limit - 12))
            self.pace = float(settings.get("pace_seconds") or 0)
            self.pauses, self.paused_seconds, self.hottest = 0, 0.0, 0.0

        @staticmethod
        def temperature() -> float | None:
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, timeout=5, check=False).stdout
                return float(out.strip().splitlines()[0])
            except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
                return None

        def check(self) -> None:
            if self.pace:
                time.sleep(self.pace)
            if not self.limit:
                return
            now = self.temperature()
            if now is None:
                return
            self.hottest = max(self.hottest, now)
            if now < self.limit:
                return
            began = time.perf_counter()
            self.pauses += 1
            LOG.info("GPU at %.0f°C (limit %.0f°C): pausing until it cools to %.0f°C", now, self.limit, self.resume)
            while True:
                time.sleep(5)
                now = self.temperature()
                if now is None or now <= self.resume:
                    break
            self.paused_seconds += time.perf_counter() - began
            LOG.info("GPU at %s°C: continuing (paused %.0f s)", "?" if now is None else f"{now:.0f}", time.perf_counter() - began)

        def on_substep_end(self, args_, state, control, **kwargs):
            self.check()

        def on_step_end(self, args_, state, control, **kwargs):
            self.check()

        def on_prediction_step(self, args_, state, control, **kwargs):
            self.check()   # validation passes heat the GPU too

    logger = RunLogger()
    guard = ThermalGuard(config.get("thermal") or {})
    trainer = SupervisedTrainer(model=model, args=arguments, train_dataset=train_examples, eval_dataset=val_examples or None,
                      data_collator=common.Collator(tokenizer.pad_token_id), callbacks=[logger, guard])
    LOG.info("%s: %d optimiser steps planned (%d per epoch, effective batch %d, warmup %d) -> %s",
             "resuming from " + resume_from.name if resume_from else "starting", planned, steps_per_epoch, batch, warmup, run_dir)
    if on_gpu:
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    try:
        trainer.train(resume_from_checkpoint=str(resume_from) if resume_from else None)
    except KeyboardInterrupt:
        session.update(status="interrupted", finished_at=now(), optimizer_steps_done=trainer.state.global_step)
        write_manifest(run_dir, manifest)
        LOG.info("Interrupted at step %d. Continue from the last checkpoint with --resume.", trainer.state.global_step)
        return 130
    except BaseException as error:
        session.update(status="failed", finished_at=now(), error=f"{type(error).__name__}: {error}"[:2000],
                       optimizer_steps_done=trainer.state.global_step)
        write_manifest(run_dir, manifest)
        raise

    evaluation = trainer.evaluate() if val_examples else {}
    adapter_dir = run_dir / "adapter"
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    lineage = {
        "base_model": manifest["base_model"], "smoke_test": bool(args.smoke), "run_name": args.run_name, "created_at": now(),
        "train_file_sha256": train_info["sha256"], "val_file_sha256": val_info["sha256"] if val_info else None,
        "lora": lora, "note": base.get("lineage_note") or (
            "This adapter is a derivative of Dolphin 3.0 Llama 3.1 8B, itself fine-tuned from Meta's Llama 3.1 8B. "
            "It inherits the Llama 3.1 Community License and its Acceptable Use Policy. Built with Llama."),
    }
    if args.smoke:
        lineage["note"] = "PIPELINE SMOKE TEST on a random tiny model. Not a real adapter; do not load it into Sulvana."
    (adapter_dir / "LINEAGE.json").write_text(json.dumps(lineage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    seconds = logger.step_seconds
    session.update(
        status="completed", finished_at=now(), wall_seconds=round(time.perf_counter() - started, 1),
        optimizer_steps_done=trainer.state.global_step,
        # The Trainer's own average is wrong after a resume, so report what this session logged.
        train_loss_last_logged=logger.losses[-1] if logger.losses else None,
        train_loss_session_mean=round(sum(logger.losses) / len(logger.losses), 5) if logger.losses else None,
        eval_loss=evaluation.get("eval_loss"),
        seconds_per_optimizer_step=round(sum(seconds) / len(seconds), 3) if seconds else None,
        vram_peak_allocated_gib=round(torch.cuda.max_memory_allocated() / 2**30, 3) if on_gpu else None,
        vram_peak_reserved_gib=round(torch.cuda.max_memory_reserved() / 2**30, 3) if on_gpu else None,
        checkpoints=sorted(path.name for path in run_dir.glob("checkpoint-*")),
        thermal={"hottest_gpu_c": guard.hottest, "pauses": guard.pauses, "paused_seconds": round(guard.paused_seconds)},
        adapter={"path": str(adapter_dir), "megabytes": round(sum(f.stat().st_size for f in adapter_dir.glob("adapter_model.*")) / 1e6, 1)},
    )
    write_manifest(run_dir, manifest)
    LOG.info("done: step %d | last train loss %s | eval loss %s | peak VRAM %s GiB allocated / %s GiB reserved | %s s per step",
             trainer.state.global_step, session["train_loss_last_logged"], evaluation.get("eval_loss"), session["vram_peak_allocated_gib"],
             session["vram_peak_reserved_gib"], session["seconds_per_optimizer_step"])
    LOG.info("adapter: %s | manifest: %s", adapter_dir, run_dir / "run.json")
    if args.smoke:
        LOG.info(SMOKE_BANNER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
