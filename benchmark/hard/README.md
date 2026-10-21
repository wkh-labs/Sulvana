# Sulvana Hard Benchmark (SHB)

253 hard questions for the whole Sulvana app (model, notes, Khmer tools), mostly in Khmer. A strong model should
get nearly everything right; Sulvana 2.0 is not expected to.

| Category | Count | What it tests |
|---|---|---|
| math_km | 45 | Multi-step Khmer word problems: change, discount then tax, average speed, ages, work rate, money |
| math_en | 15 | Classic traps (average speed, bat and ball), modular arithmetic, interest, a derivative |
| logic | 20 | Ordering, syllogisms, counting, sequences, riddles |
| dates | 16 | Weekdays of historic dates, day counts, Khmer and lunar months, zodiac years |
| code_output | 20 | Exact output of short Python snippets with common pitfalls |
| cambodia_facts | 30 | Provincial capitals, borders, history dates, heritage sites |
| khmer_language | 24 | Classifiers, royal vocabulary, grammar, word meanings, numbers written as Khmer words |
| translation | 18 | English↔Khmer with dates, months, numbers and classifiers that must be exact |
| science | 25 | Physics, biology and health questions, including common misconceptions |
| instruction_following | 20 | Strict output formats (number only, exactly N lines, JSON, no letter "e") |
| reading | 10 | Short Khmer passages with questions that need reasoning |
| trick | 10 | Riddles and wording traps |

Files:
- `questions.jsonl`: the questions (id, category, language, question).
- `answer_key.private.jsonl`: reference answers and notes. Private: never committed, never used for training,
  never put in Sulvana's notes or prompts. It is only for the person or agent grading answers.
- `build.private.py`: rebuilds both files. Maths, dates, code output and Khmer number words are computed by the
  script, not written by hand. Private, because it contains the answers.
- `run.py`: asks the running app every question and saves answers to `runs/benchmark-hard/<label>.jsonl`.
- `REVIEW_PROMPT.md`: instructions for an agent (e.g. Antigravity) to grade a run.

Run: `python3 benchmark/hard/run.py <label> [--translate local|google|off]`.
