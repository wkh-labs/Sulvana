"""Read Khmer text aloud on this computer with Meta's MMS text-to-speech model for Khmer (VITS, CPU).

The model (models/mms-tts-khm, 145 MB, CC BY-NC 4.0) reads Khmer letters only, so numbers are spelled out in
Khmer words first, and markdown, code, links and Latin-script words are left out.
"""

from __future__ import annotations

import io
import re
import threading
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models/mms-tts-khm"
MAX_CHARS = 4000
_model: dict = {}
_lock = threading.Lock()

ONES = ["សូន្យ", "មួយ", "ពីរ", "បី", "បួន", "ប្រាំ", "ប្រាំមួយ", "ប្រាំពីរ", "ប្រាំបី", "ប្រាំបួន"]
TENS = ["", "ដប់", "ម្ភៃ", "សាមសិប", "សែសិប", "ហាសិប", "ហុកសិប", "ចិតសិប", "ប៉ែតសិប", "កៅសិប"]
UNITS = [(1_000_000, "លាន"), (100_000, "សែន"), (10_000, "ម៉ឺន"), (1_000, "ពាន់"), (100, "រយ")]
KHMER_DIGITS = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")


def available() -> bool:
    return (MODEL_DIR / "model.safetensors").is_file()


def number_words(value: int) -> str:
    """25500 → ពីរម៉ឺនប្រាំពាន់ប្រាំរយ"""
    if value < 10:
        return ONES[value]
    if value < 100:
        return TENS[value // 10] + (ONES[value % 10] if value % 10 else "")
    for size, name in UNITS:
        if value >= size:
            head, rest = divmod(value, size)
            return number_words(head) + name + (number_words(rest) if rest else "")
    return str(value)


def _numbers(match: re.Match) -> str:
    text = match.group(0).translate(KHMER_DIGITS).replace(",", "").replace(" ", "")
    whole, _, fraction = text.partition(".")
    if len(whole) > 12:
        return " ".join(ONES[int(d)] for d in whole)
    words = number_words(int(whole))
    if fraction:
        words += "ចុច" + "".join(ONES[int(d)] for d in fraction)
    return words


def speakable(text: str) -> str:
    """The part of a reply that can be read aloud, with numbers as words."""
    text = re.sub(r"```[\s\S]*?```", " ", text)                    # code blocks
    text = re.sub(r"`[^`]*`|https?://\S+|\S+@\S+", " ", text)       # inline code, links, e-mail
    text = re.sub(r"[*_#>|\[\]()«»\"“”]", " ", text)                  # markdown and quotes
    for symbol, word in (("°C", " អង្សាសេ"), ("°F", " អង្សាហ្វារិនហៃ"), ("%", " ភាគរយ"), ("×", " គុណ "), ("÷", " ចែក "),
                         ("=", " ស្មើ "), ("+", " បូក "), ("−", " ដក "), ("–", " ដល់ "), ("៛", " រៀល"), ("$", " ដុល្លារ ")):
        text = text.replace(symbol, word)
    text = re.sub(r"[0-9០-៩](?:[0-9០-៩]|[,\s](?=[0-9០-៩]{3}\b))*(?:\.[0-9០-៩]+)?", _numbers, text)
    text = re.sub(r"[A-Za-z][A-Za-z'’.-]*", " ", text)               # Latin-script words cannot be read
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()[:MAX_CHARS]


def _load() -> dict:
    with _lock:
        if not _model:
            import torch
            import transformers
            torch.set_num_threads(4)
            _model["tokenizer"] = transformers.AutoTokenizer.from_pretrained(str(MODEL_DIR))
            _model["model"] = transformers.VitsModel.from_pretrained(str(MODEL_DIR)).eval()
        return _model


def speak(text: str) -> bytes:
    """WAV audio of the Khmer in `text`, sentence by sentence with short pauses. Raises ValueError if nothing to read."""
    import numpy as np
    import torch
    clean = speakable(text)
    sentences = [part.strip() for part in re.split(r"[។?!៕\n]+", clean) if re.search(r"[ក-៿]", part)]
    if not sentences:
        raise ValueError("There is no Khmer text to read aloud.")
    loaded = _load()
    rate = loaded["model"].config.sampling_rate
    pause = np.zeros(int(rate * 0.35), dtype=np.float32)
    pieces = []
    with _lock, torch.no_grad():
        for sentence in sentences:
            inputs = loaded["tokenizer"](sentence, return_tensors="pt")
            if inputs["input_ids"].shape[1] < 2:
                continue
            pieces += [loaded["model"](**inputs).waveform[0].numpy(), pause]
    if not pieces:
        raise ValueError("There is no Khmer text to read aloud.")
    audio = (np.clip(np.concatenate(pieces), -1, 1) * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(rate); handle.writeframes(audio.tobytes())
    return buffer.getvalue()
