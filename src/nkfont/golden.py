"""Visual regression: render fixed proof images and compare them with approved baselines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont

from . import config
from .proof import _pil_font

GOLDEN_DIR = config.ROOT / "tests" / "golden"

# Fixed text covering the risky areas: Hangul on the 2-cell grid, ambiguous symbols, box drawing,
# wide symbols widened by fit_terminal_widths, Powerline separators (patched fonts only).
GOLDEN_TEXT = [
    "가각힣 ㄱㅏ ﾡﾭ 0O1lI",
    "┌─┬─┐ ⚡｛｝ · ☰",
    "│가│a│ ~/문서 ",
    "└─┴─┘ 뷁똠쀍 →≠",
]


@dataclass
class GoldenResult:
    name: str
    status: str  # "pass", "fail", "new", "updated"
    ratio: float = 0.0
    detail: str = ""


def render_golden(font: TTFont | Path, size: int = 32) -> Image.Image:
    """Deterministic render: BASIC layout (no HarfBuzz), grayscale, one glyph per cell slot."""
    basic = _pil_font(font, size, layout_engine=ImageFont.Layout.BASIC)
    asc, desc = basic.getmetrics()
    line_h = asc + desc
    cell = basic.getlength("0")
    cols = 24
    img = Image.new("L", (int(cell * cols) + 8, line_h * len(GOLDEN_TEXT) + 8), 255)
    d = ImageDraw.Draw(img)
    for row, text in enumerate(GOLDEN_TEXT):
        d.text((4, 4 + row * line_h), text, fill=0, font=basic)
    return img


def compare(
    name: str,
    img: Image.Image,
    update: bool = False,
    threshold: float = 0.002,
    out_dir: Path | None = None,
) -> GoldenResult:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden = GOLDEN_DIR / f"{name}.png"
    if update or not golden.exists():
        status = "updated" if golden.exists() else "new"
        img.save(golden)
        return GoldenResult(name, status, detail=str(golden.relative_to(config.ROOT)))
    ref = Image.open(golden).convert("L")
    if ref.size != img.size:
        return GoldenResult(name, "fail", 1.0, f"size {img.size} != golden {ref.size}")
    delta = ImageChops.difference(ref, img).point(lambda v: 255 if v > 64 else 0)
    changed = sum(delta.histogram()[1:])
    ratio = changed / (img.width * img.height)
    if ratio <= threshold:
        return GoldenResult(name, "pass", ratio)
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        Image.merge("RGB", (ref, img, delta)).save(out_dir / f"{name}.diff.png")
    return GoldenResult(name, "fail", ratio, f"{ratio:.2%} pixels changed (limit {threshold:.2%})")
