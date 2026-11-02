"""Master build: Latin + Hangul -> NK master TTF (before Nerd Fonts patching).

Families with `kind = "pixel"` start from a single pixel font that already holds Latin and
Hangul on one grid; they are renamed and terminal-flagged instead of merged.
"""

from __future__ import annotations

import os
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config
from .flags import enforce_terminal_flags, fit_terminal_widths, unmap_width_conflicts
from .merge import HangulParams, half_width, merge_hangul
from .names import COPYRIGHT, set_names

# Seconds between 1904-01-01 (OpenType epoch) and 1970-01-01 (Unix epoch).
MAC_EPOCH_OFFSET = 2082844800


def save_reproducible(font: TTFont, path: Path) -> None:
    """Save with fixed timestamps so identical inputs give byte-identical fonts.

    Uses SOURCE_DATE_EPOCH when set (reproducible-builds convention), otherwise keeps the Latin
    base's `head.created`.
    """
    head = font["head"]
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is not None:
        stamp = int(epoch) + MAC_EPOCH_OFFSET
        head.created = head.modified = stamp
    else:
        head.modified = head.created
    font.recalcTimestamp = False
    font.save(path)


def hangul_params(fam: dict, **override) -> HangulParams:
    h = {**fam.get("hangul", {}), **override}
    return HangulParams(
        scale=h.get("scale", 0.96),
        dy=h.get("dy", 0),
        center=h.get("center", "advance"),
        fit=h.get("fit", 0.92),
        width=h.get("width", 1.0),
        slant=h.get("slant", 0.0),
        grade=h.get("grade", 0.0),
    )


def finish(font: TTFont, fam: dict, weight: dict, ascent: int, descent: int) -> TTFont:
    set_names(
        font,
        fam["family"],
        weight["name"],
        fam["version"],
        weight["weight_class"],
        fam.get("copyright", COPYRIGHT),
    )
    half = half_width(font)
    fit_terminal_widths(font, half)
    enforce_terminal_flags(font, half, ascent, descent)
    return font


def build_pixel(fam: dict, weight: dict) -> TTFont:
    font = TTFont(config.sources()[weight["source"]].path)
    term = fam.get("terminal", {})
    if term.get("unmap_width_conflicts", True):
        unmap_width_conflicts(font, half_width(font), [tuple(r) for r in term.get("unmap", [])])
    return finish(font, fam, weight, font["hhea"].ascent, font["hhea"].descent)


def build_master(
    fam: dict,
    weight: dict,
    params: HangulParams | None = None,
    ranges: list[tuple[int, int]] | None = None,
    latin: TTFont | None = None,
    hangul: TTFont | None = None,
) -> TTFont:
    """`ranges`, `latin` and `hangul` let the tuning studio build small previews quickly."""
    if fam.get("kind") == "pixel":
        return build_pixel(fam, weight)
    srcs = config.sources()
    latin = latin or TTFont(srcs[weight["latin"]].path)
    hangul = hangul or TTFont(srcs[weight["hangul"]].path)
    ascent, descent = latin["hhea"].ascent, latin["hhea"].descent
    merge_hangul(latin, hangul, ranges or config.ranges(), params or hangul_params(fam))
    return finish(latin, fam, weight, ascent, descent)


def master_path(fam: dict, weight: dict, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or config.BUILD_DIR / "master"
    return out_dir / f"{fam['file_prefix']}-{weight['name'].replace(' ', '')}.ttf"


def build_family(name: str, out_dir: Path | None = None, only: str | None = None) -> list[Path]:
    fam = config.family(name)
    if fam.get("status") != "active":
        raise SystemExit(f"family {name!r} is {fam.get('status')}; not buildable yet")
    outputs = []
    for weight in fam["weight"]:
        if only and weight["name"] != only:
            continue
        font = build_master(fam, weight)
        path = master_path(fam, weight, out_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        save_reproducible(font, path)
        outputs.append(path)
    return outputs
