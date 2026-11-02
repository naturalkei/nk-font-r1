"""Nerd Fonts patching through the pinned Docker image, then re-apply terminal flags."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config
from .build import save_reproducible
from .flags import enforce_terminal_flags, fit_terminal_widths
from .merge import half_width

# Never use --mono/-s: it forces every existing glyph (Hangul included) to one cell.
VARIANTS = {
    "nf": ["--complete", "--careful"],
    "nfm": ["--complete", "--careful", "--single-width-glyphs"],
}


def patch(masters: list[Path], out_dir: Path | None = None) -> list[Path]:
    out_dir = out_dir or config.DIST_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    image = config.patcher_image()
    work = config.BUILD_DIR / "patch-in"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    for m in masters:
        shutil.copy(m, work / m.name)
    results = []
    for variant, flags in VARIANTS.items():
        vout = config.BUILD_DIR / f"patch-out-{variant}"
        shutil.rmtree(vout, ignore_errors=True)
        vout.mkdir(parents=True)
        subprocess.run(
            ["docker", "run", "--rm", "-v", f"{work}:/in:Z", "-v", f"{vout}:/out:Z", image, *flags],
            check=True,
        )
        for f in sorted(vout.glob("*.ttf")):
            font = TTFont(f)
            hhea = font["hhea"]
            half = half_width(font)
            fit_terminal_widths(font, half)
            enforce_terminal_flags(font, half, hhea.ascent, hhea.descent)
            dest = out_dir / f.name
            save_reproducible(font, dest)
            results.append(dest)
    return results
