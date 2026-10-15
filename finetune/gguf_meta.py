"""Read the metadata header of a GGUF file without loading any tensor data (pure Python)."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

_SCALARS = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


def _scalar(handle, kind: int):
    fmt = _SCALARS[kind]
    return struct.unpack(fmt, handle.read(struct.calcsize(fmt)))[0]


def _string(handle) -> str:
    return handle.read(_scalar(handle, 10)).decode("utf-8", errors="replace")


def _value(handle, kind: int):
    if kind in _SCALARS:
        return _scalar(handle, kind)
    if kind == 8:
        return _string(handle)
    if kind == 9:
        element, count = _scalar(handle, 4), _scalar(handle, 10)
        return [_value(handle, element) for _ in range(count)]
    raise ValueError(f"Unknown GGUF value type {kind}")


def read_metadata(path: str | Path) -> dict:
    """Return every key/value pair of the GGUF header, plus ``_version`` and ``_tensor_count``."""
    with open(path, "rb") as handle:
        if handle.read(4) != b"GGUF":
            raise ValueError(f"{path} is not a GGUF file")
        version, tensors, pairs = _scalar(handle, 4), _scalar(handle, 10), _scalar(handle, 10)
        metadata = {"_version": version, "_tensor_count": tensors}
        for _ in range(pairs):
            key = _string(handle)
            metadata[key] = _value(handle, _scalar(handle, 4))
    return metadata


def summary(metadata: dict) -> dict:
    """The facts that decide whether a trainable checkpoint matches this GGUF."""
    keep = ("general.name", "general.organization", "general.architecture", "general.license", "general.file_type",
            "general.base_model.0.repo_url", "llama.block_count", "llama.embedding_length", "llama.feed_forward_length",
            "llama.attention.head_count", "llama.attention.head_count_kv", "llama.vocab_size", "llama.context_length",
            "tokenizer.ggml.model", "tokenizer.ggml.pre", "tokenizer.ggml.bos_token_id", "tokenizer.ggml.eos_token_id",
            "tokenizer.ggml.padding_token_id", "tokenizer.chat_template")
    result = {key: metadata.get(key) for key in keep}
    result["tokenizer.ggml.tokens.count"] = len(metadata.get("tokenizer.ggml.tokens", []))
    result["training_datasets"] = [metadata[key] for key in sorted(metadata) if key.startswith("general.dataset.") and key.endswith(".repo_url")]
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: gguf_meta.py MODEL.gguf")
    print(json.dumps(summary(read_metadata(sys.argv[1])), indent=2, ensure_ascii=False))
