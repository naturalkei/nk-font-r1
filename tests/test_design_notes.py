"""Design notes (site/design.html): stroke skeletons snap onto real strokes, rings follow their
bowl, outline points match the font, and ratios are matched to the shared phi scale."""

import json

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from nkfont import designnotes as dn
from nkfont.glyphmetrics import glyph_geometry
from nkfont.phi import PHI


def _rect(pen, x0, y0, x1, y1, cw=True):
    pts = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
    if not cw:
        pts = [pts[0], *reversed(pts[1:])]
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()


def _font():
    """'L' = stem 100..180 + bar y 0..60; 'O' = square ring (wall 80) with a dot in its counter;
    'S' = one quadratic contour (two off-curve points in a row -> an implied on-curve point)."""
    names = [".notdef", "L", "O", "S"]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap({0x4C: "L", 0x4F: "O", 0x53: "S", 0x48: "L"})
    glyphs = {}
    pen = TTGlyphPen(None)
    glyphs[".notdef"] = pen.glyph()
    pen = TTGlyphPen(None)
    _rect(pen, 100, 0, 180, 700)
    _rect(pen, 100, 0, 500, 60)
    glyphs["L"] = pen.glyph()
    pen = TTGlyphPen(None)
    _rect(pen, 100, 0, 500, 700)
    _rect(pen, 180, 80, 420, 620, cw=False)  # counter
    _rect(pen, 280, 330, 320, 370)  # dot inside, like a dotted zero
    glyphs["O"] = pen.glyph()
    pen = TTGlyphPen(None)
    pen.moveTo((100, 0))
    pen.qCurveTo((100, 300), (300, 400), (500, 400))
    pen.lineTo((500, 0))
    pen.closePath()
    glyphs["S"] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (600, 100) for n in names})
    fb.setupHorizontalHeader(ascent=1020, descent=-300)
    fb.setupNameTable({"familyName": "Fixture Notes", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=1020, sTypoDescender=-300, usWinAscent=1020, usWinDescent=300)
    fb.setupPost()
    return fb.font


@pytest.fixture
def font():
    return _font()


def _geo(font, name):
    return glyph_geometry(font, name)


def test_corner_stroke_snaps_to_stem_and_bar_centres(font):
    geo = _geo(font, "L")
    # Skeleton drawn sloppily off-centre: down the stem, then along the bar.
    st = {"pts": [[0.05, 0.95], [0.05, 0.12], [0.9, 0.12]]}
    out = dn.place_stroke(geo.polygons, st, geo.bounds, radius=150)
    (x0, y0), (x1, y1), (x2, y2) = out["pts"]
    assert x0 == x1 == pytest.approx(140)  # stem centre, kept plumb
    assert y1 == y2 == pytest.approx(30)  # bar centre, kept level
    assert y0 == pytest.approx(700 - 40)  # free end stops half a stroke inside the ink
    assert x2 == pytest.approx(500 - 30)
    assert out["w"] == pytest.approx(80)  # thickness of the body: the longest segment (stem)
    assert out["misses"] == 0


def test_thickness_ignores_junctions():
    stem = [(100, 0), (100, 700), (180, 700), (180, 0)]
    bar = [(100, 0), (100, 60), (500, 60), (500, 0)]
    poly = [stem, bar]
    assert dn.thickness(poly, (140, 0), (140, 700)) == pytest.approx(80)
    assert dn.thickness(poly, (100, 30), (500, 30)) == pytest.approx(60)


def test_ring_follows_bowl_and_skips_inner_dot(font):
    geo = _geo(font, "O")
    out = dn.place_stroke(geo.polygons, {"ring": [0.5, 0.5, 0.4, 0.45]}, geo.bounds, radius=150)
    assert out["curve"] and out["misses"] == 0
    top = out["pts"][0]
    assert top == [pytest.approx(300), pytest.approx(660)]  # centre of the top wall
    assert out["pts"][0] == out["pts"][-1]  # closed, written from the top
    assert out["pts"][6][0] < 300  # counter-clockwise: a quarter turn later it is on the left
    assert out["w"] == pytest.approx(80, abs=3)


def test_far_off_point_is_a_miss_and_misses_drop_stroke_order(font):
    geo = _geo(font, "L")
    out = dn.place_stroke(geo.polygons, {"pts": [[0.9, 0.9], [0.7, 0.6]]}, geo.bounds, radius=20)
    assert out["misses"] == 2
    cfg = {
        "page": {"max_misses": 1, "snap_radius": 0.02},
        "glyph": [{"ch": "L", "strokes": [{"pts": [[0.9, 0.9], [0.7, 0.6]]}]}],
    }
    notes = dn.family_notes(font, cfg)
    assert notes["glyphs"][0]["strokes"] == []


def test_outline_points_keep_on_off_flags(font):
    (contour,) = dn.outline_points(font, "S")
    assert [p[2] for p in contour] == [True, False, False, True, True]
    assert contour[0][:2] == [100, 0]
    rings = dn.outline_points(font, "O")
    assert len(rings) == 3 and all(len(c) == 4 for c in rings)  # closing point not repeated


def test_phi_step_matches_shared_scale():
    st = dn.phi_step(PHI ** (2 / 6))
    assert st["step"] == 2 and st["on"] and abs(st["dev"]) < 1e-6
    assert dn.phi_step(1.12)["step"] == 1 and not dn.phi_step(1.12)["on"]
    assert dn.phi_step(0) is None
    assert dn._phi_label(6) == "φ" and dn._phi_label(3) == "φ^(1/2)" and dn._phi_label(-6) == "φ^-1"


def test_build_design_writes_json(tmp_path, font):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "design.toml").write_text(
        '[page]\nfamilies = ["fx"]\n\n[[glyph]]\nch = "L"\ntitle = "L"\nnote = "n"\n'
        "strokes = [{ pts = [[0.05, 0.95], [0.05, 0.12], [0.9, 0.12]] }]\n\n"
        '[[glyph]]\nch = "?"\n'  # not in the font: skipped
    )
    path = tmp_path / "fx.ttf"
    font.save(path)
    out = tmp_path / "site"
    out.mkdir()
    dn.build_design(out, {"fx": {"family": "Fixture", "path": path}}, root=tmp_path)
    data = json.loads((out / "design.json").read_text())
    (fam,) = data["families"]
    assert fam["curves"] == "quadratic" and fam["guides"]["upm"] == 1000
    (g,) = fam["glyphs"]
    assert g["ch"] == "L" and g["adv"] == 600 and g["box"] == [100, 0, 500, 700]
    assert g["strokes"][0]["n"] == 1 and g["path"].startswith("M")
    assert all(r["phi"] for r in g["ratios"])
