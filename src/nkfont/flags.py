"""Terminal-compatibility flags. Run after merging and again after Nerd Fonts patching."""

from __future__ import annotations

import unicodedata

from fontTools.ttLib import TTFont
from wcwidth import wcwidth

USE_TYPO_METRICS = 1 << 7


def glyph_y_extent(font: TTFont) -> tuple[int, int]:
    glyf = font["glyf"]
    y_min = y_max = 0
    for name in font.getGlyphOrder():
        g = glyf[name]
        if getattr(g, "numberOfContours", 0) == 0:
            continue
        if not hasattr(g, "yMax"):
            g.recalcBounds(glyf)
        y_min = min(y_min, g.yMin)
        y_max = max(y_max, g.yMax)
    return y_min, y_max


def enforce_terminal_flags(font: TTFont, half: int, ascent: int, descent: int) -> None:
    """`ascent`/`descent` are the Latin base's line metrics (descent negative)."""
    os2, hhea = font["OS/2"], font["hhea"]

    font["post"].isFixedPitch = 1
    os2.panose.bFamilyType = 2  # Latin Text: only then does bProportion=9 mean monospaced
    os2.panose.bProportion = 9
    os2.xAvgCharWidth = half

    hhea.ascent, hhea.descent, hhea.lineGap = ascent, descent, 0
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = ascent, descent, 0
    if os2.version < 4:
        os2.version = 4
    os2.fsSelection |= USE_TYPO_METRICS

    y_min, y_max = glyph_y_extent(font)
    os2.usWinAscent = max(ascent, y_max)
    os2.usWinDescent = max(-descent, -y_min)


def fit_terminal_widths(font: TTFont, half: int) -> list[int]:
    """Make advances agree with terminal cell counts (wcwidth); returns changed code points.

    Empty zero-width characters get advance 0. Glyphs terminals treat as two cells get a
    full-width advance.

    JetBrains Mono ships some East Asian Wide symbols at one cell (U+26A1, U+FF5B, ...) and the
    Nerd Fonts patcher adds U+2630 the same way. Terminals reserve two cells for them, so centre
    them in a full-width advance.
    """
    glyf, hmtx = font["glyf"], font["hmtx"]
    fixed = []
    for cp, name in font.getBestCmap().items():
        adv, lsb = hmtx[name]
        cells = wcwidth(chr(cp))
        if cells == 0 and adv and getattr(glyf[name], "numberOfContours", 0) == 0:
            hmtx[name] = (0, 0)  # empty format characters such as U+200B ZWSP
            fixed.append(cp)
            continue
        if adv == 0 and cells == 1 and unicodedata.category(chr(cp)) not in ("Mn", "Me"):
            # Zero-advance private-use glyphs (IBM Plex Mono U+F6D7/F6D8): give them a cell.
            _shift(glyf, name, half // 2)
            hmtx[name] = (half, lsb + half // 2)
            fixed.append(cp)
            continue
        if adv != half or cells != 2:
            continue
        dx = half // 2
        _shift(glyf, name, dx)
        hmtx[name] = (2 * half, lsb + dx)
        fixed.append(cp)
    return fixed


def _shift(glyf, name: str, dx: int) -> None:
    g = glyf[name]
    if g.isComposite():
        for comp in g.components:
            comp.x += dx
    elif getattr(g, "numberOfContours", 0) > 0:
        g.coordinates.translate((dx, 0))
    g.recalcBounds(glyf)


def unmap_codepoints(font: TTFont, cps) -> None:
    """Remove code points from every cmap subtable; glyphs stay for GSUB."""
    cps = set(cps)
    for table in font["cmap"].tables:
        for cp in cps & table.cmap.keys():
            del table.cmap[cp]


def unmap_width_conflicts(font: TTFont, half: int, ranges=()) -> list[int]:
    """Unmap code points whose drawing cannot fit the cell count terminals use.

    For a single-source pixel font: legacy Korean bitmap fonts draw East Asian *Ambiguous*
    symbols (①, ■, ▶, em dash) two cells wide, but terminals give them one cell. A pixel glyph
    cannot be squeezed, so the code point is left to the fallback font instead. Code points in
    `ranges` (conjoining jamo, phase 2) are unmapped unconditionally.
    """
    hmtx = font["hmtx"]
    drop = []
    for cp, name in font.getBestCmap().items():
        if any(a <= cp <= b for a, b in ranges):
            drop.append(cp)
            continue
        w = wcwidth(chr(cp))
        if w < 0:
            continue
        if hmtx[name][0] not in (0, w * half) and w > 0:
            drop.append(cp)
    unmap_codepoints(font, drop)
    return drop
