"""Download upstream fonts listed in sources.lock and verify their SHA256."""

from __future__ import annotations

import hashlib
import urllib.request

from . import config


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_all(force: bool = False) -> list[str]:
    config.SOURCES_DIR.mkdir(exist_ok=True)
    done = []
    for src in config.sources().values():
        if force or not src.path.exists() or sha256(src.path) != src.sha256:
            urllib.request.urlretrieve(src.url, src.path)
        digest = sha256(src.path)
        if digest != src.sha256:
            src.path.unlink()
            raise RuntimeError(f"{src.id}: SHA256 mismatch ({digest} != {src.sha256})")
        done.append(src.id)
    return done
