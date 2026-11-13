"""Tests for release bundle packager."""

from __future__ import annotations

from pathlib import Path

from nkfont.package import package_all_targets


def test_package_all_targets(tmp_path: Path):
    out_dir = tmp_path / "release"
    results = package_all_targets(out_dir, version="0.1.0-test")

    assert len(results) == 3
    names = [p.name for p in results]
    assert "nk-mono-coding-v0.1.0-test.zip" in names
    assert "nk-pixel-gaming-v0.1.0-test.zip" in names
    assert "nk-novel-reader-v0.1.0-test.zip" in names

    for p in results:
        assert p.exists()
        assert p.stat().st_size > 0
