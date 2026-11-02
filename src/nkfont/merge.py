"""Inject Hangul glyphs into a Latin monospace TrueType font.

The Latin font is kept as the main context: its GSUB/GPOS (calt, cvXX, ssXX) stay untouched.
Hangul outlines are scaled uniformly, converted from cubic (CFF) to quadratic, and placed in a
cell twice as wide as the Latin advance.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import ttProgram
from wcwidth import wcwidth

# Tables indexed per glyph that we cannot extend safely; they are optional, so drop them.
_PER_GLYPH_TABLES = ("hdmx", "LTSH", "VDMX")


@dataclass(frozen=True)
class HangulParams:
    scale: float = 0.96  # for a 1000-UPM source
    dy: float = 0.0  # target units, after scaling
    center: str = "advance"  # "advance" or "bbox"
    fit: float = 0.92  # imported ink may use at most this share of its cell width


def half_width(font: TTFont) -> int:
    """Latin cell width, read from the advance of '0'."""
    return font["hmtx"][font.getBestCmap()[ord("0")]][0]


def cell_width(cp: int, half: int) -> int | None:
    """Advance for an imported code point, or None to skip it.

    Only East Asian Wide/Fullwidth/Halfwidth characters are imported (ambiguous and neutral ones
    stay with the Latin base), and the cell count must agree with wcwidth, which is what
    terminals use. Fillers and tone marks (U+3164, U+FFA0, U+302E/F) are zero-width there.
    """
    eaw = unicodedata.east_asian_width(chr(cp))
    cells = wcwidth(chr(cp))
    if eaw in ("W", "F") and cells == 2:
        return 2 * half
    if eaw == "H" and cells == 1:
        return half
    return None


def select_codepoints(latin: TTFont, hangul: TTFont, ranges) -> list[int]:
    have = latin.getBestCmap()
    src = hangul.getBestCmap()
    out = []
    for start, end in ranges:
        for cp in range(start, end + 1):
            if cp in src and cp not in have and cell_width(cp, 1) is not None:
                out.append(cp)
    return out


def merge_hangul(latin: TTFont, hangul: TTFont, ranges, params: HangulParams) -> int:
    """Mutates `latin` in place and returns the number of glyphs added."""
    if "glyf" not in latin:
        raise ValueError("Latin base must have TrueType (glyf) outlines")

    half = half_width(latin)
    upm_ratio = latin["head"].unitsPerEm / hangul["head"].unitsPerEm
    s = params.scale * upm_ratio
    src_cmap = hangul.getBestCmap()
    src_glyphs = hangul.getGlyphSet()
    src_hmtx = hangul["hmtx"]

    glyf = latin["glyf"]
    hmtx = latin["hmtx"]
    order = list(latin.getGlyphOrder())
    existing = set(order)
    new_cmap: dict[int, str] = {}

    for cp in select_codepoints(latin, hangul, ranges):
        target = cell_width(cp, half)
        src_name = src_cmap[cp]
        bp = BoundsPen(src_glyphs)
        src_glyphs[src_name].draw(bp)
        x0, _, x1, _ = bp.bounds or (0, 0, 0, 0)
        gs = s
        if (x1 - x0) * gs > target * params.fit:
            # Source glyph is wider than its cell (e.g. Source Han Sans "halfwidth" jamo are 920
            # wide): shrink uniformly so the ink stays inside the cell, then centre the bbox.
            gs = target * params.fit / (x1 - x0)
        if params.center == "bbox" or gs != s:
            dx = (target - (x1 - x0) * gs) / 2 - x0 * gs
        else:
            dx = (target - src_hmtx[src_name][0] * gs) / 2

        tt_pen = TTGlyphPen(None)
        cu2qu = Cu2QuPen(tt_pen, max_err=1.0, reverse_direction=True)
        src_glyphs[src_name].draw(TransformPen(cu2qu, (gs, 0, 0, gs, dx, params.dy)))
        glyph = tt_pen.glyph()
        glyph.program = ttProgram.Program()
        glyph.program.fromBytecode(b"")

        name = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"
        if name in existing:
            name = f"{name}.nk"
        glyph.recalcBounds(glyf)
        glyf[name] = glyph
        hmtx[name] = (target, getattr(glyph, "xMin", 0))
        order.append(name)
        existing.add(name)
        new_cmap[cp] = name

    latin.setGlyphOrder(order)
    glyf.glyphOrder = order
    if "post" in latin and latin["post"].formatType == 2.0:
        latin["post"].extraNames = []
        latin["post"].mapping = {}
    for table in latin["cmap"].tables:
        if table.isUnicode():
            for cp, name in new_cmap.items():
                if table.format == 4 and cp > 0xFFFF:
                    continue
                table.cmap[cp] = name
    for tag in _PER_GLYPH_TABLES:
        if tag in latin:
            del latin[tag]
    latin["maxp"].numGlyphs = len(order)
    return len(new_cmap)
