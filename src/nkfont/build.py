"""Master build: Latin + Hangul -> NK master TTF (before Nerd Fonts patching)."""

from __future__ import annotations

import os
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config
from .flags import enforce_terminal_flags, fit_terminal_widths
from .merge import HangulParams, half_width, merge_hangul
from .names import set_names

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
    )


def build_master(fam: dict, weight: dict, params: HangulParams | None = None) -> TTFont:
    srcs = config.sources()
    latin = TTFont(srcs[weight["latin"]].path)
    hangul = TTFont(srcs[weight["hangul"]].path)
    ascent, descent = latin["hhea"].ascent, latin["hhea"].descent
    merge_hangul(latin, hangul, config.ranges(), params or hangul_params(fam))
    set_names(latin, fam["family"], weight["name"], fam["version"], weight["weight_class"])
    half = half_width(latin)
    fit_terminal_widths(latin, half)
    enforce_terminal_flags(latin, half, ascent, descent)
    return latin


def build_family(name: str, out_dir: Path | None = None, only: str | None = None) -> list[Path]:
    fam = config.family(name)
    if fam.get("status") != "active":
        raise SystemExit(f"family {name!r} is {fam.get('status')}; not buildable yet")
    out_dir = out_dir or config.BUILD_DIR / "master"
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for weight in fam["weight"]:
        if only and weight["name"] != only:
            continue
        font = build_master(fam, weight)
        path = out_dir / f"{fam['file_prefix']}-{weight['name'].replace(' ', '')}.ttf"
        save_reproducible(font, path)
        outputs.append(path)
    return outputs
