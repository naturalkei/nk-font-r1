"""End-to-end build with the pinned upstream fonts. Run `nkfont fetch` first."""

import pytest
from fontTools.ttLib import TTFont

from nkfont import config
from nkfont.build import build_master
from nkfont.checks import run_all

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def sans():
    srcs = config.sources()
    if not all(s.path.exists() for s in srcs.values()):
        pytest.skip("upstream fonts not downloaded (run `nkfont fetch`)")
    fam = config.family("sans")
    weight = next(w for w in fam["weight"] if w["name"] == "Regular")
    return build_master(fam, weight), TTFont(srcs[weight["latin"]].path)


def test_sans_regular_passes_all_checks(sans):
    font, base = sans
    result = run_all(font, base)
    assert set(result) == {"widths", "overflow", "metrics", "names", "features"}
    assert {k: v for k, v in result.items() if v} == {}


def test_sans_regular_has_all_hangul_syllables(sans):
    cmap = sans[0].getBestCmap()
    assert all(cp in cmap for cp in range(0xAC00, 0xD7A4))
