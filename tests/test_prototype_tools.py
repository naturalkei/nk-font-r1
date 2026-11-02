"""Studio config write-back, preview measurement, pixel unmapping and site glyph index."""

from nkfont.flags import unmap_width_conflicts
from nkfont.site import glyph_index
from nkfont.studio.core import measure, update_hangul_config

TOML = """# NK Test
status = "active"
family = "NK Test"

[hangul]
# Uniform scale.
scale = 0.96   # keep this comment
dy = -10
center = "advance"

[[weight]]
name = "Regular"
"""


def _family_dir(tmp_path):
    d = tmp_path / "config" / "families"
    d.mkdir(parents=True)
    (d / "t.toml").write_text(TOML)
    return d / "t.toml"


def test_update_hangul_config_rewrites_values_and_keeps_comments(tmp_path):
    path = _family_dir(tmp_path)
    update_hangul_config("t", {"scale": 0.9425, "dy": -23.6, "center": "bbox"}, root=tmp_path)
    text = path.read_text()
    assert "scale = 0.943   # keep this comment" in text
    assert "dy = -24" in text
    assert 'center = "bbox"' in text
    assert "# Uniform scale." in text and 'name = "Regular"' in text


def test_update_hangul_config_rejects_bad_center(tmp_path):
    _family_dir(tmp_path)
    try:
        update_hangul_config("t", {"center": "middle"}, root=tmp_path)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_measure_reports_latin_guides(latin):
    m = measure(latin)
    assert (m["upm"], m["ascent"], m["descent"], m["half"]) == (1000, 1020, -300, 600)


def test_unmap_width_conflicts_drops_overwide_and_ranges(latin):
    # Fixture U+FF5B is drawn one cell (600) though terminals give it two: a conflict.
    dropped = unmap_width_conflicts(latin, 600, ranges=[(0x49, 0x49)])
    cmap = latin.getBestCmap()
    assert 0xFF5B in dropped and 0xFF5B not in cmap
    assert 0x49 not in cmap and 0x41 in cmap  # range unmapped, others kept
    assert "uniFF5B" in latin.getGlyphOrder()  # glyph kept for GSUB


def test_glyph_index_groups_runs_by_cell_count(latin):
    idx = glyph_index(latin)
    assert idx["half"] == 600
    assert [0x41, 0x41, 1] in idx["runs"]


def test_studio_static_page_is_packaged():
    from importlib import resources

    page = resources.files("nkfont.studio").joinpath("static", "index.html").read_text()
    assert "/api/preview" in page
