"""Minecraft resource pack packager for NK Pixel font."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config


def create_pack_icon(output_path: Path, font_path: Path | None = None) -> None:
    """Generate a 128x128 pack.png icon with retro pixel aesthetic."""
    img = Image.new("RGBA", (128, 128), (24, 24, 27, 255))
    draw = ImageDraw.Draw(img)

    # Pixel grid border
    draw.rectangle([4, 4, 123, 123], outline=(63, 63, 70, 255), width=2)
    draw.rectangle([8, 8, 119, 119], outline=(39, 39, 42, 255), width=1)

    # Accent color box
    draw.rectangle([20, 20, 108, 64], fill=(79, 70, 229, 255))
    draw.rectangle([22, 22, 106, 62], outline=(129, 140, 248, 255), width=1)

    # Render "NK" title
    if font_path and font_path.exists():
        try:
            f = ImageFont.truetype(str(font_path), 32)
            draw.text((64, 42), "NK", font=f, fill=(255, 255, 255, 255), anchor="mm")
            f_sub = ImageFont.truetype(str(font_path), 16)
            draw.text((64, 88), "PIXEL FONT", font=f_sub, fill=(244, 244, 245, 255), anchor="mm")
            draw.text((64, 104), "16px CRISP", font=f_sub, fill=(161, 161, 170, 255), anchor="mm")
        except Exception:
            pass

    img.save(output_path, "PNG")


def build_minecraft_resourcepack(
    font_path: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Pack NK Pixel into a Minecraft Java Edition resource pack (.zip)."""
    font_path = font_path or (config.BUILD_DIR / "master" / "NKPixel-Regular.ttf")
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")

    out_dir = out_dir or (config.DIST_DIR / "gaming")
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "NK-Pixel-Minecraft-Resourcepack.zip"

    # 1. pack.mcmeta (compatible with MC 1.20 ~ 1.21+)
    pack_mcmeta = {
        "pack": {
            "pack_format": 34,
            "supported_formats": {"min_inclusive": 15, "max_inclusive": 48},
            "description": "§6NK Pixel Font§r §7(16px Crisp Korean & Latin)§r",
        }
    }

    # 2. font/default.json (TTF font provider)
    font_json = {
        "providers": [
            {
                "type": "ttf",
                "file": f"minecraft:font/{font_path.name}",
                "shift": [0.0, 0.0],
                "size": 11.0,
                "oversample": 1.0,
            }
        ]
    }

    # 3. Create temp pack.png icon
    icon_path = out_dir / "temp_pack.png"
    create_pack_icon(icon_path, font_path)

    # 4. Assemble ZIP
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pack.mcmeta", json.dumps(pack_mcmeta, indent=2, ensure_ascii=False))
        if icon_path.exists():
            zf.write(icon_path, "pack.png")
            icon_path.unlink()
        zf.write(font_path, f"assets/minecraft/font/{font_path.name}")
        zf.writestr("assets/minecraft/font/default.json", json.dumps(font_json, indent=2))

    return zip_path
