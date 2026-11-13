"""Tests for Minecraft resource pack packaging."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from nkfont.minecraft import build_minecraft_resourcepack


def test_build_minecraft_pack(tmp_path: Path):
    # Dummy ttf file
    dummy_ttf = tmp_path / "NKPixel-Regular.ttf"
    dummy_ttf.write_bytes(b"dummy ttf content")

    out_dir = tmp_path / "out"
    zip_path = build_minecraft_resourcepack(dummy_ttf, out_dir)

    assert zip_path.exists()
    assert zip_path.name == "NK-Pixel-Minecraft-Resourcepack.zip"

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert "pack.mcmeta" in names
        assert "pack.png" in names
        assert "assets/minecraft/font/NKPixel-Regular.ttf" in names
        assert "assets/minecraft/font/default.json" in names

        mcmeta = json.loads(zf.read("pack.mcmeta"))
        assert "pack" in mcmeta
        assert mcmeta["pack"]["pack_format"] >= 15

        font_json = json.loads(zf.read("assets/minecraft/font/default.json"))
        assert "providers" in font_json
        assert font_json["providers"][0]["type"] == "ttf"
        assert font_json["providers"][0]["file"] == "minecraft:font/NKPixel-Regular.ttf"
