"""Sulvana's coding mode: a small agent harness in the spirit of Claude Code.

The model works on one project folder that the user chose in the app. It can list, read and
search files there on its own. Every file change and every command waits for the user's
approval in the app, and edits are shown as a diff first. Commands run in a bubblewrap sandbox:
no network, a read-only view of the system with credentials and browser profiles hidden, and
write access only to the project folder. Every file Sulvana changes is backed up first, so a
whole task can be undone from the app.

The model calls tools with small XML blocks, one per message, because an 8B model copies that
format far more reliably than JSON with escaped code:

    <tool name="read_file">
    <path>src/app.py</path>
    </tool>
"""

from __future__ import annotations

import difflib
import json
import os
import re
import secrets
import shutil
import subprocess
import textwrap
import threading
import time
from pathlib import Path
from typing import Callable

APP_ROOT = Path(__file__).resolve().parent
CHECKPOINTS = APP_ROOT / ".runtime" / "code-checkpoints"
HOME = Path.home().resolve()
TASK_ID = re.compile(r"[A-Za-z0-9_-]{8,40}")
MAX_STEPS = 25
MAX_RESULT = 24_000
MAX_READ_LINES = 400
COMMAND_TIMEOUT = 120
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target", ".next",
             ".cache", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".idea", ".gradle", ".tox"}
# Hidden from sandboxed commands: credentials, key stores, browser and editor profiles.
PRIVATE = [".ssh", ".gnupg", ".password-store", ".aws", ".azure", ".kube", ".docker", ".config/gcloud",
           ".config/gh", ".config/hub", ".local/share/keyrings", ".mozilla", ".thunderbird", ".config/chromium",
           ".config/google-chrome", ".config/BraveSoftware", ".config/vivaldi", ".config/Code", ".config/Claude",
           ".claude", ".codex", ".netrc", ".git-credentials", ".npmrc", ".pypirc", ".cargo/credentials.toml",
           ".config/git/credentials"]
TOOLS = ("list_files", "read_file", "search_files", "edit_file", "write_file", "run_command")
# The model is stopped as soon as it closes a tool call, so it waits for the result.
CALL_STOPS = ["</tool>", *(f"</{name}>" for name in TOOLS)]
_CALL_START = re.compile(r"<tool[\s>]|<tool_call>|<(?:%s)>" % "|".join(TOOLS))
_OPENINGS = ["<tool ", "<tool>", "<tool_call>", *(f"<{name}>" for name in TOOLS)]

# The same tools as OpenAI-style function definitions, for models with native tool calling (MiMo /
# Qwen3.5). llama-server renders them into the model's own prompt format and parses its calls.
TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "list_files", "description": "List the files under a folder of the project (respects .gitignore).",
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Folder relative to the project root. Default: ."}}}}},
    {"type": "function", "function": {"name": "read_file", "description": f"Show a file with line numbers, at most {MAX_READ_LINES} lines per call.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer", "description": "First line (default 1)"},
                                                      "end": {"type": "integer", "description": "Last line"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "search_files", "description": "Search file contents with a regular expression; returns matching lines with line numbers.",
     "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "description": "Folder or file to search. Default: ."}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": (
        "Change an existing file. Either replace lines start..end (numbers from your latest read_file of that file) with `replace`, "
        "or replace the exact text `search` (must appear once) with `replace`. An empty `search` adds `replace` at the end of the file. "
        "After an edit the line numbers change: read the file again before another numbered edit."),
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"},
                                                      "search": {"type": "string"}, "replace": {"type": "string", "description": "The new lines, with full indentation"}},
                    "required": ["path", "replace"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create a new file. Never use it to change an existing file; use edit_file.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_command", "description": (
        f"Run a shell command in the project folder, in a sandbox without network access, with a {COMMAND_TIMEOUT} second limit. "
        "Use it for tests, builds, linters or running the program. Nothing can be installed or downloaded."),
     "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
]


def native_fields(name: str, arguments) -> tuple[str, dict] | None:
    """Turn a native tool call (name plus JSON arguments) into the fields CodeSession.run expects."""
    if name not in TOOLS:
        return None
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except ValueError:
            return None
    if not isinstance(arguments, dict):
        return None
    fields = {key: (str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else value)
              for key, value in arguments.items() if value is not None}
    if name == "edit_file" and "search" in fields and not fields.get("start"):
        fields["edits"] = [(str(fields.pop("search")), str(fields.pop("replace", "")))]
    return name, fields


def parse_native_text(text: str) -> tuple[str, dict] | None:
    """A native call that reached the text unparsed: <tool_call><function=x><parameter=k>v</parameter>…"""
    match = re.search(r"<function=([a-z_]+)>(.*?)(?:</function>|$)", text, re.S)
    if not match:
        return None
    arguments = {key: _inner(value) for key, value in re.findall(r"<parameter=([a-z_]+)>(.*?)</parameter>", match.group(2), re.S)}
    return native_fields(match.group(1), arguments)


class CodeError(Exception):
    """A problem the model or the user should read as plain text."""


def project_root(raw: str) -> Path:
    """The folder a coding task may work in: a real, non-hidden folder inside the home folder."""
    if not raw or not os.path.isabs(os.path.expanduser(raw)):
        raise CodeError("Choose a project folder for coding mode (Settings → Coding project).")
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise CodeError(f"The project folder does not exist: {root}")
    if root == HOME or not root.is_relative_to(HOME):
        raise CodeError("Choose a project folder inside your home folder (not the home folder itself).")
    if any(part.startswith(".") for part in root.relative_to(HOME).parts):
        raise CodeError("Hidden folders cannot be used as a coding project.")
    return root


# ---------------------------------------------------------------- parsing the model's tool calls

def call_start(text: str) -> int:
    match = _CALL_START.search(text)
    return match.start() if match else -1


def safe_length(text: str) -> int:
    """How much of streamed text can be shown now: hold back anything that may become a tool call."""
    tail = text[-40:]
    offset = len(text) - len(tail)
    at = tail.rfind("<")
    if at >= 0 and any(opening.startswith(tail[at:]) for opening in _OPENINGS):
        fence = re.search(r"```[A-Za-z]*\s*$", tail[:at])
        return offset + (fence.start() if fence else at)
    fence = re.search(r"`{1,3}[A-Za-z]*\s*$", tail)
    return offset + fence.start() if fence else len(text)


def narration_before(text: str, start: int) -> str:
    """The prose before a tool call, without a code fence the model opened around the call."""
    return re.sub(r"```[A-Za-z]*\s*$", "", text[:start]).rstrip()


def _inner(value: str) -> str:
    value = value[1:] if value.startswith("\n") else value
    return value[:-1] if value.endswith("\n") else value


def parse_call(text: str) -> tuple[str, dict] | None:
    """Read one tool call: <tool name="x"><field>…</field></tool>, or the <x>…</x> form."""
    match = re.search(r"<tool\s+name\s*=\s*[\"']?([a-z_]+)[\"']?\s*>(.*?)(?:</tool>|$)", text, re.S)
    if not match:
        match = re.search(r"<(%s)>(.*?)(?:</\1>|$)" % "|".join(TOOLS), text, re.S)
    if not match or match.group(1) not in TOOLS:
        return None
    name, body = match.group(1), match.group(2)
    fields: dict = {}
    pairs: list[tuple[str, str]] = []
    pending_search: str | None = None
    for key, value in re.findall(r"<(path|pattern|command|content|search|replace|start|end)>(.*?)</\1>", body, re.S):
        if key == "search":
            pending_search = _inner(value)
        elif key == "replace":
            if pending_search is not None:
                pairs.append((pending_search, _inner(value)))
            else:
                fields["replace"] = _inner(value)   # a numbered edit: <start>/<end> plus <replace>
            pending_search = None
        elif key in {"content", "command"}:
            fields[key] = _inner(value)
        else:
            fields[key] = value.strip()
    if pairs:
        fields["edits"] = pairs
    if name in {"run_command", "search_files"} and not fields.get("command") and not fields.get("pattern"):
        # Tolerate a bare value: <run_command>pytest</run_command>
        bare = re.sub(r"<[^>]+>", "", body).strip()
        if bare:
            fields["command" if name == "run_command" else "pattern"] = bare
    return name, fields


# A worked example, given to the model as earlier turns: small models copy a format they have
# seen used far more reliably than one that is only described.
EXAMPLE = [
    {"role": "user", "content": "(Example task) What does greet.py print?"},
    {"role": "assistant", "content": "I'll read greet.py.\n\n<tool name=\"read_file\">\n<path>greet.py</path>\n</tool>"},
    {"role": "user", "content": "[Result of read_file]\ngreet.py (lines 1–2 of 2):\n    1\tname = \"Dara\"\n    2\tprint(f\"Hello, {name}!\")"},
    {"role": "assistant", "content": "`greet.py` prints `Hello, Dara!`."},
    {"role": "user", "content": "(End of example. The real conversation starts now, in a different project.)"},
    {"role": "assistant", "content": "Understood."},
]
# Prose that announces a step instead of taking it ("I will read the file…").
ANNOUNCES = re.compile(r"\b(?:I will|I'll|I am going to|I'm going to|let me|let's|let us|first,? I|next,? I|now,? I)\b|:\s*$", re.I)


def needs_nudge(prose: str, steps: int) -> bool:
    """The model described what it will do but used no tool."""
    if steps == 0:
        return True
    last = re.split(r"(?<=[.!?។])\s+", prose.strip())[-1] if prose.strip() else ""
    return bool(ANNOUNCES.search(last))


# Requests that need the model to change or run something, in English or Khmer.
WANTS_ACTION = re.compile(r"\b(?:fix|change|edit|add|remove|delete|rename|implement|create|write|make|update|refactor|"
                          r"run|test|build|debug|repair|improve|convert|install)\w*|កែ|បន្ថែម|លុប|បង្កើត|សរសេរ|ដំណើរការ|សាកល្បង", re.I)


def unfinished(request: str, session: "CodeSession") -> str:
    """A reminder when the model stops without having done what was asked, or "" if it may stop."""
    if not WANTS_ACTION.search(request):
        return ""
    acted = {name for name in session.used if name in {"edit_file", "write_file", "run_command"}}
    if acted:
        return ""
    return ("You have not changed any files or run anything yet, so nothing has been checked. The user asked: "
            f"\"{request[:600]}\"\nContinue with the next step using one tool call. Read the relevant source files "
            "before deciding, and run the tests or program to check. Only if no change is needed, explain exactly why.")


NUDGE = ("Go ahead and do that now with one tool call. "
         "If you are completely finished, instead summarise what you changed and how to check it.")


def code_loop(text: str) -> bool:
    """A model stuck repeating itself. Code repeats legitimately (closing braces), so only flag
    a block of real content repeated many times in a row."""
    lines = [line.strip() for line in text.splitlines() if line.strip()][-60:]
    for width in range(1, 11):
        if len(lines) < width * 6:
            break
        block = lines[-width:]
        if sum(len(line) for line in block) >= 20 and lines[-width * 6:] == block * 6:
            return True
    return False


# ---------------------------------------------------------------- the prompt

def native_system_prompt(session: "CodeSession", language_hint: str) -> str:
    """The prompt for models with native tool calling: the tools themselves arrive as definitions."""
    return f"""You are Sulvana, a careful coding agent working inside the user's project folder "{session.root.name}" on their own computer.
You can look at and change the project only through your tools. Work step by step: explore, make focused changes, then check them.

Rules:
- Before each tool call, say in one short sentence what you are about to do. Call one tool at a time.
- The user approves every edit and command. If they decline one, do not repeat it; ask what they would prefer.
- Paths are relative to the project folder; you cannot reach files outside it.
- Read the relevant code before changing it, and follow the project's existing style. Keep changes small and focused.
- Prefer numbered edits (start/end from your latest read_file). Never use write_file on an existing file.
- After changing code, check it with run_command when the project has a way to (tests, a build, running the script).
- There is no internet and no sudo: never try to install or download anything. Work with what is installed.
- If a step fails, read the error and change your approach. Never repeat a step that already failed.
- Never invent tool results.
- When the task is done, or you need the user's input, reply without a tool call: say what you changed (files and why) and how to check it. Keep it brief.
- Write explanations in {language_hint}. Keep code, identifiers, file names and commands in their original form.

{session.overview()}"""


def system_prompt(session: "CodeSession", language_hint: str) -> str:
    return f"""You are Sulvana, a careful coding assistant working inside the user's project folder "{session.root.name}" on their own computer.
You can look at and change the project only through the tools below. Work step by step: explore, make focused changes, then check them.

How to use a tool: write one short sentence saying what you are about to do, then exactly one tool block, then stop. You will receive the result in the next message. Use only one tool per message.

Tools:

<tool name="list_files">
<path>.</path>
</tool>
Lists files under a folder (respects .gitignore).

<tool name="read_file">
<path>src/app.py</path>
<start>1</start>
<end>200</end>
</tool>
Shows a file with line numbers (start and end are optional, at most {MAX_READ_LINES} lines at a time).

<tool name="search_files">
<pattern>def load_config</pattern>
<path>.</path>
</tool>
Searches file contents with a regular expression and shows matching lines with line numbers.

<tool name="edit_file">
<path>src/app.py</path>
<start>12</start>
<end>13</end>
<replace>
    total = price * count * (1 + tax_rate)
    return total
</replace>
</tool>
Replaces lines 12 to 13 of an existing file (the line numbers shown by your latest read_file) with the new lines. Write the new lines with their full indentation. After any edit the line numbers change, so read the file again before the next numbered edit.
Instead of line numbers you may give the exact old text: <search>old lines</search> then <replace>new lines</replace>. To add new code at the end of a file, use an empty <search></search> and put the new code in <replace>.

<tool name="write_file">
<path>tests/test_tax.py</path>
<content>
...the complete file...
</content>
</tool>
Creates a new file. Never use it to add to or change an existing file: that would delete everything you do not repeat. Use edit_file for existing files.

<tool name="run_command">
<command>python -m pytest -q</command>
</tool>
Runs a shell command in the project folder, in a sandbox without network access, with a {COMMAND_TIMEOUT} second limit. Use it to run tests, linters, builds or the program. There is no internet and no sudo, so nothing can be installed: never try to install or download anything. If something is missing, work without it (for example run a test file directly with python) or tell the user what to install.

Rules:
- The user approves every edit and command. If they decline one, do not repeat it; ask what they would prefer.
- Paths are relative to the project folder. You cannot reach files outside it.
- Look before you change: read the relevant code, and follow the project's existing style.
- Keep changes small and focused on what was asked. Do not rewrite files that only need an edit.
- After changing code, check it with run_command when the project has a way to (tests, a build, running the script).
- Never invent tool results. Only a result message tells you what happened.
- If a step fails, read the error and change your approach. Never repeat a step that already failed.
- When the task is done, or you need the user's input, reply without a tool: say what you changed (files and why) and how the user can check it. Keep it brief.
- Write explanations in {language_hint}. Keep code, identifiers, file names and commands in their original form; write code comments in English unless asked.

{session.overview()}"""


# ---------------------------------------------------------------- sandboxed commands

# Commands that cannot work in the sandbox (no network, no root). Refused without bothering the user.
INSTALLS = re.compile(r"\b(?:pip3?|pipx|uv|poetry|conda)\s+(?:install|add)\b|\bensurepip\b|\bget-pip\b|"
                      r"\b(?:apt|apt-get|dnf|yum|pacman|paru|yay|zypper|brew|snap|flatpak)\b|\bsudo\b|\bdoas\b|"
                      r"\bnpm\s+(?:i|install|add|ci)\b|\b(?:yarn|pnpm)\s+(?:add|install)\b|\b(?:cargo|go)\s+install\b|"
                      r"\bcurl\b|\bwget\b|\bgit\s+(?:clone|pull|fetch|push)\b", re.I)
_MISSING = re.compile(r"No module named '?([\w.]+)|([\w.-]+): command not found|ModuleNotFoundError: No module named '?([\w.]+)")

_TOOLCHAIN: str | None = None


def _toolchain() -> str:
    """Which common developer tools exist, so the model does not guess (or try to install them)."""
    global _TOOLCHAIN
    if _TOOLCHAIN is None:
        found = [name for name in ("python3", "node", "npm", "git", "make", "gcc", "cargo", "go", "java", "rg") if shutil.which(name)]
        missing = [name for name in ("python3", "node", "npm", "cargo", "go", "java") if name not in found]
        try:
            modules = subprocess.run(["python3", "-c", "import importlib.util as u; print(' '.join(m for m in ('pytest', 'numpy', 'requests') if u.find_spec(m)))"],
                                     capture_output=True, text=True, timeout=10, check=False).stdout.split()
        except (OSError, subprocess.TimeoutExpired):
            modules = []
        _TOOLCHAIN = ("Installed tools: " + ", ".join(found) + (f". Python packages available: {', '.join(modules)}" if modules else "")
                      + (". Not installed: " + ", ".join(missing + [m for m in ("pytest",) if m not in modules]) if missing or "pytest" not in modules else "") + ".")
    return _TOOLCHAIN


def sandbox_command(root: Path, command: str) -> list[str]:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise CodeError("Commands need bubblewrap (bwrap), which is not installed, so nothing was run.")
    args = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", "/run"]
    # The project is the only writable place. Masks come after it so they also apply inside it.
    args += ["--bind", str(root), str(root)]
    for relative in PRIVATE:
        path = HOME / relative
        if path.is_dir():
            args += ["--tmpfs", str(path)]
        elif path.exists():
            args += ["--ro-bind", "/dev/null", str(path)]
    if (HOME / ".cache").is_dir():
        args += ["--tmpfs", str(HOME / ".cache")]
    if (APP_ROOT / ".runtime").is_dir():
        args += ["--tmpfs", str(APP_ROOT / ".runtime")]   # Sulvana's own window profile and checkpoints
    args += ["--chdir", str(root), "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
             "--setenv", "HOME", str(HOME), "--setenv", "PATH", os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
             "--setenv", "LANG", os.environ.get("LANG", "C.UTF-8"), "--setenv", "USER", os.environ.get("USER", "user"),
             "--setenv", "TERM", "dumb", "--setenv", "NO_COLOR", "1", "--setenv", "TMPDIR", "/tmp",
             "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
             "/bin/bash", "--noprofile", "--norc", "-c", command]
    return args


def _clip(text: str, limit: int = MAX_RESULT) -> str:
    if len(text) <= limit:
        return text
    head = limit // 3
    return text[:head] + f"\n… [{len(text) - limit:,} characters omitted] …\n" + text[-(limit - head):]


# ---------------------------------------------------------------- one coding task

class CodeSession:
    """Tools for one user request. Approvals and step reports go through the callbacks."""

    def __init__(self, root: Path, approve: Callable[[dict], str], report: Callable[[dict], None],
                 stop: threading.Event):
        self.root, self.approve, self.report, self.stop = root, approve, report, stop
        self.task = secrets.token_urlsafe(12)
        self.checkpoint = CHECKPOINTS / self.task
        self.saved: dict[str, str | None] = {}
        self.allow_edits = False
        self.allowed_commands: set[str] = set()
        self.steps = 0
        self.used: list[str] = []
        self.seen: dict[Path, int] = {}   # file -> modification time when the model last read it
        _prune_checkpoints()

    # -- paths
    def _path(self, raw: str | None) -> Path:
        raw = (raw or ".").strip().strip("\"'`")
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise CodeError(f"{raw} is outside the project folder.")
        return resolved

    def _rel(self, path: Path) -> str:
        return str(path.relative_to(self.root)) or "."

    def _writable(self, raw: str | None) -> Path:
        if not raw:
            raise CodeError("No <path> was given.")
        path = self._path(raw)
        if ".git" in path.relative_to(self.root).parts:
            raise CodeError("Files inside .git cannot be changed.")
        if path.is_dir():
            raise CodeError(f"{self._rel(path)} is a folder, not a file.")
        return path

    @staticmethod
    def _text(path: Path) -> str:
        if not path.is_file():
            raise CodeError(f"{path.name} does not exist. Use list_files to find the right path.")
        if path.stat().st_size > 5_000_000:
            raise CodeError(f"{path.name} is larger than 5 MB.")
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            raise CodeError(f"{path.name} is a binary file.")
        return data.decode("utf-8", errors="replace")

    # -- context for the prompt
    def overview(self) -> str:
        entries = []
        try:
            for item in sorted(self.root.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold())):
                if item.name in {".git"} or item.name in SKIP_DIRS:
                    continue
                entries.append(item.name + ("/" if item.is_dir() else ""))
        except OSError:
            pass
        lines = [f"Project folder: {self.root}", "Top level: " + (", ".join(entries[:80]) or "(empty)")]
        if (self.root / ".git").exists():
            try:
                status = subprocess.run(["git", "-C", str(self.root), "status", "--short", "--branch"],
                                        capture_output=True, text=True, timeout=5, check=False).stdout
                lines.append("git status:\n" + "\n".join(status.splitlines()[:30]))
            except (OSError, subprocess.TimeoutExpired):
                pass
        for name in ("AGENTS.md", "CLAUDE.md", "SULVANA.md"):
            guide = self.root / name
            if guide.is_file():
                lines.append(f"Project instructions from {name} (the user's notes for coding assistants):\n"
                             + guide.read_text(encoding="utf-8", errors="replace")[:4000])
                break
        lines.append(_toolchain())
        return "\n".join(lines)

    # -- running a tool
    def run(self, name: str, fields: dict) -> str:
        self.steps += 1
        self.used.append(name)
        step = {"id": f"{self.task}-{self.steps}", "tool": name, "title": self._title(name, fields), "status": "running"}
        self.report(step)
        try:
            result, detail, status = getattr(self, "_" + name)(fields)
        except CodeError as problem:
            result, detail, status = f"Error: {problem}", str(problem), "error"
        except OSError as problem:
            result, detail, status = f"Error: {problem.strerror or problem}", str(problem), "error"
        self.report({**step, "status": status, "detail": _clip(detail, 20_000)})
        return _clip(result)

    def _title(self, name: str, fields: dict) -> str:
        path = fields.get("path") or "."
        return {
            "list_files": f"List {path}",
            "read_file": f"Read {path}" + (f" (lines {fields.get('start', 1)}–{fields['end']})" if fields.get("end") else ""),
            "search_files": f"Search “{fields.get('pattern', '')[:60]}”" + (f" in {path}" if path != "." else ""),
            "edit_file": f"Edit {path}",
            "write_file": f"Write {path}",
            "run_command": f"Run {fields.get('command', '')[:120]}",
        }[name]

    def _list_files(self, fields: dict) -> tuple[str, str, str]:
        folder = self._path(fields.get("path"))
        if not folder.is_dir():
            raise CodeError(f"{fields.get('path')} is not a folder.")
        files: list[str] = []
        if shutil.which("rg"):
            out = subprocess.run(["rg", "--files", "--hidden", "--glob", "!.git", str(folder)], capture_output=True,
                                 text=True, timeout=15, check=False).stdout
            files = sorted(self._rel(Path(line)) for line in out.splitlines() if line)
        else:
            for base, dirs, names in os.walk(folder):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
                files += [self._rel(Path(base) / n) for n in sorted(names)]
        shown = files[:500]
        text = "\n".join(shown) + (f"\n… and {len(files) - 500} more files" if len(files) > 500 else "")
        summary = f"{len(files)} files"
        return (f"{summary} under {self._rel(folder)}:\n{text}" if files else "No files found."), text or "No files.", "done"

    def _read_file(self, fields: dict) -> tuple[str, str, str]:
        path = self._path(fields.get("path"))
        lines = self._text(path).replace("\r\n", "\n").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        try:
            start = max(1, int(fields.get("start") or 1))
            end = int(fields.get("end") or start + MAX_READ_LINES - 1)
        except ValueError:
            raise CodeError("start and end must be line numbers.") from None
        end = min(len(lines), end, start + MAX_READ_LINES - 1)
        if not lines:
            return f"{self._rel(path)} is empty.", "(empty file)", "done"
        if start > len(lines):
            raise CodeError(f"{self._rel(path)} has only {len(lines)} lines.")
        self.seen[path] = path.stat().st_mtime_ns
        body = "\n".join(f"{number:>5}\t{lines[number - 1]}" for number in range(start, end + 1))
        more = f"\n(lines {start}–{end} of {len(lines)}; read more with <start>{end + 1}</start>)" if end < len(lines) else ""
        return f"{self._rel(path)} (lines {start}–{end} of {len(lines)}):\n{body}{more}", f"Lines {start}–{end} of {len(lines)}", "done"

    def _search_files(self, fields: dict) -> tuple[str, str, str]:
        pattern = (fields.get("pattern") or "").strip()
        if not pattern:
            raise CodeError("No <pattern> was given.")
        folder = self._path(fields.get("path"))
        if not shutil.which("rg"):
            raise CodeError("Search needs ripgrep (rg), which is not installed.")
        base = ["rg", "-n", "--no-heading", "--color", "never", "--max-columns", "300", "--max-count", "30", "-S"]
        done = subprocess.run([*base, "-e", pattern, str(folder)], capture_output=True, text=True, timeout=20, check=False)
        if done.returncode == 2:   # not a valid regular expression: search for the literal text instead
            done = subprocess.run([*base, "-F", "-e", pattern, str(folder)], capture_output=True, text=True, timeout=20, check=False)
        prefix = str(self.root) + os.sep
        rows = [line.removeprefix(prefix) for line in done.stdout.splitlines()]
        if not rows:
            return f"No matches for {pattern!r}.", "No matches.", "done"
        text = "\n".join(rows[:200]) + (f"\n… {len(rows) - 200} more matches" if len(rows) > 200 else "")
        return f"{len(rows)} matching lines:\n{text}", text, "done"

    # -- changes
    def _confirm(self, kind: str, title: str, command: str, diff: str = "") -> str:
        if kind in {"edit", "write"} and self.allow_edits:
            return "allow"
        if kind == "command" and command in self.allowed_commands:
            return "allow"
        decision = self.approve({"kind": kind, "title": title, "command": command, "diff": _clip(diff, 40_000)})
        if decision == "allow_all":
            if kind == "command":
                self.allowed_commands.add(command)
            else:
                self.allow_edits = True
        return decision

    def _backup(self, path: Path) -> None:
        relative = self._rel(path)
        if relative in self.saved:
            return
        self.checkpoint.mkdir(parents=True, exist_ok=True)
        entry = None
        if path.exists():
            entry = f"{len(self.saved)}.orig"
            shutil.copy2(path, self.checkpoint / entry)
        self.saved[relative] = entry
        (self.checkpoint / "manifest.json").write_text(json.dumps(
            {"root": str(self.root), "created": time.time(), "files": self.saved}, ensure_ascii=False))

    def _save(self, path: Path, old: str | None, new: str, kind: str) -> tuple[str, str, str]:
        relative = self._rel(path)
        diff = "".join(difflib.unified_diff((old or "").splitlines(True), new.splitlines(True),
                                            "/dev/null" if old is None else f"a/{relative}", f"b/{relative}"))
        added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
        title = ("Create " if old is None else "Edit " if kind == "edit" else "Replace ") + relative
        decision = self._confirm(kind, title, relative, diff)
        if decision not in {"allow", "allow_all"}:
            return (f"The user declined this change to {relative}. Do not try it again; ask what they would prefer.",
                    diff, "denied")
        self._backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        crlf = old is not None and "\r\n" in old
        with open(path, "w", encoding="utf-8", newline="\r\n" if crlf else "\n") as handle:
            handle.write(new)
        summary = (f"{'Created' if old is None else 'Edited'} {relative} (+{added} −{removed} lines). "
                   "Line numbers in this file have changed: read it again before another numbered edit.")
        return summary + "\n" + _clip(diff, 6000), diff, "done"

    def _edit_file(self, fields: dict) -> tuple[str, str, str]:
        path = self._writable(fields.get("path"))
        edits = fields.get("edits") or []
        if not edits and fields.get("start") and ("replace" in fields or "content" in fields):
            return self._edit_lines(path, fields)
        if not edits:
            raise CodeError("edit_file needs at least one <search>…</search><replace>…</replace> pair.")
        original = self._text(path)
        text = original.replace("\r\n", "\n")
        for number, (search, replace) in enumerate(edits, 1):
            text = _apply_edit(text, search, replace, self._rel(path), number if len(edits) > 1 else 0)
        if text == original.replace("\r\n", "\n"):
            raise CodeError("The edit would not change the file.")
        return self._save(path, original.replace("\r\n", "\n"), text, "edit")

    def _edit_lines(self, path: Path, fields: dict) -> tuple[str, str, str]:
        """Replace a range of lines by number. Only allowed when the model's line numbers are current."""
        relative = self._rel(path)
        original = self._text(path).replace("\r\n", "\n")
        if self.seen.get(path) != path.stat().st_mtime_ns:
            raise CodeError(f"{relative} has changed since you last read it (or you have not read it yet), so the line "
                            "numbers may be wrong. Use read_file first, then edit with the new numbers.")
        lines = original.split("\n")
        trailing = lines and lines[-1] == ""
        if trailing:
            lines.pop()
        try:
            start = int(fields["start"])
            end = int(fields.get("end") or start)
        except ValueError:
            raise CodeError("<start> and <end> must be line numbers.") from None
        if not 1 <= start <= end <= len(lines):
            raise CodeError(f"Lines {start}–{end} do not exist: {relative} has {len(lines)} lines.")
        new = fields.get("replace", fields.get("content", ""))
        replacement = new.strip("\n").split("\n") if new.strip("\n") else []
        text = "\n".join(lines[:start - 1] + replacement + lines[end:]) + ("\n" if trailing else "")
        if text == original:
            raise CodeError("The edit would not change the file.")
        return self._save(path, original, text, "edit")

    def _write_file(self, fields: dict) -> tuple[str, str, str]:
        path = self._writable(fields.get("path"))
        content = fields.get("content")
        if content is None:
            raise CodeError("write_file needs a <content>…</content> block.")
        if len(content) > 1_000_000:
            raise CodeError("The file content is larger than 1 MB.")
        if content and not content.endswith("\n"):
            content += "\n"
        old = self._text(path).replace("\r\n", "\n") if path.exists() else None
        if old == content:
            raise CodeError("The file already has exactly this content.")
        if old is not None:
            kept = set(line.strip() for line in content.split("\n") if line.strip())
            lines = [line.strip() for line in old.split("\n") if line.strip()]
            lost = sum(1 for line in lines if line not in kept)
            if len(lines) > 5 and lost > 0.4 * len(lines):
                raise CodeError(f"Not written: this would delete {lost} of the {len(lines)} lines in {self._rel(path)}. "
                                "write_file replaces the whole file. To add code, use edit_file with an empty <search> "
                                "(adds at the end) or search for nearby lines; to change code, use edit_file.")
        return self._save(path, old, content, "write")

    def _run_command(self, fields: dict) -> tuple[str, str, str]:
        command = (fields.get("command") or "").strip()
        if not command or len(command) > 2000:
            raise CodeError("Give one command of at most 2,000 characters in <command>.")
        if INSTALLS.search(command):
            note = ("Not run: the sandbox has no internet and no administrator rights, so nothing can be installed or "
                    "downloaded. Work with what is installed (" + _toolchain().removeprefix("Installed tools: ").rstrip(".")
                    + "). To run tests without pytest, run the test file directly, for example: python3 tests/test_file.py. "
                    "If something really must be installed, tell the user.")
            return note, "Blocked: installing and downloading are not possible in the sandbox.", "error"
        decision = self._confirm("command", "Run a command", command)
        if decision not in {"allow", "allow_all"}:
            return ("The user declined to run this command. Do not run it again; ask what they would prefer.",
                    "Declined.", "denied")
        started = time.monotonic()
        process = subprocess.Popen(sandbox_command(self.root, command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
        chunks: list[bytes] = []
        reader = threading.Thread(target=lambda: chunks.extend(iter(lambda: process.stdout.read(4096), b"")), daemon=True)
        reader.start()
        ended = "finished"
        while process.poll() is None:
            if self.stop.is_set():
                ended = "stopped by the user"
            elif time.monotonic() - started > COMMAND_TIMEOUT:
                ended = f"stopped after {COMMAND_TIMEOUT} seconds"
            if ended != "finished":
                process.kill()
                break
            time.sleep(0.1)
        process.wait()
        reader.join(timeout=2)
        output = b"".join(chunks).decode("utf-8", errors="replace").rstrip() or "(no output)"
        seconds = time.monotonic() - started
        status = f"exit code {process.returncode}" if ended == "finished" else ended
        result = f"$ {command}\n({status}, {seconds:.1f} s)\n{_clip(output, MAX_RESULT - 400)}"
        missing = _MISSING.search(output)
        if missing:
            name = next(group for group in missing.groups() if group)
            result += (f"\n\nNote: {name} is not installed, and nothing can be installed here. Do not try to install it."
                       + (" Run test files directly instead, for example: python3 tests/test_file.py" if name == "pytest" else
                          " Use another way, or tell the user to install it."))
        return result, result, "done" if ended == "finished" and process.returncode == 0 else "error"

    def changed_files(self) -> list[str]:
        return sorted(self.saved)


def _apply_edit(text: str, search: str, replace: str, relative: str, number: int) -> str:
    """Replace one occurrence of search. Falls back to matching that ignores trailing spaces, then
    indentation (re-indenting the replacement), because small models often get whitespace wrong."""
    which = f" (pair {number})" if number else ""
    if not search.strip():
        # An empty search adds the code at the end of the file. Top-level code often arrives
        # indented (copied from an example), so dedent it when the file ends at column 0.
        addition = replace.strip("\n")
        if not addition.strip():
            raise CodeError(f"Both the search and the replace text{which} are empty.")
        lines = text.split("\n")
        last = next((line for line in reversed(lines) if line.strip()), "")
        top = next((line for line in reversed(lines) if line[:1].strip() and not line.startswith("#")), "")
        new_block = re.match(r"\s*(?:async\s+def|def|class|@)\b", addition)
        # Python: an indented def after a module-level function belongs at the top level; after a class it may be a method.
        if not last[:1].isspace() or (relative.endswith(".py") and new_block and not top.startswith("class ")):
            addition = textwrap.dedent(addition)
        body = text.rstrip("\n")
        gap = "" if not body else "\n\n\n" if relative.endswith(".py") and not addition[:1].isspace() else "\n\n"
        return body + gap + addition + "\n"
    count = text.count(search)
    if count == 1:
        return text.replace(search, replace, 1)
    if count > 1:
        raise CodeError(f"The search text{which} appears {count} times in {relative}. Include more surrounding lines so it is unique.")
    lines = text.split("\n")
    wanted = search.strip("\n").split("\n")
    for key in (str.rstrip, str.strip):
        target = [key(line) for line in wanted]
        hits = [i for i in range(len(lines) - len(wanted) + 1) if [key(line) for line in lines[i:i + len(wanted)]] == target]
        if len(hits) > 1:
            raise CodeError(f"The search text{which} matches {len(hits)} places in {relative}. Include more surrounding lines.")
        if len(hits) == 1:
            start = hits[0]
            new = replace.strip("\n").split("\n") if replace.strip("\n") else []
            if key is str.strip:
                first = next((i for i, line in enumerate(wanted) if line.strip()), 0)
                have = len(lines[start + first]) - len(lines[start + first].lstrip())
                gave = len(wanted[first]) - len(wanted[first].lstrip())
                shift = have - gave
                pad = lines[start + first][:have][:max(0, shift)] if shift > 0 else ""
                new = [(pad + line if shift > 0 else line[min(-shift, len(line) - len(line.lstrip())):]) if line.strip() else line
                       for line in new]
            return "\n".join(lines[:start] + new + lines[start + len(wanted):])
    # Not found: show the most similar region so the model can copy it exactly next time.
    best, best_score = 0, 0.0
    size = max(1, len(wanted))
    joined = "\n".join(wanted)
    for i in range(0, max(1, len(lines) - size + 1)):
        score = difflib.SequenceMatcher(None, joined, "\n".join(lines[i:i + size]), autojunk=False).quick_ratio()
        if score > best_score:
            best, best_score = i, score
    hint = ""
    if best_score > 0.5:
        region = "\n".join(f"{n + 1:>5}\t{lines[n]}" for n in range(best, min(len(lines), best + size)))
        hint = f"\nThe most similar lines in the file are:\n{region}"
    raise CodeError(f"The search text{which} was not found in {relative}. Read the file again and copy the lines exactly.{hint}")


# ---------------------------------------------------------------- undo

def undo_task(task: str) -> list[str]:
    """Put back every file a coding task changed (and remove the files it created)."""
    if not TASK_ID.fullmatch(task or ""):
        raise CodeError("Unknown coding task.")
    folder = CHECKPOINTS / task
    try:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CodeError("There is nothing to undo for this task (it may have been undone already).") from None
    root = project_root(manifest["root"])
    restored = []
    for relative, entry in manifest["files"].items():
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            continue
        if entry is None:
            if target.is_file():
                target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / entry, target)
        restored.append(relative)
    shutil.rmtree(folder, ignore_errors=True)
    return restored


def _prune_checkpoints(days: int = 30) -> None:
    if not CHECKPOINTS.is_dir():
        return
    cutoff = time.time() - days * 86400
    for folder in CHECKPOINTS.iterdir():
        try:
            if folder.is_dir() and folder.stat().st_mtime < cutoff:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass
