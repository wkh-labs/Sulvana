#!/usr/bin/env python3
"""Score answers to the Sulvana Khmer Benchmark (SKB).

Rules that the older benchmark's scorer lacked:
- Khmer items count only if the reply is written in Khmer script (at least half of its letters).
- A reply that merely copies text from the question gets no credit for it.
- Numbers: the first or the last number in the reply may match; Khmer digits are understood.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KHMER_DIGITS = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")
KHMER = re.compile(r"[ក-៿]")


def letters(text: str) -> list[str]:
    return [char for char in text if unicodedata.category(char)[0] in "LM"]


def is_khmer(text: str) -> bool:
    found = letters(text)
    return not found or sum(bool(KHMER.match(char)) for char in found) / len(found) >= 0.5


def is_english(text: str) -> bool:
    found = letters(text)
    return bool(found) and sum("LATIN" in unicodedata.name(char, "") for char in found) / len(found) >= 0.8


def without_copied_question(reply: str, prompt: str) -> str:
    """Remove long stretches copied word for word from the question (an echo is not an answer)."""
    for piece in re.split(r"[។\n?!:៖]", prompt):
        piece = piece.strip()
        if len(piece) >= 12:
            reply = reply.replace(piece, " ")
    return reply


def numbers(text: str) -> list[float]:
    text = unicodedata.normalize("NFKC", text).translate(KHMER_DIGITS)
    values = []
    for match in re.finditer(r"-?\d[\d,]*(?:\.\d+)?", text):
        try:
            values.append(float(match.group(0).replace(",", "")))
        except ValueError:
            pass
    return values


def check(reply: str, prompt: str, rule: dict) -> tuple[bool, str]:
    text = unicodedata.normalize("NFC", reply).strip()
    if not text:
        return False, "empty"
    if rule.get("require_khmer") and not is_khmer(text):
        return False, "not in Khmer"
    if rule.get("require_english") and not is_english(text):
        return False, "not in English"
    kind = rule["type"]
    if kind == "number":
        found = numbers(text)
        ok = bool(found) and any(abs(value - rule["value"]) <= rule["tolerance"] for value in (found[0], found[-1]))
        return ok, "" if ok else f"number {found[:3]} != {rule['value']}"
    body = without_copied_question(text, prompt).casefold()
    if kind == "contains":
        ok = any(alias.casefold() in body for alias in rule["any"])
        return ok, "" if ok else "expected answer missing"
    if kind == "keywords":
        missing = [group[0] for group in rule["groups"] if not any(word.casefold() in body for word in group)]
        return not missing, "" if not missing else f"missing {missing}"
    if kind == "starts":
        clean = re.sub(r"^[\s\"'«»“”*]+", "", text).casefold()
        ok = any(clean.startswith(alias.casefold()) for alias in rule["any"]) and (not rule.get("max_chars") or len(text) <= rule["max_chars"])
        return ok, "" if ok else "wrong start or too long"
    if kind == "format":
        problems = []
        if rule.get("max_chars") and len(text) > rule["max_chars"]:
            problems.append("too long")
        if "khmer_full_stops" in rule and text.count("។") != rule["khmer_full_stops"]:
            problems.append(f"{text.count('។')} sentences")
        if "numbered_lines" in rule:
            lines = [line for line in text.splitlines() if re.match(r"^\s*[\d០-៩]+\s*[.)។:-]", line)]
            if len(lines) != rule["numbered_lines"]:
                problems.append(f"{len(lines)} numbered lines")
        for word in rule.get("contains_all", []):
            if word.casefold() not in body:
                problems.append(f"missing {word}")
        if rule.get("contains_any") and not any(word in body for word in rule["contains_any"]):
            problems.append(f"missing {rule['contains_any'][0]}")
        for word, count in rule.get("count", {}).items():
            if text.count(word) != count:
                problems.append(f"{word} x{text.count(word)}")
        if rule.get("no_latin") and re.search(r"[A-Za-z]", text):
            problems.append("contains Latin letters")
        if rule.get("no_digits") and re.search(r"[0-9០-៩]", text):
            problems.append("contains digits")
        if rule.get("min_khmer_chars") and len(KHMER.findall(text)) < rule["min_khmer_chars"]:
            problems.append("too short")
        if rule.get("ordered"):
            positions = [body.find(word) for word in rule["ordered"]]
            if -1 in positions or positions != sorted(positions):
                problems.append("wrong order")
        if rule.get("number_sequence") and [int(v) for v in numbers(text)] != rule["number_sequence"]:
            problems.append("wrong sequence")
        return not problems, ", ".join(problems)
    raise ValueError(f"unknown check type {kind}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("responses", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    read = lambda path: [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    questions = {q["id"]: q for q in read(HERE / "questions.jsonl")}
    keys = {k["id"]: k["check"] for k in read(HERE / "answer_key.private.jsonl")}
    answers = {r["id"]: r.get("answer") or "" for r in read(args.responses)}
    totals, details = defaultdict(lambda: [0, 0]), []
    for item_id, question in questions.items():
        ok, why = check(answers.get(item_id, ""), question["prompt"], keys[item_id])
        for group in ("overall", f"section:{question['section']}", f"difficulty:{question['difficulty']}", f"language:{question['lang']}"):
            totals[group][0] += ok
            totals[group][1] += 1
        details.append({"id": item_id, "section": question["section"], "correct": ok, "reason": why, "answer": answers.get(item_id, "")})
    print(f"Sulvana Khmer Benchmark: {totals['overall'][0]}/{totals['overall'][1]} = {100 * totals['overall'][0] / totals['overall'][1]:.1f}%")
    for group in sorted(totals):
        if group != "overall":
            right, total = totals[group]
            print(f"  {group:32s} {right:3d}/{total:<3d} {100 * right / total:5.1f}%")
    if args.report:
        args.report.write_text(json.dumps({"totals": {k: v for k, v in totals.items()}, "items": details}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
