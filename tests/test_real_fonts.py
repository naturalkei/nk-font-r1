"""End-to-end build with the pinned upstream fonts. Run `nkfont fetch` first."""

import pytest
from fontTools.ttLib import TTFont

from nkfont import config
from nkfont.build import build_master
from nkfont.checks import run_all

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def mono():
    srcs = config.sources()
    if not all(s.path.exists() for s in srcs.values()):
        pytest.skip("upstream fonts not downloaded (run `nkfont fetch`)")
    fam = config.family("mono")
    weight = next(w for w in fam["weight"] if w["name"] == "Regular")
    return build_master(fam, weight), TTFont(srcs[weight["latin"]].path)


def test_mono_regular_passes_all_checks(mono):
    font, base = mono
    result = run_all(font, base)
    assert set(result) == {"widths", "overflow", "metrics", "names", "features"}
    assert {k: v for k, v in result.items() if v} == {}


def test_mono_regular_has_all_hangul_syllables(mono):
    cmap = mono[0].getBestCmap()
    assert all(cp in cmap for cp in range(0xAC00, 0xD7A4))


@pytest.mark.parametrize("fid", ["sans", "novel", "comics"])
def test_new_families_pass_their_checks(fid):
    srcs = config.sources()
    if not all(s.path.exists() for s in srcs.values()):
        pytest.skip("upstream fonts not downloaded (run `nkfont fetch`)")
    fam = config.family(fid)
    weight = fam["weight"][0]
    font = build_master(fam, weight)
    result = run_all(font, TTFont(srcs[weight["latin"]].path), kind=fam.get("kind", "merge"))
    assert {k: v for k, v in result.items() if v} == {}
    assert all(cp in font.getBestCmap() for cp in range(0xAC00, 0xD7A4))
