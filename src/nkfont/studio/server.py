"""Tiny stdlib HTTP server for NK Studio. Binds to localhost only; no external dependencies."""

from __future__ import annotations

import json
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources

from .core import DEFAULT_TEXT, Studio, update_hangul_config

_LOCK = threading.Lock()


def _static(name: str) -> bytes:
    return resources.files(__package__).joinpath("static", name).read_bytes()


def make_handler(studio: Studio):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quieter console
            if not self.path.startswith("/api/preview"):
                super().log_message(fmt, *args)

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, status: int = 200) -> None:
            self._send(status, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self._send(200, _static("index.html"), "text/html; charset=utf-8")
            if self.path == "/api/families":
                return self._json({"families": studio.families(), "text": DEFAULT_TEXT})
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/preview":
                    t0 = time.perf_counter()
                    with _LOCK:
                        p = studio.build_preview(
                            req["family"],
                            req["weight"],
                            req.get("text") or DEFAULT_TEXT,
                            scale=req.get("scale"),
                            dy=req.get("dy"),
                            center=req.get("center"),
                        )
                    ms = round((time.perf_counter() - t0) * 1000)
                    return self._json({"font": p.font_b64, "metrics": p.metrics, "ms": ms})
                if self.path == "/api/save":
                    path = update_hangul_config(req["family"], req, studio.root)
                    return self._json({"saved": str(path.relative_to(studio.root))})
                self._send(404, b"not found", "text/plain")
            except Exception as exc:  # report to the UI instead of dropping the connection
                self._json({"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.BAD_REQUEST)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    studio = Studio()
    httpd = ThreadingHTTPServer((host, port), make_handler(studio))
    url = f"http://{host}:{port}/"
    print(f"NK Studio on {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
