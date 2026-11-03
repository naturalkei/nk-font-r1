"""Download upstream fonts listed in sources.lock and verify their SHA256.

Entries with `member` come from an archive (zip, or an npm-style .tgz): the archive is downloaded
once per run, its `archive_sha256` checked, and the member extracted to sources/.
"""

from __future__ import annotations

import hashlib
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from . import config


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _archive(src: config.SourceFont, cache: dict[str, Path], tmp: Path) -> Path:
    if src.url not in cache:
        dest = tmp / f"archive{len(cache)}"
        urllib.request.urlretrieve(src.url, dest)
        digest = sha256(dest)
        if src.archive_sha256 and digest != src.archive_sha256:
            raise RuntimeError(
                f"{src.id}: archive SHA256 mismatch ({digest} != {src.archive_sha256})"
            )
        cache[src.url] = dest
    return cache[src.url]


def extract_member(archive: Path, member: str, dest: Path) -> Path:
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            dest.write_bytes(z.read(member))
    else:  # .tar.gz / .tgz (npm tarballs); read the one member, never extractall
        with tarfile.open(archive) as t:
            f = t.extractfile(member)
            if f is None:
                raise RuntimeError(f"{archive.name}: {member} is not a regular file")
            dest.write_bytes(f.read())
    return dest


def fetch_all(force: bool = False) -> list[str]:
    config.SOURCES_DIR.mkdir(exist_ok=True)
    done = []
    archives: dict[str, Path] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for src in config.sources().values():
            if force or not src.path.exists() or sha256(src.path) != src.sha256:
                if src.member:
                    extract_member(_archive(src, archives, Path(tmp)), src.member, src.path)
                else:
                    urllib.request.urlretrieve(src.url, src.path)
            digest = sha256(src.path)
            if digest != src.sha256:
                src.path.unlink()
                raise RuntimeError(f"{src.id}: SHA256 mismatch ({digest} != {src.sha256})")
            done.append(src.id)
    return done
