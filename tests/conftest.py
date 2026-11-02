"""Synthetic fixture fonts so unit tests run in seconds without downloading upstream fonts."""

from __future__ import annotations

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def _box(pen, x0, y0, x1, y1):
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()


def make_latin() -> TTFont:
    """Monospace TrueType 'Latin base': UPM 1000, half width 600, line metrics 1020/-300."""
    names = [".notdef", "zero", "A", "I", "M", "uniFF5B", "uni200B"]
    cmap = {0x30: "zero", 0x41: "A", 0x49: "I", 0x4D: "M", 0xFF5B: "uniFF5B", 0x200B: "uni200B"}
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    glyphs = {}
    for n in names:
        pen = TTGlyphPen(None)
        if n != "uni200B":
            _box(pen, 100, 0, 500, 730)
        glyphs[n] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (600, 100 if n != "uni200B" else 0) for n in names})
    fb.setupHorizontalHeader(ascent=1020, descent=-300)
    fb.setupNameTable({"familyName": "Fixture Mono", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=1020, sTypoDescender=-300, usWinAscent=1020, usWinDescent=300)
    fb.setupPost()
    return fb.font


def make_hangul() -> TTFont:
    """CFF 'Hangul source': UPM 1000, Hangul advance 920 like Source Han Sans KR."""
    cmap = {
        0xAC00: "uniAC00",  # 가  wide
        0x3131: "uni3131",  # ㄱ  wide
        0xFFA1: "uniFFA1",  # ﾡ  halfwidth
        0x00B7: "uni00B7",  # ·  ambiguous: must be skipped
        0x3164: "uni3164",  # filler: wcwidth 0, must be skipped
        0x0030: "zero",  # Latin base already has it: must be skipped
        0xFF5B: "uniFF5B",  # Latin base already has it: must be skipped
    }
    names = [".notdef", *cmap.values()]
    fb = FontBuilder(1000, isTTF=False)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    charstrings = {}
    for n in names:
        pen = T2CharStringPen(920, None)
        _box(pen, 50, -80, 870, 830)
        charstrings[n] = pen.getCharString()
    fb.setupCFF("FixtureHangul", {"FullName": "Fixture Hangul"}, charstrings, {})
    fb.setupHorizontalMetrics({n: (920, 50) for n in names})
    fb.setupHorizontalHeader(ascent=880, descent=-120)
    fb.setupNameTable({"familyName": "Fixture Hangul", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    return fb.font


@pytest.fixture
def latin() -> TTFont:
    return make_latin()


@pytest.fixture
def hangul() -> TTFont:
    return make_hangul()
