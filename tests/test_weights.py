"""Thin..ExtraBold: weight names, synthesis, Hangul/Latin harmony solver and ladder QA."""

from __future__ import annotations

import pytest
from fontTools.pens.ttGlyphPen import TTGlyphPen

from nkfont import weights
from nkfont.merge import embolden
from nkfont.names import set_names
from tests.conftest import _box, make_latin


def _glyph(x0, y0, x1, y1):
    pen = TTGlyphPen(None)
    _box(pen, x0, y0, x1, y1)
    return pen.glyph()


@pytest.mark.parametrize(
    "style, cls, bold",
    [
        ("Thin", 100, False),
        ("ExtraLight", 200, False),
        ("Light", 300, False),
        ("Regular", 400, False),
        ("Medium", 500, False),
        ("SemiBold", 600, False),
        ("Bold", 700, True),
        ("ExtraBold", 800, False),
    ],
)
def test_weight_names_and_bold_bits(style, cls, bold):
    # Regression: "Bold" in "SemiBold"/"ExtraBold" used to set the bold bits, so apps linked
    # SemiBold as the bold of its own legacy family.
    font = make_latin()
    set_names(font, "NK Test", style, "0.1.0", cls)
    assert font["OS/2"].usWeightClass == cls
    assert bool(font["OS/2"].fsSelection & 0x20) is bold
    assert bool(font["head"].macStyle & 1) is bold
    assert weights.check_weight_names(font) == []
    if style not in ("Regular", "Bold"):
        assert font["name"].getDebugName(1) == f"NK Test {style}"
        assert font["name"].getDebugName(2) == "Regular"


def test_weight_names_check_catches_wrong_class():
    font = make_latin()
    set_names(font, "NK Test", "SemiBold", "0.1.0", 500)
    assert any("usWeightClass 500" in p for p in weights.check_weight_names(font))


def test_weight_classes_cover_thin_to_extrabold():
    assert weights.STANDARD == (
        "Thin",
        "ExtraLight",
        "Light",
        "Regular",
        "Medium",
        "SemiBold",
        "Bold",
        "ExtraBold",
    )
    assert [weights.WEIGHT_CLASSES[w] for w in weights.STANDARD] == list(range(100, 900, 100))


def test_embolden_contrast_keeps_horizontal_strokes():
    g = _glyph(100, 0, 300, 700)
    embolden(g, 40, contrast=0.0)
    xs, ys = [x for x, _ in g.coordinates], [y for _, y in g.coordinates]
    assert (min(xs), max(xs)) == (80, 320)  # vertical stem 40 units heavier
    assert (min(ys), max(ys)) == (0, 700)  # horizontal extent untouched


def test_embolden_amount_y_moves_bars_without_stems():
    g = _glyph(100, 0, 300, 700)
    embolden(g, 0, amount_y=20)
    xs, ys = [x for x, _ in g.coordinates], [y for _, y in g.coordinates]
    assert (min(xs), max(xs)) == (100, 300)
    assert (min(ys), max(ys)) == (-10, 710)


def test_embolden_default_contrast_is_identity_with_old_behaviour():
    a, b = _glyph(100, 0, 300, 700), _glyph(100, 0, 300, 700)
    embolden(a, 30)
    embolden(b, 30, contrast=1.0)
    assert list(a.coordinates) == list(b.coordinates)


def test_synthesize_keeps_advances_and_drops_hinting():
    font = make_latin()
    font["fpgm"] = __import__("fontTools.ttLib", fromlist=["newTable"]).newTable("fpgm")
    before = dict(font["hmtx"].metrics)
    stem = weights.stroke(font, "I")
    weights.synthesize(font, -40)
    assert weights.stroke(font, "I") == pytest.approx(stem - 40)
    assert {k: v[0] for k, v in font["hmtx"].metrics.items()} == {
        k: v[0] for k, v in before.items()
    }
    assert font["hmtx"]["I"][1] == 120  # lsb follows the thinner outline
    assert "fpgm" not in font


def test_pixel_bold_stays_on_the_grid_and_inside_the_cell():
    font = make_latin()  # boxes 100..500 in a 600 cell: on a 50-unit "pixel" grid
    font["glyf"]["M"] = _glyph(100, 0, 600, 730)  # touches the right edge of its cell
    font["glyf"]["A"] = _glyph(0, 0, 600, 730)  # fills the whole cell
    kept = weights.pixel_bold(font, 50)
    xs = [x for x, _ in font["glyf"]["I"].coordinates]
    ys = [y for _, y in font["glyf"]["I"].coordinates]
    assert (min(xs), max(xs)) == (100, 550)  # left edge kept, one pixel wider to the right
    assert (min(ys), max(ys)) == (0, 730)
    m = [x for x, _ in font["glyf"]["M"].coordinates]
    assert (min(m), max(m)) == (50, 600)  # grew to the left instead of into the next cell
    assert kept == 1  # "A" fills its cell: left as drawn


def _fam(**cfg):
    return {
        "hangul": {"scale": 1.0},
        "weights": {"match": "stem+bar", **cfg},
        "weight": [
            {"name": "Regular", "latin": "L4", "hangul": "H4"},
            {"name": "Thin", "latin": "L1", "hangul": "H4"},
            {"name": "Bold", "latin": "L7", "hangul": "H7"},
        ],
    }


@pytest.fixture
def fake_strokes(monkeypatch):
    # (stem, bar) per source id, at UPM 1000.
    table = {
        "L4": (80, 70),
        "L1": (20, 18),
        "L7": (150, 130),
        "H4": (88, 70),
        "H7": (150, 120),
    }

    class Src:
        def __init__(self, sid):
            self.path = sid

    monkeypatch.setattr(
        weights,
        "source_stroke",
        lambda path, ch, axis="h": table[path][0 if axis == "h" else 1],
    )
    return {k: Src(k) for k in table}


def test_reference_weight_is_untouched(fake_strokes):
    fam = _fam()
    assert weights.hangul_weight(fam, fam["weight"][0], fake_strokes) == (0.0, None)


def test_solver_keeps_regular_stem_and_bar_ratios(fake_strokes):
    fam = _fam(min_keep=0.1)
    for w in fam["weight"][1:]:
        grade, grade_y = weights.hangul_weight(fam, w, fake_strokes)
        lat_stem, lat_bar = (20, 18) if w["name"] == "Thin" else (150, 130)
        h_stem, h_bar = (88, 70) if w["name"] == "Thin" else (150, 120)
        # Regular: Hangul/Latin stem 88/80 = 1.1, bar 70/70 = 1.0.
        assert (h_stem + grade) / lat_stem == pytest.approx(1.1, abs=0.01)
        assert (h_bar + grade_y) / lat_bar == pytest.approx(1.0, abs=0.01)


def test_solver_never_erases_strokes(fake_strokes):
    fam = _fam()  # default min_keep 0.35: Thin may lose at most 65% of the Hangul stem
    grade, _ = weights.hangul_weight(fam, fam["weight"][1], fake_strokes)
    assert grade == pytest.approx(-0.65 * 88, abs=0.1)


def test_explicit_hangul_grade_wins(fake_strokes):
    fam = _fam()
    w = {**fam["weight"][1], "hangul_grade": 5}
    assert weights.hangul_weight(fam, w, fake_strokes)[0] == 5.0


def test_no_weights_table_means_no_change(fake_strokes):
    fam = _fam()
    del fam["weights"]
    for w in fam["weight"]:
        assert weights.hangul_weight(fam, w, fake_strokes) == (0.0, None)


def _row(ls, lb, hs, hb):
    return {
        "latin_stem": ls,
        "latin_bar": lb,
        "hangul_stem": hs,
        "hangul_bar": hb,
        "stem_ratio": round(hs / ls, 3),
        "bar_ratio": round(hb / lb, 3),
    }


def test_ladder_passes_a_harmonious_family():
    rows = [
        ("Thin", 100, _row(20, 18, 22, 18)),
        ("Regular", 400, _row(80, 70, 88, 70)),
        ("Bold", 700, _row(150, 130, 165, 131)),
    ]
    assert weights.check_weight_ladder(rows) == []


def test_ladder_flags_hangul_drift_and_inversions():
    rows = [
        ("Thin", 100, _row(20, 18, 40, 18)),  # Hangul twice as heavy as its Latin
        ("Regular", 400, _row(80, 70, 88, 70)),
        ("SemiBold", 600, _row(120, 100, 130, 100)),
        ("Bold", 700, _row(150, 130, 125, 131)),  # Hangul lighter than SemiBold's
    ]
    problems = weights.check_weight_ladder(rows)
    assert any(p.startswith("stem_ratio: Thin") for p in problems)
    assert any(p.startswith("hangul_stem: Bold") for p in problems)
    assert any(p.startswith("stem_ratio: Bold") for p in problems)


def test_default_weight_is_regular_whatever_the_order():
    fam = {
        "weight": [
            {"name": "Thin", "weight_class": 100},
            {"name": "Regular", "weight_class": 400},
        ]
    }
    assert weights.default_weight(fam) == "Regular"
    assert [w["name"] for w in weights.sorted_weights(fam)] == ["Thin", "Regular"]


def test_split_offset_keeps_the_lighter_axis_geometric():
    assert weights.split_offset(-40, -12) == (-12, -28, 0)
    assert weights.split_offset(20, 30) == (20, 0, 10)
    assert weights.split_offset(14, -5) == (0.0, 14, -5)  # opposite signs: point moves only


def test_offset_outline_thins_a_box_evenly():
    import pathops

    path = pathops.Path()
    _box(path.getPen(), 100, 0, 500, 700)
    out = weights.offset_outline(path, -40)
    assert tuple(round(v) for v in out.bounds) == (120, 20, 480, 680)


def test_synthesis_does_not_split_overlapping_parts():
    # Regression: two overlapping strokes in one glyph (like Bagel Fat One's jamo joins) were
    # thinned separately and pulled apart; merged first, they stay one shape.
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    font = make_latin()
    pen = TTGlyphPen(None)
    _box(pen, 100, 0, 300, 700)  # stem
    _box(pen, 250, 300, 550, 400)  # bar overlapping the stem
    font["glyf"]["A"] = pen.glyph()
    weights.synthesize(font, -40)
    g = font["glyf"]["A"]
    assert g.numberOfContours == 1


def test_ladder_skips_independent_pairings():
    rows = [
        ("Regular", 400, _row(80, 70, 88, 70)),
        ("Black", 900, _row(300, 300, 280, 250)),
    ]
    assert weights.check_weight_ladder(rows) != []
    assert weights.check_weight_ladder(rows, independent=["Black"]) == []


def test_off_by_one_wide_advance_is_snapped_to_the_grid():
    # Regression: JetBrains Mono Thin/ExtraLight ship U+FF5D at 599 units, which broke the
    # 0/600/1200 rule in NK Mono Thin and ExtraLight.
    from nkfont.checks import check_widths
    from nkfont.flags import fit_terminal_widths

    font = make_latin()
    font["hmtx"]["uniFF5B"] = (599, 100)
    fit_terminal_widths(font, 600)
    assert font["hmtx"]["uniFF5B"][0] == 1200
    assert not [p for p in check_widths(font) if "FF5B" in p]


def test_preset_grade_stays_a_point_move_beside_weight_synthesis():
    # Regression: a [hangul]/preset `grade` went through the weight-synthesis outline merge, so
    # contours were re-ordered and the preset harmony QA reported mono-bold-* presets as broken.
    from nkfont.merge import HangulParams, merge_hangul
    from tests.conftest import make_hangul

    def build(**kw):
        font = make_latin()
        merge_hangul(font, make_hangul(), [(0xAC00, 0xAC00)], HangulParams(**kw))
        return font["glyf"][font.getBestCmap()[0xAC00]]

    plain, graded = build(), build(grade=-10)
    assert plain.numberOfContours == graded.numberOfContours
    embolden(plain, -10)  # exactly the old point move, nothing re-drawn
    assert list(plain.coordinates) == list(graded.coordinates)
    synth = build(weight_grade=-10)
    assert synth.numberOfContours >= 1
