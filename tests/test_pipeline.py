import io

import pytest
from fontTools.ttLib import TTFont

from nkfont.checks import check_metrics, check_names, check_widths
from nkfont.flags import enforce_terminal_flags, fit_terminal_widths
from nkfont.merge import HangulParams, cell_width, merge_hangul
from nkfont.names import set_names

RANGES = [
    (0x00B7, 0x00B7),
    (0x0030, 0x0030),
    (0x3131, 0x3164),
    (0xAC00, 0xAC00),
    (0xFF5B, 0xFF5B),
    (0xFFA0, 0xFFDC),
]


def roundtrip(font: TTFont) -> TTFont:
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    return TTFont(buf)


def build(latin, hangul, **params) -> TTFont:
    merge_hangul(latin, hangul, RANGES, HangulParams(**params))
    set_names(latin, "NK Sans", "Regular", "0.1.0", 400)
    fit_terminal_widths(latin, 600)
    enforce_terminal_flags(latin, 600, 1020, -300)
    return roundtrip(latin)


def test_cell_width_follows_east_asian_width_and_wcwidth():
    assert cell_width(0xAC00, 600) == 1200  # Hangul syllable
    assert cell_width(0xFFA1, 600) == 600  # halfwidth Hangul
    assert cell_width(0x00B7, 600) is None  # ambiguous stays with the Latin base
    assert cell_width(0x3164, 600) is None  # Hangul filler is zero-width in terminals


def test_merge_imports_only_missing_wide_and_halfwidth(latin, hangul):
    font = build(latin, hangul)
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    assert hmtx[cmap[0xAC00]][0] == 1200
    assert hmtx[cmap[0x3131]][0] == 1200
    assert hmtx[cmap[0xFFA1]][0] == 600
    assert 0x00B7 not in cmap and 0x3164 not in cmap
    assert cmap[0x30] == "zero"  # Latin glyph not overwritten


def test_hangul_is_centred_in_full_cell(latin, hangul):
    font = build(latin, hangul, scale=1.0, dy=0)
    g = font["glyf"][font.getBestCmap()[0xAC00]]
    # source advance 920 centred in 1200 -> shift 140; source box 50..870
    assert (g.xMin, g.xMax) == (190, 1010)


def test_terminal_widths_and_metrics_pass(latin, hangul):
    font = build(latin, hangul)
    assert check_widths(font) == []
    assert check_metrics(font) == []
    assert check_names(font) == []
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    assert hmtx[cmap[0xFF5B]][0] == 1200  # Latin wide symbol widened for terminals
    assert hmtx[cmap[0x200B]][0] == 0  # ZWSP is zero-width


def test_line_metrics_keep_latin_base_and_win_covers_bbox(latin, hangul):
    font = build(latin, hangul, scale=1.3)
    hhea, os2 = font["hhea"], font["OS/2"]
    assert (hhea.ascent, hhea.descent, hhea.lineGap) == (1020, -300, 0)
    assert os2.usWinAscent >= font["head"].yMax
    assert os2.xAvgCharWidth == 600
    assert font["post"].isFixedPitch == 1


def test_reserved_font_name_is_rejected(latin):
    with pytest.raises(ValueError):
        set_names(latin, "Source Mono", "Regular", "0.1.0", 400)


def test_feature_ui_names_survive_renaming(latin):
    # Regression: set_names wiped nameID >= 256, so ssXX/cvXX labels from the Latin base
    # ("Classic construction" in JetBrains Mono) went missing in NK Sans.
    latin["name"].setName("Classic construction", 256, 3, 1, 0x409)
    latin["name"].setName("Old Mac record", 256, 1, 0, 0)
    set_names(latin, "NK Sans", "Regular", "0.1.0", 400)
    font = roundtrip(latin)
    assert font["name"].getName(256, 3, 1, 0x409).toUnicode() == "Classic construction"
    assert font["name"].getName(256, 1, 0, 0) is None
    assert font["name"].getName(1, 3, 1, 0x409).toUnicode() == "NK Sans"
