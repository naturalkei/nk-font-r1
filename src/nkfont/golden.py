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


# Reading faces (NK Novel, NK Comics): body text, punctuation pairs, figures and the Hangul
# extremes. Box drawing and terminal symbols are not part of these families.
GOLDEN_TEXT_PROPORTIONAL = [
    "가각힣 뷁똠쀍 ㄱㅏ 0123456789",
    "“그래, 다시 시작하자.” 그녀가 말했다.",
    "Hamburgefonstiv — 「신문」 『소설』 …?!",
    "The quick brown fox, 다람쥐 헌 쳇바퀴.",
]


@dataclass
class GoldenResult:
    name: str
    status: str  # "pass", "fail", "new", "updated"
    ratio: float = 0.0
    detail: str = ""


def render_golden(font: TTFont | Path, size: int = 32, text: bool = False) -> Image.Image:
    """Deterministic render: BASIC layout (no HarfBuzz), grayscale.

    Terminal fonts get a fixed 24-cell canvas; `text=True` (proportional faces) sizes the canvas
    from the widest line of the reading sample.
    """
    basic = _pil_font(font, size, layout_engine=ImageFont.Layout.BASIC)
    asc, desc = basic.getmetrics()
    line_h = asc + desc
    lines = GOLDEN_TEXT_PROPORTIONAL if text else GOLDEN_TEXT
    if text:
        width = int(max(basic.getlength(t) for t in lines)) + 16
    else:
        width = int(basic.getlength("0") * 24) + 8
    img = Image.new("L", (width, line_h * len(lines) + 8), 255)
    d = ImageDraw.Draw(img)
    for row, text_line in enumerate(lines):
        d.text((4, 4 + row * line_h), text_line, fill=0, font=basic)
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
