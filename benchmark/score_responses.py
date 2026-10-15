#!/usr/bin/env python3
"""Score model responses against the private benchmark key."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise SystemExit(f"Invalid JSON in {path} on line {line_number}: {error}") from error
    return records


def normalize(value) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = re.sub(r"^[\s\"'`]*(?:the answer is|answer|ចម្លើយ(?:គឺ)?)\s*[:=]?\s*", "", text)
    text = re.sub(r"[\s\"'`.,;:!?។]+$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def first_number(value) -> float | None:
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", unicodedata.normalize("NFKC", str(value)))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def exact_match(response, accepted: list[str]) -> bool:
    candidate = normalize(response)
    for alias in accepted:
        expected = normalize(alias)
        if candidate == expected:
            return True
        if len(expected) >= 4:
            pattern = rf"(?<![\w]){re.escape(expected)}(?![\w])"
            if re.search(pattern, candidate, flags=re.UNICODE):
                return True
    return False


def is_correct(response, answer: dict) -> bool:
    answer_type = answer["type"]
    if answer_type == "numeric":
        candidate = first_number(response)
        if candidate is None:
            return False
        return abs(candidate - float(answer["value"])) <= float(answer.get("tolerance", 0.0))
    if answer_type == "multiple_choice":
        candidate = normalize(response)
        label = str(answer["value"]).casefold()
        if re.match(rf"^{re.escape(label)}(?:\b|[.)\]:-])", candidate):
            return True
        return exact_match(response, answer.get("accepted", []))
    return exact_match(response, answer.get("accepted", [str(answer["value"])]))


def percent(correct: int, total: int) -> float:
    return 100.0 * correct / total if total else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score JSONL responses containing one {'id': ..., 'answer': ...} object per line."
    )
    parser.add_argument("responses", type=Path)
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--report", type=Path, help="Optional path for a detailed JSON report")
    args = parser.parse_args()

    questions = {item["id"]: item for item in read_jsonl(ROOT / "questions.jsonl")}
    keys = {item["id"]: item for item in read_jsonl(ROOT / "answer_key.private.jsonl")}
    response_records = read_jsonl(args.responses)

    responses = {}
    duplicates = []
    for record in response_records:
        if "id" not in record or "answer" not in record:
            raise SystemExit("Every response needs both an 'id' and an 'answer' field.")
        if record["id"] in responses:
            duplicates.append(record["id"])
        responses[record["id"]] = record["answer"]
    if duplicates:
        raise SystemExit(f"Duplicate response IDs: {', '.join(sorted(set(duplicates)))}")

    selected = [
        question
        for question in questions.values()
        if args.split == "all" or question["split"] == args.split
    ]
    selected.sort(key=lambda item: item["id"])

    dimensions = {
        "category": defaultdict(Counter),
        "language": defaultdict(Counter),
        "difficulty": defaultdict(Counter),
        "split": defaultdict(Counter),
    }
    details = []
    correct_total = 0
    answered_total = 0

    for question in selected:
        qid = question["id"]
        answered = qid in responses
        correct = answered and is_correct(responses[qid], keys[qid]["answer"])
        answered_total += int(answered)
        correct_total += int(correct)
        for dimension in dimensions:
            bucket = dimensions[dimension][question[dimension]]
            bucket["total"] += 1
            bucket["answered"] += int(answered)
            bucket["correct"] += int(correct)
        details.append(
            {
                "id": qid,
                "correct": correct,
                "answered": answered,
                "response": responses.get(qid),
                "expected": keys[qid]["answer"]["value"],
            }
        )

    unknown_ids = sorted(set(responses) - set(questions))
    summary = {
        "split": args.split,
        "total": len(selected),
        "answered": answered_total,
        "correct": correct_total,
        "accuracy_percent": round(percent(correct_total, len(selected)), 2),
        "accuracy_on_answered_percent": round(percent(correct_total, answered_total), 2),
        "unknown_response_ids": unknown_ids,
        "breakdown": {},
    }
    for dimension, groups in dimensions.items():
        summary["breakdown"][dimension] = {
            name: {
                **counts,
                "accuracy_percent": round(percent(counts["correct"], counts["total"]), 2),
            }
            for name, counts in sorted(groups.items())
        }

    print(f"Split: {args.split}")
    print(f"Coverage: {answered_total}/{len(selected)}")
    print(f"Score: {correct_total}/{len(selected)} ({summary['accuracy_percent']:.2f}%)")
    for dimension in ("language", "difficulty", "category"):
        print(f"\n{dimension.title()}:")
        for name, counts in summary["breakdown"][dimension].items():
            print(
                f"  {name:24} {counts['correct']:>3}/{counts['total']:<3} "
                f"{counts['accuracy_percent']:>6.2f}%"
            )
    if unknown_ids:
        print(f"\nWarning: ignored {len(unknown_ids)} unknown response IDs.")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps({"summary": summary, "details": details}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nDetailed report: {args.report}")


if __name__ == "__main__":
    main()
