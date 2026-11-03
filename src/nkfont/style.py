"""Whole-face style knobs for proportional families: one transform for Latin *and* Hangul.

`[hangul]` only reshapes the Hangul glyphs NK imports. A family whose Latin source already draws
its own Hangul (NK Comics: Gaegu draws 2,350 syllables with its Latin) needs knobs that move
both scripts together, or the two drift apart. `[style]` does that, after merging:

  slant     degrees, positive leans right; every glyph is skewed about y = 0 (the baseline), so
            Latin and Hangul lean on one line, like an italic
  grade     font units added to (or, negative, taken from) every stroke, advances unchanged
  tracking  font units added to every advance, split over both side bearings
  bounce    hand-lettering baseline wobble: each glyph moves up or down by up to this many units
  tilt      hand-lettering angle wobble: each glyph turns by up to this many degrees
  seed      which wobble pattern (any integer); the pattern is fixed per glyph name

The wobble is deterministic (hash of glyph name and seed), so builds stay reproducible. All
defaults are the identity and `apply_style` returns early, so families without `[style]` build
byte-identically. Values are given for UPM 1000 and rescaled to the font's UPM.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, fields

from fontTools.ttLib import TTFont

from .merge import embolden


@dataclass(frozen=True)
class StyleParams:
    slant: float = 0.0
    grade: float = 0.0
    tracking: float = 0.0
    bounce: float = 0.0
    tilt: float = 0.0
    seed: int = 0

    @classmethod
    def from_dict(cls, d: dict | None) -> StyleParams:
        d = d or {}
        names = {f.name for f in fields(cls)}
        unknown = set(d) - names
        if unknown:
            raise ValueError(f"unknown [style] keys: {', '.join(sorted(unknown))}")
        return cls(**{k: (int(v) if k == "seed" else float(v)) for k, v in d.items()})

    def is_identity(self) -> bool:
        return not (self.slant or self.grade or self.tracking or self.bounce or self.tilt)


def _wobble(name: str, seed: int) -> tuple[float, float]:
    """Two numbers in [-1, 1] that only depend on the glyph name and the seed."""
    h = hashlib.blake2b(f"{seed}:{name}".encode(), digest_size=4).digest()
    return h[0] / 127.5 - 1 + h[1] / 32640, h[2] / 127.5 - 1 + h[3] / 32640


def apply_style(font: TTFont, params: StyleParams, unicodes: set[int] | None = None) -> int:
    """Transform glyph outlines and advances in place; returns how many glyphs changed.

    `unicodes` limits the work to the glyphs those characters use (previews); components of
    composite glyphs are always included so a composite never mixes styled and plain parts.
    """
    if params.is_identity():
        return 0
    if "glyf" not in font:
        raise ValueError("[style] needs TrueType (glyf) outlines")
    glyf, hmtx = font["glyf"], font["hmtx"]
    k = font["head"].unitsPerEm / 1000
    names = set(font.getGlyphOrder())
    if unicodes is not None:
        cmap = font.getBestCmap()
        names = {cmap[u] for u in unicodes if u in cmap}
        todo = list(names)
        while todo:  # pull in components
            g = glyf[todo.pop()]
            if g.isComposite():
                for c in g.components:
                    if c.glyphName not in names:
                        names.add(c.glyphName)
                        todo.append(c.glyphName)
    shear = math.tan(math.radians(params.slant))
    track = params.tracking * k
    changed = 0
    for name in sorted(names):
        g = glyf[name]
        adv, lsb = hmtx[name]
        if g.isComposite():
            # Components are styled themselves: only follow the skew of their offsets.
            for c in g.components:
                c.x = round(c.x + shear * c.y)
        elif g.numberOfContours > 0:
            if params.grade:
                embolden(g, params.grade * k)
                g.recalcBounds(glyf)
            coords = g.coordinates
            dx = track / 2 if adv else 0  # marks (zero advance) keep their position
            x0, y0, x1, y1 = g.xMin, g.yMin, g.xMax, g.yMax
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            wb, wt = _wobble(name, params.seed)
            dy = params.bounce * k * wb
            a = math.radians(params.tilt * wt)
            ca, sa = math.cos(a), math.sin(a)
            for i, (x, y) in enumerate(coords):
                if a:  # turn about the ink centre so the glyph stays in its slot
                    x, y = cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca
                y += dy
                coords[i] = (round(x + shear * y + dx), round(y))
        if track and adv:
            hmtx[name] = (max(0, round(adv + track)), lsb)
        changed += 1
    for name in names:
        g = glyf[name]
        if g.isComposite() or g.numberOfContours > 0:
            g.recalcBounds(glyf)
            hmtx[name] = (hmtx[name][0], getattr(g, "xMin", 0))
    if "hdmx" in font:
        del font["hdmx"]
    if "LTSH" in font:
        del font["LTSH"]
    return changed
