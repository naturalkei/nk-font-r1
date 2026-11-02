"""Load repository configuration (families, ranges, sources.lock)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = ROOT / "sources"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"

# Reserved Font Names of upstream fonts; they must never appear in our names.
RESERVED_NAMES = ("Source", "Pretendard", "Plex", "NeoDunggeunmo", "둥근모")


def _load(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


@dataclass(frozen=True)
class SourceFont:
    id: str
    url: str
    sha256: str
    license: str

    @property
    def path(self) -> Path:
        return SOURCES_DIR / Path(self.url).name


def sources(root: Path = ROOT) -> dict[str, SourceFont]:
    data = _load(root / "sources.lock")
    return {f["id"]: SourceFont(**f) for f in data["font"]}


def patcher_image(root: Path = ROOT) -> str:
    return _load(root / "sources.lock")["patcher"]["image"]


def family(name: str, root: Path = ROOT) -> dict:
    return _load(root / "config" / "families" / f"{name}.toml")


def ranges(root: Path = ROOT) -> list[tuple[int, int]]:
    return [(r["start"], r["end"]) for r in _load(root / "config" / "ranges.toml")["range"]]
