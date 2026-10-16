"""Shared pieces of the QLoRA workflow (Dolphin 3.0, MiMo/Qwen3.5): paths, config, dataset rules, tokenisation, model loading.

Import this module (and call ``setup_environment``) before importing torch or transformers,
because Hugging Face reads its offline switch at import time.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
FINETUNE = WORKSPACE / "finetune"
DEFAULT_CONFIG = FINETUNE / "dolphin-qlora-8gb.yaml"
RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
CONTROL_TOKEN = re.compile(r"<\|[A-Za-z0-9_]+\|>")
ROLES = ("system", "user", "assistant")


def setup_environment(offline: bool = True) -> None:
    """Keep caches inside the workspace and forbid network access unless a script opts in."""
    os.environ.setdefault("HF_HOME", str(WORKSPACE / ".cache" / "huggingface"))
    os.environ.setdefault("TORCH_HOME", str(WORKSPACE / ".cache" / "torch"))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
    os.environ["HF_HUB_OFFLINE"] = "1" if offline else "0"
    os.environ["TRANSFORMERS_OFFLINE"] = "1" if offline else "0"


def workspace_path(value: str | os.PathLike) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else WORKSPACE / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- config

def _set_nested(config: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    node = config
    for key in keys[:-1]:
        if not isinstance(node.get(key), dict):
            raise SystemExit(f"Unknown config section in --set {dotted}")
        node = node[key]
    if keys[-1] not in node:
        raise SystemExit(f"Unknown config key in --set {dotted}")
    node[keys[-1]] = value


def load_config(path: str | os.PathLike | None = None, overrides: list[str] | None = None) -> dict:
    import yaml

    source = workspace_path(path) if path else DEFAULT_CONFIG
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    for item in overrides or []:
        if "=" not in item:
            raise SystemExit(f"--set expects key.subkey=value, got: {item}")
        key, raw = item.split("=", 1)
        _set_nested(config, key.strip(), yaml.safe_load(raw))
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    problems = []

    def need(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    for section in ("base_model", "data", "quantization", "lora", "training", "memory", "output"):
        need(isinstance(config.get(section), dict), f"missing section: {section}")
    if problems:
        raise SystemExit("Invalid config: " + "; ".join(problems))
    base, data, lora, training, memory = (config[name] for name in ("base_model", "data", "lora", "training", "memory"))
    need(re.fullmatch(r"[0-9a-f]{40}", str(base.get("revision", ""))) is not None, "base_model.revision must be a full 40-character commit hash")
    need(isinstance(base.get("weight_files"), dict) and base["weight_files"], "base_model.weight_files must list the weight shards")
    need(isinstance(data.get("max_seq_length"), int) and 32 <= data["max_seq_length"] <= 4096, "data.max_seq_length must be 32..4096")
    need(data.get("on_overlength") in {"truncate", "drop"}, "data.on_overlength must be truncate or drop")
    need(data.get("system_prompt", {}).get("mode") in {"as-is", "file"}, "data.system_prompt.mode must be as-is or file")
    need(config["quantization"].get("load_in_4bit") is True, "quantization.load_in_4bit must be true (this workflow is QLoRA)")
    need(isinstance(lora.get("r"), int) and 1 <= lora["r"] <= 256, "lora.r must be 1..256")
    need(isinstance(lora.get("target_modules"), list) and lora["target_modules"], "lora.target_modules must be a non-empty list")
    need(isinstance(training.get("per_device_train_batch_size"), int) and training["per_device_train_batch_size"] >= 1, "training.per_device_train_batch_size must be >= 1")
    need(isinstance(training.get("gradient_accumulation_steps"), int) and training["gradient_accumulation_steps"] >= 1, "training.gradient_accumulation_steps must be >= 1")
    need(isinstance(training.get("learning_rate"), (int, float)) and 0 < training["learning_rate"] < 1, "training.learning_rate must be between 0 and 1")
    need(0 <= float(training.get("warmup_ratio", 0)) < 1, "training.warmup_ratio must be in [0, 1)")
    for key in ("logging_steps", "eval_steps", "save_steps", "save_total_limit"):
        need(isinstance(training.get(key), int) and training[key] >= 1, f"training.{key} must be a positive integer")
    need(isinstance(memory.get("min_free_vram_gib"), (int, float)), "memory.min_free_vram_gib must be a number")
    if problems:
        raise SystemExit("Invalid config: " + "; ".join(problems))


def runs_root(config: dict) -> Path:
    return workspace_path(config["output"]["root"])


def run_directory(config: dict, run_name: str) -> Path:
    if not RUN_NAME.fullmatch(run_name or ""):
        raise SystemExit("--run-name must be 1-64 characters of letters, digits, dot, dash or underscore, starting with a letter or digit")
    return runs_root(config) / run_name


# --------------------------------------------------------------------------- base checkpoint

def cached_file(config: dict, filename: str) -> Path | None:
    """Path of a file of the pinned revision in the local Hugging Face cache, or None. Never downloads."""
    from huggingface_hub import try_to_load_from_cache

    found = try_to_load_from_cache(config["base_model"]["repo_id"], filename, revision=config["base_model"]["revision"])
    return Path(found) if isinstance(found, str) and os.path.isfile(found) else None


def weights_status(config: dict) -> dict:
    """Which weight shards of the pinned revision are present and complete in the local cache."""
    files = {}
    for name, expected in config["base_model"]["weight_files"].items():
        path = cached_file(config, name)
        size = path.stat().st_size if path else 0
        files[name] = {"expected_bytes": int(expected), "present_bytes": size, "complete": size == int(expected)}
    return {
        "complete": all(item["complete"] for item in files.values()),
        "missing": [name for name, item in files.items() if not item["complete"]],
        "total_bytes": sum(item["expected_bytes"] for item in files.values()),
        "present_bytes": sum(item["present_bytes"] for item in files.values() if item["complete"]),
        "files": files,
    }


def missing_weights_message(config: dict, status: dict) -> str:
    base = config["base_model"]
    return (
        f"The trainable checkpoint {base['repo_id']} @ {base['revision'][:12]} is not fully downloaded.\n"
        f"Missing {len(status['missing'])} of {len(status['files'])} weight files "
        f"({(status['total_bytes'] - status['present_bytes']) / 1e9:.2f} GB still needed): {', '.join(status['missing'])}\n"
        "Nothing is downloaded implicitly. Review the plan, then fetch it yourself:\n"
        "  .venv/bin/python finetune/fetch_base.py          # shows sizes, downloads nothing\n"
        "  .venv/bin/python finetune/fetch_base.py --yes    # downloads the pinned revision"
    )


def load_tokenizer(config: dict):
    from transformers import AutoTokenizer

    base = config["base_model"]
    tokenizer = AutoTokenizer.from_pretrained(base["repo_id"], revision=base["revision"])
    if not tokenizer.chat_template:
        raise SystemExit("The tokenizer has no chat template; refusing to guess the prompt format.")
    if tokenizer.eos_token_id is None or tokenizer.pad_token_id is None:
        raise SystemExit("The tokenizer must define EOS and PAD tokens.")
    # Llama-style models start every sequence with BOS; Qwen-style models (MiMo) have none.
    if base.get("uses_bos", True) and tokenizer.bos_token_id is None:
        raise SystemExit("This config expects a BOS token, but the tokenizer has none.")
    tokenizer.padding_side = "right"
    return tokenizer


# --------------------------------------------------------------------------- dataset rules

def check_messages(messages) -> list[str]:
    """Return the reasons a conversation breaks the documented format (empty list = valid)."""
    if not isinstance(messages, list) or not messages:
        return ['"messages" must be a non-empty list']
    problems = []
    for position, message in enumerate(messages):
        if not isinstance(message, dict):
            return [f"message {position + 1} is not an object"]
        role, content = message.get("role"), message.get("content")
        if role not in ROLES:
            problems.append(f"message {position + 1} has unknown role {role!r}")
        if not isinstance(content, str) or not content.strip():
            problems.append(f"message {position + 1} has empty or non-text content")
            continue
        if CONTROL_TOKEN.search(content):
            problems.append(f"message {position + 1} contains a control token such as {CONTROL_TOKEN.search(content).group(0)!r}")
        if any(ord(char) < 32 and char not in "\n\t\r" for char in content):
            problems.append(f"message {position + 1} contains a control character")
        if role == "assistant" and content != content.strip():
            problems.append(f"message {position + 1}: assistant content has leading or trailing whitespace")
        extra = set(message) - {"role", "content"}
        if extra:
            problems.append(f"message {position + 1} has unexpected keys {sorted(extra)}")
    if problems:
        return problems
    roles = [message["role"] for message in messages]
    turns = roles[1:] if roles[0] == "system" else roles
    if "system" in turns:
        problems.append("a system message is only allowed first")
    if not turns or turns[-1] != "assistant":
        problems.append("the conversation must end with an assistant message")
    if any(role != ("user" if index % 2 == 0 else "assistant") for index, role in enumerate(turns) if role != "system"):
        problems.append("after the optional system message, roles must alternate user, assistant, user, ...")
    return problems


def read_jsonl(path: Path) -> tuple[list[dict], list[str], list[str]]:
    """Parse and validate a dataset file. Returns (records, errors, warnings); records keep their line number."""
    records, errors, warnings = [], [], []
    seen: dict[str, int] = {}
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append("file starts with a UTF-8 byte order mark; save it as plain UTF-8")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return [], [f"file is not valid UTF-8: {error}"], []
    for number, line in enumerate(text.split("\n"), 1):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"line {number}: not valid JSON ({error.msg} at column {error.colno})")
            continue
        if not isinstance(item, dict):
            errors.append(f"line {number}: each line must be a JSON object")
            continue
        problems = check_messages(item.get("messages"))
        if problems:
            errors.extend(f"line {number}: {problem}" for problem in problems)
            continue
        if "meta" in item and not isinstance(item["meta"], dict):
            errors.append(f'line {number}: "meta" must be an object when present')
            continue
        unknown = set(item) - {"messages", "meta"}
        if unknown:
            warnings.append(f"line {number}: ignoring unknown keys {sorted(unknown)}")
        key = conversation_key(item["messages"])
        if key in seen:
            warnings.append(f"line {number}: exact duplicate of line {seen[key]}")
        else:
            seen[key] = number
        records.append({"line": number, "messages": item["messages"], "meta": item.get("meta")})
    if not records and not errors:
        errors.append("the file contains no conversations")
    return records, errors, warnings


def conversation_key(messages: list[dict]) -> str:
    canonical = json.dumps([[m["role"], m["content"]] for m in messages], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def with_system_prompt(messages: list[dict], config: dict) -> list[dict]:
    setting = config["data"]["system_prompt"]
    if setting["mode"] != "file" or messages[0]["role"] == "system":
        return messages
    if not setting.get("path"):
        raise SystemExit("data.system_prompt.mode is 'file' but data.system_prompt.path is not set")
    text = workspace_path(setting["path"]).read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("The system prompt file is empty")
    return [{"role": "system", "content": text}, *messages]


# --------------------------------------------------------------------------- tokenisation and label masking

def render(tokenizer, messages: list[dict], template_kwargs: dict | None = None) -> tuple[str, list[tuple[int, int]]]:
    """Template a conversation and locate every assistant answer (its text plus the end-of-turn token).

    ``template_kwargs`` go to the chat template; MiMo/Qwen3.5 uses {"enable_thinking": False}, which
    ends the prompt with an empty "<think></think>" exactly as the app's non-thinking requests do.
    """
    extra = template_kwargs or {}
    text = tokenizer.apply_chat_template(messages, tokenize=False, **extra)
    end_of_turn = tokenizer.eos_token
    spans = []
    for index, message in enumerate(messages):
        if message["role"] != "assistant":
            continue
        # The prompt that precedes this answer, exactly as the app builds it at inference time.
        prompt = tokenizer.apply_chat_template(messages[:index], tokenize=False, add_generation_prompt=True, **extra)
        through = tokenizer.apply_chat_template(messages[: index + 1], tokenize=False, **extra)
        answer = through[len(prompt):]
        if not (through.startswith(prompt) and text.startswith(through) and answer.startswith(message["content"])
                and answer[len(message["content"]):].startswith(end_of_turn)):
            raise ValueError("The chat template does not place assistant answers where this pipeline expects them.")
        spans.append((len(prompt), len(prompt) + len(message["content"]) + len(end_of_turn)))
    return text, spans


def encode(tokenizer, messages: list[dict], max_seq_length: int, on_overlength: str = "truncate",
           template_kwargs: dict | None = None) -> dict:
    """Tokenise one conversation for training. Only assistant answers carry a loss.

    Returns a dict with ``status`` ("ok", "truncated", "dropped_overlength" or "dropped_no_labels").
    """
    text, spans = render(tokenizer, messages, template_kwargs)
    encoded = tokenizer(text, add_special_tokens=True, return_offsets_mapping=True)
    ids, offsets = list(encoded["input_ids"]), list(encoded["offset_mapping"])
    # llama.cpp puts exactly one BOS in front of the templated prompt (for models that use one); training must match.
    if tokenizer.bos_token_id is not None and (ids[0] != tokenizer.bos_token_id or ids.count(tokenizer.bos_token_id) != 1):
        raise ValueError("Expected exactly one BOS token at the start of the sequence.")
    labels = [-100] * len(ids)
    for position, (start, end) in enumerate(offsets):
        if start != end and any(start >= low and end <= high for low, high in spans):
            labels[position] = ids[position]
    total = len(ids)
    status = "ok"
    if total > max_seq_length:
        if on_overlength == "drop":
            return {"status": "dropped_overlength", "tokens": total}
        ids, labels, status = ids[:max_seq_length], labels[:max_seq_length], "truncated"
    supervised = sum(label != -100 for label in labels)
    if supervised == 0:
        return {"status": "dropped_no_labels", "tokens": total}
    return {"status": status, "tokens": total, "supervised": supervised,
            "input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels}


def build_examples(tokenizer, records: list[dict], config: dict) -> tuple[list[dict], dict]:
    """Encode records and report what happened to them."""
    examples, lengths, supervised = [], [], 0
    counts = {"ok": 0, "truncated": 0, "dropped_overlength": 0, "dropped_no_labels": 0}
    for record in records:
        result = encode(tokenizer, with_system_prompt(record["messages"], config),
                        config["data"]["max_seq_length"], config["data"]["on_overlength"],
                        config["data"].get("chat_template_kwargs"))
        counts[result["status"]] += 1
        lengths.append(result["tokens"])
        if "input_ids" in result:
            supervised += result["supervised"]
            examples.append({key: result[key] for key in ("input_ids", "attention_mask", "labels")})
    ordered = sorted(lengths)
    pick = lambda fraction: ordered[min(len(ordered) - 1, int(fraction * len(ordered)))] if ordered else 0
    stats = {
        "records": len(records), "usable": len(examples), **counts, "supervised_tokens": supervised,
        "max_seq_length": config["data"]["max_seq_length"],
        "token_length": {"min": ordered[0] if ordered else 0, "median": pick(0.5), "p90": pick(0.9), "p99": pick(0.99), "max": ordered[-1] if ordered else 0},
    }
    return examples, stats


class Collator:
    """Right-pad a batch; padding never contributes to the loss."""

    def __init__(self, pad_token_id: int):
        self.pad_token_id = pad_token_id

    def __call__(self, features: list[dict]) -> dict:
        import torch

        width = max(len(feature["input_ids"]) for feature in features)
        pad = lambda values, fill: values + [fill] * (width - len(values))
        return {
            "input_ids": torch.tensor([pad(f["input_ids"], self.pad_token_id) for f in features], dtype=torch.long),
            "attention_mask": torch.tensor([pad(f["attention_mask"], 0) for f in features], dtype=torch.long),
            "labels": torch.tensor([pad(f["labels"], -100) for f in features], dtype=torch.long),
        }


# --------------------------------------------------------------------------- model loading

def smoke_base(config: dict, tokenizer) -> Path:
    """Build (once) a tiny RANDOM model of the base model's architecture with its real vocabulary.

    It has no language ability at all. Its only purpose is to run the identical training and
    evaluation code path in seconds, without the multi-gigabyte checkpoint.
    """
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM

    base = config["base_model"]
    target = runs_root(config) / ("_smoke-base" if base.get("uses_bos", True) else f"_smoke-base-{base['repo_id'].split('/')[-1]}")
    if (target / "config.json").is_file() and (target / "model.safetensors").is_file():
        return target
    tiny = AutoConfig.from_pretrained(base["repo_id"], revision=base["revision"])
    tiny = getattr(tiny, "text_config", tiny)   # multimodal checkpoints: the language model only
    tiny.hidden_size, tiny.intermediate_size, tiny.num_hidden_layers = 64, 128, 4
    tiny.num_attention_heads, tiny.num_key_value_heads, tiny.head_dim = 4, 2, 16
    if getattr(tiny, "layer_types", None):      # hybrid models (Qwen3.5): keep the mix of layer types
        tiny.layer_types = tiny.layer_types[:4]
        for key, value in (("linear_num_key_heads", 2), ("linear_num_value_heads", 4), ("linear_key_head_dim", 16), ("linear_value_head_dim", 16)):
            if hasattr(tiny, key):
                setattr(tiny, key, value)
    torch.manual_seed(0)
    model = AutoModelForCausalLM.from_config(tiny).to(torch.bfloat16)
    target.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(target)
    tokenizer.save_pretrained(target)
    (target / "README.txt").write_text(
        f"Randomly initialised 4-layer model with the architecture and vocabulary of {base['repo_id']}.\n"
        "Created by finetune/common.py for pipeline smoke tests only. It cannot produce language.\n", encoding="utf-8")
    return target


def host_embedding(embedding, device):
    """Keep the input embedding table in system RAM and send only the looked-up rows to the GPU.

    The table (128258 x 4096) is 1.05 GB in BF16 and cannot be quantised. A device map entry of
    "cpu" would not help: the loader then copies the whole table to the GPU on every forward pass.
    """
    import torch

    try:
        from accelerate.hooks import remove_hook_from_module
        remove_hook_from_module(embedding, recurse=True)
    except ImportError:
        pass

    class HostEmbedding(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            # Deliberately not registered as a sub-module: the table must stay in system RAM when a
            # caller moves the model, and must not be mistaken for the model's own device.
            self.__dict__["table"] = embedding.to("cpu")
            self.target = torch.device(device)
            self.num_embeddings, self.embedding_dim = embedding.num_embeddings, embedding.embedding_dim
            self.padding_idx = embedding.padding_idx

        @property
        def weight(self):
            return self.table.weight

        def forward(self, input_ids):
            return self.table(input_ids.to("cpu")).to(self.target)

    return HostEmbedding()


def chunked_head(config: dict, head, compute_dtype, chunks: int):
    """Replace a 4-bit output head by `chunks` smaller 4-bit heads over slices of the vocabulary.

    bitsandbytes unpacks a 4-bit weight to BF16 for every matmul. For MiMo's 248,320-token
    vocabulary that is a 1.9 GiB spike per step, which an 8 GB card cannot afford; slices are
    unpacked one at a time. The BF16 weight is read from the checkpoint on the CPU, one slice at a
    time, so the full head never has to exist on the GPU.
    """
    import bitsandbytes as bnb
    import torch
    from safetensors import safe_open

    base = config["base_model"]
    index = json.loads(cached_file(config, "model.safetensors.index.json").read_text())
    shard = cached_file(config, index["weight_map"]["lm_head.weight"])
    quant = config["quantization"]

    class ChunkedHead(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.parts = torch.nn.ModuleList()
            with safe_open(str(shard), framework="pt", device="cpu") as handle:
                full = handle.get_slice("lm_head.weight")
                rows, width = full.get_shape()
                step = -(-rows // chunks)
                for start in range(0, rows, step):
                    weight = full[start:start + step]
                    part = bnb.nn.Linear4bit(width, weight.shape[0], bias=False, compute_dtype=compute_dtype,
                                             compress_statistics=bool(quant["double_quant"]), quant_type=quant["quant_type"])
                    part.weight = bnb.nn.Params4bit(weight.to(torch.bfloat16), requires_grad=False, quant_type=quant["quant_type"],
                                                    compress_statistics=bool(quant["double_quant"]))
                    self.parts.append(part.cuda())
            self.in_features, self.out_features = width, rows

        @property
        def weight(self):
            return self.parts[0].weight

        def forward(self, hidden):
            return torch.cat([part(hidden) for part in self.parts], dim=-1)

    del head
    torch.cuda.empty_cache()
    return ChunkedHead()


def load_base(config: dict, tokenizer, smoke: bool):
    """Load the frozen base model in 4-bit, the same way for training and for evaluation."""
    import torch
    import transformers.modeling_utils
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig

    # Transformers reserves the whole model size as one GPU block before loading, only to speed loading
    # up. With the desktop holding ~2 GB of an 8 GB card that reservation fails although training fits.
    transformers.modeling_utils.caching_allocator_warmup = lambda *args, **kwargs: None
    base = config["base_model"]
    source, revision = (str(smoke_base(config, tokenizer)), None) if smoke else (base["repo_id"], base["revision"])
    quant, memory = config["quantization"], config["memory"]
    on_gpu = torch.cuda.is_available()
    kwargs: dict = {"dtype": getattr(torch, quant["compute_dtype"]), "low_cpu_mem_usage": True}
    if revision:
        kwargs["revision"] = revision
    if on_gpu:
        # The input embeddings go straight to system RAM: loading them onto the GPU first (1.9 GiB for
        # MiMo) briefly needs more memory than an 8 GB card has free next to the desktop.
        # Everything loads onto the GPU first (embeddings and output head are moved or replaced right
        # after), so loading briefly needs about 6.1 GiB free for MiMo. A "cpu" device-map entry does
        # not help: the loader's dispatch moves such modules back onto the GPU.
        kwargs["device_map"] = {"": 0}
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=quant["quant_type"],
            bnb_4bit_use_double_quant=bool(quant["double_quant"]),
            bnb_4bit_compute_dtype=getattr(torch, quant["compute_dtype"]),
            # By default the output head stays in full precision; an explicit (non-matching) skip
            # list makes bitsandbytes quantise it as well.
            llm_int8_skip_modules=["__nothing__"] if memory["quantize_lm_head"] else None,
        )
    elif not smoke:
        raise SystemExit("A CUDA GPU is required: 4-bit QLoRA of an 8B model cannot run on the CPU.")
    if smoke or not base.get("model_class"):
        model = AutoModelForCausalLM.from_pretrained(source, **kwargs)
    else:
        # A multimodal checkpoint (MiMo/Qwen3.5) loaded as its text-only language model: the vision
        # tower is not needed for text training and would only take memory.
        import transformers
        model = getattr(transformers, base["model_class"]).from_pretrained(source, **kwargs)
    offloaded = bool(on_gpu and memory["offload_embeddings_to_cpu"])
    if offloaded:
        model.set_input_embeddings(host_embedding(model.get_input_embeddings(), "cuda:0"))
        torch.cuda.empty_cache()
    # After the embeddings have left the GPU: the slices need room while they are quantised.
    if on_gpu and not smoke and memory.get("lm_head_chunks", 1) > 1:
        old_head = model.lm_head
        model.lm_head = None
        model.lm_head = chunked_head(config, old_head, getattr(torch, quant["compute_dtype"]), int(memory["lm_head_chunks"]))
        del old_head
        torch.cuda.empty_cache()
    return model, {"source": source, "revision": revision, "quantized_4bit": on_gpu, "embeddings_in_system_ram": offloaded}


def supervised_loss(model, batch: dict, reduction: str = "mean"):
    """Cross-entropy over assistant tokens only, computing vocabulary-sized logits just for those positions.

    The standard forward builds logits for every position (512 x 128258 values, upcast to FP32 for
    the loss). System and user tokens carry no loss, so skipping them saves most of that memory.
    Returns (loss, number of supervised tokens).
    """
    import torch

    from torch.utils.checkpoint import checkpoint

    core = model.get_base_model() if hasattr(model, "get_base_model") else model
    hidden = core.get_decoder()(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).last_hidden_state
    targets = batch["labels"][:, 1:].to(hidden.device)
    keep = targets != -100
    states, wanted = hidden[:, :-1][keep], targets[keep]
    head = core.get_output_embeddings()

    def piece(states_part, wanted_part):
        return torch.nn.functional.cross_entropy(head(states_part).float(), wanted_part, reduction="sum")

    # Vocabulary-sized logits for a few hundred tokens at a time, recomputed in the backward pass,
    # so a large vocabulary (MiMo: 248,320) never holds every position's logits at once.
    step = 128
    total = sum(checkpoint(piece, states[i:i + step], wanted[i:i + step], use_reentrant=False) if torch.is_grad_enabled()
                else piece(states[i:i + step], wanted[i:i + step]) for i in range(0, len(wanted), step))
    count = int(keep.sum())
    loss = total if reduction == "sum" else total / max(1, count)
    return loss, count


def describe_modules(model) -> dict:
    """How the big modules really ended up after loading (for the run manifest)."""
    head = model.get_output_embeddings()
    embeddings = model.get_input_embeddings()
    return {
        "lm_head_class": type(head).__name__, "lm_head_dtype": str(head.weight.dtype), "lm_head_device": str(head.weight.device),
        "embeddings_dtype": str(embeddings.weight.dtype), "embeddings_device": str(embeddings.weight.device),
        "linear4bit_modules": sum(type(module).__name__ == "Linear4bit" for module in model.modules()),
    }


def gpu_summary() -> dict:
    import torch

    if not torch.cuda.is_available():
        return {"available": False}
    free, total = torch.cuda.mem_get_info()
    return {"available": True, "name": torch.cuda.get_device_name(0),
            "total_gib": round(total / 2**30, 2), "free_gib": round(free / 2**30, 2)}


def library_versions() -> dict:
    import importlib.metadata as metadata
    import platform

    names = ("torch", "transformers", "peft", "bitsandbytes", "accelerate", "tokenizers", "safetensors", "huggingface_hub")
    return {"python": platform.python_version(), **{name: metadata.version(name) for name in names}}


def frozen_copy(config: dict) -> dict:
    return copy.deepcopy(config)
