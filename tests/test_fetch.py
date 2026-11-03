"""Archive-only upstreams (D2Coding ships a zip): member extraction and hash pinning."""

import hashlib
import zipfile

import pytest

from nkfont import config, fetch


def _setup(tmp_path, monkeypatch, archive_sha=None):
    payload = b"font-bytes"
    zpath = tmp_path / "up.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("Dir/Font-Regular.ttf", payload)
    zsha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    (tmp_path / "sources.lock").write_text(
        f'''[[font]]
id = "zipped"
url = "{zpath.as_uri()}"
member = "Dir/Font-Regular.ttf"
archive_sha256 = "{archive_sha or zsha}"
sha256 = "{hashlib.sha256(payload).hexdigest()}"
license = "OFL-1.1"
'''
    )
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "SOURCES_DIR", tmp_path / "sources")
    monkeypatch.setattr(config, "sources", lambda root=tmp_path, _f=config.sources: _f(tmp_path))
    return payload


def test_member_is_extracted_and_named_after_member(tmp_path, monkeypatch):
    payload = _setup(tmp_path, monkeypatch)
    assert fetch.fetch_all() == ["zipped"]
    out = tmp_path / "sources" / "Font-Regular.ttf"
    assert out.read_bytes() == payload


def test_archive_hash_mismatch_fails(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, archive_sha="0" * 64)
    with pytest.raises(RuntimeError, match="archive SHA256"):
        fetch.fetch_all()


def test_tgz_member_is_extracted(tmp_path, monkeypatch):
    """npm tarballs (Neo둥근모 Pro) are archives too: one member is read, nothing else unpacked."""
    import io
    import tarfile

    payload = b"pro-font-bytes"
    tpath = tmp_path / "pkg.tgz"
    with tarfile.open(tpath, "w:gz") as t:
        info = tarfile.TarInfo("package/font.ttf")
        info.size = len(payload)
        t.addfile(info, io.BytesIO(payload))
        other = tarfile.TarInfo("package/README.md")
        other.size = 2
        t.addfile(other, io.BytesIO(b"hi"))
    tsha = hashlib.sha256(tpath.read_bytes()).hexdigest()
    (tmp_path / "sources.lock").write_text(
        f'''[[font]]
id = "tgz"
url = "{tpath.as_uri()}"
member = "package/font.ttf"
archive_sha256 = "{tsha}"
sha256 = "{hashlib.sha256(payload).hexdigest()}"
license = "OFL-1.1"
'''
    )
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "SOURCES_DIR", tmp_path / "sources")
    monkeypatch.setattr(config, "sources", lambda root=tmp_path, _f=config.sources: _f(tmp_path))
    assert fetch.fetch_all() == ["tgz"]
    assert (tmp_path / "sources" / "font.ttf").read_bytes() == payload
    assert sorted(p.name for p in (tmp_path / "sources").iterdir()) == ["font.ttf"]
