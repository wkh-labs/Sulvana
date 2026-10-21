#!/usr/bin/env python3
"""Ask the running Sulvana app every question of the Sulvana Hard benchmark (SHB) and save its answers.

    python3 benchmark/hard/run.py <label> [--translate local|google|off] [--temperature 0.4] [--max-tokens 2048]

Sulvana must be running (http://127.0.0.1:8766). Uses the app's default settings unless told otherwise.
Answers are appended to runs/benchmark-hard/<label>.jsonl, so an interrupted run resumes where it stopped.
The questions are for evaluation only: never train on them or put them in Sulvana's notes or prompts.
"""

from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = Path(__file__).resolve().parent / "questions.jsonl"


def ask(question: str, args: argparse.Namespace) -> dict:
    body = json.dumps({"prompt": question, "history": [], "maxTokens": args.max_tokens, "temperature": args.temperature,
                       "language": "Auto", "translate": args.translate if args.translate != "off" else None}).encode()
    text, events, metrics, started = "", [], {}, time.time()
    request = urllib.request.Request("http://127.0.0.1:8766/api/chat", data=body, headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=900) as response:
                for line in response:
                    kind, _, data = line.decode().strip("\n").partition("\t")
                    if kind == "t":
                        text += base64.b64decode(data).decode()
                    elif kind == "x":
                        text = ""; events.append("rewritten")
                    elif kind == "d":
                        metrics = json.loads(base64.b64decode(data))
                    elif kind == "e":
                        events.append("error: " + base64.b64decode(data).decode()[:200])
            break
        except OSError as error:            # busy (409) or a dropped connection: wait and try again
            events.append(f"retry after: {error}")
            time.sleep(20)
    if isinstance(metrics.get("clean_reply"), str) and metrics["clean_reply"]:
        text = metrics["clean_reply"]
    return {"answer": text, "seconds": round(time.time() - started, 1), "events": events,
            "khmer_tools": metrics.get("translated") or "", "model_language": metrics.get("model_language") or "",
            "truncated": bool(metrics.get("truncated"))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("label")
    parser.add_argument("--translate", choices=["off", "local", "google"], default="local")
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--max-tokens", type=int, default=2048)
    args = parser.parse_args()
    out = ROOT / "runs/benchmark-hard" / f"{args.label}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(line)["id"] for line in out.read_text(encoding="utf-8").splitlines() if line.strip()} if out.exists() else set()
    questions = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    for number, item in enumerate(questions, 1):
        if item["id"] in done:
            continue
        result = {**item, **ask(item["question"], args), "settings": {"translate": args.translate, "temperature": args.temperature}}
        with open(out, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        print(f"{number}/{len(questions)} {item['id']} {item['category']} {result['seconds']}s "
              + result["answer"][:90].replace("\n", " / "), flush=True)
    print("saved", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
