"""Automated QA checks. Each returns a list of human-readable problems (empty = pass)."""

from __future__ import annotations

import unicodedata

from fontTools.ttLib import TTFont
from wcwidth import wcwidth

from .config import RESERVED_NAMES
from .flags import USE_TYPO_METRICS, glyph_y_extent
from .merge import half_width


def expected_advance(cp: int, half: int) -> int | None:
    """Advance a terminal expects for `cp`, from wcwidth. None = no expectation."""
    w = wcwidth(chr(cp))
    if w < 0:
        return None  # control characters
    return {0: 0, 1: half, 2: 2 * half}[w]


def check_widths(font: TTFont) -> list[str]:
    """Every mapped code point's advance must match the cell count terminals use (wcwidth)."""
    half = half_width(font)
    hmtx = font["hmtx"]
    allowed = {0, half, 2 * half}
    problems = []
    for cp, name in sorted(font.getBestCmap().items()):
        adv = hmtx[name][0]
        if adv not in allowed:
            problems.append(f"U+{cp:04X} advance {adv} not in {sorted(allowed)}")
            continue
        exp = expected_advance(cp, half)
        if exp is None or adv == exp:
            continue
        if exp == 0 and unicodedata.category(chr(cp)) in ("Mn", "Me"):
            continue  # spacing combining marks in a monospace font are acceptable
        problems.append(f"U+{cp:04X} advance {adv}, terminal expects {exp}")
    return problems


def is_pua(cp: int) -> bool:
    return 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0x10FFFF


def check_overflow(
    font: TTFont, inherited: set[int] | None = None, tolerance: float = 0.05
) -> tuple[list[str], list[str]]:
    """Ink that leaves its cell overlaps the neighbouring character in a terminal.

    Returns (errors, warnings). Glyphs we added are errors. Code points in `inherited` (from the
    Latin base, or added by the Nerd Fonts patcher whose non-Mono variant overhangs on purpose)
    and PUA icons are warnings.
    """
    glyf, hmtx = font["glyf"], font["hmtx"]
    errors, warnings = [], []
    for cp, name in sorted(font.getBestCmap().items()):
        g = glyf[name]
        adv = hmtx[name][0]
        if adv == 0 or getattr(g, "numberOfContours", 0) == 0:
            continue
        if not hasattr(g, "xMin"):
            g.recalcBounds(glyf)
        tol = adv * tolerance
        if g.xMin >= -tol and g.xMax <= adv + tol:
            continue
        msg = f"U+{cp:04X} ink {g.xMin}..{g.xMax} outside cell 0..{adv}"
        theirs = inherited is not None and cp in inherited
        (warnings if theirs or is_pua(cp) else errors).append(msg)
    return errors, warnings


def check_metrics(font: TTFont) -> list[str]:
    os2, hhea, post = font["OS/2"], font["hhea"], font["post"]
    half = half_width(font)
    p = []
    if post.isFixedPitch == 0:
        p.append("post.isFixedPitch is 0")
    if (os2.panose.bFamilyType, os2.panose.bProportion) != (2, 9):
        p.append(f"panose family/proportion is {os2.panose.bFamilyType}/{os2.panose.bProportion}")
    if os2.xAvgCharWidth != half:
        p.append(f"xAvgCharWidth {os2.xAvgCharWidth} != {half}")
    if (hhea.ascent, hhea.descent) != (os2.sTypoAscender, os2.sTypoDescender):
        p.append("hhea and typo ascender/descender differ")
    if hhea.lineGap or os2.sTypoLineGap:
        p.append("lineGap is not 0")
    if not os2.fsSelection & USE_TYPO_METRICS:
        p.append("USE_TYPO_METRICS not set")
    y_min, y_max = glyph_y_extent(font)
    if os2.usWinAscent < y_max or os2.usWinDescent < -y_min:
        p.append(f"usWin {os2.usWinAscent}/{os2.usWinDescent} clips bbox {y_max}/{y_min}")
    return p


def check_names(font: TTFont) -> list[str]:
    p = []
    for rec in font["name"].names:
        text = rec.toUnicode()
        if rec.nameID in (0, 13, 14):
            continue  # copyright/license lines must keep upstream notices
        for word in RESERVED_NAMES:
            if word.lower() in text.lower():
                p.append(f"nameID {rec.nameID} contains reserved name {word!r}: {text}")
    return p


def check_features(font: TTFont, base: TTFont) -> list[str]:
    def tags(f):
        if "GSUB" not in f:
            return set()
        return {r.FeatureTag for r in f["GSUB"].table.FeatureList.FeatureRecord}

    missing = tags(base) - tags(font)
    return [f"GSUB feature lost: {t}" for t in sorted(missing)]


def inherited_codepoints(
    font: TTFont, base: TTFont | None, own: set[int] | None = None
) -> set[int] | None:
    """Code points not added by us: everything except `own` if given, else the base's cmap."""
    if own is not None:
        return set(font.getBestCmap()) - own
    return set(base.getBestCmap()) if base is not None else None


def run_all(
    font: TTFont, base: TTFont | None = None, own: set[int] | None = None
) -> dict[str, list[str]]:
    """`own`: code points we import (master cmap minus Latin base); improves overflow triage."""
    result = {
        "widths": check_widths(font),
        "overflow": check_overflow(font, inherited_codepoints(font, base, own))[0],
        "metrics": check_metrics(font),
        "names": check_names(font),
    }
    if base is not None:
        result["features"] = check_features(font, base)
    return result
