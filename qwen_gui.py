#!/usr/bin/env python3
"""Native Tk desktop chat client for the local post-trained Qwen3-1.7B model."""

from __future__ import annotations

import queue
import gc
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    StoppingCriteria,
    StoppingCriteriaList,
    TextIteratorStreamer,
)


MODEL_PATH = Path("/home/tanchjim/Documents/Codex/ai-workspace/models/Qwen3-1.7B")
IMAGE_SCRIPT = Path("/home/tanchjim/Documents/Codex/ai-workspace/z-image.sh")
IMAGE_OUTPUT_DIR = Path("/home/tanchjim/Documents/Codex/ai-workspace/runs/z-image")
VISION_CLI = Path("/home/tanchjim/Documents/Codex/ai-workspace/vision-runner/llama-mtmd-cli")
VISION_MODEL = Path("/home/tanchjim/Documents/Codex/ai-workspace/models/Qwen2.5-VL-3B/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf")
VISION_PROJECTOR = Path("/home/tanchjim/Documents/Codex/ai-workspace/models/Qwen2.5-VL-3B/mmproj-F16.gguf")
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, honest assistant. Reply in the same language as the user. "
    "If you are uncertain, say so instead of inventing facts."
)

COLORS = {
    "window": "#0f1117",
    "panel": "#171a23",
    "surface": "#202431",
    "surface_hover": "#292e3e",
    "border": "#303647",
    "text": "#e7eaf0",
    "muted": "#9199ad",
    "accent": "#8066ff",
    "accent_hover": "#927cff",
    "user": "#aebcff",
    "assistant": "#72d5b4",
    "danger": "#ff7085",
    "success": "#63d69f",
}


def has_runaway_repetition(text: str) -> bool:
    """Catch obvious repeated tails that sampling controls fail to stop."""
    words = text.casefold().split()
    for width in range(1, 13):
        repeated_length = width * 4
        if len(words) < repeated_length:
            continue
        tail = words[-repeated_length:]
        pattern = tail[:width]
        if tail == pattern * 4:
            return True
    return False


class StopOnEvent(StoppingCriteria):
    def __init__(self, event: threading.Event):
        self.event = event

    def __call__(self, input_ids, scores, **kwargs) -> bool:
        return self.event.is_set()


class ModelWorker:
    """Own the model and run all expensive work away from Tk's UI thread."""

    def __init__(self, events: queue.Queue):
        self.events = events
        self.commands: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.shutdown_event = threading.Event()
        self.image_lock = threading.Lock()
        self.image_process: subprocess.Popen | None = None
        self.messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def send(self, text: str, settings: dict) -> None:
        self.stop_event.clear()
        self.commands.put(("generate", text, settings))

    def send_image(self, prompt: str) -> None:
        self.stop_event.clear()
        self.commands.put(("image", prompt))

    def send_vision(self, prompt: str, image_path: str) -> None:
        self.stop_event.clear()
        self.commands.put(("vision", prompt, image_path))

    def clear(self) -> None:
        self.commands.put(("clear",))

    def stop(self) -> None:
        self.stop_event.set()
        with self.image_lock:
            if self.image_process is not None and self.image_process.poll() is None:
                self.image_process.terminate()

    def shutdown(self) -> None:
        self.stop_event.set()
        self.shutdown_event.set()
        self.commands.put(("shutdown",))
        if self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=15)

    def _emit(self, kind: str, payload=None) -> None:
        self.events.put((kind, payload))

    def _run(self) -> None:
        try:
            model, tokenizer, stop_token_ids = self._load_model()
        except BaseException as error:
            self._emit("fatal", f"Could not load the model:\n{error}")
            return

        while not self.shutdown_event.is_set():
            command = self.commands.get()
            if command[0] == "shutdown":
                return
            if command[0] == "clear":
                self.messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
                self._emit("cleared")
                continue
            if command[0] == "generate":
                _, text, settings = command
                try:
                    self._generate(model, tokenizer, stop_token_ids, text, settings)
                except BaseException as error:
                    self._emit("generation_error", str(error))
            if command[0] == "image":
                _, prompt = command
                try:
                    self._emit("status", "Preparing Z-Image Turbo…")
                    del model
                    gc.collect()
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    model = None
                    self._emit("image_started", {"state": "started"})
                    result = self._generate_image(prompt)
                    self._emit("status", "Reloading Qwen…")
                    model, tokenizer, stop_token_ids = self._load_model()
                    self._emit("image_done", result)
                except BaseException as error:
                    self._emit("image_error", str(error))
                    if model is None and not self.shutdown_event.is_set():
                        try:
                            model, tokenizer, stop_token_ids = self._load_model()
                        except BaseException as reload_error:
                            self._emit("fatal", f"Could not reload Qwen after image generation:\n{reload_error}")
                            return
            if command[0] == "vision":
                _, prompt, image_path = command
                try:
                    self._emit("status", "Preparing vision model…")
                    del model
                    gc.collect()
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    model = None
                    self._emit("vision_started", {"state": "started"})
                    result = self._analyze_image(prompt, image_path)
                    self._emit("status", "Reloading Qwen…")
                    model, tokenizer, stop_token_ids = self._load_model()
                    self._emit("vision_done", result)
                except BaseException as error:
                    self._emit("vision_error", str(error))
                    if model is None and not self.shutdown_event.is_set():
                        try:
                            model, tokenizer, stop_token_ids = self._load_model()
                        except BaseException as reload_error:
                            self._emit("fatal", f"Could not reload Qwen after vision:\n{reload_error}")
                            return

    def _load_model(self):
        self._emit("status", "Loading tokenizer…")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
        self._emit("status", "Loading Qwen onto GPU…")
        torch.set_float32_matmul_precision("high")
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
        self._emit(
            "ready",
            {
                "model": MODEL_PATH.name,
                "gpu": torch.cuda.get_device_name(0),
            },
        )
        return model, tokenizer, stop_token_ids

    def _generate_image(self, prompt: str) -> dict:
        if not IMAGE_SCRIPT.is_file():
            raise FileNotFoundError(f"Z-Image launcher is missing: {IMAGE_SCRIPT}")
        IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output = IMAGE_OUTPUT_DIR / f"qwen-{time.strftime('%Y%m%d-%H%M%S')}.png"
        started = time.perf_counter()
        with self.image_lock:
            self.image_process = subprocess.Popen(
                [str(IMAGE_SCRIPT), prompt, str(output)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            process = self.image_process
        try:
            _logs, _ = process.communicate(timeout=900)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=15)
            raise TimeoutError("Image generation timed out after 15 minutes.")
        finally:
            with self.image_lock:
                self.image_process = None
        if self.stop_event.is_set():
            raise RuntimeError("Image generation was stopped.")
        if process.returncode != 0:
            raise RuntimeError("Z-Image Turbo could not generate the image.")
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("Z-Image Turbo finished without creating an image.")
        return {
            "state": "done",
            "image_path": str(output),
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }

    def _analyze_image(self, prompt: str, image_path: str) -> dict:
        image = Path(image_path).expanduser().resolve()
        for file in (VISION_CLI, VISION_MODEL, VISION_PROJECTOR, image):
            if not file.is_file():
                raise FileNotFoundError(f"Required vision file is missing: {file}")
        if image.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            raise ValueError("Attach a PNG, JPG, JPEG, WebP, or BMP image.")
        started = time.perf_counter()
        command = [
            str(VISION_CLI),
            "-m", str(VISION_MODEL),
            "--mmproj", str(VISION_PROJECTOR),
            "--image", str(image),
            "--prompt", prompt or "Describe this image in detail.",
            "--ctx-size", "4096",
            "--predict", "512",
            "--gpu-layers", "99",
            "--image-min-tokens", "1024",
            "--image-max-tokens", "1024",
            "--temp", "0.2",
            "--no-warmup",
        ]
        with self.image_lock:
            self.image_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            process = self.image_process
        try:
            output, _ = process.communicate(timeout=900)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=15)
            raise TimeoutError("Image analysis timed out after 15 minutes.")
        finally:
            with self.image_lock:
                self.image_process = None
        if self.stop_event.is_set():
            raise RuntimeError("Image analysis was stopped.")
        if process.returncode != 0:
            raise RuntimeError("The vision model could not analyze that image.")
        marker = "encoding done in"
        if marker in output:
            answer = output.rsplit(marker, 1)[1].split("\n", 1)[-1].strip()
        else:
            answer = output.strip()
        if not answer:
            raise RuntimeError("The vision model returned an empty answer.")
        return {
            "state": "done",
            "answer": answer,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }

    def _render_inputs(self, tokenizer, max_context_tokens: int):
        working = self.messages.copy()
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
                self.messages = working
                return inputs
            if len(working) <= 2:
                raise ValueError(
                    f"The latest message exceeds the {max_context_tokens}-token context limit."
                )
            del working[1:3]

    def _generate(self, model, tokenizer, stop_token_ids, text: str, settings: dict) -> None:
        language = settings.get("language", "").strip()[:80]
        system_prompt = DEFAULT_SYSTEM_PROMPT
        if language and language.lower() not in {"auto", "auto (match my message)"}:
            system_prompt += f" Respond in {language}."
        self.messages[0] = {"role": "system", "content": system_prompt}
        self.messages.append({"role": "user", "content": text})
        try:
            inputs = self._render_inputs(tokenizer, settings["max_context_tokens"]).to("cuda")
        except BaseException:
            self.messages.pop()
            raise

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
            "max_new_tokens": settings["max_new_tokens"],
            "do_sample": True,
            "temperature": settings["temperature"],
            "top_p": 0.8,
            "top_k": 20,
            "repetition_penalty": 1.1,
            "no_repeat_ngram_size": 5,
            "eos_token_id": stop_token_ids,
            "pad_token_id": tokenizer.pad_token_id,
            "stopping_criteria": StoppingCriteriaList([StopOnEvent(self.stop_event)]),
        }
        result: dict = {}
        failure: dict = {}

        def generation_thread() -> None:
            try:
                result["output"] = model.generate(**generation)
            except BaseException as error:
                failure["error"] = error
                streamer.end()

        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        runner = threading.Thread(target=generation_thread, daemon=True)
        runner.start()
        self._emit("generation_started")

        pieces = []
        loop_guard_triggered = False
        for piece in streamer:
            pieces.append(piece)
            self._emit("token", piece)
            if not self.stop_event.is_set() and has_runaway_repetition("".join(pieces)):
                loop_guard_triggered = True
                self.stop_event.set()
        runner.join()

        if "error" in failure:
            self.messages.pop()
            raise failure["error"]
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        output = result["output"]
        generated_tokens = output.shape[1] - input_tokens
        reply = "".join(pieces).strip()
        if reply:
            self.messages.append({"role": "assistant", "content": reply})
        stats = {
            "input_tokens": input_tokens,
            "output_tokens": generated_tokens,
            "tokens_per_second": generated_tokens / elapsed if elapsed else 0.0,
            "peak_vram_gib": torch.cuda.max_memory_allocated() / 2**30,
            "stopped": self.stop_event.is_set(),
            "loop_guard_triggered": loop_guard_triggered,
        }
        self._emit("generation_done", stats)


class QwenChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.events: queue.Queue = queue.Queue()
        self.worker = ModelWorker(self.events)
        self.ready = False
        self.generating = False
        self.assistant_open = False

        self.root.title("Qwen Local Chat")
        self.root.geometry("1060x760")
        self.root.minsize(760, 560)
        self.root.configure(bg=COLORS["window"])
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._configure_styles()
        self._build_header()
        self._build_chat()
        self._build_composer()
        self._build_statusbar()
        self._append_system(
            "Local Qwen3-1.7B chat. The model runs entirely on this laptop; "
            "messages are not sent to an online service."
        )
        self.root.after(50, self._poll_events)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=COLORS["window"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure(
            "Accent.TButton",
            background=COLORS["accent"],
            foreground="white",
            borderwidth=0,
            padding=(18, 10),
            font=("DejaVu Sans", 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", COLORS["accent_hover"]), ("disabled", COLORS["border"])])
        style.configure(
            "Quiet.TButton",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            borderwidth=0,
            padding=(12, 8),
        )
        style.map("Quiet.TButton", background=[("active", COLORS["surface_hover"]), ("disabled", COLORS["panel"])])
        style.configure(
            "Dark.TSpinbox",
            fieldbackground=COLORS["surface"],
            background=COLORS["surface"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["muted"],
            bordercolor=COLORS["border"],
        )

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, style="Panel.TFrame", padding=(22, 16))
        header.pack(fill="x")
        title_box = ttk.Frame(header, style="Panel.TFrame")
        title_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_box,
            text="Qwen Local Chat",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("DejaVu Sans", 16, "bold"),
        ).pack(anchor="w")
        self.model_label = tk.Label(
            title_box,
            text="Loading Qwen3-1.7B…",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("DejaVu Sans", 9),
        )
        self.model_label.pack(anchor="w", pady=(3, 0))

        self.stop_button = ttk.Button(header, text="Stop", style="Quiet.TButton", command=self.stop)
        self.stop_button.pack(side="right", padx=(8, 0))
        self.stop_button.state(["disabled"])
        self.clear_button = ttk.Button(header, text="Clear", style="Quiet.TButton", command=self.clear)
        self.clear_button.pack(side="right")
        self.clear_button.state(["disabled"])

    def _build_chat(self) -> None:
        holder = tk.Frame(self.root, bg=COLORS["window"], padx=18, pady=16)
        holder.pack(fill="both", expand=True)
        self.chat = ScrolledText(
            holder,
            wrap="word",
            state="disabled",
            bg=COLORS["window"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            borderwidth=0,
            font=("DejaVu Sans", 11),
            padx=16,
            pady=12,
            spacing1=2,
            spacing3=8,
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_configure("user_header", foreground=COLORS["user"], font=("DejaVu Sans", 10, "bold"), spacing1=12)
        self.chat.tag_configure("assistant_header", foreground=COLORS["assistant"], font=("DejaVu Sans", 10, "bold"), spacing1=12)
        self.chat.tag_configure("body", foreground=COLORS["text"], lmargin1=12, lmargin2=12, rmargin=20)
        self.chat.tag_configure("system", foreground=COLORS["muted"], font=("DejaVu Sans", 9, "italic"), justify="center", spacing1=8, spacing3=12)
        self.chat.tag_configure("error", foreground=COLORS["danger"], font=("DejaVu Sans", 10, "bold"), spacing1=8)

    def _build_composer(self) -> None:
        outer = tk.Frame(self.root, bg=COLORS["window"], padx=18)
        outer.pack(fill="x", pady=(0, 12))
        panel = tk.Frame(
            outer,
            bg=COLORS["surface"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        panel.pack(fill="x")
        self.input = tk.Text(
            panel,
            height=4,
            wrap="word",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["accent"],
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            font=("DejaVu Sans", 11),
        )
        self.input.pack(side="left", fill="both", expand=True)
        self.input.bind("<Return>", self._return_pressed)
        self.input.bind("<Control-Return>", self._force_newline)

        side = tk.Frame(panel, bg=COLORS["surface"], padx=10, pady=10)
        side.pack(side="right", fill="y")
        self.send_button = ttk.Button(side, text="Send", style="Accent.TButton", command=self.send)
        self.send_button.pack(side="bottom")
        self.send_button.state(["disabled"])

        settings = tk.Frame(outer, bg=COLORS["window"])
        settings.pack(fill="x", pady=(8, 0))
        tk.Label(settings, text="Max reply tokens", bg=COLORS["window"], fg=COLORS["muted"], font=("DejaVu Sans", 9)).pack(side="left")
        self.max_tokens = tk.IntVar(value=256)
        ttk.Spinbox(settings, from_=32, to=1024, increment=32, width=6, textvariable=self.max_tokens, style="Dark.TSpinbox").pack(side="left", padx=(7, 18))
        tk.Label(settings, text="Temperature", bg=COLORS["window"], fg=COLORS["muted"], font=("DejaVu Sans", 9)).pack(side="left")
        self.temperature = tk.DoubleVar(value=0.7)
        ttk.Spinbox(settings, from_=0.1, to=1.5, increment=0.1, width=5, textvariable=self.temperature, style="Dark.TSpinbox").pack(side="left", padx=(7, 0))
        tk.Label(settings, text="Enter sends • Ctrl+Enter adds a line", bg=COLORS["window"], fg=COLORS["muted"], font=("DejaVu Sans", 9)).pack(side="right")

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self.root, style="Panel.TFrame", padding=(18, 9))
        bar.pack(fill="x")
        self.status_dot = tk.Label(bar, text="●", bg=COLORS["panel"], fg=COLORS["muted"], font=("DejaVu Sans", 9))
        self.status_dot.pack(side="left")
        self.status_label = tk.Label(bar, text="Starting…", bg=COLORS["panel"], fg=COLORS["muted"], font=("DejaVu Sans", 9))
        self.status_label.pack(side="left", padx=(6, 0))
        self.stats_label = tk.Label(bar, text="", bg=COLORS["panel"], fg=COLORS["muted"], font=("DejaVu Sans", 9))
        self.stats_label.pack(side="right")

    def _return_pressed(self, event):
        if event.state & 0x0004:
            return None
        self.send()
        return "break"

    def _force_newline(self, _event):
        self.input.insert("insert", "\n")
        return "break"

    def send(self) -> None:
        if not self.ready or self.generating:
            return
        text = self.input.get("1.0", "end-1c").strip()
        if not text:
            return
        try:
            max_new_tokens = max(1, min(1024, int(self.max_tokens.get())))
            temperature = max(0.1, min(1.5, float(self.temperature.get())))
        except (ValueError, tk.TclError):
            messagebox.showerror("Invalid settings", "Token count and temperature must be numbers.")
            return
        self.input.delete("1.0", "end")
        self._append_message("You", text, "user_header")
        self._begin_assistant()
        self.generating = True
        self._set_controls()
        self._set_status("Generating…", COLORS["accent"])
        self.worker.send(
            text,
            {
                "max_new_tokens": max_new_tokens,
                "max_context_tokens": 4096,
                "temperature": temperature,
            },
        )

    def stop(self) -> None:
        if self.generating:
            self.worker.stop()
            self._set_status("Stopping…", COLORS["danger"])

    def clear(self) -> None:
        if not self.ready or self.generating:
            return
        self.worker.clear()
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self._append_system("Conversation cleared. The model remains loaded locally.")
        self.stats_label.configure(text="")

    def close(self) -> None:
        self.worker.shutdown()
        self.root.destroy()

    def _set_controls(self) -> None:
        if self.ready and not self.generating:
            self.send_button.state(["!disabled"])
            self.clear_button.state(["!disabled"])
            self.stop_button.state(["disabled"])
            self.input.configure(state="normal")
        elif self.generating:
            self.send_button.state(["disabled"])
            self.clear_button.state(["disabled"])
            self.stop_button.state(["!disabled"])
            self.input.configure(state="disabled")
        else:
            self.send_button.state(["disabled"])
            self.clear_button.state(["disabled"])
            self.stop_button.state(["disabled"])
            self.input.configure(state="disabled")

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text)
        self.status_dot.configure(fg=color)

    def _append_message(self, speaker: str, text: str, header_tag: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{speaker}\n", header_tag)
        self.chat.insert("end", text + "\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _append_system(self, text: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", text + "\n", "system")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _begin_assistant(self) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", "Qwen\n", "assistant_header")
        self.chat.configure(state="disabled")
        self.assistant_open = True

    def _append_token(self, text: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", text, "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _finish_assistant(self) -> None:
        if not self.assistant_open:
            return
        self.chat.configure(state="normal")
        self.chat.insert("end", "\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")
        self.assistant_open = False

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self._set_status(payload, COLORS["muted"])
                elif kind == "ready":
                    self.ready = True
                    self.model_label.configure(text=f"{payload['model']} • {payload['gpu']} • BF16")
                    self._set_status("Ready", COLORS["success"])
                    self._set_controls()
                    self.input.focus_set()
                elif kind == "token":
                    self._append_token(payload)
                elif kind == "generation_done":
                    self._finish_assistant()
                    self.generating = False
                    if payload["loop_guard_triggered"]:
                        label = "Repetition loop stopped"
                        color = COLORS["danger"]
                        self._append_system("Stopped an obvious repetition loop automatically.")
                    elif payload["stopped"]:
                        label = "Stopped"
                        color = COLORS["danger"]
                    else:
                        label = "Ready"
                        color = COLORS["success"]
                    self._set_status(label, color)
                    self.stats_label.configure(
                        text=(
                            f"{payload['output_tokens']} tokens • "
                            f"{payload['tokens_per_second']:.1f} tok/s • "
                            f"{payload['peak_vram_gib']:.2f} GiB VRAM"
                        )
                    )
                    self._set_controls()
                    self.input.focus_set()
                elif kind == "generation_error":
                    self._finish_assistant()
                    self.generating = False
                    self._set_status("Generation failed", COLORS["danger"])
                    self._append_message("Error", payload, "error")
                    self._set_controls()
                elif kind == "fatal":
                    self._set_status("Model failed to load", COLORS["danger"])
                    self._append_message("Error", payload, "error")
                    messagebox.showerror("Qwen failed to load", payload)
                elif kind == "cleared":
                    self._set_status("Ready", COLORS["success"])
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(50, self._poll_events)


def main() -> None:
    root = tk.Tk()
    QwenChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
