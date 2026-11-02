"""Benchmark measurements (nkfont.compare) on synthetic fonts."""

import io

from conftest import make_latin
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont

from nkfont import compare
from nkfont.flags import fit_terminal_widths
from nkfont.merge import HangulParams, merge_hangul

CFG = {"latin_sample": "AIM0", "hangul_sample": "가", "raster_px": 64, "hangul_probe": "가"}
GROUPS = [
    {"id": "ai", "title": "A I", "note": "", "chars": ["A", "I"]},
    {"id": "il1", "title": "I l", "note": "", "chars": ["I", "l"]},
    {"id": "ai-again", "title": "A I", "note": "", "chars": ["A", "I"]},
]


def merged(latin, hangul) -> TTFont:
    merge_hangul(latin, hangul, [(0xAC00, 0xAC00), (0x3131, 0x3164)], HangulParams())
    fit_terminal_widths(latin, 600)  # fixes the fixture's U+200B / U+FF5B quirks like the build
    buf = io.BytesIO()
    latin.save(buf)
    buf.seek(0)
    return TTFont(buf)


def test_measure_reports_grid_coverage_and_hangul_cells(latin, hangul):
    font = merged(latin, hangul)
    r = compare.measure_font(font, CFG, GROUPS)
    assert r["grid"]["mismatches"] == 0
    assert r["grid"]["ambiguous_wide"] == 0
    assert r["coverage"]["hangul_syllables"] == 1
    assert r["metrics"]["hangul_cells"] == 2.0
    assert r["metrics"]["half"] == 600
    assert r["guides"]["han"]["adv"] == 1200


def test_ambiguous_drawn_wide_is_counted(latin):
    # D2Coding draws Ambiguous symbols (①, ·) two cells wide; terminals give them one.
    latin["cmap"].getcmap(3, 1).cmap[0x00B7] = "A"
    font = TTFont(io.BytesIO(compare.font_bytes(latin)))
    font["hmtx"]["A"] = (1200, 100)
    g = compare.grid(font)
    assert g["ambiguous_wide"] == 1 and "·" in g["ambiguous_examples"]
    assert g["mismatches"] >= 1


def test_specimen_scores_identical_glyphs_zero_and_flags_missing(latin):
    data = compare.font_bytes(latin)
    same = compare.specimen_group(latin, data, ["A", "I"], 64)  # fixture boxes are identical
    assert same["distinct"] == 0.0 and same["closest"] == ["A", "I"]
    missing = compare.specimen_group(latin, data, ["I", "l"], 64)
    assert missing["missing"] == ["l"] and missing["distinct"] is None
    assert missing["glyphs"][0]["d"].startswith("M")


def test_features_list_user_facing_tags_with_changed_chars(latin):
    addOpenTypeFeaturesFromString(
        latin,
        "feature ss01 { sub A by I; } ss01;\nfeature zero { sub zero by M; } zero;\n"
        "feature ccmp { sub M by A; } ccmp;\n",
    )
    font = TTFont(io.BytesIO(compare.font_bytes(latin)))
    feats = {f["tag"]: f for f in compare.features(font)}
    assert set(feats) == {"ss01", "zero"}  # ccmp is plumbing, hidden
    assert feats["ss01"]["chars"] == "A" and feats["ss01"]["label"] == "스타일 세트 1"
    assert feats["zero"]["label"] == "빗금 0"


def test_improvement_notes_are_honest(latin, hangul):
    nk = compare.measure_font(merged(latin, hangul), CFG, GROUPS)
    ref = compare.measure_font(make_latin(), CFG, GROUPS)
    notes = compare.improvement_notes(nk, {"Ref Mono": ref})
    assert any("Ref Mono와 같습니다" in n for n in notes)  # same Latin outlines
    assert any("기호" in n and "①" in n for n in notes)  # Korean symbols missing
    assert sum("겹침" in n for n in notes) == 1  # A/I identical in two groups, reported once
