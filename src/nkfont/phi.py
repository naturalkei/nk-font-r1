"""Golden-ratio (φ) rules for NK metrics.

Every ratio NK derives on purpose is a power of φ, so the families share one proportion system:

  φ^1   = 1.618  line height of NK Novel (long-form reading)
  φ^0.5 = 1.272  line height of NK Comics (tight speech-bubble lettering)
  φ^-1  = 0.618  reserved for the tuning rules (e.g. Hangul optical-centre offsets)

Terminal families (Sans, Serif, Mono, Pixel) keep the Latin base's line metrics: terminals size
cells from them, and Powerline separators must meet without seams (CLAUDE.md invariants).
Config values like `line_height = "phi"` or `"phi^0.5"` are resolved here, never hard-coded.
"""

from __future__ import annotations

import math
import re

PHI = (1 + math.sqrt(5)) / 2

_TOKEN = re.compile(r"^phi(?:\^(-?\d+(?:\.\d+)?))?$")


def ratio(value: float | int | str) -> float:
    """`1.5` -> 1.5, `"phi"` -> φ, `"phi^0.5"` -> √φ, `"phi^-1"` -> 1/φ."""
    if isinstance(value, (int, float)):
        return float(value)
    m = _TOKEN.match(value.strip().lower().replace("φ", "phi"))
    if not m:
        raise ValueError(f"not a ratio: {value!r} (use a number, 'phi' or 'phi^N')")
    return PHI ** float(m.group(1) or 1)


def line_metrics(
    ascent: int, descent: int, upm: int, line_height: float | str
) -> tuple[int, int, int]:
    """Keep ascent/descent (descent negative) and set lineGap so the default line is exact.

    Returns (ascent, descent, line_gap) with ascent - descent + line_gap == round(r * upm).
    Raises if ascent and descent alone are already taller than the target.
    """
    total = round(ratio(line_height) * upm)
    gap = total - (ascent - descent)
    if gap < 0:
        raise ValueError(
            f"ascent {ascent} + descent {-descent} exceed line height {total} ({line_height})"
        )
    return ascent, descent, gap
