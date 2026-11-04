"""Render proof sheets (PNG) for visual review and tuning."""

from __future__ import annotations

import io
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

SAMPLE = [
    "가나다라 ABCD abcd 0O1lI |",
    "다람쥐 헌 쳇바퀴에 타고파 0123456789",
    "The quick brown fox → 빠른 갈색 여우",
    "if (x != y) { return a <= b; } // 주석",
    "┌──┬──┐ ▏▎▍▌▋▊▉█ ═══",
    "│한│ab│  [] {} () \"\" '' ``",
    "└──┴──┘  ~/문서/프로젝트 ❯ git:(main)",
]


def _pil_font(font: TTFont | Path, size: int, **kwargs) -> ImageFont.FreeTypeFont:
    if isinstance(font, TTFont):
        buf = io.BytesIO()
        font.save(buf)
        buf.seek(0)
        return ImageFont.truetype(buf, size, **kwargs)
    return ImageFont.truetype(str(font), size, **kwargs)


def render(fonts: list[tuple[str, TTFont | Path]], size: int = 28, lines=SAMPLE) -> Image.Image:
    """Stack one block per (label, font). Draws a cell grid so 1:2 alignment is visible."""
    label_font = ImageFont.load_default()
    blocks = []
    for label, f in fonts:
        pf = _pil_font(f, size)
        cell_w = pf.getlength("0")
        asc, desc = pf.getmetrics()
        line_h = asc + desc
        cols = max(
            sum(2 if ord(c) >= 0x1100 and ord(c) not in range(0x2500, 0x2600) else 1 for c in ln)
            for ln in lines
        )
        w = int(cell_w * (cols + 2)) + 20
        h = line_h * len(lines) + 40
        img = Image.new("RGB", (w, h), "white")
        d = ImageDraw.Draw(img)
        d.text((10, 4), label, fill=(120, 0, 0), font=label_font)
        for i in range(cols + 1):
            x = 10 + i * cell_w
            d.line([(x, 24), (x, h - 8)], fill=(235, 235, 245))
        for row, ln in enumerate(lines):
            d.text((10, 24 + row * line_h), ln, fill="black", font=pf)
        blocks.append(img)
    total = Image.new("RGB", (max(b.width for b in blocks), sum(b.height for b in blocks)), "white")
    y = 0
    for b in blocks:
        total.paste(b, (0, y))
        y += b.height
    return total


WEIGHT_SAMPLE = "한글 Hangul 다람쥐 Quartz 0O1lI"


def render_weights(
    fonts: list[tuple[str, TTFont | Path]], size: int = 44, text: str = WEIGHT_SAMPLE
) -> Image.Image:
    """One line per weight (label, font), Thin at the top: Hangul and Latin side by side so a
    weight where one script looks lighter or darker than the other stands out."""
    label_font = ImageFont.load_default()
    rows = []
    for label, f in fonts:
        pf = _pil_font(f, size)
        asc, desc = pf.getmetrics()
        w = int(pf.getlength(text)) + 190
        img = Image.new("RGB", (w, asc + desc + 16), "white")
        d = ImageDraw.Draw(img)
        d.text((10, (asc + desc) // 2), label, fill=(120, 0, 0), font=label_font)
        d.text((170, 8), text, fill="black", font=pf)
        rows.append(img)
    total = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows)), "white")
    y = 0
    for r in rows:
        total.paste(r, (0, y))
        y += r.height
    return total
