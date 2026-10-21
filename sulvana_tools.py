"""Small, local-only tools exposed to the Sulvana model worker."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
import urllib.parse
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable


ROOT = Path("/home/tanchjim/Documents/Codex/ai-workspace").resolve()
DOC_ROOTS = (ROOT / "knowledge",)
PROJECT_DOCS = (ROOT / "README.md", ROOT / "Z-Image-Turbo.md")
MAX_OUTPUT = 50_000

TOOL_INSTRUCTIONS = """
You can use tools when they genuinely help. Documentation search and safe terminal inspection are pre-approved. Web search is allowed only when the user explicitly asks to search, look up, or verify online/current information. If you need one tool, output only one exact tool request and nothing else:
[[tool:docs.search {\"query\":\"short keywords\"}]]
[[tool:web.search {\"query\":\"public search query\"}]]
[[tool:terminal.read {\"command\":\"allowed inspection command\"}]]
You can request additional read-only inspection with `ls folder`, `head -n 1..120 source-file`, `wc -l source-file`, `rg -n -F text source-file`, or `git log -5 --oneline`; these wait for the user's one-time approval. Never claim you ran a tool unless a tool result was given to you. Never use the terminal to write, install, delete, access secrets, or open a website.
""".strip()


def search_docs(query: str) -> str:
    terms = [term.casefold() for term in re.findall(r"[\w-]{2,}", query)][:8]
    if not terms:
        return "No useful search terms were provided."
    scored: list[tuple[int, str]] = []
    files = sorted(
        {path for root in DOC_ROOTS if root.exists() for path in root.rglob("*.md")}
        | {path for path in PROJECT_DOCS if path.is_file()}
    )
    for path in files:
        if ".git" in path.parts or path.stat().st_size > 1_000_000:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            score = sum(term in line.casefold() for term in terms)
            if score:
                relative = path.relative_to(ROOT)
                scored.append((score, f"{relative}:{number}: {line.strip()}"))
    scored.sort(key=lambda item: item[0], reverse=True)
    return "\n".join(item[1] for item in scored[:20]) if scored else "No matching Markdown documentation was found."


NOTES_ROOT = ROOT / "knowledge"
NOTES_BUDGET = 12000     # characters of notes added to one reply (Khmer is ~1.6 tokens per character)
_KHMER_RUN = re.compile(r"[ក-៿᧠-᧿]+")
_STOPWORDS = frozenset("""the and for are was were what when where which who why how does did with this that
from into your you can about have has had will would should could there their them they its it's not but
than then also just like some any all our out use using tell me please""".split())
_note_cache: dict[Path, tuple[float, list[tuple[str, str]]]] = {}


def _note_terms(text: str) -> set[str]:
    """Words for Latin-script text, and character trigrams for Khmer, which has no spaces."""
    terms = {word for word in re.findall(r"[a-z0-9][a-z0-9'-]{2,}", text.casefold()) if word not in _STOPWORDS}
    for run in _KHMER_RUN.findall(text):
        terms.update(run[i:i + 3] for i in range(max(1, len(run) - 2)))
    return terms


def _note_sections(path: Path) -> list[tuple[str, str]]:
    """Split a Markdown file into (title, text) sections at its headings, cached until it changes."""
    mtime = path.stat().st_mtime
    cached = _note_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    sections: list[tuple[str, str]] = []
    title, lines = path.stem, []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        heading = re.match(r"#{1,4}\s+(.+)", line)
        if heading and lines:
            sections.append((title, "\n".join(lines).strip()))
            lines = []
        if heading:
            title = heading.group(1).strip()
        lines.append(line)
    if lines:
        sections.append((title, "\n".join(lines).strip()))
    sections = [(t, body[:3000]) for t, body in sections if body]
    _note_cache[path] = (mtime, sections)
    return sections


def note_passages(query: str, budget: int = NOTES_BUDGET, limit: int = 5) -> list[dict[str, str]]:
    """The note sections in knowledge/ that best match a message, for adding to Sulvana's context."""
    wanted = _note_terms(query)
    if not wanted or not NOTES_ROOT.is_dir():
        return []
    scored: list[tuple[float, str, str, str]] = []
    for path in sorted(NOTES_ROOT.rglob("*.md")):
        if (path.name == "README.md" or any(part.startswith(".") for part in path.relative_to(NOTES_ROOT).parts)
                or path.stat().st_size > 2_000_000):
            continue
        try:
            sections = _note_sections(path)
        except OSError:
            continue
        for title, body in sections:
            have = _note_terms(body)
            shared = wanted & have
            # Fraction of the message's terms the section covers, so short notes are not drowned out.
            score = len(shared) / len(wanted)
            single_match = len(wanted) == 1 and len(shared) == 1 and len(next(iter(wanted))) >= 4
            # Two shared words out of ten ("write", "short") is a coincidence, not a match.
            if single_match or (len(shared) >= 2 and score >= 0.3) or (len(shared) >= 3 and score >= 0.15):
                scored.append((score, str(path.relative_to(ROOT)), title, body))
    scored.sort(key=lambda item: item[0], reverse=True)
    chosen: list[dict[str, str]] = []
    used = 0
    for _score, file, title, body in scored[:limit]:
        if used + len(body) > budget:
            body = body[: max(0, budget - used)]
        if len(body) < 80:
            break
        chosen.append({"file": file, "title": title, "text": body})
        used += len(body)
    return chosen


def _project_path(raw: str, *, directory: bool) -> Path | None:
    if not raw or raw.startswith("-") or Path(raw).is_absolute():
        return None
    candidate = (ROOT / raw).resolve()
    if not candidate.is_relative_to(ROOT):
        return None
    parts = candidate.relative_to(ROOT).parts
    excluded = {"models", "datasets", "runs", "node_modules", "__pycache__"}
    if not parts or any(part.startswith(".") or part in excluded for part in parts):
        return None
    if directory:
        return candidate if candidate.is_dir() else None
    if not candidate.is_file() or candidate.suffix.lower() not in {".md", ".py", ".java", ".js", ".jsx", ".ts", ".tsx", ".css", ".json", ".sh"}:
        return None
    return candidate if candidate.stat().st_size <= 256_000 else None


def _approved_read_only(parts: list[str]) -> list[str] | None:
    if len(parts) == 2 and parts[0] == "ls":
        folder = _project_path(parts[1], directory=True)
        return ["ls", str(folder)] if folder else None
    if len(parts) == 4 and parts[:2] == ["head", "-n"] and parts[2].isdigit() and 1 <= int(parts[2]) <= 120:
        file = _project_path(parts[3], directory=False)
        return ["head", "-n", parts[2], str(file)] if file else None
    if len(parts) == 3 and parts[:2] == ["wc", "-l"]:
        file = _project_path(parts[2], directory=False)
        return ["wc", "-l", str(file)] if file else None
    if len(parts) == 5 and parts[:3] == ["rg", "-n", "-F"] and 1 <= len(parts[3]) <= 100 and not parts[3].startswith("-"):
        file = _project_path(parts[4], directory=False)
        return ["rg", "-n", "-F", "--max-count", "20", "--", parts[3], str(file)] if file else None
    if parts == ["git", "log", "-5", "--oneline"]:
        return parts
    return None


def _safe_terminal(command: str, *, approve: Callable[[str], bool] | None = None) -> str:
    if len(command) > 300 or any(token in command for token in ("|", ";", "&", ">", "<", "`", "$", "\n")):
        return "Blocked: terminal commands cannot use shell operators."
    try:
        parts = shlex.split(command)
    except ValueError:
        return "Blocked: invalid command syntax."
    if not parts:
        return "Blocked: empty command."
    allowed = {
        ("pwd",), ("ls",), ("ls", "-la"), ("git", "status"), ("git", "diff", "--stat"),
        ("python", "--version"), ("python3", "--version"), ("node", "--version"),
        ("nvidia-smi",), ("df", "-h", "."),
    }
    permitted = tuple(parts) in allowed
    if parts[0] == "rg":
        permitted = (len(parts) == 2 and parts[1] == "--files") or (
            len(parts) == 2 and len(parts[1]) <= 100 and not parts[1].startswith("-")
        )
    if parts[0] == "du":
        candidate = (ROOT / parts[2]).resolve() if len(parts) == 3 else ROOT
        permitted = (len(parts) == 3 and parts[1] == "-sh" and
                     not Path(parts[2]).is_absolute() and candidate.is_relative_to(ROOT))
    approved_command = None
    if not permitted:
        approved_command = _approved_read_only(parts)
        if approved_command is None:
            return "Blocked: this command is outside Sulvana's read-only workspace tools."
        if approve is None:
            return "Approval required: this read-only workspace inspection needs Allow once."
        if not approve(command):
            return "Denied: this read-only workspace inspection was not approved."
        # Check again after approval in case a path changed while the user decided.
        approved_command = _approved_read_only(parts)
        if approved_command is None:
            return "Blocked: the target changed while approval was pending."
    try:
        actual = approved_command or parts
        if approved_command is None and parts[0] == "rg":
            if parts[1] == "--files":
                actual = ["rg", "--files", "--glob", "!sulvana-ui/node_modules/**", "--glob", "!models/**", "."]
            else:
                actual = ["rg", "--max-count", "20", "--", parts[1], "knowledge", "README.md", "Z-Image-Turbo.md"]
        result = subprocess.run(actual, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10, check=False)
    except subprocess.TimeoutExpired:
        return "Stopped after 10 seconds."
    if len(result.stdout) > MAX_OUTPUT:
        return result.stdout[:MAX_OUTPUT] + "\n[Output truncated at 50,000 characters.]"
    return result.stdout or "Command completed with no output."


class _LiteResults(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self.capture = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result-link" in classes:
            self.capture = ""
            self.current = None
            if len(self.results) >= 8:
                return
            href = urllib.parse.urljoin("https://duckduckgo.com", attributes.get("href") or "")
            parsed = urllib.parse.urlsplit(href)
            if parsed.netloc == "duckduckgo.com" and parsed.path == "/l/":
                href = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
            if urllib.parse.urlsplit(href).scheme not in {"http", "https"}:
                return
            self.current = {"title": "", "url": href, "snippet": ""}
            self.results.append(self.current)
            self.capture = "title"
        elif tag == "td" and "result-snippet" in classes and self.current is not None:
            self.capture = "snippet"

    def handle_data(self, data: str) -> None:
        if self.capture and self.current is not None:
            self.current[self.capture] += data

    def handle_endtag(self, tag: str) -> None:
        if (tag == "a" and self.capture == "title") or (tag == "td" and self.capture == "snippet"):
            self.capture = ""


def web_search_results(query: str) -> tuple[list[dict[str, str]], str]:
    """Look a query up on the public web. Returns (results, problem); results hold title, url, snippet."""
    clean = " ".join(query.split())[:240]
    if not clean:
        return [], "No search query was provided."
    url = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(clean)
    request = urllib.request.Request(url, headers={"User-Agent": "Sulvana/1.0 local research"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            page = response.read(500_000).decode("utf-8", errors="replace")
            if response.status != 200:
                return [], f"Web search provider returned HTTP {response.status}. Try again later."
    except Exception as error:
        return [], f"Web search could not connect: {error}"
    parser = _LiteResults()
    parser.feed(page)
    results = []
    for item in parser.results:
        title = " ".join(item["title"].split())[:200]
        if title:
            results.append({"title": title, "url": item["url"], "snippet": " ".join(item["snippet"].split())[:500]})
    if results:
        return results, ""
    if "anomaly" in page.lower() or "captcha" in page.lower():
        return [], "Web search provider requested a bot challenge. Try again later."
    return [], "No public search results were returned for that query."


def web_search(query: str, sources: list | None = None) -> str:
    results, problem = web_search_results(query)
    if sources is not None:
        sources.extend({"title": item["title"], "url": item["url"]} for item in results)
    return "\n".join(f"- {item['title']}\n  {item['url']}\n  {item['snippet']}" for item in results) if results else problem


# Khmer translation. Sulvana's own Khmer is weak, so when the online translator is enabled a Khmer message is
# translated to English, answered in English (the model's strongest language) and the answer translated back.
# This uses Google Translate's public web endpoint (the one translate.google.com uses; no key, unofficial,
# may be rate-limited or change) and sends the text to Google, so it is a user setting the app discloses.
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
_CODE = re.compile(r"```[\s\S]*?```|`[^`\n]+`")
_translations: dict[tuple[str, str], str] = {}
_translator_paused_until = 0.0   # after "too many requests", leave the service alone for a while


def translate(text: str, target: str, source: str = "auto") -> str | None:
    """Translate text with code blocks and inline code left untouched. None when the service cannot be reached."""
    clean = text.strip()
    if not clean:
        return text
    key = (clean, target)
    if key in _translations:
        return _translations[key]
    kept: list[str] = []

    def hold(match: re.Match) -> str:
        kept.append(match.group(0))
        return f"⟦{len(kept) - 1}⟧"

    protected = _CODE.sub(hold, clean)
    if not re.search(r"[^\W\d_]", re.sub(r"⟦\d+⟧", "", protected)):
        return text                                     # only code, numbers or punctuation: nothing to translate
    global _translator_paused_until
    if time.time() < _translator_paused_until:
        return None
    query = urllib.parse.urlencode({"client": "gtx", "sl": source, "tl": target, "dt": "t"})
    body = urllib.parse.urlencode({"q": protected}).encode()
    for attempt in range(2):
        try:
            request = urllib.request.Request(f"{TRANSLATE_URL}?{query}", data=body,
                                             headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            result = "".join(part[0] for part in data[0] if part and part[0])
            break
        except urllib.error.HTTPError as error:
            result = ""
            if error.code == 429:
                # Retrying makes the block last longer; Sulvana answers on its own for the next 10 minutes.
                _translator_paused_until = time.time() + 600
                break
        except (OSError, ValueError, IndexError, TypeError):
            result = ""
    if not result:
        return None
    for index, block in enumerate(kept):
        result = re.sub(rf"⟦\s*{index}\s*⟧", lambda _m, block=block: block, result)
    # The translator pads markdown markers with spaces ("** word **", "1 ."); put them back together.
    result = re.sub(r"\*\*\s*([^*\n]+?)\s*\*\*", r"**\1**", result)
    result = re.sub(r"^(\s*)(\d+)\s+\.\s", r"\1\2. ", result, flags=re.M)
    if len(_translations) > 2000:
        _translations.clear()
    _translations[key] = result
    return result


def translate_markdown(text: str, target: str) -> str | None:
    """Translate a reply paragraph by paragraph so that fenced code blocks pass through unchanged."""
    out: list[str] = []
    for part in re.split(r"(```[\s\S]*?```)", text):
        if part.startswith("```") or not part.strip():
            out.append(part)
            continue
        translated = translate(part, target)
        if translated is None:
            return None
        lead, trail = part[:len(part) - len(part.lstrip())], part[len(part.rstrip()):]
        out.append(lead + translated + trail)
    return "".join(out)


def run_tool(name: str, arguments: dict, *, allow_web: bool = False,
             approve: Callable[[str], bool] | None = None, sources: list | None = None) -> str:
    if name == "docs.search":
        return search_docs(str(arguments.get("query", "")))
    if name == "terminal.read":
        return _safe_terminal(str(arguments.get("command", "")), approve=approve)
    if name == "web.search":
        if not allow_web:
            return "Blocked: web search requires the user's explicit request to search online."
        return web_search(str(arguments.get("query", "")), sources)
    return "Blocked: unknown tool."


TOOL_CALL = re.compile(r"^\s*\[\[tool:(docs\.search|web\.search|terminal\.read)\s+(\{.*?\})\]\]\s*$", re.S)


def parse_tool_call(text: str) -> tuple[str, dict] | None:
    match = TOOL_CALL.match(text)
    if not match:
        return None
    try:
        arguments = json.loads(match.group(2))
    except json.JSONDecodeError:
        return None
    return match.group(1), arguments if isinstance(arguments, dict) else {}
