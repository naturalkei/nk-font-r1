"""Whole-face [style], pixel-grid [pixel] knobs, preset validation and the harmony QA."""

from __future__ import annotations

import math
import tomllib
from collections import Counter

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from nkfont import config, presetqa
from nkfont.pixelstyle import PixelParams, apply_pixel, outline, rasterize, transform
from nkfont.studio import presets
from nkfont.style import StyleParams, apply_style

# ---- synthetic fonts ---------------------------------------------------------------------------


def _rects(rects, skew: float = 0.0):
    """A TrueType glyph from (x0, y0, x1, y1) boxes, optionally skewed (degrees, right)."""
    k = math.tan(math.radians(skew))
    pen = TTGlyphPen(None)
    for x0, y0, x1, y1 in rects:
        pts = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
        pen.moveTo((round(pts[0][0] + k * pts[0][1]), pts[0][1]))
        for x, y in pts[1:]:
            pen.lineTo((round(x + k * y), y))
        pen.closePath()
    return pen.glyph()


def make_text_font(hangul_stem: int = 90, hangul_skew: float = 0.0):
    """Proportional font: Latin H x l (stem 90) and Hangul ㅣ ㅡ 한 drawn from boxes."""
    shapes = {
        "H": ([(50, 0, 140, 700), (410, 0, 500, 700), (140, 320, 410, 390)], 550, 0.0),
        "x": ([(50, 0, 450, 500)], 500, 0.0),
        "l": ([(100, 0, 190, 740)], 290, 0.0),
        "zero": ([(50, 0, 500, 700)], 550, 0.0),
        "uni3163": ([(400, -40, 400 + hangul_stem, 800)], 900, hangul_skew),  # ㅣ
        "uni3161": ([(80, 330, 820, 400)], 900, hangul_skew),  # ㅡ
        "uniD55C": (  # 한
            [(100, 600, 800, 670), (150, -40, 150 + hangul_stem, 560), (500, 300, 800, 370)],
            900,
            hangul_skew,
        ),
    }
    cmap = {0x48: "H", 0x78: "x", 0x6C: "l", 0x30: "zero"}
    cmap.update({0x3163: "uni3163", 0x3161: "uni3161", 0xD55C: "uniD55C"})
    names = [".notdef", *shapes]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    glyphs.update({n: _rects(r, skew) for n, (r, _, skew) in shapes.items()})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(
        {".notdef": (500, 0), **{n: (adv, 0) for n, (_, adv, _) in shapes.items()}}
    )
    fb.setupHorizontalHeader(ascent=900, descent=-200)
    fb.setupNameTable({"familyName": "Fixture Text", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    font = fb.font
    for n in names:
        font["glyf"][n].recalcBounds(font["glyf"])
    return font


def make_pixel_font():
    """UPM 1024, 64 units a pixel: 'H' 8 px cell and a ㄹ-like Hangul glyph with 1-px gaps."""
    px = 64
    cells = {
        # H: two 2-px stems and a bar
        "H": [(0, 0, 2, 10), (5, 0, 7, 10), (2, 4, 5, 5)],
        # ㄹ-ish: three bars one pixel apart, joined on alternate sides
        "uni3139": [(1, 0, 14, 1), (1, 2, 14, 3), (1, 4, 14, 5), (13, 2, 14, 5), (1, 0, 2, 3)],
    }
    fb = FontBuilder(1024, isTTF=True)
    names = [".notdef", *cells]
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap({0x48: "H", 0x3139: "uni3139"})
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    glyphs.update(
        {
            n: _rects([(a * px, b * px, c * px, d * px) for a, b, c, d in r])
            for n, r in cells.items()
        }
    )
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({".notdef": (512, 0), "H": (512, 0), "uni3139": (1024, 0)})
    fb.setupHorizontalHeader(ascent=768, descent=-256)
    fb.setupNameTable({"familyName": "Fixture Pixel", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    return fb.font


# ---- [pixel] ----------------------------------------------------------------------------------


def _bits(rows: list[str]) -> set[tuple[int, int]]:
    """'#' = ink; the last string is row 0 (the baseline row)."""
    return {
        (c, r) for r, line in enumerate(reversed(rows)) for c, ch in enumerate(line) if ch == "#"
    }


def test_outline_is_the_exact_union_with_truetype_winding():
    ring = _bits(["###", "#.#", "###"])
    outer, hole = outline(ring)
    assert outer == [(0, 0), (0, 3), (3, 3), (3, 0)]  # clockwise, y up
    assert hole == [(1, 1), (2, 1), (2, 2), (1, 2)]  # counter-clockwise
    # Pixels that only touch at a corner stay two contours (no bow-tie).
    assert len(outline(_bits([".#", "#."]))) == 2
    # Round trip through the rasterizer.
    blob = _bits(["##..#", "#####", ".#.##"])
    polys = [[(x * 64, y * 64) for x, y in c] for c in outline(blob)]
    assert rasterize(polys, 64) == blob


def test_bold_and_heavy_never_close_a_one_pixel_gap():
    rieul = _bits(["######", "......", "######", "......", "######"])
    heavy = transform(rieul, PixelParams(heavy=1))
    for r in (1, 3):  # the two gap rows stay white
        assert not any((c, r) in heavy for c in range(6))
    stems = _bits(["#.#", "#.#"])
    assert transform(stems, PixelParams(bold=1)) == stems | {(3, 0), (3, 1)}


def test_heavy_keeps_the_baseline_and_light_keeps_one_pixel_details():
    bar = _bits(["####"])  # a lone bottom bar grows up, never below row 0
    assert min(r for _, r in transform(bar, PixelParams(heavy=1))) == 0
    thin = _bits(["#..##"])
    assert transform(thin, PixelParams(bold=-1)) == _bits(["#..#."])


def test_italic_pivots_on_the_middle_row_and_shadow_drops_right_down():
    col = {(0, r) for r in range(12)}
    it = transform(col, PixelParams(italic=4), pivot=4)
    shift = {r: c for c, r in it}
    assert [shift[r] for r in (0, 3, 4, 7, 8, 11)] == [-1, -1, 0, 0, 1, 1]
    dot = {(0, 5)}
    assert transform(dot, PixelParams(shadow=1)) == {(0, 5), (1, 4)}


def test_pixel_scope_and_hangul_dy():
    p = PixelParams(bold=1, scope="latin", hangul_dy=1)
    assert p.for_glyph(hangul=False) == PixelParams(bold=1)
    assert p.for_glyph(hangul=True) == PixelParams(dy=1)
    with pytest.raises(ValueError):
        PixelParams.from_dict({"bold": 2})
    with pytest.raises(ValueError):
        PixelParams.from_dict({"scope": "greek"})


def test_apply_pixel_stays_on_grid_and_keeps_advances():
    font = make_pixel_font()
    assert apply_pixel(font, PixelParams(), 64) == 0  # identity: untouched
    n = apply_pixel(font, PixelParams(bold=1, italic=4, shadow=1, hangul_dy=1), 64)
    assert n == 2
    glyf = font["glyf"]
    for name, adv in (("H", 512), ("uni3139", 1024)):
        assert font["hmtx"][name][0] == adv
        coords = glyf[name].getCoordinates(glyf)[0]
        assert all(x % 64 == 0 and y % 64 == 0 for x, y in coords)


# ---- [style] ----------------------------------------------------------------------------------


def test_style_identity_changes_nothing():
    font = make_text_font()
    before = list(font["glyf"]["H"].coordinates)
    assert apply_style(font, StyleParams()) == 0
    assert list(font["glyf"]["H"].coordinates) == before


def test_style_slant_and_tracking_move_latin_and_hangul_together():
    font = make_text_font()
    adv = {n: font["hmtx"][n][0] for n in ("l", "uni3163")}
    apply_style(font, StyleParams(slant=10, tracking=40))
    assert {n: font["hmtx"][n][0] for n in adv} == {n: a + 40 for n, a in adv.items()}
    m = presetqa.measure(font, "text")
    assert abs(m["slant"]) < 0.5  # both lean 10°, so the difference stays ~0


def test_style_wobble_is_deterministic_per_seed():
    def coords(seed):
        f = make_text_font()
        apply_style(f, StyleParams(bounce=30, tilt=4, seed=seed))
        return list(f["glyf"]["uniD55C"].coordinates)

    assert coords(1) == coords(1)
    assert coords(1) != coords(2)
    with pytest.raises(ValueError):
        StyleParams.from_dict({"wobble": 3})


# ---- harmony measurements -------------------------------------------------------------------


def test_measure_reports_size_weight_and_lean():
    m = presetqa.measure(make_text_font(), "text")
    assert m["height"] == pytest.approx(710 / 700, abs=0.01)  # 한 -40..670 vs H 0..700
    assert m["slant"] == 0
    heavy = presetqa.measure(make_text_font(hangul_stem=130), "text")
    assert heavy["weight"] > m["weight"]


def test_hangul_only_slant_fails_the_band():
    m = presetqa.measure(make_text_font(hangul_skew=8), "text")
    assert m["slant"] == pytest.approx(8, abs=0.6)
    checks = presetqa.evaluate(m, {"slant": [-1.5, 1.5]})
    assert not checks[0].ok


def test_pixel_gaps_catch_a_closed_gap():
    base = make_pixel_font()
    same = make_pixel_font()
    assert presetqa.pixel_gaps(base, same, 64, ("H", "ㄹ")) == 1.0
    blob = make_pixel_font()
    glyf = blob["glyf"]
    glyf["uni3139"] = _rects([(64, 0, 14 * 64, 5 * 64)])  # gaps filled in
    assert presetqa.pixel_gaps(base, blob, 64, ("H", "ㄹ")) < 0.5


def test_bands_merge_kind_and_family_tables_and_saved_presets_do_not_gate():
    checks = presetqa.evaluate(
        {"stem": 1.3, "height": None}, {"stem": [0.8, 1.2], "height": [1, 2]}
    )
    assert [c.ok for c in checks] == [False, True]  # unmeasurable values are reported only
    bad = presetqa.Result({"id": "saved:x"}, {}, [presetqa.Check("a", 2, 0, 1)])
    worse = presetqa.Result({"id": "p"}, {}, [presetqa.Check("a", 2, 0, 1)])
    assert presetqa.gating([bad, worse]) == [worse]


# ---- preset files -------------------------------------------------------------------------------

FAMILIES = {
    "m": 'status = "active"\nfamily = "M"\n[hangul]\nscale = 1.0\n[[weight]]\nname = "Regular"\n',
    "t": 'status = "active"\nkind = "text"\nfamily = "T"\n[[weight]]\nname = "Regular"\n',
    "p": 'status = "active"\nkind = "pixel"\nfamily = "P"\n[[weight]]\nname = "Regular"\n',
}


@pytest.fixture
def root(tmp_path):
    d = tmp_path / "config" / "families"
    d.mkdir(parents=True)
    for k, v in FAMILIES.items():
        (d / f"{k}.toml").write_text(v)
    return tmp_path


def test_style_and_pixel_tables_round_trip(root):
    s = presets.save(
        {"label": "pen", "family": "t", "style": {"grade": -80, "slant": 6.5, "seed": 3.0}}, root
    )
    p = presets.save(
        {"label": "px", "family": "p", "pixel": {"bold": -1, "italic": 4, "scope": "all"}}, root
    )
    data = tomllib.loads((root / "config" / "presets" / "pen.toml").read_text())
    assert data["style"] == {"slant": 6.5, "grade": -80, "seed": 3}
    data = tomllib.loads((root / "config" / "presets" / "px.toml").read_text())
    assert data["pixel"] == {"bold": -1, "italic": 4, "scope": "all"}
    loaded = {x["id"]: x for x in presets.load(root)}
    assert loaded["pen"] == s and loaded["px"] == p


@pytest.mark.parametrize(
    "bad",
    [
        {"label": "a", "family": "m", "style": {"slant": 5}},  # terminal family: no [style]
        {"label": "a", "family": "t", "pixel": {"bold": 1}},  # only NK Pixel has [pixel]
        {"label": "a", "family": "t", "style": {"bounce": 500}},
        {"label": "a", "family": "t", "style": {"wobble": 1}},
        {"label": "a", "family": "p", "pixel": {"bold": 2}},
        {"label": "a", "family": "p", "pixel": {"scope": "greek"}},
    ],
)
def test_style_and_pixel_validation(root, bad):
    with pytest.raises(ValueError):
        presets.validate(bad, root)


def test_repo_presets_are_twenty_distinct_per_reference_family():
    loaded = [p for p in presets.load() if not p.get("readonly")]
    assert not [p for p in loaded if "error" in p]
    count = Counter(p["family"] for p in loaded)
    assert {f: count[f] for f in ("mono", "pixel", "comics")} == {
        "mono": 20,
        "pixel": 20,
        "comics": 20,
    }
    seen = set()
    for p in loaded:  # no two presets of a family share every value
        key = repr(
            (
                p["family"],
                p["weight"],
                p.get("hangul"),
                p.get("style"),
                p.get("pixel"),
                p["features"],
            )
        )
        assert key not in seen, p["id"]
        seen.add(key)


@pytest.mark.slow
def test_every_repo_preset_is_inside_its_harmony_bands():
    srcs = config.sources()
    if not all(s.path.exists() for s in srcs.values()):
        pytest.skip("upstream fonts not downloaded (run `nkfont fetch`)")
    results = presetqa.run()
    bad = presetqa.gating(results)
    assert not bad, presetqa.format_table(bad)
