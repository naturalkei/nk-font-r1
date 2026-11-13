"""Package target-specific release bundles for NK Font."""

from __future__ import annotations

import zipfile
from pathlib import Path

from . import config


def create_bundle(
    zip_path: Path,
    font_files: list[Path],
    extra_files: list[Path] | None = None,
    readme_text: str = "",
) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in font_files:
            if f.exists():
                z.write(f, f"{zip_path.stem}/{f.name}")
        for ef in extra_files or []:
            if ef.exists():
                z.write(ef, f"{zip_path.stem}/{ef.name}")
        if (config.ROOT / "OFL.txt").exists():
            z.write(config.ROOT / "OFL.txt", f"{zip_path.stem}/OFL.txt")
        if readme_text:
            z.writestr(f"{zip_path.stem}/README.txt", readme_text)
    return zip_path


def package_all_targets(out_dir: Path | None = None, version: str = "0.1.0") -> list[Path]:
    out_dir = out_dir or (config.DIST_DIR / "release")
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    # 1. NK Mono Coding Bundle
    mono_fonts = sorted((config.BUILD_DIR / "master").glob("NKMono-*.ttf"))
    mono_zip = out_dir / f"nk-mono-coding-v{version}.zip"
    mono_readme = (
        f"NK Mono v{version} (Coding & Terminal)\n"
        "====================================\n\n"
        "JetBrains Mono + D2Coding Hangul with perfect 1:2 cell grid.\n\n"
        "Guides included:\n"
        "- SETUP_GUIDE.md: Recommended settings for VS Code, WezTerm, Alacritty, iTerm2\n"
        "- OPENTYPE.md: Programming ligatures (calt), slashed zero (zero), stylistic sets\n"
    )
    create_bundle(
        mono_zip,
        mono_fonts,
        [config.ROOT / "docs" / "SETUP_GUIDE.md", config.ROOT / "docs" / "OPENTYPE.md"],
        mono_readme,
    )
    results.append(mono_zip)

    # 2. NK Pixel Gaming Bundle
    pixel_fonts = sorted((config.BUILD_DIR / "master").glob("NKPixel-*.ttf"))
    pixel_zip = out_dir / f"nk-pixel-gaming-v{version}.zip"
    pixel_extras = [
        config.DIST_DIR / "gaming" / "NK-Pixel-Minecraft-Resourcepack.zip",
        config.DIST_DIR / "gaming" / "NKPixel-Regular@1x.fnt",
        config.DIST_DIR / "gaming" / "NKPixel-Regular@1x_0.png",
        config.DIST_DIR / "gaming" / "NKPixel-Bold@2x.fnt",
        config.DIST_DIR / "gaming" / "NKPixel-Bold@2x_0.png",
    ]
    pixel_readme = (
        f"NK Pixel v{version} (Retro & Gaming)\n"
        "==================================\n\n"
        "16px integer-scaled crisp bitmap font based on Neo둥근모 Code.\n\n"
        "Assets included:\n"
        "- NK-Pixel-Minecraft-Resourcepack.zip: Minecraft Java Edition resource pack\n"
        "- *.fnt / *.png: AngelCode BMFont for Godot, Unity, Terraria, LibGDX\n"
        "- TTF fonts: Regular (1px) and Bold (smear 1px bitmap bold)\n"
    )
    create_bundle(pixel_zip, pixel_fonts, pixel_extras, pixel_readme)
    results.append(pixel_zip)

    # 3. NK Novel Reader Bundle
    novel_fonts = sorted((config.BUILD_DIR / "master").glob("NKNovel-*.ttf"))
    novel_zip = out_dir / f"nk-novel-reader-v{version}.zip"
    novel_readme = (
        f"NK Novel v{version} (Text Viewer & Books)\n"
        "=======================================\n\n"
        "Crimson Text + Gowun Batang for comfortable long-form reading.\n\n"
        "Features:\n"
        "- Golden-ratio (phi = 1.618 em) built-in line height\n"
        "- READER_GUIDE.md: Setup guide for Obsidian, EPUB readers, Apple Books\n"
    )
    create_bundle(
        novel_zip,
        novel_fonts,
        [config.ROOT / "docs" / "READER_GUIDE.md"],
        novel_readme,
    )
    results.append(novel_zip)

    return results
