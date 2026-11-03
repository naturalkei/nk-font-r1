"""Glyph Lab core view: a few design targets derive the raw [hangul] params (studio/controls.py)."""

from __future__ import annotations

import json
import shutil
import threading
import urllib.request
from importlib import resources

import pytest

from nkfont import config
from nkfont.studio import controls
from nkfont.studio.core import update_hangul_config

CONTROLS = [
    {
        "id": "height",
        "numerator": "han_height",
        "denominator": "cap_height",
        "drives": "scale",
        "solve": "mul",
        "tolerance": 0.015,
    },
    {
        "id": "aspect",
        "numerator": "han_width",
        "denominator": "han_height",
        "drives": "width",
        "solve": "mul",
        "tolerance": 0.015,
    },
    {
        "id": "stem",
        "numerator": "hangul_stem",
        "denominator": "latin_stem",
        "drives": "grade",
        "solve": "add",
        "tolerance": 0.03,
    },
    {
        "id": "center",
        "numerator": "han_center",
        "denominator": None,
        "drives": "dy",
        "solve": "add",
        "tolerance": 2,
    },
    {"id": "slant", "drives": "slant", "solve": "direct"},
]


def fake_measure(p: dict) -> dict:
    """A toy merge: like the real one, scale moves height, stems and the centre together."""
    h = 900 * p["scale"]
    calls.append(dict(p))
    return {
        "cap_height": 730,
        "latin_stem": 90,
        "han_height": round(h),
        "han_width": round(h * 0.95 * p["width"]),
        "hangul_stem": round(80 * p["scale"] + p["grade"], 1),
        "han_center": round(h / 2 - 120 + p["dy"] - 365, 1),
    }


calls: list[dict] = []
START = {"scale": 1.0, "width": 1.0, "grade": 0.0, "dy": 0.0, "slant": 0.0, "tracking": 0}


def test_solver_meets_every_target_in_a_few_rounds():
    calls.clear()
    t = {"height": 1.174, "aspect": 0.923, "stem": 0.923, "center": 0, "slant": 4}
    out = controls.solve(CONTROLS, t, START, fake_measure)
    m = out["metrics"]
    assert m["han_height"] / m["cap_height"] == pytest.approx(1.174, rel=0.01)
    assert m["han_width"] / m["han_height"] == pytest.approx(0.923, rel=0.01)
    assert m["hangul_stem"] / m["latin_stem"] == pytest.approx(0.923, rel=0.02)
    assert abs(m["han_center"]) <= 1
    assert out["params"]["slant"] == 4  # direct controls are copied, not solved
    assert all(r["met"] for r in out["results"] if r["id"] != "slant")
    assert out["rounds"] <= 6 and len(calls) <= 7


def test_changing_one_target_keeps_the_others():
    """The point of the core view: shrink Hangul, and stem weight and centre stay put."""
    base = controls.solve(CONTROLS, {}, START, fake_measure)["metrics"]
    keep = {
        "aspect": base["han_width"] / base["han_height"],
        "stem": base["hangul_stem"] / base["latin_stem"],
        "center": base["han_center"],
    }
    out = controls.solve(CONTROLS, {"height": 1.1, **keep}, START, fake_measure)
    m = out["metrics"]
    assert out["params"]["scale"] < 1  # smaller Hangul...
    assert out["params"]["grade"] > 0 and out["params"]["dy"] != 0  # ...derived compensation
    assert m["hangul_stem"] / m["latin_stem"] == pytest.approx(keep["stem"], rel=0.03)
    assert m["han_center"] == pytest.approx(keep["center"], abs=1.5)


def test_no_targets_only_measures_and_out_of_range_is_clamped():
    calls.clear()
    out = controls.solve(CONTROLS, {}, START, fake_measure)
    assert len(calls) == 1 and out["params"] == START
    out = controls.solve(CONTROLS, {"height": 5.0}, START, fake_measure)
    assert out["params"]["scale"] == controls.PARAM_BOUNDS["scale"][1]
    assert next(r for r in out["results"] if r["id"] == "height")["met"] is False


def test_controls_take_phi_targets_and_skip_text_only_on_grid():
    grid = controls.load_controls(fam={"family": "NK Mono"})
    text = controls.load_controls(fam={"family": "NK Sans", "kind": "text"})
    gid = [c["id"] for c in grid["controls"]]
    assert gid[:4] == ["height", "aspect", "stem", "center"]
    assert "tracking" not in gid and "tracking" in [c["id"] for c in text["controls"]]
    h = grid["controls"][0]
    assert h["drives"] == "scale" and h["phi"] == pytest.approx(1.174, abs=1e-3)
    assert grid["controls"][3]["phi"] == 0 and grid["controls"][3]["denominator"] is None
    assert grid["latin"] and grid["hangul"]
    for c in grid["controls"] + text["controls"]:  # every control drives a real [hangul] key
        assert c["drives"] in controls.PARAM_BOUNDS and c["min"] < c["max"]
    assert "hangul_cell" in grid["checks"]


def test_centre_metric():
    m = controls.with_centre({}, {"cap_top": 700, "han_top": 800, "han_bottom": -100})
    assert m["han_center"] == 0.0


def test_save_writes_tracking(tmp_path):
    d = tmp_path / "config" / "families"
    d.mkdir(parents=True)
    (d / "t.toml").write_text('family = "T"\n\n[hangul]\nscale = 1.0  # keep\n\n[[weight]]\n')
    update_hangul_config("t", {"tracking": -12.4, "dy": 3}, tmp_path)
    text = (d / "t.toml").read_text()
    assert "tracking = -12\n" in text and "dy = 3\n" in text and "scale = 1.0  # keep" in text


def test_core_and_advanced_pages_are_packaged_and_routed():
    from nkfont.studio.app import PAGES as APP_PAGES
    from nkfont.studio.server import PAGES

    static = resources.files("nkfont.studio").joinpath("static")
    core = static.joinpath("lab.html").read_text()
    adv = static.joinpath("lab-advanced.html").read_text()
    assert "/api/lab/solve" in core and "/api/preview" in core and "/api/presets/save" in core
    assert 'href="/lab/advanced"' in core and 'href="/lab"' in adv
    assert "/api/lab/glyphs" in adv and "/api/lab/features" in adv
    assert PAGES["/lab"] == "lab.html" and PAGES["/lab/advanced"] == "lab-advanced.html"
    assert APP_PAGES["lab-advanced"] == "/lab/advanced"


def test_core_api_over_http(tmp_path):
    from http.server import ThreadingHTTPServer

    from nkfont.studio.core import Studio
    from nkfont.studio.server import make_handler

    for name in ("lab.toml", "proportions.toml"):
        (tmp_path / "config").mkdir(exist_ok=True)
        shutil.copy(config.ROOT / "config" / name, tmp_path / "config" / name)
    shutil.copytree(config.ROOT / "config" / "families", tmp_path / "config" / "families")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Studio(tmp_path)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        req = urllib.request.Request(
            base + "/api/lab/core", json.dumps({"family": "sans"}).encode()
        )
        with urllib.request.urlopen(req) as r:
            out = json.loads(r.read())
        assert "tracking" in [c["id"] for c in out["controls"]]
        with urllib.request.urlopen(base + "/lab/advanced") as r:
            assert b"/api/lab/features" in r.read()
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.mark.slow
def test_solver_on_real_fonts_meets_phi_targets():
    from nkfont.studio.lab import Lab

    if not all(s.path.exists() for s in config.sources().values()):
        pytest.skip("upstream fonts not downloaded (run `nkfont fetch`)")
    lab = Lab()
    phi = {c["id"]: c["phi"] for c in lab.core("mono")["controls"] if c.get("phi") is not None}
    out = lab.solve({"family": "mono", "weight": "Regular", "params": {}, "targets": phi})
    assert all(r["met"] for r in out["results"] if r["id"] in phi), out["results"]
    assert out["rounds"] <= 6
    # The derived params are ordinary [hangul] values a build accepts.
    assert set(out["params"]) >= {"scale", "width", "grade", "dy"}
    assert {c["id"] for c in out["checks"]} >= {"hangul_cell", "line_height"}


# ---- versions: every studio save is numbered and restorable (studio/versions.py) ------------
FAMILY_TOML = """status = "active"
family = "NK Test"

[hangul]
# hand-written comment stays
scale = 1.08
dy = 40
center = "advance"

[[weight]]
name = "Regular"
"""


@pytest.fixture
def vroot(tmp_path):
    d = tmp_path / "config" / "families"
    d.mkdir(parents=True)
    (d / "t.toml").write_text(FAMILY_TOML)
    return tmp_path


def test_first_save_keeps_the_old_values_as_v1(vroot):
    from nkfont.studio import versions

    out = versions.save("t", {"scale": 0.945, "grade": 12, "dy": 85}, "높이 φ", vroot)
    hist = versions.load("t", vroot)
    assert [v["n"] for v in hist] == [1, 2] and out["version"]["n"] == 2
    assert hist[0]["hangul"] == {"scale": 1.08, "dy": 40, "center": "advance"}
    assert hist[1]["hangul"]["grade"] == 12 and hist[1]["note"] == "높이 φ"
    # Saving the same values again adds nothing.
    versions.save("t", {"scale": 0.945}, "", vroot)
    assert len(versions.load("t", vroot)) == 2


def test_restore_writes_back_and_is_recorded(vroot):
    from nkfont import config as cfg
    from nkfont.studio import versions

    versions.save("t", {"scale": 0.945, "grade": 12, "dy": 85}, "", vroot)
    out = versions.restore("t", 1, vroot)
    h = cfg.family("t", vroot)["hangul"]
    # v1 never set grade: it goes back to the identity, so the build matches v1 again.
    assert (h["scale"], h["dy"], h["grade"]) == (1.08, 40, 0.0)
    assert out["version"]["n"] == 3 and out["version"]["restored_from"] == 1
    assert "# hand-written comment stays" in (vroot / "config/families/t.toml").read_text()
    with pytest.raises(ValueError):
        versions.restore("t", 99, vroot)
    with pytest.raises(ValueError):
        versions.load("../t", vroot)


def test_versions_api_over_http(vroot):
    from http.server import ThreadingHTTPServer

    from nkfont.studio.core import Studio
    from nkfont.studio.server import make_handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Studio(vroot)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path, body):
        req = urllib.request.Request(base + path, json.dumps(body).encode())
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())

    try:
        saved = call("/api/save", {"family": "t", "scale": 1.0, "note": "http"})
        assert saved["saved"] == "config/families/t.toml" and saved["version"]["n"] == 2
        assert [v["n"] for v in call("/api/versions", {"family": "t"})["versions"]] == [1, 2]
        assert call("/api/versions/restore", {"family": "t", "n": 1})["version"]["n"] == 3
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_lab_page_has_versions_and_undo():
    page = resources.files("nkfont.studio").joinpath("static", "lab.html").read_text()
    assert "/api/versions" in page and "/api/versions/restore" in page
    assert 'id="undo"' in page and 'id="redo"' in page
