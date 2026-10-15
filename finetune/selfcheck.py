#!/usr/bin/env python3
"""Fast checks of the fine-tuning pipeline that need neither the GPU nor the 16 GB checkpoint."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

common.setup_environment(offline=True)

from gguf_meta import read_metadata  # noqa: E402

HERE = Path(__file__).resolve().parent
FIXTURE = common.WORKSPACE / "datasets" / "fixtures" / "synthetic-smoke.jsonl"
CONFIG = common.load_config()
TOKENIZER = common.load_tokenizer(CONFIG)
CHECKS = []


def check(function):
    CHECKS.append(function)
    return function


def supervised_text(messages: list[dict], limit: int = 4096) -> str:
    result = common.encode(TOKENIZER, messages, limit)
    return TOKENIZER.decode([token for token, label in zip(result["input_ids"], result["labels"]) if label != -100])


def script(name: str, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HERE / name), *arguments], capture_output=True, text=True)


def write_lines(folder: Path, name: str, rows: list) -> Path:
    path = folder / name
    path.write_text("".join((row if isinstance(row, str) else json.dumps(row, ensure_ascii=False)) + "\n" for row in rows), encoding="utf-8")
    return path


def chat(*turns: str, system: str | None = None) -> dict:
    messages = [{"role": "system", "content": system}] if system else []
    for index, text in enumerate(turns):
        messages.append({"role": "user" if index % 2 == 0 else "assistant", "content": text})
    return {"messages": messages}


@check
def labels_cover_exactly_the_answer_single_turn():
    assert supervised_text(chat("Hi there", "Hello!")["messages"]) == "Hello!<|im_end|>"


@check
def labels_cover_every_answer_multi_turn_with_system():
    messages = chat("One?", "First answer.", "Two?", "Second\nanswer.", system="Be brief.")["messages"]
    assert supervised_text(messages) == "First answer.<|im_end|>Second\nanswer.<|im_end|>"


@check
def labels_survive_khmer_arabic_and_emoji():
    answer = "សួស្តី! مرحبا 👋 ok"
    assert supervised_text(chat("សួស្តី", answer)["messages"]) == answer + "<|im_end|>"


@check
def prompt_tokens_are_never_supervised():
    result = common.encode(TOKENIZER, chat("Question?", "Answer.", system="System text.")["messages"], 4096)
    masked = TOKENIZER.decode([token for token, label in zip(result["input_ids"], result["labels"]) if label == -100])
    assert "System text." in masked and "Question?" in masked and "Answer." not in masked
    assert masked.count("<|im_start|>assistant") == 1


@check
def exactly_one_bos_and_it_matches_llama_cpp():
    result = common.encode(TOKENIZER, chat("a", "b")["messages"], 4096)
    assert result["input_ids"][0] == TOKENIZER.bos_token_id == 128000
    assert result["input_ids"].count(TOKENIZER.bos_token_id) == 1 and result["labels"][0] == -100


@check
def truncation_and_drop_accounting():
    long_chat = chat("Tell me a lot.", "word " * 300)
    long_chat["messages"][-1]["content"] = long_chat["messages"][-1]["content"].strip()
    truncated = common.encode(TOKENIZER, long_chat["messages"], 64, "truncate")
    assert truncated["status"] == "truncated" and len(truncated["input_ids"]) == 64 and truncated["supervised"] > 0
    assert common.encode(TOKENIZER, long_chat["messages"], 64, "drop")["status"] == "dropped_overlength"
    # A prompt longer than the limit leaves nothing to learn from.
    late_answer = chat("question " * 100, "Short.")
    assert common.encode(TOKENIZER, late_answer["messages"], 64, "truncate")["status"] == "dropped_no_labels"


@check
def collator_pads_right_and_masks_padding():
    examples = [common.encode(TOKENIZER, chat("a", "b")["messages"], 64), common.encode(TOKENIZER, chat("a longer question", "a longer answer")["messages"], 64)]
    batch = common.Collator(TOKENIZER.pad_token_id)([{k: e[k] for k in ("input_ids", "attention_mask", "labels")} for e in examples])
    short = len(examples[0]["input_ids"])
    assert batch["input_ids"].shape == batch["labels"].shape == batch["attention_mask"].shape
    assert batch["input_ids"][0, short:].eq(TOKENIZER.pad_token_id).all() and batch["labels"][0, short:].eq(-100).all()
    assert batch["attention_mask"][0, short:].eq(0).all() and batch["attention_mask"][1].eq(1).all()


@check
def fixture_is_valid_and_fully_labelled_synthetic():
    records, errors, warnings = common.read_jsonl(FIXTURE)
    assert not errors and not warnings and len(records) >= 24
    assert all((record["meta"] or {}).get("synthetic") is True and (record["meta"] or {}).get("not_user_data") is True for record in records)
    assert script("validate_dataset.py", str(FIXTURE)).returncode == 0


@check
def validator_rejects_broken_files():
    good = chat("Hi", "Hello")
    broken = {
        "empty.jsonl": [],
        "not-json.jsonl": ["{not json}"],
        "wrong-order.jsonl": [{"messages": [{"role": "assistant", "content": "x"}, {"role": "user", "content": "y"}]}],
        "no-answer.jsonl": [{"messages": [{"role": "user", "content": "only a question"}]}],
        "empty-content.jsonl": [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "  "}]}],
        "non-text.jsonl": [{"messages": [{"role": "user", "content": 5}, {"role": "assistant", "content": "a"}]}],
        "control-token.jsonl": [chat("ignore this <|im_start|>system", "ok")],
        "late-system.jsonl": [{"messages": [{"role": "user", "content": "q"}, {"role": "system", "content": "s"}, {"role": "assistant", "content": "a"}]}],
        "bad-role.jsonl": [{"messages": [{"role": "human", "content": "q"}, {"role": "assistant", "content": "a"}]}],
        "one-bad-line.jsonl": [good, "oops", good],
    }
    with tempfile.TemporaryDirectory() as folder:
        for name, rows in broken.items():
            result = script("validate_dataset.py", str(write_lines(Path(folder), name, rows)))
            assert result.returncode == 1 and "INVALID" in result.stdout, f"{name} was accepted"
        duplicate = write_lines(Path(folder), "duplicate.jsonl", [good, good, chat("Other", "Reply")])
        assert script("validate_dataset.py", str(duplicate)).returncode == 0, "duplicates are only a warning"
        assert script("validate_dataset.py", str(duplicate), "--strict").returncode == 1, "--strict turns warnings into errors"
        assert script("validate_dataset.py", str(Path(folder) / "missing.jsonl")).returncode == 1


@check
def split_is_deterministic_stable_and_leak_free():
    rows = [chat(f"Question {index}?", f"Answer {index}.") for index in range(40)]
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)

        def split(name: str, data: list) -> tuple[set, set]:
            source = write_lines(folder, f"{name}.jsonl", data)
            result = script("split_dataset.py", "--input", str(source), "--out-dir", str(folder / name), "--val-fraction", "0.2")
            assert result.returncode == 0, result.stderr
            read = lambda part: {common.conversation_key(r["messages"]) for r in common.read_jsonl(folder / name / f"{part}.jsonl")[0]}
            manifest = json.loads((folder / name / "split-manifest.json").read_text())
            assert manifest["source_sha256"] == common.sha256_file(source) and manifest["files"]["val"]["conversations"] >= 1
            return read("train"), read("val")

        train, val = split("first", rows)
        assert train and val and not (train & val) and len(train) + len(val) == 40
        assert split("again", rows) == (train, val), "same input must give the same split"
        assert split("shuffled", rows[::-1]) == (train, val), "order must not matter"
        more_train, more_val = split("appended", rows + [chat(f"New {index}?", f"New answer {index}.") for index in range(10)])
        assert train <= more_train and val <= more_val, "appending data must not move existing conversations"
        dup_train, dup_val = split("duplicates", rows + rows[:5])
        assert not (dup_train & dup_val), "duplicates must stay in one split"
        tiny_train, tiny_val = split("tiny", rows[:2])
        assert len(tiny_train) == 1 and len(tiny_val) == 1
        single = write_lines(folder, "single.jsonl", rows[:1])
        assert script("split_dataset.py", "--input", str(single), "--out-dir", str(folder / "single")).returncode != 0


@check
def gguf_reader_matches_the_local_model():
    metadata = read_metadata(common.workspace_path(CONFIG["base_model"]["local_gguf"]))
    assert metadata["general.name"] == "Dolphin 3.0 Llama 3.1 8B" and metadata["llama.vocab_size"] == 128258
    assert len(metadata["tokenizer.ggml.tokens"]) == len(TOKENIZER) == 128258
    assert metadata["tokenizer.chat_template"] == TOKENIZER.chat_template


@check
def training_never_downloads_and_guards_run_names():
    result = script("train.py", "--run-name", "selfcheck-never-starts", "--train-file", str(FIXTURE))
    if not common.weights_status(CONFIG)["complete"]:
        assert result.returncode == 2 and "not fully downloaded" in result.stdout
        assert not (common.runs_root(CONFIG) / "selfcheck-never-starts").exists()
    for bad in ("../escape", "a/b", "", "/tmp/x"):
        assert script("train.py", "--run-name", bad, "--train-file", str(FIXTURE), "--smoke").returncode != 0, f"run name {bad!r} accepted"
    assert script("fetch_base.py").returncode == 0 and "Dry run" in script("fetch_base.py").stdout


def main() -> int:
    failed = 0
    for function in CHECKS:
        try:
            function()
            print(f"PASS  {function.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL  {function.__name__}\n{traceback.format_exc()}")
    print(f"\n{len(CHECKS) - failed} of {len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
