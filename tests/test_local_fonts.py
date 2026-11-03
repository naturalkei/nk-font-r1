"""Local-only reference fonts (config/local_fonts.toml): found on disk, never fetched or shipped."""

import subprocess

import pytest

from nkfont import config, fetch
from nkfont.studio.lab import Lab


@pytest.fixture
def root(tmp_path, monkeypatch, latin):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "lab.toml").write_text("")
    (tmp_path / "sources.lock").write_text("font = []\n")
    (tmp_path / "config" / "local_fonts.toml").write_text(
        """[[font]]
id = "komic"
label = "Komic (local)"
license = "free, redistribution unverified"
weights = { Regular = ["Komic.ttf", "Komic.otf"] }
"""
    )
    monkeypatch.setattr(config, "SYSTEM_FONT_DIRS", ())
    monkeypatch.delenv("NK_LOCAL_FONTS", raising=False)
    return tmp_path


def _ref(lab):
    return next(r for r in lab.info()["references"] if r["id"] == "ref:local:komic")


def test_missing_local_font_is_listed_as_missing_with_hint(root):
    ref = _ref(Lab(root))
    assert ref["missing"] and ref["local"] and ref["weights"] == []
    assert "Komic.ttf" in ref["hint"]
    assert fetch.local_status(root) == [
        "--  komic Regular: not installed (local only: Komic.ttf, Komic.otf)"
    ]


def test_local_font_in_sources_local_is_loaded(root, latin):
    path = root / "sources" / "local" / "Komic.otf"
    path.parent.mkdir(parents=True)
    latin.save(path)
    lab = Lab(root)
    assert _ref(lab)["weights"] == ["Regular"] and not _ref(lab)["missing"]
    font = lab.font("ref:local:komic", "comics", "Regular")
    assert "glyf" in font
    assert lab.font_bytes("ref:local:komic", "comics", "Black") == path.read_bytes()
    assert fetch.local_status(root) == [f"loc komic Regular: {path}"]


def test_env_dir_and_release_mismatch_warning(root, latin, tmp_path_factory, monkeypatch):
    d = tmp_path_factory.mktemp("fonts")
    latin.save(d / "Komic.ttf")
    monkeypatch.setenv("NK_LOCAL_FONTS", str(d))
    (root / "config" / "local_fonts.toml").write_text(
        (root / "config" / "local_fonts.toml").read_text() + 'sha256 = { "Komic.ttf" = "00" }\n'
    )
    assert config.local_fonts(root)["komic"].find("Regular", root) == d / "Komic.ttf"
    assert fetch.local_status(root)[0].endswith("(different release than pinned)")


def test_uninstalled_local_font_cannot_be_opened(root):
    with pytest.raises(FileNotFoundError):
        Lab(root).font("ref:local:komic", "comics", "Regular")


def test_repo_local_fonts_are_never_pinned_built_or_committed():
    """Non-redistributable references must stay out of sources.lock, builds and git."""
    local = config.local_fonts()
    assert "komacon" in local
    pinned = set(config.sources())
    names = {n.lower() for lf in local.values() for v in lf.weights.values() for n in v}
    for lf in local.values():
        assert lf.id not in pinned
        assert lf.license and lf.weights
    for fid in config.family_ids():
        text = (config.ROOT / "config" / "families" / f"{fid}.toml").read_text().lower()
        assert not any(n in text for n in names), fid
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=config.ROOT, capture_output=True, text=True, check=True
    ).stdout.lower()
    assert not any(line.rsplit("/", 1)[-1] in names for line in tracked.splitlines())
