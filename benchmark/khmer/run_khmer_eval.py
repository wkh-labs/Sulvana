#!/usr/bin/env python3
"""Send the Khmer evaluation prompts through the running Sulvana app and score the replies."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
KHMER = re.compile(r"[ក-៿᧠-᧿]")
FOREIGN = {  # scripts a Khmer answer should never drift into
    "Thai": re.compile(r"[฀-๿]"), "Lao": re.compile(r"[຀-໿]"), "Myanmar": re.compile(r"[က-႟]"),
    "CJK": re.compile(r"[぀-ヿ㐀-鿿가-힯]"), "Cyrillic": re.compile(r"[Ѐ-ӿ]"),
    "Arabic": re.compile(r"[؀-ۿ]"), "Indic": re.compile(r"[ऀ-෿]"), "Vietnamese": re.compile(r"[Ạ-ỹăđơưĂĐƠƯ]"),
}
CODE = re.compile(r"```.*?(```|$)|`[^`\n]+`", re.S)
CONSONANT = "ក-អ"
MALFORMED = re.compile(
    rf"្(?![{CONSONANT}])"              # coeng not followed by a consonant
    rf"|(?<![{CONSONANT}ឣ-ឳា-៓៝​‌‍])[ា-៑៓៝]"  # mark without a base
    r"|([ា-ៅ])\1"                  # the same dependent vowel twice
    r"|�")


def runaway(text: str) -> bool:
    words = text.casefold().split()
    for width in range(1, 13):
        if len(words) >= width * 4 and words[-width * 4:] == words[-width:] * 4:
            return True
    tail = "".join(text.split())[-600:]
    return any(len(tail) >= width * 5 and tail[-width * 5:] == tail[-width:] * 5 and KHMER.search(tail[-width:]) for width in range(3, 61))


def score(item: dict, reply: str, metrics: dict, max_tokens: int) -> dict:
    prose = CODE.sub(" ", reply)
    letters = [char for char in prose if unicodedata.category(char)[0] in "LM"]
    khmer = sum(bool(KHMER.match(char)) for char in letters)
    latin = sum("LATIN" in unicodedata.name(char, "") for char in letters)
    foreign = {name: len(pattern.findall(prose)) for name, pattern in FOREIGN.items() if pattern.search(prose)}
    wanted = item.get("reply", item["lang"])
    khmer_share = khmer / len(letters) if letters else 0.0
    latin_share = latin / len(letters) if letters else 0.0
    right_language = bool(letters) and (khmer_share >= 0.6 if wanted == "km" else latin_share >= 0.8)
    expected = item.get("expect_any")
    return {
        "id": item["id"], "prompt": item["prompt"], "reply": reply, "wanted_language": wanted,
        "khmer_share": round(khmer_share, 3), "latin_share": round(latin_share, 3),
        "right_language": right_language, "foreign_scripts": foreign,
        "malformed_khmer": len(MALFORMED.findall(prose)), "runaway_repetition": runaway(reply),
        "cut_off": metrics.get("output_tokens", 0) >= max_tokens, "empty": not reply.strip(),
        "expected_found": None if not expected else any(needle.casefold() in reply.casefold() for needle in expected),
        "output_tokens": metrics.get("output_tokens", 0), "tokens_per_second": round(metrics.get("tokens_per_second", 0), 1),
        "seconds": metrics.get("seconds"), "error": metrics.get("error"),
    }


def ask(base_url: str, prompt: str, max_tokens: int, temperature: float, language: str) -> tuple[str, dict]:
    body = json.dumps({"prompt": prompt, "history": [], "maxTokens": max_tokens, "temperature": temperature, "language": language}).encode()
    request = urllib.request.Request(base_url + "/api/chat", data=body, headers={"Content-Type": "application/json"}, method="POST")
    reply, metrics, started = "", {}, time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            for raw in response:
                kind, _, data = raw.decode("ascii").rstrip("\n").partition("\t")
                text = base64.b64decode(data).decode("utf-8", errors="replace")
                if kind == "t":
                    reply += text
                elif kind == "d":
                    metrics = json.loads(text)
                elif kind == "e":
                    metrics["error"] = text
    except Exception as error:  # the report should show a failed prompt, not stop the run
        metrics["error"] = f"{type(error).__name__}: {error}"
    metrics["seconds"] = round(time.perf_counter() - started, 1)
    return reply.strip(), metrics


def wait_ready(base_url: str, seconds: int = 120) -> dict:
    for _ in range(seconds):
        try:
            with urllib.request.urlopen(base_url + "/api/status", timeout=3) as response:
                status = json.loads(response.read())
            if status.get("state") == "ready":
                return status
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit("Sulvana's engine is not ready. Start it with `sulvana` first.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="name of this run, e.g. baseline")
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--language", default="Auto", help="the app's reply-language setting")
    parser.add_argument("--prompts", default=str(HERE / "prompts.jsonl"))
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,60}", args.label):
        raise SystemExit("--label may only contain letters, digits, dot, dash and underscore")
    status = wait_ready(args.base_url)
    items = [json.loads(line) for line in Path(args.prompts).read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for item in items:
        wait_ready(args.base_url, 60)
        reply, metrics = ask(args.base_url, item["prompt"], args.max_tokens, args.temperature, args.language)
        rows.append(score(item, reply, metrics, args.max_tokens))
        row = rows[-1]
        print(f"{row['id']:18s} lang={'ok ' if row['right_language'] else 'BAD'} khmer={row['khmer_share']:.2f} "
              f"foreign={','.join(row['foreign_scripts']) or '-':10s} malformed={row['malformed_khmer']} "
              f"{'REPEAT ' if row['runaway_repetition'] else ''}{'CUT ' if row['cut_off'] else ''}"
              f"{'' if row['expected_found'] is None else ('hit ' if row['expected_found'] else 'MISS ')}{row['output_tokens']} tok", flush=True)
    khmer_rows = [row for row in rows if row["wanted_language"] == "km"]
    checked = [row for row in rows if row["expected_found"] is not None]
    share = lambda part, whole: f"{sum(part)}/{len(whole)}"
    summary = {
        "right_language_khmer_prompts": share([r["right_language"] for r in khmer_rows], khmer_rows),
        "right_language_all": share([r["right_language"] for r in rows], rows),
        "clean_script_khmer_replies": share([not r["foreign_scripts"] and not r["malformed_khmer"] for r in khmer_rows], khmer_rows),
        "no_runaway_repetition": share([not r["runaway_repetition"] for r in rows], rows),
        "not_cut_off": share([not r["cut_off"] for r in rows], rows),
        "expected_content_found": share([r["expected_found"] for r in checked], checked),
        "errors": sum(bool(r["error"]) for r in rows),
        "mean_tokens_per_second": round(sum(r["tokens_per_second"] for r in rows) / max(1, len(rows)), 1),
    }
    report = {"label": args.label, "run_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "engine": status.get("detail"),
              "settings": {"max_tokens": args.max_tokens, "temperature": args.temperature, "language": args.language},
              "summary": summary, "replies": rows}
    out = ROOT / "runs" / "khmer-eval"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.label}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f"# Khmer evaluation: {args.label}", "", f"Engine: {status.get('detail')}", "", "| measure | result |", "|---|---|"]
    lines += [f"| {key.replace('_', ' ')} | {value} |" for key, value in summary.items()]
    for row in rows:
        flags = [name for name, on in (("wrong language", not row["right_language"]), ("foreign script", bool(row["foreign_scripts"])),
                                       ("malformed Khmer", bool(row["malformed_khmer"])), ("repetition", row["runaway_repetition"]),
                                       ("cut off", row["cut_off"]), ("expected content missing", row["expected_found"] is False)) if on]
        lines += ["", f"## {row['id']}" + (f" — {', '.join(flags)}" if flags else ""), "", f"**Prompt:** {row['prompt']}", "", row["reply"] or "(no reply)"]
    (out / f"{args.label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(f"{key.replace('_', ' '):32s} {value}" for key, value in summary.items()))
    print(f"\nwritten: {out / (args.label + '.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
