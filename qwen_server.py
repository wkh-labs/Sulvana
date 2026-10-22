#!/usr/bin/env python3
"""Loopback-only streaming bridge between the JavaFX UI and Sulvana."""

from __future__ import annotations

import base64
import json
import queue
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sulvana_worker import CONTEXT_TOKENS, MAX_REPLY_TOKENS, ModelWorker


IMAGE_REQUEST = re.compile(
    r"^\s*(?:please\s+)?(?:generate|create|make)\s+(?:me\s+)?"
    r"(?:an?\s+)?(?:image|picture|photo|illustration|artwork|drawing|painting)\b",
    re.IGNORECASE,
)


def image_prompt(text: str) -> str | None:
    """Return the image description for an explicit local-image request."""
    stripped = text.strip()
    if re.match(r"^/image(?:\s|:|$)", stripped, re.IGNORECASE):
        description = stripped[6:].lstrip(" :,-")
        return description or None
    match = IMAGE_REQUEST.match(stripped)
    if not match:
        return None
    description = stripped[match.end():].lstrip(" :,-")
    if description.lower().startswith("of "):
        description = description[3:]
    return description or None


def decoded_json(value: str | None) -> dict:
    try:
        data = json.loads(base64.b64decode(value or "").decode("utf-8")) if value else {}
    except (ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def encoded(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


class ChatService:
    def __init__(self) -> None:
        self.events: queue.Queue = queue.Queue()
        self.worker = ModelWorker(self.events)
        self.lock = threading.Lock()
        self.active: queue.Queue | None = None
        self.state = "loading"
        self.detail = "Loading Sulvana…"
        self.ready_detail = ""
        threading.Thread(target=self._dispatch, daemon=True).start()

    def _dispatch(self) -> None:
        while True:
            kind, payload = self.events.get()
            with self.lock:
                if kind == "status":
                    self.detail = payload
                elif kind == "ready":
                    if self.state == "loading":
                        self.state = "ready"
                    self.detail = self.ready_detail = f"{payload['model']} • {payload['gpu']} • Q4_K_M"
                elif kind == "fatal":
                    self.state = "fatal"
                    self.detail = payload
                elif kind in {"generation_started", "image_started", "vision_started"}:
                    self.state = "generating"
                elif kind in {
                    "generation_done", "generation_error", "image_done", "image_error", "vision_done", "vision_error"
                }:
                    self.state = "ready"
                    # Progress messages such as "Searching the web…" must not outlive the request.
                    if self.ready_detail:
                        self.detail = self.ready_detail
                stream = self.active
                if kind in {
                    "generation_done", "generation_error", "image_done", "image_error", "vision_done", "vision_error"
                }:
                    self.active = None
            if stream is not None and kind in {
                "token", "generation_done", "generation_error", "image_started", "image_done", "image_error",
                "vision_started", "vision_done", "vision_error", "approval_requested", "reasoning", "sources", "code_step", "retry"
            }:
                stream.put((kind, payload))

    def status(self) -> tuple[str, str]:
        with self.lock:
            return self.state, self.detail

    def start_chat(self, prompt: str, settings: dict) -> queue.Queue | None:
        with self.lock:
            if self.state != "ready" or self.active is not None:
                return None
            stream: queue.Queue = queue.Queue()
            self.active = stream
            self.state = "generating"
        self.worker.send(prompt, settings)
        return stream

    def start_image(self, prompt: str) -> queue.Queue | None:
        with self.lock:
            if self.state != "ready" or self.active is not None:
                return None
            stream: queue.Queue = queue.Queue()
            self.active = stream
            self.state = "generating"
        self.worker.send_image(prompt)
        return stream

    def start_vision(self, prompt: str, image_path: str) -> queue.Queue | None:
        with self.lock:
            if self.state != "ready" or self.active is not None:
                return None
            stream: queue.Queue = queue.Queue()
            self.active = stream
            self.state = "generating"
        self.worker.send_vision(prompt, image_path)
        return stream

    def end_chat(self, stream: queue.Queue) -> None:
        with self.lock:
            if self.active is stream:
                self.active = None

    def clear(self) -> bool:
        with self.lock:
            if self.active is not None or self.state != "ready":
                return False
        self.worker.clear()
        return True

    def restart(self) -> bool:
        """Reload the model, but only from the otherwise permanent "fatal" state."""
        with self.lock:
            if self.active is not None or self.state != "fatal":
                return False
            self.state = "loading"
            self.detail = "Restarting the model…"
        self.worker.restart()
        return True


def main() -> None:
    secret = secrets.token_urlsafe(32)
    service = ChatService()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *_args) -> None:
            pass

        def _reply(self, code: int, body: str = "") -> None:
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorized(self) -> bool:
            if secrets.compare_digest(self.headers.get("X-Local-Token", ""), secret):
                return True
            self._reply(403, "Forbidden")
            return False

        def do_GET(self) -> None:
            if not self._authorized():
                return
            if self.path == "/status":
                state, detail = service.status()
                self._reply(200, f"{state}\t{encoded(detail)}\n")
            elif self.path == "/pending-approval":
                self._reply(200, json.dumps(service.worker.pending_approval_status()))
            else:
                self._reply(404, "Not found")

        def do_POST(self) -> None:
            if not self._authorized():
                return
            if self.path == "/stop":
                service.worker.stop()
                self._reply(204)
                return
            if self.path == "/clear":
                self._reply(204 if service.clear() else 409)
                return
            if self.path == "/restart":
                self._reply(204 if service.restart() else 409)
                return
            if self.path == "/approval":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 2048:
                        self._reply(400, "Invalid approval request")
                        return
                    data = json.loads(self.rfile.read(length))
                    request_id, decision = data.get("id"), data.get("decision")
                    if not isinstance(request_id, str) or not isinstance(decision, str):
                        raise ValueError("Invalid approval fields")
                except (ValueError, TypeError, json.JSONDecodeError):
                    self._reply(400, "Invalid approval request")
                    return
                self._reply(204 if service.worker.resolve_approval(request_id, decision) else 409)
                return
            if self.path == "/shutdown":
                self._reply(204)
                service.worker.shutdown()
                threading.Thread(target=server.shutdown, daemon=True).start()
                return
            if self.path not in {"/chat", "/vision"}:
                self._reply(404, "Not found")
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 8_000_000:
                    self._reply(413, "Message must be 1 to 8,000,000 bytes")
                    return
                raw = self.rfile.read(length).decode("utf-8")
                history = None
                if self.headers.get("Content-Type", "").startswith("application/json"):
                    data = json.loads(raw)
                    prompt = str(data.get("prompt", "")).strip()
                    history = data.get("history")
                    if not isinstance(history, list) or len(history) > 400:
                        self._reply(400, "Invalid conversation history")
                        return
                else:
                    prompt = raw.strip()
                if not prompt:
                    self._reply(400, "Message is empty")
                    return
                max_tokens = max(32, min(MAX_REPLY_TOKENS, int(self.headers.get("X-Max-Tokens", "256"))))
                temperature = max(0.1, min(1.5, float(self.headers.get("X-Temperature", "0.7"))))
                language = base64.b64decode(self.headers.get("X-Language", ""), validate=True).decode("utf-8")
                code_root = (base64.b64decode(self.headers["X-Code-Root"], validate=True).decode("utf-8")
                             if "X-Code-Root" in self.headers else None)
            except (ValueError, UnicodeError, TypeError, json.JSONDecodeError) as error:
                self._reply(400, f"Invalid request: {error}")
                return

            if self.path == "/vision":
                try:
                    attached_image = base64.b64decode(
                        self.headers.get("X-Image-Path", ""), validate=True
                    ).decode("utf-8")
                except (ValueError, UnicodeError) as error:
                    self._reply(400, f"Invalid image path: {error}")
                    return
                if not attached_image:
                    self._reply(400, "Attach an image before asking Sulvana about it.")
                    return
                stream = service.start_vision(prompt, attached_image)
            else:
                description = image_prompt(prompt)
                if description is not None:
                    stream = service.start_image(description)
                else:
                    stream = service.start_chat(
                        prompt,
                        {
                            "max_new_tokens": max_tokens,
                            "max_context_tokens": CONTEXT_TOKENS,
                            "temperature": temperature,
                            "language": language,
                            "history": history,
                            "search": self.headers.get("X-Search") == "1",
                            "reasoning": self.headers.get("X-Reasoning") == "1",
                            "translate": self.headers.get("X-Translate") if self.headers.get("X-Translate") in {"google", "local"} else "",
                            "remote": self.headers.get("X-Remote") != "0",
                            "auto_search": self.headers.get("X-Auto-Search") == "1",
                            "profile": decoded_json(self.headers.get("X-Profile")),
                            # Coding mode: the project folder the agent may work in (checked by the worker).
                            "code_root": code_root,
                        },
                    )
            if stream is None:
                self._reply(409, "Model is busy or still loading")
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=ascii")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                while True:
                    kind, payload = stream.get(timeout=900)
                    if kind == "token":
                        line = "t\t" + encoded(payload) + "\n"
                    elif kind == "generation_done":
                        line = "d\t" + encoded(json.dumps(payload)) + "\n"
                    elif kind in {"image_started", "image_done"}:
                        line = "i\t" + encoded(json.dumps(payload)) + "\n"
                    elif kind in {"vision_started", "vision_done"}:
                        line = "v\t" + encoded(json.dumps(payload)) + "\n"
                    elif kind == "approval_requested":
                        line = "p\t" + encoded(json.dumps(payload)) + "\n"
                    elif kind == "reasoning":
                        line = "r\t" + encoded(payload) + "\n"
                    elif kind == "sources":
                        line = "s\t" + encoded(json.dumps(payload)) + "\n"
                    elif kind == "code_step":
                        line = "c\t" + encoded(json.dumps(payload)) + "\n"
                    elif kind == "retry":
                        line = "x\t\n"
                    else:
                        line = "e\t" + encoded(str(payload)) + "\n"
                    self.wfile.write(line.encode("ascii"))
                    self.wfile.flush()
                    if kind not in {"token", "image_started", "vision_started", "approval_requested", "reasoning", "sources", "code_step", "retry"}:
                        break
            except (BrokenPipeError, ConnectionResetError, TimeoutError, queue.Empty):
                service.worker.stop()
            finally:
                service.end_chat(stream)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    print(f"QWEN_SERVER_READY\t{server.server_port}\t{secret}", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        service.worker.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
