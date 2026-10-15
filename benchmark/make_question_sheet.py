#!/usr/bin/env python3
"""Render the JSONL benchmark as an answer-free plain-text question sheet."""

from __future__ import annotations

import json
import re
import textwrap
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "question_sheet.txt"
WIDTH = 100

CATEGORY_ORDER = [
    "mathematics",
    "science",
    "computing_ai",
    "general_knowledge",
    "language",
    "reasoning",
    "reading_comprehension",
    "safety_reliability",
]

CATEGORY_LABELS = {
    "mathematics": {"en": "MATHEMATICS", "km": "គណិតវិទ្យា"},
    "science": {"en": "SCIENCE", "km": "វិទ្យាសាស្ត្រ"},
    "computing_ai": {"en": "COMPUTING AND ARTIFICIAL INTELLIGENCE", "km": "កុំព្យូទ័រ និងបញ្ញាសិប្បនិម្មិត"},
    "general_knowledge": {"en": "GENERAL KNOWLEDGE AND CAMBODIA", "km": "ចំណេះដឹងទូទៅ និងកម្ពុជា"},
    "language": {"en": "ENGLISH LANGUAGE", "km": "ភាសាខ្មែរ"},
    "reasoning": {"en": "LOGICAL REASONING", "km": "ការគិតតាមតក្កវិជ្ជា"},
    "reading_comprehension": {"en": "READING COMPREHENSION", "km": "ការអានយល់ន័យ"},
    "safety_reliability": {"en": "SAFETY AND RELIABILITY", "km": "សុវត្ថិភាព និងភាពអាចទុកចិត្តបាន"},
}

DIFFICULTY_LABELS = {
    "basic": {"en": "Basic", "km": "មូលដ្ឋាន"},
    "intermediate": {"en": "Intermediate", "km": "មធ្យម"},
    "advanced": {"en": "Advanced", "km": "កម្រិតខ្ពស់"},
}


def load_questions() -> list[dict]:
    records = []
    with (ROOT / "questions.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    if len(records) != 800:
        raise SystemExit(f"Expected 800 questions, found {len(records)}")
    return records


def id_number(question: dict) -> int:
    return int(question["id"].split("-")[1])


def wrapped(text: str, initial: str = "", subsequent: str = "") -> list[str]:
    return textwrap.wrap(
        text,
        width=WIDTH,
        initial_indent=initial,
        subsequent_indent=subsequent,
        break_long_words=False,
        break_on_hyphens=False,
        replace_whitespace=False,
    ) or [initial]


def format_prompt(prompt: str) -> list[str]:
    lines = prompt.splitlines()
    output = []
    for line in lines:
        choice = re.match(r"^([A-D])\.\s+(.*)$", line)
        if choice:
            output.extend(wrapped(choice.group(2), initial=f"     {choice.group(1)}. ", subsequent="        "))
        else:
            output.extend(wrapped(line, initial="     ", subsequent="     "))
    return output


def answer_space(question: dict, language: str) -> list[str]:
    label = "Answer" if language == "en" else "ចម្លើយ"
    if question["answer_format"] == "multiple_choice":
        return [f"     {label}: ______"]
    return [f"     {label}: " + "_" * 72, ""]


def question_header(display_number: int, question: dict, language: str) -> str:
    difficulty = DIFFICULTY_LABELS[question["difficulty"]][language]
    return f"{display_number:03d}. [{question['id']}] [{difficulty}]"


def render_standard_section(items: list[dict], language: str, start_number: int) -> tuple[list[str], int]:
    output = []
    number = start_number
    for question in sorted(items, key=id_number):
        output.append(question_header(number, question, language))
        output.extend(format_prompt(question["prompt"]))
        output.extend(answer_space(question, language))
        output.append("")
        number += 1
    return output, number


def split_reading_prompt(prompt: str) -> tuple[str, str]:
    passage, question = prompt.split("\n\n", 1)
    passage = re.sub(r"^(?:Passage|អត្ថបទ):\s*", "", passage)
    return passage, question


def render_reading_section(items: list[dict], language: str, start_number: int) -> tuple[list[str], int]:
    groups: OrderedDict[str, list[tuple[dict, str]]] = OrderedDict()
    for item in sorted(items, key=id_number):
        passage, question = split_reading_prompt(item["prompt"])
        groups.setdefault(passage, []).append((item, question))

    output = []
    number = start_number
    passage_label = "PASSAGE" if language == "en" else "អត្ថបទ"
    instruction = (
        "Read the passage, then answer Questions"
        if language == "en"
        else "អានអត្ថបទ រួចឆ្លើយសំណួរ"
    )
    for passage_number, (passage, entries) in enumerate(groups.items(), start=1):
        first = number
        last = number + len(entries) - 1
        output.append(f"{passage_label} {passage_number} — {instruction} {first:03d}–{last:03d}")
        output.append("-" * WIDTH)
        output.extend(wrapped(passage))
        output.append("")
        for question, question_text in entries:
            output.append(question_header(number, question, language))
            output.extend(format_prompt(question_text))
            output.extend(answer_space(question, language))
            output.append("")
            number += 1
        output.append("")
    return output, number


def build_sheet(questions: list[dict]) -> str:
    lines = [
        "=" * WIDTH,
        "KHMER BILINGUAL AI BENCHMARK — HUMAN QUESTION SHEET".center(WIDTH),
        "កម្រងសំណួរវាយតម្លៃ AI ជាភាសាខ្មែរ និងអង់គ្លេស".center(WIDTH),
        "Version 1.0.0 — 800 questions — answer key not included".center(WIDTH),
        "=" * WIDTH,
        "",
        "Participant / Model: " + "_" * 50,
        "Evaluator:          " + "_" * 50,
        "Date:               " + "_" * 50,
        "",
        "INSTRUCTIONS / សេចក្តីណែនាំ",
        "- Answer every question without looking at the private answer key.",
        "- ឆ្លើយគ្រប់សំណួរ ដោយមិនមើលឯកសារចម្លើយឯកជន។",
        "- For multiple-choice questions, write the letter A, B, C, or D.",
        "- សម្រាប់សំណួរជ្រើសរើស សរសេរអក្សរ A, B, C ឬ D។",
        "- For other questions, give a short, direct answer unless the question says otherwise.",
        "- សម្រាប់សំណួរផ្សេងៗ ឆ្លើយខ្លី និងចំៗ លុះត្រាតែសំណួរប្រាប់ផ្សេង។",
        "- Use no internet, AI assistant, retrieval system, or human help during a closed-book benchmark.",
        "- កុំប្រើអ៊ីនធឺណិត AI ប្រព័ន្ធស្វែងរក ឬជំនួយពីមនុស្ស ក្នុងការធ្វើតេស្តបិទសៀវភៅ។",
        "",
    ]

    display_number = 1
    section_number = 1
    for language in ("km", "en"):
        language_heading = "ផ្នែកភាសាខ្មែរ" if language == "km" else "ENGLISH-LANGUAGE PART"
        lines.extend(["#" * WIDTH, language_heading.center(WIDTH), "#" * WIDTH, ""])
        for category in CATEGORY_ORDER:
            items = [
                item
                for item in questions
                if item["language"] == language and item["category"] == category
            ]
            if not items:
                continue
            label = CATEGORY_LABELS[category][language]
            lines.extend(
                [
                    "=" * WIDTH,
                    f"SECTION {section_number} — {label} — {len(items)} QUESTIONS",
                    "=" * WIDTH,
                    "",
                ]
            )
            if category == "reading_comprehension":
                rendered, display_number = render_reading_section(items, language, display_number)
            else:
                rendered, display_number = render_standard_section(items, language, display_number)
            lines.extend(rendered)
            section_number += 1

    if display_number != 801:
        raise SystemExit(f"Expected final display number 801, got {display_number}")
    lines.extend(
        [
            "=" * WIDTH,
            "END OF QUESTION SHEET / ចប់កម្រងសំណួរ".center(WIDTH),
            "=" * WIDTH,
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    sheet = build_sheet(load_questions())
    OUTPUT.write_text(sheet, encoding="utf-8")
    ids = re.findall(r"\[KBAI-\d{4}\]", sheet)
    if len(ids) != 800 or len(set(ids)) != 800:
        raise SystemExit("Question-sheet ID validation failed")
    print(f"Created {OUTPUT}")
    print(f"Questions: {len(ids)}")
    print(f"Characters: {len(sheet):,}")


if __name__ == "__main__":
    main()
