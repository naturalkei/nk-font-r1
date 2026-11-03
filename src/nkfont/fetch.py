"""Download upstream fonts listed in sources.lock and verify their SHA256.

Entries with `member` come from an archive (zip, or an npm-style .tgz): the archive is downloaded
once per run, its `archive_sha256` checked, and the member extracted to sources/.
Entries with `instance` come from a variable font: the download is checked against `sha256`, then
pinned to one static instance (sources/<id>.ttf) with a sidecar <id>.ttf.sha256 recording the
digest of the variable font it came from.
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


def instantiate(var_path: Path, axes: dict, dest: Path) -> Path:
    """Write the static instance of `var_path` at `axes` (unnamed axes at their default)."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    font = TTFont(var_path)
    limits = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
    unknown = set(axes) - set(limits)
    if unknown:
        raise RuntimeError(f"{var_path.name}: no axis {', '.join(sorted(unknown))}")
    limits.update({k: float(v) for k, v in axes.items()})
    instancer.instantiateVariableFont(font, limits, inplace=True)
    font.save(dest)
    return dest


def _fetch_instance(src: config.SourceFont, cache: dict[str, Path], tmp: Path, force: bool):
    pin = src.pin_path
    if not force and src.path.exists() and pin.exists() and pin.read_text().strip() == src.sha256:
        return
    if src.url not in cache:
        dest = tmp / f"var{len(cache)}"
        urllib.request.urlretrieve(src.url, dest)
        digest = sha256(dest)
        if digest != src.sha256:
            raise RuntimeError(f"{src.id}: SHA256 mismatch ({digest} != {src.sha256})")
        cache[src.url] = dest
    instantiate(cache[src.url], src.instance, src.path)
    pin.write_text(src.sha256 + "\n")


def fetch_all(force: bool = False) -> list[str]:
    config.SOURCES_DIR.mkdir(exist_ok=True)
    done = []
    archives: dict[str, Path] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for src in config.sources().values():
            if src.instance:
                _fetch_instance(src, archives, Path(tmp), force)
                done.append(src.id)
                continue
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


def local_status(root: Path = config.ROOT) -> list[str]:
    """One line per local-only reference (config/local_fonts.toml): found where, or missing.

    These are never downloaded; a pinned `sha256` that differs only warns (another release).
    """
    lines = []
    for lf in config.local_fonts(root).values():
        for weight in lf.weights:
            path = lf.find(weight, root)
            if path is None:
                names = ", ".join(lf.weights[weight])
                lines.append(f"--  {lf.id} {weight}: not installed (local only: {names})")
                continue
            want = lf.sha256.get(path.name)
            note = "" if not want or sha256(path) == want else " (different release than pinned)"
            lines.append(f"loc {lf.id} {weight}: {path}{note}")
    return lines
