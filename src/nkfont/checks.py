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


def run_all(font: TTFont, base: TTFont | None = None) -> dict[str, list[str]]:
    result = {
        "widths": check_widths(font),
        "metrics": check_metrics(font),
        "names": check_names(font),
    }
    if base is not None:
        result["features"] = check_features(font, base)
    return result
