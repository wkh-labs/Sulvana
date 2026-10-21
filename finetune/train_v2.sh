#!/usr/bin/env bash
# Khmer adapter v2 for MiMo: rebuild the quality-only mix, train, convert, and benchmark the adapter
# at several strengths against plain MiMo and v1. Usage: finetune/train_v2.sh <run-name> [epochs]
# Progress and results: runs/mimo/<run-name>.log
set -u
cd /home/tanchjim/Documents/Codex/ai-workspace
RUN=${1:?run name}; EPOCHS=${2:-2}
OUT=runs/finetune/$RUN
LOG=runs/mimo/$RUN.log
SNAP=$(ls -d .cache/huggingface/hub/models--XiaomiMiMo--MiMo-V2.6-Distill-Qwen-9B/snapshots/*/ | head -1)
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }

say "mix: $(.venv/bin/python finetune/mix_khmer_v2.py 2>&1 | tail -1)"
# Loading MiMo briefly needs ~6.1 GiB of free GPU memory; wait (up to 12 h) for the desktop to leave that much.
free_mib() { nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1; }
if [ "$(free_mib)" -lt 6300 ]; then
  say "waiting for 6.3 GB of free GPU memory (now $(free_mib) MiB): close GPU-heavy apps such as ChatGPT or a browser playing video"
  for _ in $(seq 1 1440); do [ "$(free_mib)" -ge 6300 ] && break; sleep 30; done
fi
say "training $RUN ($EPOCHS epochs), $(free_mib) MiB free"
.venv/bin/python finetune/train.py --force ${RESUME:+--resume} --run-name "$RUN" --config finetune/mimo-khmer-qlora-8gb.yaml \
  --train-file datasets/khmer-v2/train.jsonl --val-file datasets/khmer-v2/val.jsonl \
  --set data.max_seq_length=1024 --set training.num_train_epochs="$EPOCHS" \
  --set training.per_device_train_batch_size=1 --set training.gradient_accumulation_steps=16 \
  --set training.eval_steps=25 --set training.save_steps=25 --set training.save_total_limit=20 \
  --set thermal.max_gpu_temp_c="${MAX_GPU_TEMP:-80}" --set thermal.resume_gpu_temp_c=72 > "runs/finetune/$RUN.console.log" 2>&1
status=$?
say "training exit $status; $(grep -a 'done:' "$OUT/train.log" | tail -1 | cut -c1-160)"
[ "$status" -eq 0 ] || exit "$status"

.venv/bin/python .runtime/llama.cpp/convert_lora_to_gguf.py --base "$SNAP" --outtype f16 \
  --outfile "$OUT/$RUN.gguf" "$OUT/adapter" >> "$LOG" 2>&1 && say "converted" || { say "conversion failed"; exit 1; }

for scale in 0.3 0.6 1.0; do
  .venv/bin/python benchmark/run_benchmark.py --base mimo --suite skb --label "$RUN-x$scale" \
    --lora "$OUT/$RUN.gguf" --lora-scale "$scale" >> "$LOG" 2>&1
  .venv/bin/python benchmark/run_benchmark.py --base mimo --split dev --label "$RUN-x$scale" \
    --lora "$OUT/$RUN.gguf" --lora-scale "$scale" >> "$LOG" 2>&1
  say "benchmarked x$scale"
done

.venv/bin/python - "$RUN" >> "$LOG" 2>&1 <<'EOF'
import json, sys
run = sys.argv[1]
def score(label):
    skb = json.load(open(f"runs/benchmark/skb-{label}/report.json"))["totals"]["overall"]
    kbai = json.load(open(f"runs/benchmark/{label}/report.json"))["summary"]
    return round(100 * skb[0] / skb[1], 1), kbai["accuracy_percent"]
rows = {"plain MiMo": score("mimo-base"), "v1 adapter x0.3": score("mimo-khmer-01-x0.3"), "v2 adapter x0.3": score("mimo-khmer-v2-x0.3")}
for s in ("0.3", "0.6", "1.0"):
    rows[f"{run} x{s}"] = score(f"{run}-x{s}")
print("==== RESULTS (hard Khmer benchmark %, 800-question dev set %)")
for name, (a, b) in rows.items():
    print(f"  {name:<28} {a:5.1f}  {b:6.2f}  mean {(a + b) / 2:5.1f}")
best = max(rows, key=lambda k: sum(rows[k]))
print("  BEST:", best)
EOF
say "done"
