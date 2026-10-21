You are grading a Khmer-first AI assistant called Sulvana on a hard benchmark. Be a strict, careful examiner who
reads Khmer fluently. Work in this folder: /home/tanchjim/Documents/Codex/ai-workspace

## Files
- Sulvana's answers: runs/benchmark-hard/sulvana-2.0-local.jsonl
  One JSON object per line: id, category, language, question, answer (Sulvana's reply), plus run details.
- Reference answers: benchmark/hard/answer_key.private.jsonl
  One JSON object per line: id, answer (the reference), notes (working or rubric), kind:
  "exact" = one correct answer; "judged" = judge meaning and quality; "format" = the instruction's format must be followed exactly.

## How to grade each of the 253 answers
1. Read the question, the reference answer and notes, and Sulvana's answer.
2. Score **correct** as 1 (fully right), 0.5 (partly right, or right answer with a real mistake in the explanation),
   or 0 (wrong, missing, or does not answer the question).
   - Numbers may be written with Khmer digits (០–៩) or Arabic digits, and with any thousands separator: ២៤ ៥០០ = 24,500.
   - "exact" items: the final answer must match. Wrong working with the right final number is 0.5.
   - "format" items: the answer must follow the instruction exactly (only a number, exactly N lines, valid JSON,
     no letter "e", Khmer or English as asked). A correct answer in the wrong format scores 0.5 at most.
   - "judged" items: compare meaning with the reference; accept any equivalent correct answer.
   - Translation items: the meaning must be complete, and dates, months, numbers and names must be exact
     (for example May is ខែឧសភា, not ខែមេសា).
3. For answers written in Khmer, also score **khmer** as 2 (natural, correctly spelled), 1 (understandable but with
   wrong words, misspellings or awkward phrasing), or 0 (garbled, mixed with unexpected English, or unreadable).
   Use null for answers that are correctly in English.
4. Write a short **problem** note in English naming the specific mistake (empty if none).
5. If you believe the **reference answer itself is wrong or ambiguous**, do not guess silently: grade by what is
   actually true, and set "key_issue" to explain what is wrong with the reference.

## Output
1. Write runs/benchmark-hard/sulvana-2.0-local.review.jsonl, one line per question, in the same order:
   {"id": "...", "category": "...", "correct": 1|0.5|0, "khmer": 2|1|0|null, "problem": "...", "key_issue": ""}
2. Write runs/benchmark-hard/sulvana-2.0-local.review.md with:
   - Overall score: sum of "correct" out of 253, and as a percentage.
   - A table per category: number of questions, score, percentage, average Khmer score.
   - The 10 most common kinds of mistakes, each with 2–3 example ids.
   - Every "key_issue" you found, listed separately so the reference answers can be fixed.
   - 5 concrete suggestions for improving Sulvana (prompting, notes, tools or training), based on the mistakes.

## Rules
- Only create the two output files above. Do not edit, move or delete any other file, including the questions,
  the reference answers and Sulvana's answers.
- Do not copy these questions or answers into any training data, dataset, notes or knowledge file. This benchmark
  must stay unseen by Sulvana's training.
- Do not run Sulvana or any other program, and do not change the app.
- Grade all 253 answers; if you must stop early, say how far you got at the top of the .md file.
