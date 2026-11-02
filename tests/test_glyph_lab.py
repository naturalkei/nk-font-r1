"""Glyph Lab: stroke measurements, Hangul width/slant/grade params, phi rules, GSUB helpers."""

import math
from importlib import resources

import pytest
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.ttGlyphPen import TTGlyphPen

from nkfont import config
from nkfont.glyphmetrics import (
    FlattenPen,
    area,
    glyph_geometry,
    gsub_features,
    harmony,
    hruns,
    measure_glyph,
    single_substitutions,
    slant,
    vruns,
)
from nkfont.merge import HangulParams, embolden, merge_hangul
from nkfont.proportions import (
    PHI,
    evaluate,
    load_rules,
    nearest_step,
    phi_target,
    proportion_metrics,
    snap,
)
from nkfont.studio.core import update_hangul_config


def _square(pen, x0, y0, x1, y1):
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()


def test_scanlines_measure_box_stem_and_bar(latin):
    geo = glyph_geometry(latin, "I")  # fixture box 100..500 x 0..730
    assert hruns(geo.polygons, 300) == [(100, 500)]
    assert vruns(geo.polygons, 300) == [(0, 730)]
    assert area(geo.polygons) == pytest.approx(400 * 730)
    m = measure_glyph(geo, scan_y=[300], scan_x=[300])
    assert (m["advance"], m["lsb"], m["rsb"], m["width"]) == (600, 100, 100, 400)
    assert (m["stem"], m["bar"], m["coverage"]) == (400, 730, 1.0)
    assert m["slant"] is None  # a plain box has no stem axis to read


def test_overlapping_contours_count_once_nonzero_rule():
    pen = FlattenPen()
    _square(pen, 0, 0, 100, 100)
    _square(pen, 50, 0, 150, 100)  # same direction, overlaps by 50
    assert hruns(pen.polygons, 50) == [(0, 150)]


def test_counter_is_a_gap():
    pen = FlattenPen()
    _square(pen, 0, 0, 300, 300)  # outer, clockwise
    pen.moveTo((100, 100))  # inner, counter-clockwise (a hole)
    pen.lineTo((200, 100))
    pen.lineTo((200, 200))
    pen.lineTo((100, 200))
    pen.closePath()
    assert hruns(pen.polygons, 150) == [(0, 100), (200, 300)]
    assert area(pen.polygons) == pytest.approx(300 * 300 - 100 * 100)


def test_slant_of_skewed_stem():
    pen = FlattenPen()
    k = math.tan(math.radians(9))
    pen.moveTo((0, 0))
    pen.lineTo((700 * k, 700))
    pen.lineTo((700 * k + 80, 700))
    pen.lineTo((80, 0))
    pen.closePath()
    assert slant(pen.polygons, 100, 600) == pytest.approx(9, abs=0.05)


def _merged(latin, hangul, **kw):
    merge_hangul(latin, hangul, [(0xAC00, 0xAC00)], HangulParams(**kw))
    return glyph_geometry(latin, "uniAC00")


def test_default_params_keep_previous_outline(hangul):
    from tests.conftest import make_latin

    a = make_latin()
    merge_hangul(a, hangul, [(0xAC00, 0xAC00)], HangulParams())
    b = make_latin()
    merge_hangul(b, hangul, [(0xAC00, 0xAC00)], HangulParams(width=1.0, slant=0.0, grade=0.0))
    assert a["glyf"]["uniAC00"].coordinates == b["glyf"]["uniAC00"].coordinates
    # Fixture source box 50..870 x -80..830 at scale 0.96, centred in the 1200 cell.
    assert glyph_geometry(a, "uniAC00").bounds == (206, -77, 994, 797)


def test_grade_thickens_strokes_without_moving_advance(latin, hangul):
    geo = _merged(latin, hangul, grade=20)
    x0, y0, x1, y1 = geo.bounds
    assert (x1 - x0, y1 - y0) == (788 + 20, 874 + 20)
    assert geo.advance == 1200


def test_embolden_negative_thins():
    pen = TTGlyphPen(None)
    _square(pen, 100, 0, 300, 700)
    g = pen.glyph()
    embolden(g, -40)
    xs = [x for x, _ in g.coordinates]
    assert (min(xs), max(xs)) == (120, 280)


def test_width_and_slant_params(latin, hangul):
    from tests.conftest import make_latin

    narrow = _merged(latin, hangul, width=0.9)
    x0, _, x1, _ = narrow.bounds
    assert x1 - x0 == pytest.approx(788 * 0.9, abs=2)
    assert (x0 + x1) / 2 == pytest.approx(600, abs=1)  # still centred in the cell

    slanted = _merged(make_latin(), hangul, slant=10)
    lo, hi = hruns(slanted.polygons, 0)[0], hruns(slanted.polygons, 600)[0]
    assert (hi[0] - lo[0]) / 600 == pytest.approx(math.tan(math.radians(10)), abs=0.005)
    x0, _, x1, _ = slanted.bounds
    assert (x0 + x1) / 2 == pytest.approx(600, abs=2)


def test_update_hangul_config_writes_new_keys(tmp_path):
    d = tmp_path / "config" / "families"
    d.mkdir(parents=True)
    path = d / "t.toml"
    path.write_text('[hangul]\nscale = 0.96\nwidth = 1.0  # note\n\n[[weight]]\nname = "R"\n')
    update_hangul_config("t", {"width": 0.93, "slant": 9.46, "grade": 4}, root=tmp_path)
    text = path.read_text()
    assert "width = 0.93  # note" in text
    assert "slant = 9.5" in text and "grade = 4.0" in text
    assert text.index("grade") < text.index("[[weight]]")


def test_single_substitutions_and_feature_samples(latin):
    addOpenTypeFeaturesFromString(
        latin, "feature ss01 { sub A by I; } ss01;\nfeature zero { sub zero by M; } zero;"
    )
    assert single_substitutions(latin, ["ss01"]) == {"A": "I"}
    assert single_substitutions(latin, []) == {}
    feats = {f["tag"]: f["sample"] for f in gsub_features(latin)}
    assert feats == {"ss01": "A", "zero": "0"}


def test_harmony_reads_probe_strokes(latin):
    h = harmony(latin, {"latin_stem": "I", "latin_bar": "A", "hangul_stem": "가"})
    assert (h["latin_stem"], h["latin_bar"]) == (400, 730)
    assert h["hangul_stem"] is None and h["grade_delta"] is None


def test_phi_scale_and_nearest_step():
    assert phi_target(6, 6) == pytest.approx(PHI)
    assert phi_target(-6, 6) == pytest.approx(1 / PHI)
    assert nearest_step(1.174, 6) == 2
    assert nearest_step(0.923, 6) == -1


RULES = {
    "scale": {"divisions": 6, "tolerance": 0.01},
    "rule": [
        {
            "id": "h",
            "numerator": "han_height",
            "denominator": "cap_height",
            "step": 2,
            "drives": "scale",
        },
        {
            "id": "s",
            "numerator": "hangul_stem",
            "denominator": "latin_stem",
            "step": -1,
            "drives": "grade",
        },
        {
            "id": "x",
            "numerator": "x_height",
            "denominator": "cap_height",
            "step": -3,
            "locked": True,
            "drives": "scale",
        },
    ],
}


def test_evaluate_and_snap_meet_targets():
    guides = {
        "ascent": 1020,
        "descent": -300,
        "cap_top": 730,
        "x_top": 550,
        "half": 600,
        "han_top": 783,
        "han_bottom": -66,
        "han_left": 200,
        "han_right": 1000,
    }
    harm = {"latin_stem": 90, "hangul_stem": 80}
    res = {r["id"]: r for r in evaluate(proportion_metrics(guides, harm), RULES)}
    assert res["h"]["actual"] == pytest.approx(849 / 730, abs=1e-4) and res["h"]["ok"] is True
    assert res["s"]["ok"] is False
    new = snap({"scale": 0.96, "grade": 0.0}, list(res.values()))
    assert new["scale"] == pytest.approx(0.96 * phi_target(2, 6) / (849 / 730), abs=1e-4)
    assert new["grade"] == pytest.approx(phi_target(-1, 6) * 90 - 80, abs=0.1)
    assert "x" in res and res["x"]["locked"]  # reported but never snapped


def test_shared_proportion_rules_use_known_measurements():
    known = set(
        proportion_metrics(
            {
                "ascent": 1,
                "descent": 0,
                "half": 1,
                "han_top": 1,
                "han_bottom": 0,
                "han_left": 0,
                "han_right": 1,
            },
            {},
        )
    )
    rules = load_rules()
    for r in rules["rule"]:
        assert r["numerator"] in known and r["denominator"] in known, r["id"]
        assert r.get("drives") in (None, "scale", "width", "grade"), r["id"]


def test_lab_config_references_are_pinned():
    from nkfont.studio.lab import lab_config

    srcs = config.sources()
    for ref in lab_config()["reference"]:
        for key, sid in ref.items():
            if key not in ("id", "label"):
                assert sid in srcs, f"{ref['id']}: {sid} not in sources.lock"


def test_lab_page_is_packaged():
    page = resources.files("nkfont.studio").joinpath("static", "lab.html").read_text()
    assert "/api/lab/glyphs" in page and "/api/lab/features" in page


@pytest.mark.slow
def test_lab_measures_real_fonts():
    from nkfont.studio.lab import Lab

    srcs = config.sources()
    if not all(s.path.exists() for s in srcs.values()):
        pytest.skip("upstream fonts not downloaded (run `nkfont fetch`)")
    out = Lab().glyphs(
        {
            "family": "sans",
            "weight": "Regular",
            "chars": "lㅣ",
            "params": {"grade": 10},
            "fonts": ["nk-edit", "ref:jetbrains-mono", "ref:d2coding"],
            "scan_y": [275],
        }
    )
    nk, jb = out["nk-edit"], out["ref:jetbrains-mono"]
    assert nk["glyphs"][0]["stem"] == jb["glyphs"][0]["stem"]  # Latin is untouched
    assert nk["harmony"]["hangul_stem"] == pytest.approx(nk["harmony"]["latin_stem"], abs=2)
    assert out["ref:d2coding"]["guides"]["half"] == 500
    assert {r["id"] for r in nk["proportions"]} >= {"hangul_height", "hangul_stem"}


def test_proportional_family_skips_grid_rules():
    from nkfont.proportions import on_grid

    rules = load_rules()
    m = {
        "cap_height": 730,
        "x_height": 550,
        "line_height": 1320,
        "upm": 1000,
        "han_cell": 1200,
        "han_width": 800,
        "han_height": 850,
    }
    grid = {r["id"]: r for r in evaluate(m, rules, {"family": "NK Mono"})}
    text = {r["id"]: r for r in evaluate(m, rules, {"family": "NK Sans", "grid": False})}
    assert on_grid({"kind": "text"}) is False and on_grid(None) is True
    assert "hangul_cell" in grid and "hangul_cell" not in text
    assert grid["line_height"]["locked"] is True and text["line_height"]["locked"] is False
