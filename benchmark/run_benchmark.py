#!/usr/bin/env python3
"""Run the Khmer Bilingual AI Benchmark against Sulvana's model, optionally with a LoRA adapter.

Follows the benchmark rules in README.md: greedy decoding, one fixed prompt, the same token
limit for every model, and no tools, search or retrieval. It starts its own llama-server with
the same model file and settings Sulvana uses, so stop Sulvana first (it needs the GPU).

    systemctl --user stop sulvana-web
    python3 benchmark/run_benchmark.py --label dolphin-base --split dev
    python3 benchmark/run_benchmark.py --label khmer-quick-01 --split dev \
        --lora runs/finetune/khmer-quick-01/sulvana-khmer-quick-01.gguf

Answers go to runs/benchmark/<label>/ and are scored with score_responses.py.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODELS = {
    "dolphin": ROOT / "models/Dolphin3.0-Llama3.1-8B/Dolphin3.0-Llama3.1-8B-Q4_K_M.gguf",
    "mimo": ROOT / "models/MiMo-V2.6-Distill-Qwen-9B/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf",
}
MODEL = MODELS["dolphin"]
LORA_SCALE = [1.0]
SERVER = ROOT / "vision-runner/llama-server"
# One fixed instruction for every model. No tool instructions: tools are not part of this score.
SYSTEM = ("You are Sulvana, a Khmer-first AI assistant. Answer the question directly and briefly. "
          "Give the final answer first, in the language of the question, with at most one short sentence "
          "of explanation. For multiple-choice questions, answer with the letter of the correct option.")


def gpu_temperature() -> float | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5, check=False).stdout
        return float(out.split()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def cool_down(limit: float, resume: float) -> None:
    now = gpu_temperature()
    if now is None or now < limit:
        return
    print(f"  GPU at {now:.0f}°C: pausing until {resume:.0f}°C", flush=True)
    while (now := gpu_temperature()) is not None and now > resume:
        time.sleep(5)


def start_server(lora: Path | None, context: int) -> tuple[subprocess.Popen, str]:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command = [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(port),
               "--ctx-size", str(context), "--gpu-layers", "99", "--flash-attn", "auto",
               "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--parallel", "1", "--no-webui"]
    if lora:   # one adapter, or several applied together (paths and scales separated by commas)
        command += ["--lora-scaled", ",".join(f"{path}:{scale}" for path, scale in zip(lora, LORA_SCALE))]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    endpoint = f"http://127.0.0.1:{port}"
    for _ in range(240):
        if process.poll() is not None:
            raise SystemExit("llama-server stopped while loading. Is Sulvana still using the GPU? "
                             "Run: systemctl --user stop sulvana-web")
        try:
            with urllib.request.urlopen(endpoint + "/health", timeout=1) as response:
                if response.status == 200:
                    return process, endpoint
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    process.terminate()
    raise SystemExit("llama-server took too long to start.")


def ask(endpoint: str, prompt: str, max_tokens: int) -> str:
    request = {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
               "temperature": 0, "max_tokens": max_tokens, "stream": False}
    if MODEL == MODELS["mimo"]:
        request["chat_template_kwargs"] = {"enable_thinking": False}   # answer directly, like Dolphin
    body = json.dumps(request).encode()
    request = urllib.request.Request(endpoint + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)["choices"][0]["message"]["content"].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True)
    parser.add_argument("--suite", choices=["kbai", "skb"], default="kbai",
                        help="kbai = the 800-question Khmer Bilingual AI Benchmark; skb = the harder Sulvana Khmer Benchmark")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    parser.add_argument("--base", choices=sorted(MODELS), default="dolphin", help="which base model GGUF to load")
    parser.add_argument("--lora", default=None, help="GGUF LoRA adapter to apply on top of the model")
    parser.add_argument("--lora-scale", default="1.0", help="adapter strength, 1.0 = as trained (comma-separated for several adapters)")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--limit", type=int, default=None, help="only the first N questions (quick check)")
    parser.add_argument("--max-gpu-temp", type=float, default=80, help="pause above this temperature (0 = off)")
    parser.add_argument("--resume-gpu-temp", type=float, default=68)
    args = parser.parse_args()
    global MODEL, LORA_SCALE
    MODEL = MODELS[args.base]
    LORA_SCALE = [float(x) for x in str(args.lora_scale).split(",")]
    if not MODEL.is_file():
        raise SystemExit(f"Model file not found: {MODEL}")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,60}", args.label):
        raise SystemExit("--label may only contain letters, digits, dot, dash and underscore")
    if subprocess.run(["systemctl", "--user", "is-active", "--quiet", "sulvana-web.service"]).returncode == 0:
        raise SystemExit("Sulvana is running and holds the GPU. Stop it first: systemctl --user stop sulvana-web")
    lora = [Path(item).resolve() for item in args.lora.split(",")] if args.lora else None
    if lora and len(LORA_SCALE) == 1:
        LORA_SCALE = LORA_SCALE * len(lora)
    if lora and (len(lora) != len(LORA_SCALE) or not all(item.is_file() for item in lora)):
        raise SystemExit(f"Adapter not found: {lora}")
    suite = HERE / "skb" if args.suite == "skb" else HERE
    questions = [json.loads(line) for line in (suite / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    questions = [q for q in questions if args.suite == "skb" or args.split == "all" or q["split"] == args.split][: args.limit]
    out = ROOT / "runs" / "benchmark" / (args.label if args.suite == "kbai" else f"skb-{args.label}")
    out.mkdir(parents=True, exist_ok=True)
    answers_path = out / "responses.jsonl"
    done = {}
    if answers_path.exists():   # resume an interrupted run
        done = {row["id"]: row for row in map(json.loads, answers_path.read_text(encoding="utf-8").splitlines()) if row.get("answer") is not None}
    server, endpoint = start_server(lora, 4096)
    started = time.perf_counter()
    try:
        with open(answers_path, "a", encoding="utf-8") as handle:
            for number, question in enumerate(questions, 1):
                if question["id"] in done:
                    continue
                if args.max_gpu_temp:
                    cool_down(args.max_gpu_temp, args.resume_gpu_temp)
                answer = ask(endpoint, question["prompt"], args.max_tokens)
                handle.write(json.dumps({"id": question["id"], "answer": answer}, ensure_ascii=False) + "\n")
                handle.flush()
                if number % 20 == 0 or number == len(questions):
                    print(f"  {number}/{len(questions)} answered ({time.perf_counter() - started:.0f}s)", flush=True)
    finally:
        server.terminate()
        server.wait(timeout=30)
    manifest = {"label": args.label, "suite": args.suite, "split": args.split, "questions": len(questions), "model": str(MODEL),
                "lora": [str(item) for item in lora] if lora else None, "lora_scale": LORA_SCALE if lora else None, "system_prompt": SYSTEM, "temperature": 0,
                "max_tokens": args.max_tokens, "tools": "none", "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (out / "run.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.suite == "skb":
        return subprocess.run([sys.executable, str(suite / "score.py"), str(answers_path), "--report", str(out / "report.json")]).returncode
    return subprocess.run([sys.executable, str(HERE / "score_responses.py"), str(answers_path), "--split", args.split,
                           "--report", str(out / "report.json")]).returncode


if __name__ == "__main__":
    sys.exit(main())
