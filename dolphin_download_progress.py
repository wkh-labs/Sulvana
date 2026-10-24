#!/usr/bin/env python3
"""A tiny live progress window for Sulvana's Dolphin model download."""

from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk


MODEL = (Path(__file__).resolve().parent / "models/Dolphin3.0-Llama3.1-8B/Dolphin3.0-Llama3.1-8B-Q4_K_M.gguf")
TOTAL = 4_920_749_472


def format_size(value: float) -> str:
    return f"{value / 1024**3:.2f} GB"


class ProgressWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Sulvana — Downloading Dolphin 8B")
        self.root.geometry("520x230")
        self.root.resizable(False, False)
        self.root.configure(bg="#12141c")
        self.last_size = 0
        self.last_time = time.monotonic()
        self.speed = 0.0

        panel = tk.Frame(self.root, bg="#1a1d28", padx=26, pady=24)
        panel.pack(fill="both", expand=True, padx=14, pady=14)
        tk.Label(panel, text="Preparing Sulvana", font=("Sans", 18, "bold"), fg="#f1f2f8", bg="#1a1d28").pack(anchor="w")
        tk.Label(panel, text="Dolphin 3.0 · Llama 3.1 8B", font=("Sans", 11), fg="#aeb5cc", bg="#1a1d28").pack(anchor="w", pady=(3, 20))
        self.bar = ttk.Progressbar(panel, length=460, mode="determinate", maximum=100)
        self.bar.pack(fill="x")
        self.percent = tk.Label(panel, font=("Sans", 15, "bold"), fg="#a78bfa", bg="#1a1d28")
        self.percent.pack(anchor="w", pady=(14, 2))
        self.detail = tk.Label(panel, font=("Sans", 10), fg="#c9cedd", bg="#1a1d28")
        self.detail.pack(anchor="w")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.update()

    def update(self) -> None:
        try:
            size = MODEL.stat().st_size
        except FileNotFoundError:
            size = 0
        now = time.monotonic()
        elapsed = now - self.last_time
        if elapsed >= 0.4:
            instant = max(0, size - self.last_size) / elapsed
            self.speed = instant if self.speed == 0 else self.speed * 0.72 + instant * 0.28
            self.last_size, self.last_time = size, now
        ratio = min(size / TOTAL, 1.0)
        self.bar["value"] = ratio * 100
        self.percent.config(text=f"{ratio * 100:.1f}% downloaded")
        if size >= TOTAL:
            self.detail.config(text="Download complete — you can open Sulvana now.", fg="#74d8ad")
        else:
            remaining = TOTAL - size
            if self.speed > 50_000:
                seconds = remaining / self.speed
                eta = f"about {seconds / 60:.0f} min left" if seconds >= 60 else f"about {seconds:.0f} sec left"
                rate = f"{self.speed / 1024**2:.1f} MB/s"
                extra = f" • {rate} • {eta}"
            else:
                extra = " • waiting for download data…"
            self.detail.config(text=f"{format_size(size)} of {format_size(TOTAL)}{extra}", fg="#c9cedd")
        self.root.after(500, self.update)


if __name__ == "__main__":
    ProgressWindow().root.mainloop()
