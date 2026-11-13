"""BMFont (AngelCode) generator for NK Pixel and retro game engines."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config


def export_bmfont(
    font_path: Path | None = None,
    out_dir: Path | None = None,
    scale: int = 1,
    chars: str | None = None,
) -> tuple[Path, Path]:
    """Export font as AngelCode BMFont text (.fnt) and PNG atlas.

    scale=1 is 16px grid, scale=2 is 32px, etc.
    """
    font_path = font_path or (config.BUILD_DIR / "master" / "NKPixel-Regular.ttf")
    if not font_path.exists():
        raise FileNotFoundError(f"Font not found: {font_path}")

    out_dir = out_dir or (config.DIST_DIR / "gaming")
    out_dir.mkdir(parents=True, exist_ok=True)

    base_size = 16 * scale
    ttfont = ImageFont.truetype(str(font_path), base_size)

    # Default character set: ASCII + Korean KS X 1001 common subset or passed chars
    if chars is None:
        ascii_chars = [chr(c) for c in range(32, 127)]
        # Sample common Korean characters for lightweight game font
        kr_sample = [
            "가",
            "나",
            "다",
            "라",
            "마",
            "바",
            "사",
            "아",
            "자",
            "차",
            "카",
            "타",
            "파",
            "하",
            "한",
            "글",
            "게임",
            "시작",
            "설정",
            "종료",
            "레벨",
            "체력",
            "마나",
            "공격",
            "방어",
            "아이템",
            "인벤토리",
            "퀘스트",
            "경험치",
            "골드",
            "능력",
            "속도",
            "점수",
            "랭킹",
            "성공",
            "실패",
            "승리",
            "패배",
            "저장",
            "불러오기",
            "옵션",
            "도움말",
            "대화",
        ]
        kr_chars = sorted(set("".join(kr_sample)))
        chars = "".join(ascii_chars) + "".join(kr_chars)

    # Unique characters sorted by code point
    unique_cps = sorted({ord(c) for c in chars})

    # Estimate atlas size
    cell_w = 16 * scale
    cell_h = 16 * scale
    cols = 32
    rows = math.ceil(len(unique_cps) / cols)
    atlas_w = cols * cell_w
    atlas_h = max(rows * cell_h, 128)

    # Create atlas image
    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(atlas)

    char_records = []
    for idx, cp in enumerate(unique_cps):
        col = idx % cols
        row = idx // cols
        x = col * cell_w
        y = row * cell_h

        char = chr(cp)
        # Check advance width: ASCII is half-width (8px * scale), CJK is full-width (16px * scale)
        is_half = cp < 128
        adv = 8 * scale if is_half else 16 * scale
        w = adv
        h = cell_h

        # Draw character on atlas (snap to integer pixel)
        draw.text((x, y), char, font=ttfont, fill=(255, 255, 255, 255))

        char_records.append(
            {
                "id": cp,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "xoffset": 0,
                "yoffset": 0,
                "xadvance": adv,
                "page": 0,
                "chnl": 15,
            }
        )

    prefix = f"{font_path.stem}@{scale}x"
    png_path = out_dir / f"{prefix}_0.png"
    fnt_path = out_dir / f"{prefix}.fnt"

    atlas.save(png_path, "PNG")

    # Generate BMFont text (.fnt)
    lines = [
        (
            f'info face="{font_path.stem}" size={base_size} bold=0 italic=0 charset="" '
            "unicode=1 stretchH=100 smooth=0 aa=0 padding=0,0,0,0 spacing=0,0"
        ),
        (
            f"common lineHeight={base_size} base={int(13 * scale)} "
            f"scaleW={atlas_w} scaleH={atlas_h} pages=1 packed=0"
        ),
        f'page id=0 file="{png_path.name}"',
        f"chars count={len(char_records)}",
    ]
    for r in char_records:
        lines.append(
            f"char id={r['id']:<5} x={r['x']:<5} y={r['y']:<5} "
            f"width={r['width']:<4} height={r['height']:<4} "
            f"xoffset={r['xoffset']:<3} yoffset={r['yoffset']:<3} "
            f"xadvance={r['xadvance']:<4} page={r['page']} chnl={r['chnl']}"
        )

    fnt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return fnt_path, png_path
