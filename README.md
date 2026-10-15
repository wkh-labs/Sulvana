# Local AI workspace

This directory contains an isolated Python 3.12 environment for NVIDIA GPU work.
It does not modify CachyOS's system Python.

## Sulvana desktop app

Run `sulvana` from a terminal or open **Sulvana** from the application launcher.
It opens a native desktop window; the Python model service stays on this laptop.
The assistant is **Sulvana 2.0** by WKH Labs, a Khmer-first assistant built on
MiMo-V2.6-Distill-Qwen-9B (a Qwen3.5-9B fine-tune); `SULVANA_BASE=dolphin` runs the earlier
Sulvana v1 on Dolphin 3.0 Llama 3.1 8B (Built with Llama). Credits and licences: `NOTICE.md`. The app also uses a separate local vision model for image questions and
Z-Image Turbo for image generation. The image
features switch models in GPU memory, so their first response can take longer.

Sulvana can search its bundled Markdown documentation, perform a public web
search when explicitly asked, and run a small allowlist of read-only inspection
commands. It cannot run arbitrary terminal commands or make system changes.
The exact tool limits are documented in `knowledge/TOOLS.md` and
`knowledge/AGENT_SAFETY.md`.

Sulvana replies in Khmer when you write in Khmer or when the language is unclear, and in
your language when you clearly write in another one; the Reply language setting overrides
both. Its name, the model it is built on, the context size and both system prompts are at the
top of `sulvana_worker.py`. Khmer text needs about 1.6 tokens per character, so the engine
runs with a 65,536-token context and replies can be up to 8,192 tokens; a reply that stops at
the limit gets a Continue button. That context does not fit in 8 GB of VRAM next to the model,
so llama.cpp (`--fit`) keeps some layers in system RAM, which makes replies slower; start Sulvana
with `SULVANA_CONTEXT=16384` for full GPU speed with a shorter memory.

Under the message box, **Code** turns Sulvana into a coding agent for one project folder you choose: it
reads and searches files by itself, and asks before every edit (shown as a diff) and every command (run in
a sandbox with no network). See `knowledge/TOOLS.md` and `sulvana_code.py`.

Under the message box, **Search** lets Sulvana look that one message up on the web (the
sources it used are listed under the answer and open in your browser), and **Reason** makes it
work a problem out step by step first, with the thinking shown in a section you can open. The
reasoning is prompted, not a trained reasoning model: it helps with arithmetic and logic and
makes replies slower.

**Khmer quality today:** the base model writes Khmer script but not meaningful Khmer. That is
measured, not assumed: see `benchmark/khmer/` and the "Teaching Dolphin Khmer" section of
`finetune/README.md`, which is the plan for fixing it.

In the app, Enter sends and Shift+Enter starts a new line; Escape stops a reply or closes a
dialog. You can browse other conversations while a reply is being written. If the model
process stops, Sulvana shows a banner with a **Restart engine** button, and relaunching
`sulvana` also replaces an engine that has stopped.

The window is an Electron (Chromium) shell (`electron-ui/`) around the web interface in
`sulvana-ui/` (entry point `src/DesktopApp.tsx`), served locally by `sulvana_web.py`. It uses the
`electron` already installed on this system and has no Node access to the page. The older
JavaFX shell (`java-ui/src/SulvanaDesktop.java`) is still there and starts with
`SULVANA_SHELL=javafx sulvana`, but its WebView cannot shape Khmer: vowels that sit before or
around their consonant (េ ែ ៃ ោ ៅ ើ ៀ and ្រ) are drawn in the wrong place, which makes Khmer
unreadable. That is why Electron is the default. The first Electron launch carries over the
conversations saved by the JavaFX window; each shell then keeps its own history. After
editing the interface run `npm run build` in `sulvana-ui/`; the launcher also rebuilds it when
the sources are newer than the build. Restart the engine after editing the Python files with
`systemctl --user stop sulvana-web` and launch `sulvana` again.

The interface follows Apple's Liquid Glass design language: translucent, blurred panels floating
over a softly tinted backdrop, with spring animations. Colours, glass, type and weights are tokens
at the top of `sulvana-ui/src/index.css`. The logo (`sulvana-icon.svg`) is a five-petal lotus,
also drawn inline in the interface. San Francisco itself is licensed for Apple platforms only, so the
font stack uses it where it exists and otherwise Inter or the Inter-based Adwaita Sans that
ships with this desktop; Khmer text falls through to Noto Sans Khmer. Medium, semibold and bold
come from the `--weight-*` tokens rather than `font-weight`, and surfaces are solid rather than
the JavaFX fallback shell gets opaque panels, because it can draw neither real weights of that
font nor background blur.

## Start an interactive environment

```bash
source /home/tanchjim/Documents/Codex/ai-workspace/activate-ai.sh
```

## Run a long job at full plugged-in performance

The wrapper checks that the main AC adapter is connected, switches to the
Performance power profile, activates the environment, runs the command, and
restores the previous power profile when the command exits.

```bash
/home/tanchjim/Documents/Codex/ai-workspace/run-performance.sh python train.py
```

## Verify the GPU stack

```bash
/home/tanchjim/Documents/Codex/ai-workspace/run-performance.sh \
  python /home/tanchjim/Documents/Codex/ai-workspace/gpu-check.py
```

Run the optional 20-second cooling and stability check:

```bash
/home/tanchjim/Documents/Codex/ai-workspace/run-performance.sh \
  python /home/tanchjim/Documents/Codex/ai-workspace/gpu-benchmark.py
```

Large reusable files belong in `datasets/`, `models/`, and `runs/`. Hugging Face
and PyTorch caches are kept inside this workspace so disk usage is easy to audit.

For an 8 GB GPU, prefer BF16, gradient checkpointing, short initial context
lengths, gradient accumulation, and 4-bit QLoRA for 7B/8B models.

## Fine-tune Dolphin 3.0 · 8B

`finetune/` holds a QLoRA workflow for the model Sulvana uses: dataset validation and
splitting, resumable training with logged runs, and evaluation against the original
checkpoint. It trains a separate adapter under `runs/finetune/` and never changes Sulvana's
model file. It has been smoke-tested on a tiny stand-in model only; a real run first needs the
16 GB trainable checkpoint and a dataset. Start with `finetune/README.md`.

```bash
.venv/bin/python finetune/selfcheck.py      # quick pipeline check, no GPU or download
.venv/bin/python finetune/fetch_base.py     # shows what the 16 GB download would fetch
```

## Chat with Qwen3 1.7B

Launch the JavaFX desktop GUI (styled with CSS, using the local Python model backend):

```bash
/home/tanchjim/Documents/Codex/ai-workspace/qwen-gui.sh
```

The desktop app supports Unicode input and display, right-to-left chat text,
streaming replies, Stop, New chat, copy, and an editable reply-language field.
Choose Auto to match your message, or type any language name. The interface can
handle any language supported by your installed fonts; answer quality depends
on Qwen3-1.7B's actual training and is weaker for some languages, including Khmer.
Its Java 25 and JavaFX 25 runtimes are stored locally in `.runtime/`.

Or use the Qwen terminal interface:

```bash
/home/tanchjim/Documents/Codex/ai-workspace/qwen-chat.sh \
  --max-new-tokens 256
```

The terminal launcher uses the post-trained Qwen3-1.7B checkpoint in non-thinking mode,
keeps conversation history, streams replies, and supports `/help`, `/clear`,
`/stats`, `/system TEXT`, and `/quit`. The separate base checkpoint remains in
`models/Qwen3-1.7B-Base` for baseline evaluation and future fine-tuning.

## Sulvana images and vision

In Sulvana, ask `Generate an image of …` or start a message with `/image …`
to create an image locally with Z-Image Turbo. Attach a PNG, JPG, JPEG, or WebP
and ask a question about it.

For image requests and image understanding, Sulvana temporarily swaps the
normal chat model out of GPU memory, runs the specialist model, then reloads
Dolphin. This keeps the workflow reliable on the laptop's 8 GB GPU, but each
swap adds a short wait before the reply appears.
