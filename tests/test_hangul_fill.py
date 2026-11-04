"""`[hangul] replace` (re-import a source's own Hangul) and a weight's `fill` source (NK Comics)."""

from __future__ import annotations

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from nkfont import config, presetqa
from nkfont.build import build_master, drop_hangul, fill_params, hangul_params
from nkfont.merge import HangulParams


def _font(glyphs: dict[int, tuple[tuple[int, int, int, int], int]], family: str) -> TTFont:
    """TrueType font from {code point: ((x0, y0, x1, y1), advance)} boxes, UPM 1000."""
    names = {cp: f"uni{cp:04X}" for cp in glyphs}
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", *names.values()])
    fb.setupCharacterMap(names)
    pens = {".notdef": TTGlyphPen(None).glyph()}
    for cp, ((x0, y0, x1, y1), _) in glyphs.items():
        pen = TTGlyphPen(None)
        pen.moveTo((x0, y0))
        pen.lineTo((x0, y1))
        pen.lineTo((x1, y1))
        pen.lineTo((x1, y0))
        pen.closePath()
        pens[names[cp]] = pen.glyph()
    fb.setupGlyf(pens)
    fb.setupHorizontalMetrics(
        {".notdef": (500, 0), **{names[cp]: (adv, box[0]) for cp, (box, adv) in glyphs.items()}}
    )
    fb.setupHorizontalHeader(ascent=900, descent=-200)
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    return fb.font


HAND = {  # one handwriting source: Latin H 0 and its own 가 / ㄱ (like Gaegu)
    0x48: ((50, 0, 500, 700), 550),
    0x30: ((50, 0, 500, 700), 550),
    0xAC00: ((100, 0, 800, 900), 900),
    0x3131: ((100, 0, 700, 800), 900),
}
PEN = {  # the fill source: 각 drawn smaller (like Nanum Pen Script), and its own 가
    0xAC00: ((100, 0, 500, 500), 600),
    0xAC01: ((100, 0, 500, 500), 600),
}
RANGES = [(0xAC00, 0xD7A3), (0x3131, 0x318E)]


def _ink(font: TTFont, cp: int):
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[font.getBestCmap()[cp]].draw(bp)
    return bp.bounds


def _fam(**extra) -> dict:
    return {
        "kind": "text",
        "family": "NK Fixture",
        "file_prefix": "NKFixture",
        "version": "0.1.0",
        **extra,
    }


WEIGHT = {"name": "Regular", "weight_class": 400, "fill": "pen"}


def test_drop_hangul_unmaps_and_removes_the_sources_own_hangul():
    latin = _font(HAND, "Hand")
    n = drop_hangul(latin, _font(HAND, "Hand"), RANGES)
    assert n == 2
    cmap = latin.getBestCmap()
    assert set(cmap) == {0x48, 0x30}
    assert "uniAC00" not in latin.getGlyphOrder() and "uni3131" not in latin.getGlyphOrder()
    assert latin["maxp"].numGlyphs == len(latin.getGlyphOrder())


def test_drop_hangul_keeps_hangul_the_other_source_lacks():
    latin = _font(HAND, "Hand")
    assert drop_hangul(latin, _font(PEN, "Pen"), RANGES) == 1  # only 가: the pen has no ㄱ
    assert set(latin.getBestCmap()) == {0x48, 0x30, 0x3131}


def test_replace_reimports_own_hangul_with_hangul_params_and_fill_adds_the_rest():
    fam = _fam(hangul={"replace": True, "scale": 0.5, "dy": 20}, fill={"scale": 2.0, "dy": -20})
    font = build_master(
        fam,
        WEIGHT,
        hangul_params(fam),
        ranges=RANGES,
        latin=_font(HAND, "Hand"),
        hangul=_font(HAND, "Hand"),
        fill=_font(PEN, "Pen"),
    )
    cmap = font.getBestCmap()
    assert {0x48, 0xAC00, 0xAC01, 0x3131} <= set(cmap)
    # 가 comes from the main source again, scaled 0.5 and moved up 20 (not the pen's 가).
    assert _ink(font, 0xAC00)[1::2] == (20, 470)
    # 각 is only in the pen: scale 0.5 × 2.0 = 1.0, dy 20 - 20 = 0.
    assert _ink(font, 0xAC01)[1::2] == (0, 500)
    assert _ink(font, 0x48) == (50, 0, 500, 700)  # Latin untouched


def test_without_replace_the_sources_own_hangul_is_kept_as_drawn():
    fam = _fam(hangul={"scale": 0.5})
    font = build_master(
        fam,
        {"name": "Regular", "weight_class": 400},
        hangul_params(fam),
        ranges=RANGES,
        latin=_font(HAND, "Hand"),
        hangul=_font(PEN, "Pen"),
    )
    assert _ink(font, 0xAC00) == (100, 0, 800, 900)  # the Latin source's own 가 wins
    assert _ink(font, 0xAC01)[1::2] == (0, 250)


def test_fill_params_are_relative_and_identity_by_default():
    base = HangulParams(scale=0.9, dy=-10, slant=4.0, grade=5.0, tracking=20, width=1.1)
    assert fill_params(_fam(), base) == base
    f = fill_params(
        _fam(fill={"scale": 2.0, "dy": -5, "slant": 1, "grade": -3, "tracking": 10}), base
    )
    assert (f.scale, f.dy, f.slant, f.grade, f.tracking) == (1.8, -15, 5.0, 2.0, 30)
    w = fill_params(_fam(fill={"grade": -3}), base, {"fill_adjust": {"grade": 7}})
    assert w.grade == 12.0  # a weight's fill_adjust replaces the [fill] value for that weight
    with pytest.raises(ValueError, match="unknown"):
        fill_params(_fam(fill={"sclae": 2}), base)


def test_measure_reports_fill_weight_and_centre():
    from test_preset_styles import make_text_font

    font = make_text_font()
    m = presetqa.measure(font, "text", fill="한")  # the same glyph: a perfect match
    assert m["fill_weight"] == 1.0 and m["fill_centre"] == 0
    assert "fill_weight" not in presetqa.measure(font, "text")


def test_comics_uses_a_pen_handwriting_base_with_a_fill_source():
    fam = config.family("comics")
    assert fam["hangul"].get("replace") is True
    for w in fam["weight"]:
        assert w["latin"].startswith("gaegu-") and w["hangul"] == w["latin"]
        assert w["fill"] == "nanum-pen-script"
    srcs = config.sources()
    if not srcs["gaegu-regular"].path.exists():
        pytest.skip("real fonts not fetched")
    assert presetqa.fill_chars(fam, "Regular")  # Gaegu lacks the non-KS X 1001 syllables
