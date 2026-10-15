# Khmer evaluation for Sulvana

A small, repeatable check of how Sulvana behaves as a Khmer-first assistant. It sends the
prompts in `prompts.jsonl` through the running app (the same path the chat window uses) and
scores each reply automatically.

The prompts were written for this check; they are not user data and are not for training.

```bash
sulvana                                   # or any way of starting the engine
python3 benchmark/khmer/run_khmer_eval.py --label my-change
```

Results land in `runs/khmer-eval/<label>.json` and `.md` (replies included, so a Khmer
reader can judge fluency, which the script cannot).

What is scored:

- **Right language** – replies to Khmer prompts are mostly Khmer script; replies to English
  prompts are mostly Latin script.
- **Clean script** – no Thai, Lao, CJK or other foreign letters mixed into a Khmer reply, no
  broken characters, no malformed Khmer sequences.
- **No runaway repetition** and **not cut off** by the reply-length limit.
- **Expected content** for the few prompts that have a checkable answer.

These are proxies. They catch a reply in the wrong language or with garbled script; they do
not measure grammar or word choice.
