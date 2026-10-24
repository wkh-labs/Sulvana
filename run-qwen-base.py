#!/usr/bin/env python3
"""Persistent terminal chatbot for the local post-trained Qwen3-1.7B model."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from threading import Thread

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer


MODEL_PATH = (Path(__file__).resolve().parent / "models/Qwen3-1.7B")
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, honest assistant. Reply in the same language as the user. "
    "If you are uncertain, say so instead of inventing facts."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chat with the local post-trained Qwen3-1.7B model.")
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional first message. The interactive chat continues afterward.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--max-context-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--system", default=DEFAULT_SYSTEM_PROMPT)
    return parser.parse_args()


def print_help() -> None:
    print(
        """
Commands:
  /clear          Forget the conversation but keep the system prompt
  /system TEXT    Replace the system prompt and clear the conversation
  /stats          Show performance from the previous reply
  /help           Show these commands
  /quit           Exit the chatbot
""".strip()
    )


def render_inputs(tokenizer, messages: list[dict], max_context_tokens: int):
    """Apply the chat template and discard oldest complete turns when necessary."""
    working = messages.copy()
    while True:
        inputs = tokenizer.apply_chat_template(
            working,
            add_generation_prompt=True,
            enable_thinking=False,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        if inputs["input_ids"].shape[1] <= max_context_tokens:
            return inputs, working
        if len(working) <= 2:
            raise ValueError(
                f"The current message exceeds the {max_context_tokens}-token context limit."
            )
        del working[1:3]


def generate_reply(
    *,
    model,
    tokenizer,
    messages: list[dict],
    args: argparse.Namespace,
    stop_token_ids: list[int],
) -> tuple[str, list[dict], dict]:
    inputs, trimmed_messages = render_inputs(tokenizer, messages, args.max_context_tokens)
    inputs = inputs.to("cuda")
    input_tokens = inputs["input_ids"].shape[1]
    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )
    generation = {
        **inputs,
        "streamer": streamer,
        "max_new_tokens": args.max_new_tokens,
        "repetition_penalty": 1.1,
        "no_repeat_ngram_size": 5,
        "eos_token_id": stop_token_ids,
        "pad_token_id": tokenizer.pad_token_id,
    }
    if args.temperature > 0:
        generation.update(
            do_sample=True,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=20,
        )
    else:
        generation.update(do_sample=False)

    result: dict = {}
    failure: dict = {}

    def worker() -> None:
        try:
            result["output"] = model.generate(**generation)
        except BaseException as error:
            failure["error"] = error

    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    thread = Thread(target=worker, daemon=True)
    thread.start()

    pieces = []
    print("\nAssistant: ", end="", flush=True)
    for piece in streamer:
        pieces.append(piece)
        print(piece, end="", flush=True)
    thread.join()
    print()

    if "error" in failure:
        raise failure["error"]
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    output = result["output"]
    generated_tokens = output.shape[1] - input_tokens
    reply = "".join(pieces).strip()
    stats = {
        "input_tokens": input_tokens,
        "generated_tokens": generated_tokens,
        "seconds": elapsed,
        "tokens_per_second": generated_tokens / elapsed if elapsed else 0.0,
        "peak_vram_gib": torch.cuda.max_memory_allocated() / 2**30,
    }
    return reply, trimmed_messages, stats


def show_stats(stats: dict | None) -> None:
    if not stats:
        print("No reply has been generated yet.")
        return
    print(
        f"Input: {stats['input_tokens']} tokens | "
        f"Output: {stats['generated_tokens']} tokens | "
        f"Speed: {stats['tokens_per_second']:.1f} tokens/s | "
        f"Peak VRAM: {stats['peak_vram_gib']:.2f} GiB"
    )


def main() -> None:
    args = parse_args()
    if args.max_context_tokens < 256:
        raise SystemExit("--max-context-tokens must be at least 256.")
    if args.max_new_tokens < 1:
        raise SystemExit("--max-new-tokens must be positive.")
    if not MODEL_PATH.exists():
        raise SystemExit(f"Model directory not found: {MODEL_PATH}")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is unavailable. Check the NVIDIA driver and AI environment.")

    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.set_float32_matmul_precision("high")

    print(f"Loading {MODEL_PATH.name} in BF16 on {torch.cuda.get_device_name(0)} …")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        dtype=torch.bfloat16,
        device_map={"": 0},
        local_files_only=True,
        low_cpu_mem_usage=True,
    )
    model.eval()

    stop_token_ids = list(
        dict.fromkeys(
            token_id
            for token_id in (
                tokenizer.eos_token_id,
                tokenizer.convert_tokens_to_ids("<|im_end|>"),
            )
            if token_id is not None and token_id >= 0
        )
    )
    system_prompt = args.system
    messages = [{"role": "system", "content": system_prompt}]
    last_stats = None
    pending = " ".join(args.prompt).strip() or None

    print("\nQwen CLI chatbot is ready. Type /help for commands.")
    print("Post-trained non-thinking chat mode is enabled.\n")

    while True:
        try:
            if pending is not None:
                user_text = pending
                pending = None
                print(f"You: {user_text}")
            else:
                user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_text:
            continue
        command = user_text.casefold()
        if command in {"/quit", "/exit"}:
            print("Goodbye.")
            break
        if command == "/help":
            print_help()
            continue
        if command == "/clear":
            messages = [{"role": "system", "content": system_prompt}]
            last_stats = None
            print("Conversation cleared.")
            continue
        if command == "/stats":
            show_stats(last_stats)
            continue
        if command.startswith("/system"):
            replacement = user_text[len("/system") :].strip()
            if not replacement:
                print(f"Current system prompt: {system_prompt}")
                continue
            system_prompt = replacement
            messages = [{"role": "system", "content": system_prompt}]
            last_stats = None
            print("System prompt replaced and conversation cleared.")
            continue
        if user_text.startswith("/"):
            print("Unknown command. Type /help to list commands.")
            continue

        messages.append({"role": "user", "content": user_text})
        try:
            reply, trimmed_messages, last_stats = generate_reply(
                model=model,
                tokenizer=tokenizer,
                messages=messages,
                args=args,
                stop_token_ids=stop_token_ids,
            )
            messages = trimmed_messages
            messages.append({"role": "assistant", "content": reply})
        except (RuntimeError, ValueError) as error:
            messages.pop()
            print(f"\nGeneration error: {error}")
            if isinstance(error, torch.cuda.OutOfMemoryError):
                torch.cuda.empty_cache()
                print("Try /clear or restart with a smaller --max-context-tokens value.")


if __name__ == "__main__":
    main()
