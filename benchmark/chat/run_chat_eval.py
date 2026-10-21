#!/usr/bin/env python3
"""Ask the running Sulvana app the 24 everyday Khmer questions in prompts.json and save its answers.

    python3 benchmark/chat/run_chat_eval.py <label> [--temperature 0.4] [--translate local|google]

Sulvana must be running (http://127.0.0.1:8766). Answers go to runs/chat-eval/<label>.json, for a person
to read and compare between versions; there is no automatic score. These questions are for evaluation
only and must not be used as training data.
"""

from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ask(prompt: str, temperature: float, translate: str) -> dict:
    body = json.dumps({"prompt": prompt, "history": [], "maxTokens": 900, "temperature": temperature,
                       "language": "Auto", "translate": translate}).encode()
    text, events, started = "", [], time.time()
    request = urllib.request.Request("http://127.0.0.1:8766/api/chat", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            for line in response:
                kind, _, data = line.decode().strip("\n").partition("\t")
                if kind == "t":
                    text += base64.b64decode(data).decode()
                elif kind == "x":
                    text = ""; events.append("retry")
                elif kind == "d":
                    language = json.loads(base64.b64decode(data)).get("model_language")
                    if language:
                        events.append(f"model:{language}")
                elif kind == "s":
                    events.append("sources")
                elif kind == "e":
                    events.append("error: " + base64.b64decode(data).decode()[:200])
    except OSError as error:
        events.append(f"error: {error}")
    return {"answer": text, "events": events, "seconds": round(time.time() - started, 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("label")
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--translate", choices=["off", "local", "google"], default="off", help="Better Khmer translator")
    args = parser.parse_args()
    prompts = json.loads((Path(__file__).parent / "prompts.json").read_text(encoding="utf-8"))
    out = ROOT / "runs/chat-eval" / f"{args.label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for item in prompts:
        result = {**item, **ask(item["prompt"], args.temperature, args.translate)}
        results.append(result)
        print(f"## {item['key']} {result['seconds']}s {' '.join(result['events'])} | "
              + result["answer"][:380].replace("\n", " / "), flush=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
