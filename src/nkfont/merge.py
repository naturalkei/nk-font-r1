"""Inject Hangul glyphs into a Latin TrueType font.

The Latin font is kept as the main context: its GSUB/GPOS (calt, cvXX, ssXX, kern) stay untouched.
Hangul outlines are scaled uniformly and converted from cubic (CFF) to quadratic when needed.
Terminal families (`advance = "cell"`) place them in a cell twice as wide as the Latin advance;
reading families (`advance = "proportional"`) keep the source's own spacing, scaled.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.filterPen import DecomposingFilterPen
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
    width: float = 1.0  # extra horizontal scale (1.0 = keep proportions)
    slant: float = 0.0  # degrees, positive leans right (for italics; skewed about the ink centre)
    grade: float = 0.0  # font units added to stem weight without changing the advance
    advance: str = "cell"  # "cell" (terminal grid) or "proportional" (reading faces)
    tracking: float = 0.0  # proportional only: target units added to each Hangul advance


def is_cubic(font: TTFont) -> bool:
    """CFF/CFF2 outlines are cubic with the opposite contour direction to TrueType."""
    return "CFF " in font or "CFF2" in font


def embolden(glyph, amount: float) -> None:
    """Thicken (amount > 0) or thin a TrueType glyph's strokes by `amount` font units in total.

    Every point moves along the bisector of its two edge normals by amount/2, the method
    FreeType's FT_Outline_Embolden uses. Outer contours are clockwise and holes counter-clockwise
    in TrueType, so holes shrink while outlines grow. Advances are not touched (like a GRAD axis).
    """
    if not amount or glyph.numberOfContours <= 0:
        return
    coords = glyph.coordinates
    contours, start = [], 0
    for end in glyph.endPtsOfContours:
        contours.append((start, end))
        start = end + 1

    def signed_area(a, b):
        pts = [coords[i] for i in range(a, b + 1)]
        return sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))

    # The biggest contour is an outline: if it runs counter-clockwise the whole glyph is
    # reversed (not TrueType convention), so flip the normals to keep "outward" outward.
    outer = max((signed_area(a, b) for a, b in contours), key=abs)
    half = amount / 2 if outer >= 0 else -amount / 2
    new = list(coords)
    for start, end in contours:
        pts = [coords[i] for i in range(start, end + 1)]
        n = len(pts)
        for k in range(n):
            px, py = pts[k - 1]
            cx, cy = pts[k]
            nx, ny = pts[(k + 1) % n]
            ax, ay = cx - px, cy - py
            bx, by = nx - cx, ny - cy
            la, lb = math.hypot(ax, ay), math.hypot(bx, by)
            if la == 0 or lb == 0:
                continue
            # Outward normal of a clockwise (y-up) edge direction (dx, dy) is (-dy, dx).
            n1 = (-ay / la, ax / la)
            n2 = (-by / lb, bx / lb)
            d = max(1 + n1[0] * n2[0] + n1[1] * n2[1], 0.35)  # clamp spikes at sharp corners
            new[start + k] = (cx + (n1[0] + n2[0]) * half / d, cy + (n1[1] + n2[1]) * half / d)
    for i, (x, y) in enumerate(new):
        coords[i] = (round(x), round(y))


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
    if params.advance not in ("cell", "proportional"):
        raise ValueError(f"advance must be 'cell' or 'proportional', not {params.advance!r}")
    proportional = params.advance == "proportional"
    # Only cubic (PostScript) sources need their contours reversed; reversing TrueType sources
    # would flip them to the wrong direction and break non-zero filling and hinting.
    reverse = is_cubic(hangul)

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
        src_name = src_cmap[cp]
        bp = BoundsPen(src_glyphs)
        src_glyphs[src_name].draw(bp)
        x0, _, x1, _ = bp.bounds or (0, 0, 0, 0)
        _, y0, _, y1 = bp.bounds or (0, 0, 0, 0)
        gs = s
        if proportional:
            sx = gs * params.width
            target = round(src_hmtx[src_name][0] * sx + params.tracking)
            dx = params.tracking / 2  # keep the source side bearings, split the tracking
        else:
            target = cell_width(cp, half)
            # Ink width after the horizontal scale and the skew (a slanted box gets wider).
            span = (x1 - x0) * params.width + abs(math.tan(math.radians(params.slant))) * (y1 - y0)
            if span * gs > target * params.fit:
                # Source glyph is wider than its cell (e.g. Source Han Sans "halfwidth" jamo are
                # 920 wide): shrink uniformly so the ink stays inside the cell, then centre it.
                gs = target * params.fit / span
            sx = gs * params.width
            if params.center == "bbox" or gs != s:
                dx = (target - (x1 - x0) * sx) / 2 - x0 * sx
            else:
                dx = (target - src_hmtx[src_name][0] * sx) / 2
        if params.slant:
            # Skew about the ink's vertical centre so the glyph stays centred in its cell.
            k = math.tan(math.radians(params.slant))
            matrix = (sx, 0, k * gs, gs, dx - k * gs * (y0 + y1) / 2, params.dy)
        else:
            matrix = (sx, 0, 0, gs, dx, params.dy)

        tt_pen = TTGlyphPen(None)
        cu2qu = Cu2QuPen(tt_pen, max_err=1.0, reverse_direction=reverse)
        # TrueType sources (D2Coding, Gowun Batang) use composite glyphs; decompose them,
        # since their component glyphs are not copied into the Latin font.
        out = TransformPen(cu2qu, matrix)
        src_glyphs[src_name].draw(DecomposingFilterPen(out, src_glyphs))
        glyph = tt_pen.glyph()
        embolden(glyph, params.grade)
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
