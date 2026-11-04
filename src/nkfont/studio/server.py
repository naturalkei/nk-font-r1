"""Tiny stdlib HTTP server for NK Studio. Binds to localhost only; no external dependencies."""

from __future__ import annotations

import json
import mimetypes
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import presets, update, versions
from .core import _KEYS, DEFAULT_TEXT, Studio
from .lab import Lab

PAGES = {
    "/": "index.html",
    "/lab": "lab.html",
    "/lab/advanced": "lab-advanced.html",
    "/presets": "presets.html",
    "/specimen": "specimen.html",
    "/update": "update.html",
}
# Sample texts for the preset comparison page (one tab each).
SAMPLES = {
    "hangul": "\n".join(
        [
            "다람쥐 헌 쳇바퀴에 타고파",
            "키스의 고유조건은 입술끼리 만나야 하고 특별한 기술은 필요치 않다.",
            "읽꽃뷁됐 · 가나다라마바사아자차카타파하",
        ]
    ),
    "latin": "\n".join(
        [
            "The quick brown fox jumps over the lazy dog.",
            "Sphinx of black quartz, judge my vow.",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789 Il1| O0o",
        ]
    ),
    "code": "\n".join(
        [
            "fn main() {",
            '    let 이름 = "나크";  // 한글 식별자 → 두 칸',
            "    if x != y && a >= b { return Ok(()); }",
            '    println!("{이름}: {:#x}", 0xFF);',
            "}",
        ]
    ),
    "terminal": "\n".join(
        [
            "~/dev/nk-font on main [!?] via py v3.14",
            "❯ ls -la 문서/",
            "drwxr-xr-x  5 nk staff  160 11월  3 09:00 프로젝트",
            "-rw-r--r--  1 nk staff 4.2K 11월  3 09:01 메모.md",
            "┌──┬──┐ ✔ 완료  ✘ 실패  ➜ 다음",
        ]
    ),
}


def site_file(root: Path, rel: str) -> Path | None:
    """A file of the built prototype site (build/site), or None. Never leaves that folder."""
    base = (root / "build" / "site").resolve()
    path = (base / unquote(rel)).resolve()
    if path.is_dir():
        path = path / "index.html"
    if base not in path.parents or not path.is_file():
        return None
    return path


_LOCK = threading.Lock()


def _static(name: str) -> bytes:
    return resources.files(__package__).joinpath("static", name).read_bytes()


def make_handler(studio: Studio, lab: Lab | None = None, restart=None):
    """`restart` is set by the desktop app: a callable that reopens it after an update."""
    lab = lab or Lab(studio.root)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quieter console
            if not self.path.startswith(("/api/preview", "/api/lab/glyphs")):
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
            url = urlparse(self.path)
            page = PAGES.get(url.path.removesuffix(".html").replace("/index", "/") or "/")
            if page:
                return self._send(200, _static(page), "text/html; charset=utf-8")
            if url.path == "/site":
                self.send_response(301)
                self.send_header("Location", "/site/")
                self.end_headers()
                return
            if url.path.startswith("/site/"):
                path = site_file(studio.root, url.path.removeprefix("/site/"))
                if path is None:
                    msg = "build/site not found: run `nkfont build all && nkfont site` first"
                    return self._send(404, msg.encode(), "text/plain; charset=utf-8")
                ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                if path.suffix == ".woff2":
                    ctype = "font/woff2"
                return self._send(200, path.read_bytes(), ctype)
            if url.path == "/api/families":
                return self._json({"families": studio.families(), "text": DEFAULT_TEXT})
            if url.path == "/api/presets":
                return self._json({"presets": presets.load(studio.root), "samples": SAMPLES})
            if url.path == "/api/lab/info":
                return self._json(lab.info())
            if url.path == "/api/lab/font":
                q = {k: v[0] for k, v in parse_qs(url.query).items()}
                try:
                    data = lab.font_bytes(q["id"], q["family"], q["weight"])
                except Exception as exc:
                    return self._json({"error": f"{type(exc).__name__}: {exc}"}, 400)
                return self._send(200, data, "font/ttf")
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
                            style=req.get("style"),
                            pixel=req.get("pixel"),
                            **{k: req.get(k) for k in (*_KEYS, "tracking")},
                        )
                    ms = round((time.perf_counter() - t0) * 1000)
                    return self._json({"font": p.font_b64, "metrics": p.metrics, "ms": ms})
                if self.path == "/api/lab/glyphs":
                    t0 = time.perf_counter()
                    with _LOCK:
                        out = lab.glyphs(req)
                    ms = round((time.perf_counter() - t0) * 1000)
                    return self._json({"fonts": out, "ms": ms})
                if self.path == "/api/lab/core":
                    return self._json(lab.core(req["family"]))
                if self.path == "/api/lab/solve":
                    t0 = time.perf_counter()
                    with _LOCK:
                        out = lab.solve(req)
                    out["ms"] = round((time.perf_counter() - t0) * 1000)
                    return self._json(out)
                if self.path == "/api/lab/charset":
                    return self._json({"blocks": lab.charset(req["family"], req["weight"])})
                if self.path == "/api/lab/features":
                    feats = lab.features(req["font"], req["family"], req["weight"])
                    return self._json({"features": feats})
                if self.path == "/api/update/check":
                    return self._json({**update.status(studio.root), "app": restart is not None})
                if self.path == "/api/update/apply":
                    with _LOCK:
                        return self._json(update.apply(studio.root))
                if self.path == "/api/app/restart":
                    if restart is None:
                        raise RuntimeError(
                            "브라우저 모드: 터미널에서 nkfont studio를 다시 실행하세요"
                        )
                    threading.Timer(0.3, restart).start()  # answer before the window closes
                    return self._json({"restarting": True})
                if self.path == "/api/presets/qa":  # harmony + distinctness of one preset
                    from ..presetqa import Checker, as_dict

                    rid = str(req.get("id") or "check")
                    saved = rid.startswith("saved:")  # starting points: not compared
                    preset = presets.validate({**req, "id": "check" if saved else rid}, studio.root)
                    with _LOCK:
                        checker = studio.__dict__.setdefault("_qa", Checker(studio.root, studio))
                        r = checker.check(preset) if saved else checker.check_in_family(preset)
                        return self._json(as_dict(r))
                if self.path == "/api/presets/save":
                    return self._json({"preset": presets.save(req, studio.root)})
                if self.path == "/api/presets/delete":
                    presets.delete(req["id"], studio.root)
                    return self._json({"deleted": req["id"]})
                if self.path == "/api/save":  # every save is also a numbered version
                    with _LOCK:
                        out = versions.save(req["family"], req, req.get("note", ""), studio.root)
                    return self._json(out)
                if self.path == "/api/versions":
                    return self._json({"versions": versions.load(req["family"], studio.root)})
                if self.path == "/api/versions/restore":
                    with _LOCK:
                        return self._json(versions.restore(req["family"], req["n"], studio.root))
                self._send(404, b"not found", "text/plain")
            except Exception as exc:  # report to the UI instead of dropping the connection
                self._json({"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.BAD_REQUEST)

    return Handler


def make_server(host: str = "127.0.0.1", port: int = 8765, restart=None) -> ThreadingHTTPServer:
    """Port 0 picks a free port (the desktop app does this); see `server_address`."""
    return ThreadingHTTPServer((host, port), make_handler(Studio(), restart=restart))


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    httpd = make_server(host, port)
    url = f"http://{host}:{httpd.server_address[1]}/"
    print(f"NK Studio on {url}  (Ctrl+C to stop)")
    print(f"  Glyph Lab {url}lab  ·  Presets {url}presets  ·  Specimen {url}specimen")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
