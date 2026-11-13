"""Tests for BMFont generator."""

from __future__ import annotations

from pathlib import Path

from nkfont.bmfont import export_bmfont


def test_export_bmfont(tmp_path: Path):
    font_path = Path("build/master/NKPixel-Regular.ttf")
    if not font_path.exists():
        return

    out_dir = tmp_path / "bmfont"
    fnt, png = export_bmfont(font_path, out_dir, scale=1, chars="ABC한글123")

    assert fnt.exists()
    assert png.exists()
    assert fnt.suffix == ".fnt"
    assert png.suffix == ".png"

    content = fnt.read_text(encoding="utf-8")
    assert 'info face="NKPixel-Regular"' in content
    assert "common lineHeight=16" in content
    assert "chars count=" in content
