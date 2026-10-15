# Datasets

Training data for the Dolphin fine-tuning workflow in `finetune/`.

**There is no real dataset here yet.** Nothing in this folder was written by, or collected from,
the owner of this workspace.

- `fixtures/synthetic-smoke.jsonl` is a small **synthetic** file written only to test that the
  pipeline runs. Every record carries
  `"meta": {"synthetic": true, "purpose": "pipeline smoke test", "not_user_data": true}`.
  Do not train a real adapter on it.
- Everything else you put under `datasets/` is ignored by git (only this README and the fixture
  are tracked), so private conversations stay out of version control. Sulvana's own inspection
  tools are not allowed to read files in this folder either.

## Format

JSON Lines, UTF-8, one conversation per line:

```json
{"messages": [{"role": "user", "content": "What is the capital of France?"}, {"role": "assistant", "content": "Paris."}]}
{"messages": [{"role": "system", "content": "You are Sulvana."}, {"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}, {"role": "user", "content": "Who are you?"}, {"role": "assistant", "content": "I'm Sulvana, your local assistant."}]}
```

Rules, enforced by `finetune/validate_dataset.py`:

- `messages` is a list of `{"role", "content"}` objects with roles `system`, `user`, `assistant`.
- A `system` message is optional and only allowed first.
- After it, `user` and `assistant` alternate, starting with `user` and ending with `assistant`.
- `content` is non-empty text; assistant text has no leading or trailing whitespace.
- No control tokens such as `<|im_start|>` or `<|im_end|>` inside the text.
- An optional `meta` object is allowed and ignored by training.

Only assistant messages are learned from. Conversations longer than `data.max_seq_length`
tokens (512 by default) are cut at that length; the validator reports how many.

## Typical layout

```
datasets/my-data/all.jsonl      your conversations
datasets/my-data/train.jsonl    written by split_dataset.py
datasets/my-data/val.jsonl      written by split_dataset.py
datasets/my-data/split-manifest.json
```

```bash
.venv/bin/python finetune/validate_dataset.py datasets/my-data/all.jsonl
.venv/bin/python finetune/split_dataset.py --input datasets/my-data/all.jsonl --out-dir datasets/my-data --val-fraction 0.1
```

The split is decided per conversation from a hash of its content, so adding lines later and
splitting again never moves an existing conversation between train and validation.
