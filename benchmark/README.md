# Khmer Bilingual AI Benchmark

This is an original, deterministic benchmark for evaluating a small
Khmer-focused language model. It contains 800 questions and no scraped text.

## Coverage

| Area | Questions |
|---|---:|
| Mathematics | 320 |
| Science | 100 |
| Computing and AI | 100 |
| General knowledge and Cambodia | 80 |
| Khmer and English language | 80 |
| Logical reasoning | 50 |
| Safety and reliability | 40 |
| Reading comprehension | 30 |

There are 400 Khmer questions and 400 English questions. Difficulty is tagged
as basic, intermediate, or advanced. The fixed split contains 160 development
questions and 640 final-test questions.

## Files

- `questions.jsonl` — prompts and metadata, with no answers.
- `answer_key.private.jsonl` — expected answers. Keep this away from the model.
- `manifest.json` — version, seed, provenance, and exact distribution.
- `build_benchmark.py` — reproduces all generated files exactly.
- `score_responses.py` — scores answers and reports category breakdowns.
- `question_sheet.txt` — answer-free, human-readable sheet containing all 800 questions.
- `make_question_sheet.py` — rebuilds the human-readable question sheet.

Each line of a response file must look like this:

```json
{"id": "KBAI-0001", "answer": "42"}
```

Score the private test split:

```bash
source /home/tanchjim/Documents/Codex/ai-workspace/activate-ai.sh
python /home/tanchjim/Documents/Codex/ai-workspace/benchmark/score_responses.py \
  /path/to/model-responses.jsonl \
  --split test \
  --report /path/to/report.json
```

Use `--split dev` while fixing your evaluation code. Use the test split only
for real milestone results. Unanswered questions count as incorrect.

## Rules for an honest result

1. Never put `answer_key.private.jsonl`, scored reports, or test answers in
   training data, retrieval documents, prompts, or model context.
2. Freeze the model and evaluation settings before running the test split.
3. Use temperature 0 or greedy decoding, a consistent prompt, and the same
   token limit for every compared model.
4. For the knowledge score, disable web search, terminal tools, retrieval, and
   human help. Tool-using ability should be measured as a separate benchmark.
5. Report overall accuracy plus Khmer, English, subject, and difficulty
   breakdowns. Do not report only the best category.
6. Preserve failed answers. They are more useful for improving the model than
   a single final percentage.

The automatic scorer accepts common aliases and short explanatory responses,
but language can be ambiguous. Manually review a sample of marked-wrong answers
before publishing a final score.

## License and versioning

The benchmark is original synthetic content released as CC0-1.0. If any
question or answer is corrected, increment the benchmark version in
`build_benchmark.py`, rebuild it, and do not directly compare scores from the
old and new versions without saying so.
