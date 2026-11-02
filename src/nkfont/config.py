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
RESERVED_NAMES = (
    "Source",
    "Pretendard",
    "Plex",
    "NeoDunggeunmo",
    "둥근모",
    "Nanum",
    "나눔",
    "D2Coding",
)


def _load(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


@dataclass(frozen=True)
class SourceFont:
    id: str
    url: str
    sha256: str
    license: str
    # Upstreams that only ship archives: `member` is the file inside the zip at `url`, `sha256`
    # is the extracted file's hash and `archive_sha256` pins the zip itself.
    member: str | None = None
    archive_sha256: str | None = None

    @property
    def path(self) -> Path:
        return SOURCES_DIR / Path(self.member or self.url).name


def sources(root: Path = ROOT) -> dict[str, SourceFont]:
    data = _load(root / "sources.lock")
    return {f["id"]: SourceFont(**f) for f in data["font"]}


def patcher_image(root: Path = ROOT) -> str:
    return _load(root / "sources.lock")["patcher"]["image"]


def family(name: str, root: Path = ROOT) -> dict:
    return _load(root / "config" / "families" / f"{name}.toml")


# Display/build order of the families; config/families/<id>.toml.
FAMILY_ORDER = ("mono", "serif", "pixel", "sans", "novel", "comics")


def family_ids(root: Path = ROOT) -> list[str]:
    found = {p.stem for p in (root / "config" / "families").glob("*.toml")}
    order = {f: i for i, f in enumerate(FAMILY_ORDER)}
    return sorted(found, key=lambda f: (order.get(f, len(order)), f))


def ranges(root: Path = ROOT) -> list[tuple[int, int]]:
    return [(r["start"], r["end"]) for r in _load(root / "config" / "ranges.toml")["range"]]
