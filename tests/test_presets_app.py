"""Style presets (config/presets/*.toml), their HTTP API and the desktop app launcher."""

from __future__ import annotations

import json
import plistlib
import threading
import tomllib
import urllib.error
import urllib.request
from importlib import resources

import pytest

from nkfont.studio import presets
from nkfont.studio.app import mac_app_bundle
from nkfont.studio.server import site_file

FAMILY = """status = "active"
family = "NK Test"
file_prefix = "NKTest"

[hangul]
scale = 0.96
dy = -10
center = "advance"

[[weight]]
name = "Regular"

[[weight]]
name = "Bold"
"""


@pytest.fixture
def root(tmp_path):
    d = tmp_path / "config" / "families"
    d.mkdir(parents=True)
    (d / "t.toml").write_text(FAMILY)
    (d / "off.toml").write_text(FAMILY.replace('"active"', '"planned"'))
    return tmp_path


def test_saved_family_presets_are_read_only_and_listed_first(root):
    out = presets.load(root)
    assert [p["id"] for p in out] == ["saved:t"]  # planned families are left out
    assert out[0]["readonly"] and out[0]["hangul"] == {
        "scale": 0.96,
        "dy": -10,
        "center": "advance",
    }


def test_save_round_trips_through_toml(root):
    p = presets.save(
        {
            "label": "Mono Airy",
            "family": "t",
            "weight": "Bold",
            "hangul": {"scale": 1.04, "dy": 12.6, "center": "bbox", "grade": None},
            "features": ["zero", "ss01", "zero"],
            "note": 'quote " and \\ back',
        },
        root,
    )
    assert p["id"] == "mono-airy"
    path = root / "config" / "presets" / "mono-airy.toml"
    data = tomllib.loads(path.read_text())
    assert data["hangul"] == {"scale": 1.04, "dy": 13, "center": "bbox"}
    assert data["features"] == ["zero", "ss01"] and data["note"] == 'quote " and \\ back'
    loaded = next(x for x in presets.load(root) if x["id"] == "mono-airy")
    assert loaded == p


def test_new_preset_never_overwrites_and_hangul_label_gets_an_id(root):
    a = presets.save({"label": "같은 이름", "family": "t"}, root)
    b = presets.save({"label": "같은 이름", "family": "t"}, root)
    assert a["id"] == "preset-1" and b["id"] == "preset-2"
    c = presets.save({"label": "x", "family": "t"}, root)
    d = presets.save({"label": "x", "family": "t"}, root)
    assert (c["id"], d["id"]) == ("x", "x-1")
    # An explicit id is an edit: it replaces the file.
    presets.save({"id": "x", "label": "x edited", "family": "t"}, root)
    assert "x edited" in (root / "config" / "presets" / "x.toml").read_text()


@pytest.mark.parametrize(
    "bad",
    [
        {"label": "", "family": "t"},
        {"label": "a", "family": "nope"},
        {"label": "a", "family": "t", "weight": "Thin"},
        {"label": "a", "family": "t", "hangul": {"scale": 9}},
        {"label": "a", "family": "t", "hangul": {"scale": "nan"}},
        {"label": "a", "family": "t", "hangul": {"center": "middle"}},
        {"label": "a", "family": "t", "hangul": {"fit": 0.9}},
        {"label": "a", "family": "t", "features": ["ss01;x"]},
        {"id": "../evil", "label": "a", "family": "t"},
        {"id": "saved:t", "label": "a", "family": "t"},
    ],
)
def test_validate_rejects_bad_presets(root, bad):
    with pytest.raises(ValueError):
        presets.validate(bad, root)


def test_broken_preset_file_is_reported_not_fatal(root):
    d = root / "config" / "presets"
    d.mkdir(parents=True)
    (d / "old.toml").write_text('label = "old"\nfamily = "gone"\n')
    bad = next(p for p in presets.load(root) if p["id"] == "old")
    assert "unknown family" in bad["error"]


def test_delete_only_takes_plain_ids(root):
    presets.save({"label": "gone soon", "family": "t"}, root)
    presets.delete("gone-soon", root)
    assert [p["id"] for p in presets.load(root)] == ["saved:t"]
    with pytest.raises(ValueError):
        presets.delete("../../pyproject", root)


def test_site_file_stays_inside_build_site(tmp_path):
    site = tmp_path / "build" / "site"
    site.mkdir(parents=True)
    (site / "index.html").write_text("ok")
    (tmp_path / "secret.txt").write_text("no")
    assert site_file(tmp_path, "") == site / "index.html"
    assert site_file(tmp_path, "index.html") == site / "index.html"
    assert site_file(tmp_path, "../../secret.txt") is None
    assert site_file(tmp_path, "%2e%2e/%2e%2e/secret.txt") is None
    assert site_file(tmp_path, "missing.css") is None


def test_presets_api_over_http(root):
    from http.server import ThreadingHTTPServer

    from nkfont.studio.core import Studio
    from nkfont.studio.server import make_handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Studio(root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        try:
            with urllib.request.urlopen(urllib.request.Request(base + path, data=data)) as r:
                return r.read()
        except urllib.error.HTTPError as exc:  # errors come back as JSON with status 400
            assert exc.code == 400
            return exc.read()

    try:
        assert b"/api/presets/save" in call("/presets")
        assert b"NK Specimen" in call("/specimen")
        saved = json.loads(call("/api/presets/save", {"label": "Http", "family": "t"}))
        assert saved["preset"]["id"] == "http"
        listing = json.loads(call("/api/presets"))
        assert [p["id"] for p in listing["presets"]] == ["saved:t", "http"]
        assert set(listing["samples"]) == {"hangul", "latin", "code", "terminal"}
        err = json.loads(call("/api/presets/save", {"label": "x", "family": "zz"}))
        assert "unknown family" in err["error"]
        assert json.loads(call("/api/presets/delete", {"id": "http"})) == {"deleted": "http"}
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_mac_app_bundle_runs_nkfont_app(tmp_path):
    app = mac_app_bundle(tmp_path, python="/venv/bin/python", root=tmp_path / "repo")
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleExecutable"] == "nk-studio" and info["CFBundlePackageType"] == "APPL"
    launcher = app / "Contents" / "MacOS" / "nk-studio"
    script = launcher.read_text()
    assert script.startswith("#!/bin/sh") and launcher.stat().st_mode & 0o111
    assert f'cd "{tmp_path / "repo"}"' in script
    assert 'exec "/venv/bin/python" -m nkfont.cli app "$@"' in script


def test_preset_page_is_packaged_and_linked():
    static = resources.files("nkfont.studio").joinpath("static")
    page = static.joinpath("presets.html").read_text()
    assert "/api/presets" in page and "/api/preview" in page
    for other in ("index.html", "lab.html"):
        assert 'href="/presets"' in static.joinpath(other).read_text()
        assert 'href="/specimen"' in static.joinpath(other).read_text()
    spec = static.joinpath("specimen.html").read_text()
    assert "/api/preview" in spec and "/api/presets/save" in spec and 'href="/presets"' in spec


def test_checked_in_presets_are_valid():
    for p in presets.load():
        assert "error" not in p, p
