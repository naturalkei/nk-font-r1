"""Load repository configuration (families, ranges, sources.lock)."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
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
    "NeoDunggeunmo",  # also covers "NeoDunggeunmo Pro"
    "둥근모",
    "Nanum",
    "나눔",
    "D2Coding",
    "Mulmaru",
    "물마루",
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
    # Upstreams that only ship archives: `member` is the file inside the zip/tgz at `url`, `sha256`
    # is the extracted file's hash and `archive_sha256` pins the zip itself.
    member: str | None = None
    archive_sha256: str | None = None
    # Upstreams that only ship a variable font (google/fonts): `instance` pins every axis, e.g.
    # {wght = 700}; unnamed axes take their default. `sha256` then pins the downloaded variable
    # font and `nkfont fetch` writes the static instance to sources/<id>.ttf (reference use only).
    instance: dict | None = None

    @property
    def path(self) -> Path:
        if self.instance:
            return SOURCES_DIR / f"{self.id}.ttf"
        return SOURCES_DIR / Path(self.member or self.url).name

    @property
    def pin_path(self) -> Path:
        """Where the pinned digest is checked: the font itself, or a sidecar for instances."""
        return self.path.with_suffix(".ttf.sha256") if self.instance else self.path


def sources(root: Path = ROOT) -> dict[str, SourceFont]:
    data = _load(root / "sources.lock")
    return {f["id"]: SourceFont(**f) for f in data["font"]}


# Where local-only reference fonts (config/local_fonts.toml) are looked up, after
# <root>/sources/local and $NK_LOCAL_FONTS.
SYSTEM_FONT_DIRS = (
    "~/Library/Fonts",
    "/Library/Fonts",
    "~/.local/share/fonts",
    "~/.fonts",
)


@dataclass(frozen=True)
class LocalFont:
    """A reference font we may compare against but not redistribute (never fetched or shipped)."""

    id: str
    label: str
    license: str
    weights: dict[str, list[str]]
    homepage: str = ""
    sha256: dict[str, str] = field(default_factory=dict)
    # NK families this reference is meant for (empty = any family), as in config/lab.toml.
    families: tuple[str, ...] = ()

    def find(self, weight: str, root: Path = ROOT) -> Path | None:
        for name in self.weights.get(weight, []):
            for d in local_font_dirs(root):
                if any(c in name for c in "*?["):
                    hits = sorted(p for p in d.glob(name) if p.is_file()) if d.is_dir() else []
                    if hits:
                        return hits[0]
                elif (d / name).is_file():
                    return d / name
        return None

    def available(self, root: Path = ROOT) -> dict[str, Path]:
        found = {w: self.find(w, root) for w in self.weights}
        return {w: p for w, p in found.items() if p}


def local_font_dirs(root: Path = ROOT) -> list[Path]:
    env = [
        Path(p).expanduser() for p in os.environ.get("NK_LOCAL_FONTS", "").split(os.pathsep) if p
    ]
    return [root / "sources" / "local", *env, *(Path(d).expanduser() for d in SYSTEM_FONT_DIRS)]


def local_fonts(root: Path = ROOT) -> dict[str, LocalFont]:
    path = root / "config" / "local_fonts.toml"
    if not path.exists():
        return {}
    return {
        f["id"]: LocalFont(**{**f, "families": tuple(f.get("families", ()))})
        for f in _load(path).get("font", [])
    }


def patcher_image(root: Path = ROOT) -> str:
    return _load(root / "sources.lock")["patcher"]["image"]


def family(name: str, root: Path = ROOT) -> dict:
    return _load(root / "config" / "families" / f"{name}.toml")


# Display/build order of the families; config/families/<id>.toml.
FAMILY_ORDER = ("mono", "pixel", "sans", "serif", "novel", "comics")


def family_ids(root: Path = ROOT) -> list[str]:
    found = {p.stem for p in (root / "config" / "families").glob("*.toml")}
    order = {f: i for i, f in enumerate(FAMILY_ORDER)}
    return sorted(found, key=lambda f: (order.get(f, len(order)), f))


def ranges(root: Path = ROOT) -> list[tuple[int, int]]:
    return [(r["start"], r["end"]) for r in _load(root / "config" / "ranges.toml")["range"]]
