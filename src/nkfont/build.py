"""Master build: Latin + Hangul -> NK master TTF (before Nerd Fonts patching).

Family kinds:
  merge (default)  terminal monospace: Latin mono + Hangul on the 1:2 cell grid (Mono)
  pixel            one pixel font that already holds Latin and Hangul on one grid; renamed and
                   terminal-flagged instead of merged (Pixel)
  text             proportional reading face: Latin text face + Hangul with its own spacing,
                   no terminal grid and no Nerd Fonts icons (Sans, Serif, Novel, Comics)
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config
from .flags import (
    enforce_terminal_flags,
    enforce_text_flags,
    fit_terminal_widths,
    unmap_width_conflicts,
)
from .merge import HangulParams, half_width, merge_hangul
from .names import COPYRIGHT, set_names
from .phi import line_metrics
from .pixelstyle import PixelParams, apply_pixel
from .style import StyleParams, apply_style
from .weights import hangul_weight, pixel_bold, synthesize

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


TERMINAL_KINDS = ("merge", "pixel")


def kind(fam: dict) -> str:
    return fam.get("kind", "merge")


def is_terminal(fam: dict) -> bool:
    """Terminal families keep the 0/600/1200 grid and get Nerd Fonts icons."""
    return kind(fam) in TERMINAL_KINDS


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
        stem=h.get("stem", 0.0),
        contrast=fam.get("weights", {}).get("contrast", 1.0),
        advance="cell" if is_terminal(fam) else "proportional",
        tracking=h.get("tracking", 0),
    )


def _names(font: TTFont, fam: dict, weight: dict) -> None:
    set_names(
        font,
        fam["family"],
        weight["name"],
        fam["version"],
        weight["weight_class"],
        fam.get("copyright", COPYRIGHT),
    )


def finish(font: TTFont, fam: dict, weight: dict, ascent: int, descent: int) -> TTFont:
    _names(font, fam, weight)
    half = half_width(font)
    fit_terminal_widths(font, half)
    enforce_terminal_flags(font, half, ascent, descent)
    return font


def pixel_params(fam: dict, **override) -> PixelParams:
    """`[pixel]` of a pixel family (bitmap-level knobs, see pixelstyle.py), identity by default."""
    return PixelParams.from_dict({**fam.get("pixel", {}), **override})


def style_params(fam: dict, **override) -> StyleParams:
    """`[style]` of a text family (whole-face knobs, see style.py), identity by default."""
    return StyleParams.from_dict({**fam.get("style", {}), **override})


def build_pixel(
    fam: dict,
    weight: dict,
    pixel: PixelParams | None = None,
    unicodes: set[int] | None = None,
) -> TTFont:
    font = TTFont(config.sources()[weight["source"]].path)
    term = fam.get("terminal", {})
    if term.get("unmap_width_conflicts", True):
        unmap_width_conflicts(font, half_width(font), [tuple(r) for r in term.get("unmap", [])])
    if weight.get("smear"):
        # Bitmap-style bold: every vertical stroke `smear` pixels wider to the right, horizontal
        # strokes untouched, so the outline stays on the pixel grid (the classic bitmap bold).
        pixel_bold(font, fam["grid"]["units_per_pixel"] * weight["smear"])
    px = fam.get("grid", {}).get("units_per_pixel", 64)
    apply_pixel(font, pixel or pixel_params(fam), px, unicodes)
    return finish(font, fam, weight, font["hhea"].ascent, font["hhea"].descent)


def build_master(
    fam: dict,
    weight: dict,
    params: HangulParams | None = None,
    ranges: list[tuple[int, int]] | None = None,
    latin: TTFont | None = None,
    hangul: TTFont | None = None,
    style: StyleParams | None = None,
    pixel: PixelParams | None = None,
    unicodes: set[int] | None = None,
) -> TTFont:
    """`ranges`, `latin`, `hangul` and `unicodes` let the tuning studio build small previews
    quickly; `style` / `pixel` override the family's `[style]` / `[pixel]` tables."""
    if fam.get("kind") == "pixel":
        return build_pixel(fam, weight, pixel, unicodes)
    srcs = config.sources()
    latin = latin or TTFont(srcs[weight["latin"]].path)
    hangul = hangul or TTFont(srcs[weight["hangul"]].path)
    hhea = latin["hhea"]
    ascent, descent, line_gap = hhea.ascent, hhea.descent, hhea.lineGap
    contrast = fam.get("weights", {}).get("contrast", 1.0)
    # Weights the Latin upstream does not ship are derived from the nearest master (weights.py).
    synthesize(latin, weight.get("latin_grade", 0.0), contrast)
    params = params or hangul_params(fam)
    delta, grade_y = hangul_weight(fam, weight, srcs)
    # Grades are in the Latin font's units; the solver works at UPM 1000.
    k = latin["head"].unitsPerEm / 1000
    if delta:
        params = dataclasses.replace(params, weight_grade=delta * k)
    if grade_y is not None:
        params = dataclasses.replace(params, grade_y=grade_y * k)
    merge_hangul(latin, hangul, ranges or config.ranges(), params)
    if is_terminal(fam):
        return finish(latin, fam, weight, ascent, descent)
    apply_style(latin, style or style_params(fam), unicodes)
    return finish_text(latin, fam, weight, ascent, descent, line_gap)


def finish_text(
    font: TTFont, fam: dict, weight: dict, ascent: int, descent: int, line_gap: int
) -> TTFont:
    """Proportional reading faces: names and text flags only; widths are the designers'."""
    _names(font, fam, weight)
    m = fam.get("metrics", {})
    upm = font["head"].unitsPerEm
    # Config values are expressed for UPM 1000, like the Hangul scale.
    to_units = upm / 1000
    if "ascent" in m:
        ascent = round(m["ascent"] * to_units)
    if "descent" in m:
        descent = round(m["descent"] * to_units)
    if "line_gap" in m:
        line_gap = round(m["line_gap"] * to_units)
    if "line_height" in m:  # golden-ratio rule, see phi.py
        ascent, descent, line_gap = line_metrics(ascent, descent, upm, m["line_height"])
    enforce_text_flags(font, ascent, descent, line_gap)
    return font


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
