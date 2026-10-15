#!/usr/bin/env python3
"""Generate Khmer instruction data with the Gemini API, in batches, with quality filters.

The API key is read from the environment and never written anywhere:

    export GEMINI_API_KEY=...            # fish: set -x GEMINI_API_KEY ...
    .venv/bin/python finetune/generate_gemini.py --list-models
    .venv/bin/python finetune/generate_gemini.py --model <model-id> --target 4000

Output: datasets/khmer-gemini/raw.jsonl (accepted examples, appended; the run resumes where it
stopped) and rejected.jsonl (what the filters threw out, with the reason). Data generated with
Gemini is for non-commercial use (see NOTICE.md).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

API = "https://generativelanguage.googleapis.com/v1beta"
OUT = common.WORKSPACE / "datasets" / "khmer-gemini"
KHMER = re.compile(r"[ក-៿]")
THAI_LAO = re.compile(r"[฀-໿]")

TASKS = {
    "math_word_problem": "a maths word problem set in everyday Cambodian life (riel, kilograms, time, ages, distances, markets, school)",
    "logic_puzzle": "a short logic or reasoning puzzle with one clear answer",
    "cambodia_fact": "a question about Cambodian history, geography, culture, festivals, government or famous places, answered only with facts you are certain of",
    "science_explanation": "a science or health question a high-school student might ask",
    "writing_task": "a writing request (formal letter, message, short essay, invitation, announcement, CV paragraph)",
    "summarization": "a summary request that includes a short Khmer passage (3–6 sentences) you write inside the request",
    "translation_en_km": "an English sentence or short paragraph to translate into natural Khmer",
    "translation_km_en": "a Khmer sentence or short paragraph to translate into English",
    "everyday_advice": "practical everyday advice (study, money, cooking, phones, health habits, farming, travel in Cambodia)",
    "programming": "a beginner programming question (Python or JavaScript) answered in Khmer with a short code example",
    "explanation": "an explanation of a concept (economics, technology, history, language, ethics) for a student",
    "conversation": "a casual question or request a Cambodian user might send to a chat assistant",
}

PROMPT = """You write training data for a Khmer-first AI assistant. Write {n} NEW, varied examples.
Each example is one user request in Khmer and the ideal assistant reply in Khmer.
All {n} examples are of this type: {task_text}.
For variety, make them about: {themes}.

Khmer quality (most important):
- Natural, modern Khmer as written by an educated native speaker in Cambodia. Correct spelling. Never romanize. Sentences end with ។.
- Use Khmer digits (០–៩) in prose; code, formulas and English names stay as they are.
- Keep English technical terms (Python, Wi-Fi, GDP) when Khmer speakers normally do.

Reply style:
- Maths, logic, "how many/which" questions: short step-by-step working, then the final answer on its own line starting with "ចម្លើយ៖".
- Facts: be accurate. If something is uncertain, say so instead of guessing. Never invent dates, numbers or names.
- Writing tasks: well structured, appropriate length, no filler.
- Keep every reply under about 250 words. Answer exactly what was asked; no repeated phrases.

Return a JSON array of objects, each {{"user": "...", "assistant": "..."}}."""

THEMES = ["markets and shopping", "school and exams", "farming and rice", "Phnom Penh city life", "Siem Reap and tourism",
          "Mekong and Tonle Sap", "family and festivals", "health and food", "phones and the internet", "jobs and business",
          "provinces of Cambodia", "Khmer New Year and Pchum Ben", "transport and travel", "sport and games", "nature and weather",
          "money and saving", "Angkor and history", "science at school", "technology and AI", "cooking Khmer food"]

SCHEMA = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"user": {"type": "STRING"}, "assistant": {"type": "STRING"}},
                                        "required": ["user", "assistant"]}}


def api(path: str, body: dict | None = None) -> dict:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise SystemExit("Set GEMINI_API_KEY in your shell first (it is never stored).")
    request = urllib.request.Request(f"{API}/{path}", data=json.dumps(body).encode() if body else None,
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key},
                                     method="POST" if body else "GET")
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def problems(user: str, answer: str, task: str, seen: set[str]) -> list[str]:
    reasons = []
    messages = [{"role": "user", "content": user.strip()}, {"role": "assistant", "content": answer.strip()}]
    reasons += common.check_messages(messages)
    text = user + answer
    if THAI_LAO.search(text):
        reasons.append("thai/lao characters")
    khmer_share = len(KHMER.findall(answer)) / max(1, len(re.sub(r"\s|`[^`]*`|```.*?```", "", answer, flags=re.S)))
    if task != "translation_km_en" and khmer_share < 0.5:
        reasons.append(f"answer only {khmer_share:.0%} Khmer")
    if task in {"math_word_problem", "logic_puzzle"} and "ចម្លើយ៖" not in answer:
        reasons.append("no final-answer line")
    if len(answer) > 3500:
        reasons.append("answer too long")
    words = answer.split()
    if len(words) > 40 and len(set(words)) / len(words) < 0.3:
        reasons.append("repetitive")
    key = re.sub(r"\s+", "", user)[:200]
    if key in seen:
        reasons.append("duplicate request")
    return reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", help="Gemini model id (see --list-models)")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--target", type=int, default=4000, help="stop when this many accepted examples exist")
    parser.add_argument("--batch", type=int, default=15, help="examples per request")
    parser.add_argument("--pause", type=float, default=4.0, help="seconds between requests (rate limits)")
    args = parser.parse_args()

    if args.list_models:
        for model in api("models?pageSize=200").get("models", []):
            if "generateContent" in model.get("supportedGenerationMethods", []):
                print(model["name"].removeprefix("models/"), "-", model.get("displayName", ""))
        return 0
    if not args.model:
        raise SystemExit("Pass --model (list them with --list-models).")

    OUT.mkdir(parents=True, exist_ok=True)
    raw, rejected = OUT / "raw.jsonl", OUT / "rejected.jsonl"
    seen, count = set(), 0
    if raw.exists():
        for line in raw.read_text(encoding="utf-8").splitlines():
            seen.add(re.sub(r"\s+", "", json.loads(line)["messages"][0]["content"])[:200]); count += 1
    rng = random.Random()
    failures = 0
    while count < args.target:
        task = rng.choice(list(TASKS))
        themes = ", ".join(rng.sample(THEMES, 3))
        body = {"contents": [{"role": "user", "parts": [{"text": PROMPT.format(n=args.batch, task_text=TASKS[task], themes=themes)}]}],
                "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json", "responseSchema": SCHEMA}}
        try:
            reply = api(f"models/{args.model}:generateContent", body)
            items = json.loads(reply["candidates"][0]["content"]["parts"][0]["text"])
            failures = 0
        except urllib.error.HTTPError as error:
            failures += 1
            wait = min(300, 10 * 2 ** min(failures, 5)) if error.code in (429, 500, 503) else 0
            print(f"HTTP {error.code}: {error.read()[:200]!r}" + (f"; waiting {wait}s" if wait else ""), flush=True)
            if not wait or failures > 8:
                return 1
            time.sleep(wait); continue
        except (KeyError, IndexError, ValueError, OSError) as error:
            failures += 1
            print(f"bad response ({type(error).__name__}); retrying", flush=True)
            if failures > 8:
                return 1
            time.sleep(10); continue
        kept = 0
        with open(raw, "a", encoding="utf-8") as good, open(rejected, "a", encoding="utf-8") as bad:
            for item in items if isinstance(items, list) else []:
                user, answer = str(item.get("user", "")), str(item.get("assistant", ""))
                reasons = problems(user, answer, task, seen)
                record = {"messages": [{"role": "user", "content": user.strip()}, {"role": "assistant", "content": answer.strip()}],
                          "meta": {"source": f"gemini:{args.model}", "task": task, "synthetic": True}}
                if reasons:
                    bad.write(json.dumps({**record, "rejected": reasons}, ensure_ascii=False) + "\n")
                    continue
                good.write(json.dumps(record, ensure_ascii=False) + "\n")
                seen.add(re.sub(r"\s+", "", user)[:200]); count += 1; kept += 1
        print(f"{time.strftime('%H:%M:%S')} {task:<20} kept {kept}/{len(items) if isinstance(items, list) else 0}  total {count}/{args.target}", flush=True)
        time.sleep(args.pause)
    print("target reached:", count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
