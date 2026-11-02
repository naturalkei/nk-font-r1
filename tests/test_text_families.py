"""NK Novel / NK Comics (kind = "text"), NK Mono sources and the golden-ratio rules."""

import io
import math

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from nkfont.build import finish_text, hangul_params, is_terminal
from nkfont.checks import check_hangul_coverage, check_text_metrics, run_all
from nkfont.merge import HangulParams, merge_hangul
from nkfont.names import set_names
from nkfont.phi import PHI, line_metrics, ratio

RANGES = [(0x3131, 0x3131), (0xAC00, 0xAC00), (0x00B7, 0x00B7)]
TEXT_FAM = {
    "kind": "text",
    "family": "NK Novel",
    "version": "0.1.0",
    "metrics": {"ascent": 960, "descent": -300, "line_height": "phi"},
}


def _box(pen, x0, y0, x1, y1):
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()


def make_tt_hangul() -> TTFont:
    """TrueType Hangul source like NanumGothicCoding / Gowun Batang, with a composite glyph."""
    cmap = {0xAC00: "uniAC00", 0x3131: "uni3131", 0x00B7: "uni00B7"}
    names = [".notdef", "base", *cmap.values()]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    glyphs = {}
    for n in names:
        pen = TTGlyphPen({"base": None})
        if n == "uniAC00":
            pen.addComponent("base", (1, 0, 0, 1, 0, 0))  # composite, must be decomposed
        else:
            _box(pen, 50, -80, 850, 800)
        glyphs[n] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (900, 50) for n in names})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Fixture TT Hangul", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    return fb.font


def roundtrip(font: TTFont) -> TTFont:
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    return TTFont(buf)


def first_point_order(font: TTFont, cp: int) -> list:
    rec = RecordingPen()
    font.getGlyphSet()[font.getBestCmap()[cp]].draw(rec)
    return [args[0] for op, args in rec.value if op in ("moveTo", "lineTo")][:3]


def test_phi_ratio_tokens():
    assert ratio("phi") == pytest.approx(1.6180339887)
    assert ratio("phi^0.5") == pytest.approx(math.sqrt(PHI))
    assert ratio("phi^-1") == pytest.approx(PHI - 1)
    assert ratio(1.5) == 1.5
    with pytest.raises(ValueError):
        ratio("golden")


def test_line_metrics_make_default_line_exactly_phi():
    asc, desc, gap = line_metrics(960, -300, 1000, "phi")
    assert (asc, desc) == (960, -300)
    assert asc - desc + gap == 1618
    with pytest.raises(ValueError):
        line_metrics(1100, -400, 1000, "phi^0.5")  # 1500 > 1272


def test_truetype_source_keeps_contour_direction_and_decomposes(latin):
    """Regression: CFF sources need reversed contours, TrueType sources must not be reversed."""
    src = make_tt_hangul()
    expected = first_point_order(src, 0x3131)
    merge_hangul(latin, src, RANGES, HangulParams(scale=1.0, dy=0, center="bbox"))
    font = roundtrip(latin)
    got = first_point_order(font, 0x3131)
    # Same winding: points keep their order, only shifted horizontally into the cell.
    dx = got[0][0] - expected[0][0]
    assert got == [(x + dx, y) for x, y in expected]
    g = font["glyf"][font.getBestCmap()[0xAC00]]
    assert not g.isComposite() and g.numberOfContours == 1


def test_proportional_merge_keeps_source_spacing_plus_tracking(latin, hangul):
    merge_hangul(
        latin, hangul, RANGES, HangulParams(scale=1.0, advance="proportional", tracking=-20)
    )
    font = roundtrip(latin)
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    assert hmtx[cmap[0xAC00]][0] == 900  # source 920 - 20, not a 1200 cell
    g = font["glyf"][cmap[0xAC00]]
    assert g.xMin == 40  # source lsb 50 shifted by tracking / 2
    assert 0x00B7 not in cmap  # ambiguous characters still stay with the Latin base


def test_text_family_flags_and_checks(latin, hangul):
    params = hangul_params(TEXT_FAM)
    assert params.advance == "proportional" and not is_terminal(TEXT_FAM)
    merge_hangul(latin, hangul, RANGES, params)
    font = roundtrip(
        finish_text(latin, TEXT_FAM, {"name": "Regular", "weight_class": 400}, 1020, -300, 0)
    )
    hhea = font["hhea"]
    assert font["post"].isFixedPitch == 0
    assert hhea.ascent - hhea.descent + hhea.lineGap == 1618
    assert check_text_metrics(font) == []
    # The synthetic font has one syllable, so the reading-face coverage check must flag it.
    assert check_hangul_coverage(font) == ["11171 Hangul syllables missing, first U+AC01"]
    assert set(run_all(font, kind="text")) == {"text-metrics", "hangul-coverage", "names"}


def test_text_metrics_catch_monospace_claims(latin):
    set_names(latin, "NK Novel", "Regular", "0.1.0", 400)
    assert "post.isFixedPitch is set on a proportional face" not in check_text_metrics(latin)
    latin["post"].isFixedPitch = 1
    assert "post.isFixedPitch is set on a proportional face" in check_text_metrics(latin)


@pytest.mark.parametrize("name", ["Nanum Mono", "NK 나눔", "NeoDunggeunmo Pixel"])
def test_new_reserved_names_are_rejected(latin, name):
    with pytest.raises(ValueError):
        set_names(latin, name, "Regular", "0.1.0", 400)
