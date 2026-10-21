#!/usr/bin/env python3
"""Local web shell for Sulvana's imported React interface."""

from __future__ import annotations

import base64
import http.client
import json
import mimetypes
import os
import time
import re
import secrets
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path("/home/tanchjim/Documents/Codex/ai-workspace")
sys.path.insert(0, str(ROOT))
import sulvana_code  # noqa: E402  (undo of coding-mode edits)
from sulvana_worker import die_with_parent  # noqa: E402

import sulvana_speech  # noqa: E402  (reading Khmer replies aloud)
DIST = ROOT / "sulvana-ui/dist"
IMAGE_DIR = ROOT / "runs/z-image"
PROFILE_FILE = ROOT / ".runtime" / "sulvana-model.json"
FEEDBACK_FILE = ROOT / "datasets" / "feedback" / "corrections.jsonl"
KHMER_ADAPTER = ROOT / "runs/finetune/mimo-khmer-01/sulvana-khmer-mimo-01.gguf"
KHMER_ADAPTER_V2 = Path(os.environ.get("SULVANA_KHMER_ADAPTER") or ROOT / "runs/finetune/mimo-khmer-v2/mimo-khmer-v2.gguf")
REMOTE_KEY_FILE = ROOT / ".runtime" / "sulvana-remote.json"


def get_remote_key() -> str:
    env_key = os.environ.get("SULVANA_REMOTE_KEY", "").strip()
    if env_key:
        return env_key
    try:
        if REMOTE_KEY_FILE.is_file():
            key = json.loads(REMOTE_KEY_FILE.read_text()).get("key", "").strip()
            if key:
                return key
    except Exception:
        pass
    new_key = secrets.token_urlsafe(16)
    try:
        REMOTE_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        REMOTE_KEY_FILE.write_text(json.dumps({"key": new_key, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}) + "\n")
    except OSError:
        pass
    return new_key
# The models Sulvana can run, chosen in Settings. Each is a set of environment variables for the engine.
PROFILES = {
    "sulvana-2.0": {"label": "Sulvana 2.0", "detail": "MiMo-V2.6 9B · fast, Khmer and coding",
                    "file": ROOT / "models/MiMo-V2.6-Distill-Qwen-9B/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf",
                    "env": {"SULVANA_BASE": "mimo"}},
    # Two WKH Labs adapters, routed per message: v2 (Gemini-written Khmer) when the reply is Khmer,
    # v1 for other languages. Measured 82.3% / 82.5% on the two Khmer benchmarks (v1 alone: 81.6 / 81.3);
    # v3 (2026-10-16) measured no better than v2.
    "sulvana-2.0-khmer": {"label": "Sulvana 2.0 + Khmer adapters", "detail": "MiMo with the WKH Labs Khmer fine-tunes (v2 for Khmer, v1 for English)",
                          "file": KHMER_ADAPTER_V2,
                          "env": {"SULVANA_BASE": "mimo", "SULVANA_LORA_ADAPTER": f"{KHMER_ADAPTER},{KHMER_ADAPTER_V2}",
                                  "SULVANA_LORA_SCALE": "0.3,0", "SULVANA_LORA_KHMER": "0,0.3", "SULVANA_LORA_OTHER": "0.3,0"}},
    "sulvana-1.0-code": {"label": "Sulvana 1.0 Code", "detail": "Qwen3.8 27B · strongest coder, slow, English",
                         "file": ROOT / "models/Qwen3.8-27B/Qwen3.8-27B-UD-Q4_K_M.gguf", "env": {"SULVANA_BASE": "code"}},
}


DEFAULT_PROFILE = "sulvana-2.0-khmer"   # the best-measured model; Settings can switch to any other


def profile_available(name: str) -> bool:
    if name not in PROFILES:
        return False
    info = PROFILES[name]
    if name == "sulvana-2.0-khmer":
        return (PROFILES["sulvana-2.0"]["file"].is_file() and
                KHMER_ADAPTER.is_file() and KHMER_ADAPTER_V2.is_file())
    if name == "sulvana-1.0-code":
        return info["file"].is_file() and info["file"].stat().st_size > 16_000_000_000
    return info["file"].is_file() and info["file"].stat().st_size >= 4_000_000_000


def saved_profile() -> str | None:
    try:
        name = json.loads(PROFILE_FILE.read_text())["profile"]
    except (OSError, ValueError, KeyError):
        name = DEFAULT_PROFILE
    if profile_available(name):
        return name
    return "sulvana-2.0" if profile_available("sulvana-2.0") else None


def profile_env(name: str | None) -> dict[str, str]:
    """The engine's environment: the launcher's own variables, overridden by the model chosen in Settings."""
    env = dict(os.environ)
    if name and name in PROFILES:
        for key in ("SULVANA_BASE", "SULVANA_LORA_ADAPTER", "SULVANA_LORA_SCALE", "SULVANA_LORA_KHMER", "SULVANA_LORA_OTHER"):
            env.pop(key, None)
        env.update(PROFILES[name]["env"])
    return env


class LocalEngine:
    def __init__(self, profile: str | None = None) -> None:
        self.profile = profile
        self.process = subprocess.Popen([sys.executable, "-u", str(ROOT / "qwen_server.py")], cwd=ROOT, text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=profile_env(profile),
                                        preexec_fn=die_with_parent)
        line = self.process.stdout.readline().strip()
        parts = line.split("\t")
        if len(parts) != 3 or parts[0] != "QWEN_SERVER_READY":
            raise RuntimeError("Sulvana's local engine could not start.")
        self.port, self.secret = int(parts[1]), parts[2]

    def request(self, method: str, path: str, body: bytes = b"", headers: dict[str, str] | None = None) -> http.client.HTTPResponse:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=900)
        merged = {"X-Local-Token": self.secret, **(headers or {})}
        connection.request(method, path, body=body, headers=merged)
        return connection.getresponse()

    def stop(self) -> None:
        if self.process.poll() is None:
            try: self.request("POST", "/shutdown").read()
            except Exception: self.process.terminate()


def main() -> None:
    if not (DIST / "index.html").is_file():
        raise SystemExit("Build the UI first with: npm run build")
    engine = LocalEngine(saved_profile())
    engine_lock = threading.Lock()

    def switch_engine(name: str) -> int:
        """Replace the running engine with another model; the choice is remembered."""
        nonlocal engine
        with engine_lock:
            engine.stop()
            try: engine.process.wait(timeout=30)
            except subprocess.TimeoutExpired: engine.process.kill()
            PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
            PROFILE_FILE.write_text(json.dumps({"profile": name}) + "\n")
            try:
                engine = LocalEngine(name)
            except (OSError, RuntimeError):
                return 502
            return 204

    def restart_engine() -> int:
        """Recover from a fatal engine: reload the model, or replace the bridge process if it died."""
        nonlocal engine
        with engine_lock:
            if engine.process.poll() is None:
                try:
                    response = engine.request("POST", "/restart")
                    response.read()
                    return response.status
                except (OSError, http.client.HTTPException):
                    engine.process.terminate()
                    try: engine.process.wait(timeout=10)
                    except subprocess.TimeoutExpired: engine.process.kill()
            try:
                engine = LocalEngine(engine.profile)
            except (OSError, RuntimeError):
                return 502
            return 204

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, format, *args) -> None:
            try:
                code = str(args[1]) if len(args) > 1 else ""
                sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {self.command} {self.path.split('?')[0]} -> {code}\n")
                sys.stderr.flush()
            except Exception:
                pass

        def _is_local(self) -> bool:
            # Only Sulvana's own page on this computer. Pages from other local ports (another dev server)
            # or any website must use the access key like a remote friend.
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            app = {"127.0.0.1:8766", "localhost:8766"}
            return host in app and (not origin or origin in {f"http://{name}" for name in app})

        def _cors_headers(self) -> None:
            origin = self.headers.get("Origin")
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Max-Age", "86400")

        def _send(self, code: int, payload: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(payload)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self._cors_headers()
            self.end_headers()

        def _check_access(self) -> bool:
            if self._is_local():
                return True
            provided = self.headers.get("X-Sulvana-Key", "").strip()
            if not provided:
                auth = self.headers.get("Authorization", "").strip()
                if auth.lower().startswith("bearer "):
                    provided = auth[7:].strip()
            if not provided:
                query_key = parse_qs(urlsplit(self.path).query).get("key", [""])[0].strip()
                if query_key:
                    provided = query_key
            expected = get_remote_key()
            if not provided or not secrets.compare_digest(provided, expected):
                self._send(401, b'{"state":"offline","detail":"Invalid or missing Sulvana access key"}', "application/json")
                return False
            return True

        def _status(self) -> None:
            try:
                response = engine.request("GET", "/status")
                raw = response.read().decode("utf-8", errors="replace").strip().split("\t", 1)
            except (OSError, http.client.HTTPException):
                self._send(502, b'{"state":"fatal","detail":"Local engine is unavailable"}', "application/json")
                return
            if len(raw) == 2:
                try:
                    detail = base64.b64decode(raw[1], validate=True).decode("utf-8", errors="replace")
                except (ValueError, base64.binascii.Error):
                    detail = "Local engine returned an invalid status"
                approval = None
                if raw[0] == "generating" and self._is_local():
                    try:
                        pending = engine.request("GET", "/pending-approval")
                        if pending.status == 200:
                            approval = json.loads(pending.read())
                    except (OSError, http.client.HTTPException, ValueError, json.JSONDecodeError):
                        pass
                self._send(200, json.dumps({"state": raw[0], "detail": detail, "approval": approval}).encode(), "application/json")
            else:
                self._send(502, b'{"state":"error","detail":"Engine unavailable"}', "application/json")

        def do_GET(self) -> None:
            req_path = urlsplit(self.path).path.rstrip("/")
            if req_path.startswith("/api/") and not self._check_access(): return
            if req_path == "/api/status": self._status(); return
            if req_path == "/api/models":
                current = engine.profile or saved_profile()
                items = [{"id": name, "label": info["label"], "detail": info["detail"],
                          "available": profile_available(name)}
                         for name, info in PROFILES.items()]
                self._send(200, json.dumps({"current": current, "models": items}).encode(), "application/json"); return
            if req_path.startswith("/api/image"):
                name = parse_qs(urlsplit(self.path).query).get("name", [""])[0]
                if not re.fullmatch(r"[A-Za-z0-9_.-]+\.png", name):
                    self._send(400, b"Invalid image name", "text/plain"); return
                image = (IMAGE_DIR / name).resolve()
                if not image.is_relative_to(IMAGE_DIR.resolve()) or not image.is_file():
                    self._send(404, b"Image not found", "text/plain"); return
                self._send(200, image.read_bytes(), "image/png"); return
            requested = req_path.lstrip("/") or "index.html"
            file = (DIST / requested).resolve()
            if not file.is_relative_to(DIST) or not file.is_file(): file = DIST / "index.html"
            self._send(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "application/octet-stream")

        def do_POST(self) -> None:
            if not self._check_access(): return
            req_path = urlsplit(self.path).path.rstrip("/")
            if not self._is_local() and req_path in {"/api/approval", "/api/code/undo"}:
                self._send(403, b"Forbidden: Coding mode and system approvals are only available locally on the laptop", "text/plain"); return
            if req_path == "/api/speak":
                # Read a Khmer reply aloud with the speech model on this computer (sulvana_speech.py).
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 64_000: raise ValueError("Text is empty or too long")
                    text = json.loads(self.rfile.read(length)).get("text")
                    if not isinstance(text, str) or not text.strip(): raise ValueError("Text is empty")
                    if not sulvana_speech.available(): raise ValueError("The Khmer voice is not installed")
                    self._send(200, sulvana_speech.speak(text), "audio/wav")
                except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as problem:
                    self._send(400, str(problem).encode(), "text/plain")
                except (OSError, RuntimeError) as problem:
                    self._send(500, f"Could not read aloud: {problem}".encode(), "text/plain")
                return
            if req_path not in {"/api/chat", "/api/stop", "/api/clear", "/api/approval", "/api/restart", "/api/code/undo", "/api/model", "/api/feedback"}:
                self._send(404, b"Not found", "text/plain"); return
            if req_path == "/api/code/undo":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 512: raise ValueError("Invalid undo request")
                    restored = sulvana_code.undo_task(str(json.loads(self.rfile.read(length)).get("task", "")))
                    self._send(200, json.dumps({"restored": restored}).encode(), "application/json")
                except sulvana_code.CodeError as problem:
                    self._send(409, str(problem).encode(), "text/plain")
                except (ValueError, TypeError, AttributeError, OSError) as problem:
                    self._send(400, f"Could not undo: {problem}".encode(), "text/plain")
                return
            if req_path == "/api/model":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 256: raise ValueError("Invalid request")
                    name = json.loads(self.rfile.read(length)).get("profile")
                    if name not in PROFILES: raise ValueError("Unknown model")
                    if not profile_available(name): raise ValueError("That model or its adapter is not downloaded yet")
                except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as problem:
                    self._send(400, str(problem).encode(), "text/plain"); return
                code = switch_engine(name)
                self._send(code, b"" if code == 204 else b"The model could not be started", "text/plain"); return
            if req_path == "/api/feedback":
                # A user-approved or user-corrected answer, saved as a training example (datasets/feedback/).
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 400_000: raise ValueError("Invalid feedback")
                    item = json.loads(self.rfile.read(length))
                    prompt, answer = str(item.get("prompt", "")).strip(), str(item.get("answer", "")).strip()
                    rating = item.get("rating")
                    if not prompt or not answer or rating not in {"good", "corrected"}: raise ValueError("Invalid feedback")
                    history = [m for m in item.get("history") or [] if isinstance(m, dict) and m.get("role") in {"user", "assistant"}
                               and isinstance(m.get("content"), str) and m["content"].strip()][-6:]
                    record = {"messages": [*({"role": m["role"], "content": m["content"].strip()} for m in history),
                                           {"role": "user", "content": prompt}, {"role": "assistant", "content": answer}],
                              "meta": {"source": "user-feedback", "rating": rating, "model": str(item.get("model", ""))[:120],
                                       "original": str(item.get("original", ""))[:20000] if rating == "corrected" else None,
                                       "created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}}
                    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(FEEDBACK_FILE, "a", encoding="utf-8") as handle:
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    self._send(204, b"", "text/plain")
                except (ValueError, TypeError, AttributeError, json.JSONDecodeError, OSError) as problem:
                    self._send(400, str(problem).encode(), "text/plain")
                return
            if req_path == "/api/restart":
                code = restart_engine()
                self._send(code, b"" if code == 204 else b"The engine is busy or could not be restarted", "text/plain"); return
            if req_path == "/api/stop":
                try:
                    response = engine.request("POST", "/stop"); self._send(response.status, response.read(), "text/plain")
                except (OSError, http.client.HTTPException):
                    self._send(502, b"Local engine is unavailable", "text/plain")
                return
            if req_path == "/api/clear":
                try:
                    response = engine.request("POST", "/clear"); self._send(response.status, response.read(), "text/plain")
                except (OSError, http.client.HTTPException):
                    self._send(502, b"Local engine is unavailable", "text/plain")
                return
            if req_path == "/api/approval":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 2048: raise ValueError("Invalid approval request")
                    request = json.loads(self.rfile.read(length))
                    request_id, decision = request.get("id"), request.get("decision")
                    if (not isinstance(request_id, str) or len(request_id) > 100 or
                            decision not in {"allow", "deny", "allow_all"}):
                        raise ValueError("Invalid approval request")
                    body = json.dumps({"id": request_id, "decision": decision}).encode()
                    response = engine.request("POST", "/approval", body, {"Content-Type": "application/json"})
                    self._send(response.status, response.read(), "text/plain")
                except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
                    self._send(400, b"Invalid approval request", "text/plain")
                except (OSError, http.client.HTTPException):
                    self._send(502, b"Local engine is unavailable", "text/plain")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 20_000_000: raise ValueError("Request is too large")
                request = json.loads(self.rfile.read(length))
                prompt = str(request.get("prompt", "")).strip()
                if not prompt: raise ValueError("Message is empty")
                max_tokens = max(32, min(8192, int(request.get("maxTokens", 2048))))
                temperature = max(.1, min(1.5, float(request.get("temperature", .4))))
                language = str(request.get("language", "Auto-detect"))
                if len(language) > 80:
                    raise ValueError("Reply language name is too long")
                history = request.get("history", [])
                if not isinstance(history, list) or len(history) > 400: raise ValueError("Invalid chat history")
                image_data = request.get("image")
            except (ValueError, json.JSONDecodeError) as error:
                self._send(400, str(error).encode(), "text/plain"); return
            temporary_image = None
            streaming = False
            try:
                path, body, content_type = "/chat", json.dumps({"prompt": prompt, "history": history}).encode(), "application/json"
                headers = {"Content-Type": content_type, "X-Max-Tokens": str(max_tokens), "X-Temperature": str(temperature), "X-Language": base64.b64encode(language.encode()).decode(),
                           "X-Search": "1" if request.get("search") is True else "0",
                           "X-Reasoning": "1" if request.get("reasoning") is True else "0",
                           "X-Translate": request.get("translate") if request.get("translate") in {"google", "local"} else "off",
                           # A friend on the shared link may chat, but not inspect this computer.
                           "X-Remote": "0" if self._is_local() else "1"}
                if self._is_local():
                    code = request.get("code")
                    if isinstance(code, dict) and isinstance(code.get("root"), str) and 0 < len(code["root"]) <= 1000:
                        headers["X-Code-Root"] = base64.b64encode(code["root"].encode()).decode()
                if image_data:
                    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", str(image_data))
                    if not match: raise ValueError("Unsupported image format")
                    binary = base64.b64decode(match.group(2), validate=True)
                    if len(binary) > 10_000_000: raise ValueError("Image exceeds 10 MB")
                    suffix = ".jpg" if match.group(1) == "jpeg" else "." + match.group(1)
                    with tempfile.NamedTemporaryFile(prefix="sulvana-vision-", suffix=suffix, delete=False) as saved:
                        saved.write(binary); temporary_image = Path(saved.name)
                    path, body = "/vision", prompt.encode()
                    headers["X-Image-Path"] = base64.b64encode(str(temporary_image).encode()).decode()
                    headers["Content-Type"] = "text/plain; charset=utf-8"
                response = engine.request("POST", path, body, headers)
                if response.status != 200:
                    self._send(response.status, response.read(), "text/plain"); return
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=ascii")
                self.send_header("Cache-Control", "no-store")
                self._cors_headers()
                self.end_headers()
                streaming = True
                while line := response.readline():
                    self.wfile.write(line)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                try: engine.request("POST", "/stop").read()
                except Exception: pass
            except (ValueError, base64.binascii.Error) as error:
                self._send(400, str(error).encode(), "text/plain")
            except (OSError, http.client.HTTPException):
                if not streaming:
                    self._send(502, b"Local engine is unavailable", "text/plain")
            finally:
                if temporary_image is not None: temporary_image.unlink(missing_ok=True)

    server = ThreadingHTTPServer(("127.0.0.1", 8766), Handler); server.daemon_threads = True
    # A plain kill (SIGTERM) must still shut the engine down cleanly instead of orphaning it.
    import signal
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
    print("SULVANA_WEB_READY\thttp://127.0.0.1:8766", flush=True)
    try: server.serve_forever(poll_interval=.2)
    finally: engine.stop(); server.server_close()


if __name__ == "__main__": main()
