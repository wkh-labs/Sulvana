# Fine-tuning Dolphin 3.0 · 8B for Sulvana v1

A small, reproducible QLoRA workflow for the model Sulvana already uses. It trains a LoRA
**adapter**; it never modifies or replaces Sulvana's model file and never downloads anything
unless you run `fetch_base.py --yes`.

**Status: set up and smoke-tested only.** No real training run has been done. The 16 GB
trainable checkpoint is not downloaded, and no real dataset exists yet. Every memory and
runtime number for the real model below is an estimate until the probe run (step 6) measures it.

Run everything from the workspace root with the workspace interpreter, `.venv/bin/python`
(the system `python` has no PyTorch).

## Which model is trained

| | |
|---|---|
| Sulvana runs | `models/Dolphin3.0-Llama3.1-8B/Dolphin3.0-Llama3.1-8B-Q4_K_M.gguf` (inference only; cannot be trained) |
| Trainable checkpoint | [`dphn/Dolphin3.0-Llama3.1-8B`](https://huggingface.co/dphn/Dolphin3.0-Llama3.1-8B), BF16 Safetensors, 8.03 B parameters (formerly `cognitivecomputations/…`) |
| Pinned revision | `f065677950dfc7e708d518d64cf1f5041ee007a0` |
| Lineage | Dolphin 3.0 by Cognitive Computations, fine-tuned from `meta-llama/Llama-3.1-8B` |
| License | Llama 3.1 Community License (`llama3.1`) |

`verify_base.py` checks, offline, that the two describe the same model: architecture numbers,
all 128,258 vocabulary entries id-for-id, a byte-identical ChatML chat template, and the same
BOS/EOS/PAD ids. Sulvana's llama-server puts one `<|begin_of_text|>` in front of the templated
prompt, so training sequences are built the same way.

**License, in plain language (not legal advice):** an adapter trained from this checkpoint is a
derivative of Llama 3.1 and of Dolphin 3.0. It inherits the Llama 3.1 Community License and its
Acceptable Use Policy. Private use needs nothing more. If you share the adapter or a merged
model, ship a copy of the license, show "Built with Llama", and give the model a name that
starts with "Llama". The full text is linked from the model page above. Each adapter gets a
`LINEAGE.json` recording the base model, revision, license and dataset hashes.

## Dataset format

One conversation per line (JSONL, UTF-8):

```json
{"messages": [{"role": "system", "content": "You are Sulvana."}, {"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello! How can I help?"}]}
```

- An optional `system` message first, then `user` and `assistant` strictly alternating,
  starting with `user` and ending with `assistant`. Multi-turn conversations are fine.
- The model learns only from assistant messages (and to stop after them). System and user
  text is context.
- Contents must be non-empty text without control tokens such as `<|im_start|>`.
- An optional `"meta": {...}` object is kept but ignored.

Put your data under `datasets/`; it is git-ignored. See `datasets/README.md`.
`datasets/fixtures/synthetic-smoke.jsonl` is a **synthetic** fixture for testing the pipeline.
It is not your data and is useless for real training.

Sulvana always sends its own system prompt. To train with it, export it once and set
`data.system_prompt` to `mode: file` in the config (records without a system message then get
it). The Khmer-first prompt is about 490 tokens long, which is nearly the whole default budget,
so either raise `data.max_seq_length` (memory permitting) or train with a short prompt of your own:

```bash
python3 -c "import sulvana_worker; print(sulvana_worker.SYSTEM)" > datasets/sulvana-system.txt
```

## Teaching Dolphin Khmer (the Sulvana v1 goal)

Sulvana v1 is meant to be Khmer-first, and today the base model is not: measured with
`benchmark/khmer/` on 13 Oct 2026, Dolphin replies in Khmer *script* but the text is not
meaningful Khmer. It could not name Phnom Penh as the capital, even with greedy decoding, and
it only partly understands Khmer questions. Prompts and settings do not fix that; training has to.

What that asks of a fine-tune, and what this folder provides for it:

- **A lot of Khmer text.** This is teaching a language, not a style. Plan for tens of thousands
  of conversations, and keep some English ones in the mix so the model does not lose what it has.
  Khmer costs about 1.6 tokens per character here, so 512 tokens is roughly 300 Khmer characters.
- **`dolphin-khmer-qlora-8gb.yaml`**, a profile for this job: LoRA on every linear layer (41.9 M
  parameters instead of 13.6 M), a 4-bit output head to pay for that in VRAM, learning rate 1e-4,
  one epoch. Estimated peak 5.1 to 5.7 GiB; the probe run measures it. A checkpoint is about 170 MB.
- **`convert_dataset.py`** turns Alpaca-style files, ShareGPT conversations and English/Khmer
  translation pairs into the chat format (translation prompts are written in Khmer).
- **Time.** Unmeasured; at very roughly 2 s per conversation, 30,000 conversations take about
  17 hours per epoch. Runs resume from checkpoints, so this can be spread over several nights.
- **A yardstick.** After each run, load the adapter into the app (see "Testing an adapter inside
  Sulvana") and run `python3 benchmark/khmer/run_khmer_eval.py --label my-run`. Compare with
  `runs/khmer-eval/sulvana-v1-dolphin.md`, and read the replies: the script checks language and
  script, not grammar.

```bash
.venv/bin/python finetune/convert_dataset.py --input path/to/alpaca_khmer.json --format alpaca \
  --output datasets/khmer/all.jsonl --source-name "where this data came from"
.venv/bin/python finetune/validate_dataset.py datasets/khmer/all.jsonl
.venv/bin/python finetune/split_dataset.py --input datasets/khmer/all.jsonl --out-dir datasets/khmer --val-fraction 0.02
./run-performance.sh python finetune/train.py --run-name khmer-01 --config finetune/dolphin-khmer-qlora-8gb.yaml \
  --train-file datasets/khmer/train.jsonl --val-file datasets/khmer/val.jsonl
```

Whether an adapter of this size can make an 8B model fluent in a language it barely knows is
an open question; the evaluation above is how to find out early, on a short run, before
committing nights of training.

## Steps

```bash
# 1. Pipeline self-check (no GPU, no download; about 30 s)
.venv/bin/python finetune/selfcheck.py

# 2. Confirm the checkpoint matches Sulvana's GGUF (offline)
.venv/bin/python finetune/verify_base.py --hash-gguf

# 3. Validate your data, then split it (deterministic; safe to re-run after adding lines)
.venv/bin/python finetune/validate_dataset.py datasets/my-data/all.jsonl
.venv/bin/python finetune/split_dataset.py --input datasets/my-data/all.jsonl --out-dir datasets/my-data --val-fraction 0.1

# 4. Optional: smoke-test the whole pipeline on a tiny random model (seconds, about 0.2 GB VRAM)
.venv/bin/python finetune/split_dataset.py --input datasets/fixtures/synthetic-smoke.jsonl --out-dir runs/finetune/smoke-data --val-fraction 0.2
.venv/bin/python finetune/train.py --smoke --overwrite --run-name smoke --max-steps 8 \
  --train-file runs/finetune/smoke-data/train.jsonl --val-file runs/finetune/smoke-data/val.jsonl \
  --set training.gradient_accumulation_steps=2 --set training.save_steps=4 --set training.eval_steps=4
.venv/bin/python finetune/evaluate.py --run-name smoke

# 5. Download the checkpoint: 16.06 GB. The first command only prints the plan.
.venv/bin/python finetune/fetch_base.py
.venv/bin/python finetune/fetch_base.py --yes

# 6. Probe run: two optimiser steps to MEASURE peak VRAM and seconds per step. Do this first.
systemctl --user stop sulvana-web        # Sulvana holds about 4.8 GB of VRAM while it runs
.venv/bin/python finetune/train.py --run-name probe --max-steps 2 --set training.save_steps=2 \
  --train-file datasets/my-data/train.jsonl --val-file datasets/my-data/val.jsonl

# 7. The real run (the wrapper needs AC power and sets the performance profile)
./run-performance.sh python finetune/train.py --run-name my-run \
  --train-file datasets/my-data/train.jsonl --val-file datasets/my-data/val.jsonl

# 8. If it is interrupted: continue from the newest checkpoint with the same settings
./run-performance.sh python finetune/train.py --run-name my-run --resume

# 9. Compare the original checkpoint with checkpoint + adapter on the validation set
.venv/bin/python finetune/evaluate.py --run-name my-run
```

`train.py` refuses to start when the checkpoint is not fully downloaded (exit code 2), when
less than `memory.min_free_vram_gib` of VRAM is free (exit code 3, `--force` overrides), or
when the run name already exists (use `--resume`, `--overwrite`, or another name). Settings live
in `finetune/dolphin-qlora-8gb.yaml`; change one for a single run with `--set section.key=value`.

A resumed run keeps the settings, data files and step budget it started with and continues the
optimiser, learning-rate schedule and data order from the checkpoint. Work done after the last
checkpoint (`training.save_steps`, 50 by default) is repeated.

## Outputs

Everything lands in `runs/finetune/<run-name>/` (git-ignored):

| File | Content |
|---|---|
| `run.json` | Manifest: base repo, pinned revision, license, GGUF hash; data files with SHA-256 and token statistics; the full resolved config; library versions; GPU; command line; one entry per session (including resumes) with steps, losses, peak VRAM, seconds per step, checkpoints and the adapter path; evaluation results |
| `train.log`, `metrics.jsonl` | Human-readable log and one JSON line per logging step |
| `checkpoint-N/` | Resumable state (adapter, optimiser, schedule, RNG); the newest 3 are kept |
| `adapter/` | The final LoRA adapter, tokenizer files and `LINEAGE.json` |
| `eval.json`, `eval-samples.md` | Loss and perplexity over assistant tokens for the original base and for base + adapter, and side-by-side answers |

## Expected resources for the real run

| | |
|---|---|
| Download | 16.06 GB of weights (the 17 MB of config and tokenizer files are already cached) |
| Disk | about 16.1 GB in `.cache/huggingface`, plus about 55 MB per adapter and about 90 MB per checkpoint (13,631,488 LoRA parameters at rank 16). Under 17 GB in total; 771 GB were free when this was set up |
| System RAM | under 10 GB (30 GB installed) |
| GPU memory | **estimated** 5.6 to 6.2 GiB peak with the default settings; see below |
| Time | not measured. Expect very roughly 20 to 50 s per optimiser step (16 conversations). Total ≈ seconds per step × ceil(conversations ÷ 16) × epochs; for 1,000 conversations and 3 epochs that is 189 steps, somewhere around 1 to 2.5 hours. The probe run prints the real seconds per step |

Why GPU memory is tight, and what the defaults do about it. The card has 8 GB; PyTorch sees
7.59 GiB, and the desktop itself held 0.8 to 1.3 GB during setup, leaving roughly 6.3 to 6.8 GiB
once Sulvana is stopped.

- The 4-bit layers of the model are about 3.4 GiB.
- The output head (128,258 × 4,096) stays in BF16: 0.98 GiB. The loader leaves it unquantised by
  default (verified on the smoke model).
- The input embedding table is another 0.98 GiB and cannot be quantised. The default keeps it in
  system RAM and sends only the looked-up rows to the GPU (`memory.offload_embeddings_to_cpu`).
  It is on the GPU briefly while loading, so loading needs about 5.5 GiB free.
- PEFT's usual `prepare_model_for_kbit_training` helper is deliberately not used: it converts the
  embedding table and output head to FP32, which costs about 2 GiB more and would not fit.
- Vocabulary-sized logits are computed only at assistant-token positions, so long system and
  user text costs little extra memory.
- On top of that come the CUDA context, activations (gradient checkpointing is on), LoRA
  weights and the 8-bit optimiser state: about 1.2 to 1.8 GiB at 512 tokens.

If the probe run runs out of memory, in this order: close other GPU apps (browsers and chat
apps hold several hundred MB), `--set data.max_seq_length=384` (or 256),
`--set memory.quantize_lm_head=true` (saves about 0.8 GiB, slightly noisier training signal),
`--set lora.r=8`. If the probe shows more than 1 GiB to spare you can raise `max_seq_length`.

## Testing an adapter inside Sulvana

Sulvana's default model does not change. An adapter is loaded only when you ask for it, on top
of the unmodified GGUF, and the app shows a `LoRA · <name>` chip in the top bar while it is active.

1. Convert the adapter to llama.cpp's GGUF LoRA format. This needs the llama.cpp source tree
   and its `gguf` Python package, which are not in this workspace (a one-time download you start
   yourself; this step was not run during setup, so check `--help` if a flag has changed):

   ```bash
   git clone --depth 1 https://github.com/ggml-org/llama.cpp .runtime/llama.cpp
   uv pip install --python .venv/bin/python gguf
   .venv/bin/python .runtime/llama.cpp/convert_lora_to_gguf.py runs/finetune/my-run/adapter \
     --base .cache/huggingface/hub/models--dphn--Dolphin3.0-Llama3.1-8B/snapshots/f065677950dfc7e708d518d64cf1f5041ee007a0 \
     --outtype f16 --outfile runs/finetune/my-run/my-run.gguf
   ```

2. Start Sulvana with the adapter (the engine must be restarted to load it):

   ```bash
   systemctl --user stop sulvana-web
   SULVANA_LORA_ADAPTER="$PWD/runs/finetune/my-run/my-run.gguf" sulvana
   ```

3. Go back to plain Dolphin:

   ```bash
   systemctl --user stop sulvana-web
   sulvana
   ```

If the path is wrong Sulvana reports an engine error instead of silently running without the
adapter. To compare answers without converting anything, use `evaluate.py` (step 9).
Merging the adapter into a new GGUF is intentionally not part of this workflow.

## Troubleshooting

- **`not fully downloaded` (exit 2):** run `fetch_base.py --yes`; interrupted downloads resume.
- **`Only … GiB of VRAM is free` (exit 3):** stop Sulvana (`systemctl --user stop sulvana-web`) and close GPU apps.
- **CUDA out of memory during training:** see the list above; then `--resume` or start again with `--overwrite`.
- **Validation loss rises while training loss falls:** the adapter is memorising. Use fewer epochs, a lower learning rate (`1e-4`) or more data.
