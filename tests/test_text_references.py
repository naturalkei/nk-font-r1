"""NK Sans / Serif / Novel: reference fonts, the `stem` knob and their 20 presets each."""

from __future__ import annotations

from collections import Counter

from fontTools.pens.ttGlyphPen import TTGlyphPen

from nkfont import config
from nkfont.build import hangul_params
from nkfont.merge import embolden
from nkfont.studio import presets


def _box(x0, y0, x1, y1):
    """A clockwise (TrueType outer) rectangle."""
    pen = TTGlyphPen(None)
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()
    return pen.glyph()


def _bounds(g):
    xs = [x for x, _ in g.coordinates]
    ys = [y for _, y in g.coordinates]
    return min(xs), min(ys), max(xs), max(ys)


def test_embolden_xy_thickens_stems_only():
    """`stem` (embolden amount_y = grade) widens vertical strokes and leaves bars alone."""
    g = _box(100, 0, 200, 700)
    embolden(g, 20, 0)
    x0, y0, x1, y1 = _bounds(g)
    assert (x1 - x0, y1 - y0) == (120, 700)


def test_embolden_default_is_uniform_and_zero_is_identity():
    g = _box(100, 0, 200, 700)
    embolden(g, 20)
    x0, y0, x1, y1 = _bounds(g)
    assert (x1 - x0, y1 - y0) == (120, 720)
    h = _box(100, 0, 200, 700)
    before = list(h.coordinates)
    embolden(h, 0, 0)
    assert list(h.coordinates) == before


def test_stem_defaults_to_identity():
    """A family without `stem` builds exactly as before."""
    assert hangul_params({"hangul": {}}).stem == 0.0
    assert hangul_params(config.family("sans")).stem == 0.0
    assert hangul_params(config.family("novel")).stem > 0  # the 0.725 stroke-ratio fix


def test_stem_is_a_preset_knob(tmp_path):
    p = presets.validate({"label": "x", "family": "novel", "hangul": {"stem": 12}})
    assert p["hangul"]["stem"] == 12
    assert "stem = 12" in presets.dumps(p)


def test_text_families_have_twenty_presets_each():
    loaded = [p for p in presets.load() if not p.get("readonly")]
    count = Counter(p["family"] for p in loaded)
    assert {f: count[f] for f in ("sans", "serif", "novel")} == {
        "sans": 20,
        "serif": 20,
        "novel": 20,
    }


def test_reference_sources_are_pinned_with_licenses():
    srcs = config.sources()
    for sid in (
        "pretendard-regular",
        "plex-sans-kr-regular",
        "gothic-a1-regular",
        "inter-regular",
        "nanum-myeongjo-regular",
        "hahmlet-regular",
        "source-serif-4-regular",
        "song-myung",
        "crimson-pro-regular",
        "literata-regular",
        "eb-garamond-regular",
    ):
        s = srcs[sid]
        assert s.license.startswith("OFL-1.1"), sid
        assert len(s.sha256) == 64, sid
    # variable upstreams become one static instance per entry, never two ids on one file
    inst = [s for s in srcs.values() if s.instance]
    assert len({s.path for s in inst}) == len(inst)
