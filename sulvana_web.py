#!/usr/bin/env python3
"""Local web shell for Sulvana's imported React interface."""

from __future__ import annotations

import base64
import http.client
import json
import mimetypes
import re
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
DIST = ROOT / "sulvana-ui/dist"
IMAGE_DIR = ROOT / "runs/z-image"


class LocalEngine:
    def __init__(self) -> None:
        self.process = subprocess.Popen([sys.executable, "-u", str(ROOT / "qwen_server.py")], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
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
    engine = LocalEngine()
    engine_lock = threading.Lock()

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
                engine = LocalEngine()
            except (OSError, RuntimeError):
                return 502
            return 204

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *_args) -> None: pass

        def _send(self, code: int, payload: bytes, content_type: str) -> None:
            self.send_response(code); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(payload))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(payload)

        def _same_app(self) -> bool:
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            allowed = {"http://127.0.0.1:8766", "http://localhost:8766"}
            if host not in {"127.0.0.1:8766", "localhost:8766"} or (origin and origin not in allowed):
                self._send(403, b"Local app requests only", "text/plain")
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
                if raw[0] == "generating":
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
            if not self._same_app(): return
            if self.path == "/api/status": self._status(); return
            if self.path.startswith("/api/image?"):
                name = parse_qs(urlsplit(self.path).query).get("name", [""])[0]
                if not re.fullmatch(r"[A-Za-z0-9_.-]+\.png", name):
                    self._send(400, b"Invalid image name", "text/plain"); return
                image = (IMAGE_DIR / name).resolve()
                if not image.is_relative_to(IMAGE_DIR.resolve()) or not image.is_file():
                    self._send(404, b"Image not found", "text/plain"); return
                self._send(200, image.read_bytes(), "image/png"); return
            requested = self.path.split("?", 1)[0].lstrip("/") or "index.html"
            file = (DIST / requested).resolve()
            if not file.is_relative_to(DIST) or not file.is_file(): file = DIST / "index.html"
            self._send(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "application/octet-stream")

        def do_POST(self) -> None:
            if not self._same_app(): return
            if self.path not in {"/api/chat", "/api/stop", "/api/clear", "/api/approval", "/api/restart", "/api/code/undo"}:
                self._send(404, b"Not found", "text/plain"); return
            if self.path == "/api/code/undo":
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
            if self.path == "/api/restart":
                code = restart_engine()
                self._send(code, b"" if code == 204 else b"The engine is busy or could not be restarted", "text/plain"); return
            if self.path == "/api/stop":
                try:
                    response = engine.request("POST", "/stop"); self._send(response.status, response.read(), "text/plain")
                except (OSError, http.client.HTTPException):
                    self._send(502, b"Local engine is unavailable", "text/plain")
                return
            if self.path == "/api/clear":
                try:
                    response = engine.request("POST", "/clear"); self._send(response.status, response.read(), "text/plain")
                except (OSError, http.client.HTTPException):
                    self._send(502, b"Local engine is unavailable", "text/plain")
                return
            if self.path == "/api/approval":
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
                temperature = max(.1, min(1.5, float(request.get("temperature", .7))))
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
                           "X-Reasoning": "1" if request.get("reasoning") is True else "0"}
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
                self.send_response(200); self.send_header("Content-Type", "text/plain; charset=ascii"); self.send_header("Cache-Control", "no-store"); self.end_headers()
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
    print("SULVANA_WEB_READY\thttp://127.0.0.1:8766", flush=True)
    try: server.serve_forever(poll_interval=.2)
    finally: engine.stop(); server.server_close()


if __name__ == "__main__": main()
