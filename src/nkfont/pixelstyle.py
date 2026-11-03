"""Pixel-grid style knobs for NK Pixel (`kind = "pixel"`), applied on whole pixels only.

NK Pixel is one source font renamed, so the `[hangul]` outline knobs (scale, grade in font units,
skew) do not apply: they would put points off the pixel grid. `[pixel]` works on the bitmap
instead. Each glyph is sampled at its pixel centres (non-zero winding), changed as a bitmap and
written back as pixel-exact rectangles, so every point stays on the `units_per_pixel` grid and
advances never change (terminal cells stay 0 / half / full).

  bold    -1, 0 or 1 px on vertical stems: +1 smears each row one pixel to the right (bitmap
          bold that never closes a one-pixel gap), -1 trims one pixel off the right of every run
          that is 2 px or wider (a light face; 1 px details are kept)
  heavy   0 or 1 px on horizontal bars: +1 smears each column one pixel down (the bottom row
          grows up instead, so the glyph keeps its baseline)
  italic  0 = upright, N = shift one pixel right every N rows above the middle of the line
          (and left below it), the usual pixel-font stair-step italic
  shadow  0 or 1: add the glyph again one pixel right and one pixel down (game UI drop shadow,
          drawn in the same colour so it reads as a 3D/embossed face), never touching other ink
  dy      whole pixels to move glyphs up (+) or down (-)
  scope   "all" (default), "hangul" or "latin": which glyphs the knobs above touch. Hangul =
          Hangul syllables and jamo; latin = everything else that has an advance.
  hangul_dy  whole pixels to move Hangul only, whatever the scope (aligns the Hangul centre
          with the Latin capitals while the other knobs style both scripts)

All defaults are the identity and `apply_pixel` returns early, so builds stay byte-identical.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

SCOPES = ("all", "hangul", "latin")
_HANGUL = ((0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F), (0xAC00, 0xD7A3), (0xD7B0, 0xD7FF))


@dataclass(frozen=True)
class PixelParams:
    bold: int = 0
    heavy: int = 0
    italic: int = 0
    shadow: int = 0
    dy: int = 0
    hangul_dy: int = 0
    scope: str = "all"

    @classmethod
    def from_dict(cls, d: dict | None) -> PixelParams:
        d = d or {}
        names = {f.name for f in fields(cls)}
        unknown = set(d) - names
        if unknown:
            raise ValueError(f"unknown [pixel] keys: {', '.join(sorted(unknown))}")
        out = {k: (str(v) if k == "scope" else int(v)) for k, v in d.items()}
        p = cls(**out)
        if p.scope not in SCOPES:
            raise ValueError(f"pixel.scope must be one of {', '.join(SCOPES)}")
        if p.bold not in (-1, 0, 1) or p.heavy not in (0, 1) or p.shadow not in (0, 1):
            raise ValueError("pixel.bold is -1..1, pixel.heavy and pixel.shadow are 0 or 1")
        if not 0 <= p.italic <= 8 or abs(p.dy) > 4 or abs(p.hangul_dy) > 4:
            raise ValueError("pixel.italic is 0..8 rows per pixel, pixel.dy is -4..4 px")
        return p

    def is_identity(self) -> bool:
        return not (
            self.bold or self.heavy or self.italic or self.shadow or self.dy or self.hangul_dy
        )

    def for_glyph(self, hangul: bool) -> PixelParams:
        """The knobs one glyph gets: shape knobs and `dy` only in scope, `hangul_dy` on Hangul."""
        in_scope = self.scope == "all" or (self.scope == "hangul") == hangul
        return PixelParams(
            bold=self.bold if in_scope else 0,
            heavy=self.heavy if in_scope else 0,
            italic=self.italic if in_scope else 0,
            shadow=self.shadow if in_scope else 0,
            dy=(self.dy if in_scope else 0) + (self.hangul_dy if hangul else 0),
        )


def is_hangul(cp: int) -> bool:
    return any(a <= cp <= b for a, b in _HANGUL)


def _polygons(glyph, glyf) -> list[list[tuple[float, float]]]:
    coords, ends, _ = glyph.getCoordinates(glyf)
    out, start = [], 0
    for end in ends:
        out.append([tuple(coords[i]) for i in range(start, end + 1)])
        start = end + 1
    return out


def rasterize(polys, px: int) -> set[tuple[int, int]]:
    """Pixels (column, row) whose centre is inside the outline (non-zero winding).

    Pixel fonts are drawn with straight on-curve edges, so the contour points are the polygon.
    Rows count from the baseline: row 0 is the pixel just above y = 0.
    """
    if not polys:
        return set()
    ys = [y for p in polys for _, y in p]
    xs = [x for p in polys for x, _ in p]
    on = set()
    for row in range(int(min(ys) // px), int(max(ys) // px) + 1):
        cy = (row + 0.5) * px
        crossings = []  # (x, winding direction)
        for poly in polys:
            n = len(poly)
            for i in range(n):
                (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
                if (y0 <= cy) != (y1 <= cy):
                    x = x0 + (cy - y0) * (x1 - x0) / (y1 - y0)
                    crossings.append((x, 1 if y1 > y0 else -1))
        if not crossings:
            continue
        crossings.sort()
        for col in range(int(min(xs) // px), int(max(xs) // px) + 1):
            cx = (col + 0.5) * px
            if sum(w for x, w in crossings if x < cx):
                on.add((col, row))
    return on


def transform(bits: set[tuple[int, int]], p: PixelParams, pivot: int = 0) -> set[tuple[int, int]]:
    """The bitmap changes, in a fixed order: weight, bars, slant, shadow, shift.

    `pivot` is the row that italic leaves in place (the middle of the line), so the stair-step
    spreads to both sides of the cell instead of piling up on the right.
    """
    out = set(bits)

    # Growing strokes never bridges a one-pixel gap: a pixel is only added where the pixel
    # beyond it is white, so 를's bars and m's stems stay apart (bitmap fonts' "smart bold").
    def bridges(c: int, r: int) -> bool:
        """Would ink at (c, r) close a one-pixel gap across or along its row/column?"""
        return ((c - 1, r) in out and (c + 1, r) in out) or (
            (c, r - 1) in out and (c, r + 1) in out
        )

    if p.bold > 0:
        out |= {
            (c + 1, r)
            for c, r in out
            if (c + 1, r) not in out and (c + 2, r) not in out and not bridges(c + 1, r)
        }
    elif p.bold < 0:
        # Drop the rightmost pixel of every horizontal run that is at least 2 px long.
        out = {(c, r) for c, r in out if (c + 1, r) in out or (c - 1, r) not in out}
    if p.heavy and out:
        # Bars grow downwards, except on the glyph's bottom row (baseline or descender), which
        # grows upwards so nothing new hangs below the original ink.
        bottom = min(r for _, r in out)
        grown = set()
        for c, r in out:
            to = (c, r - 1) if r > bottom else (c, r + 1)
            beyond = (c, r - 2) if r > bottom else (c, r + 2)
            if to not in out and beyond not in out and not bridges(*to):
                grown.add(to)
        out |= grown
    if p.italic:
        out = {(c + (r - pivot) // p.italic, r) for c, r in out}
    if p.shadow:
        shade = {(c + 1, r - 1) for c, r in out}
        # The shadow may not close a gap either: skip pixels that would touch other ink.
        out |= {
            (c, r)
            for c, r in shade
            if (c, r) not in out
            and (c + 1, r) not in out
            and (c, r - 1) not in out
            and not bridges(c, r)
        }
    if p.dy:
        out = {(c, r + p.dy) for c, r in out}
    return out


def outline(bits: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """Trace the bitmap's boundary into closed contours of pixel corners.

    Outer contours run clockwise and holes counter-clockwise (TrueType, y up), corners where
    the direction does not change are dropped, and pixels that touch only at a corner stay
    separate contours, so the result is the exact union with no overlaps or seams.
    """
    # Directed boundary edges, each pixel walked clockwise: left side up, top right, right
    # side down, bottom left. An edge shared with a neighbour pixel is not a boundary.
    nxt: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for c, r in bits:
        x0, y0, x1, y1 = c, r, c + 1, r + 1
        if (c - 1, r) not in bits:
            nxt.setdefault((x0, y0), []).append((x0, y1))
        if (c, r + 1) not in bits:
            nxt.setdefault((x0, y1), []).append((x1, y1))
        if (c + 1, r) not in bits:
            nxt.setdefault((x1, y1), []).append((x1, y0))
        if (c, r - 1) not in bits:
            nxt.setdefault((x1, y0), []).append((x0, y0))
    contours = []
    while nxt:
        start = min(nxt)
        pts, prev, cur = [start], None, start
        while True:
            outs = nxt[cur]
            if len(outs) == 1 or prev is None:
                to = outs[0]
            else:
                # Two pixels meet at this corner only: turn right (clockwise) so they stay apart.
                dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                right = (cur[0] + dy, cur[1] - dx)
                to = right if right in outs else outs[0]
            outs.remove(to)
            if not outs:
                del nxt[cur]
            prev, cur = cur, to
            if cur == start:
                break
            pts.append(cur)
        # Keep only the corners.
        n = len(pts)
        keep = []
        for i in range(n):
            a, b, c2 = pts[i - 1], pts[i], pts[(i + 1) % n]
            if (b[0] - a[0]) * (c2[1] - b[1]) != (b[1] - a[1]) * (c2[0] - b[0]):
                keep.append(b)
        contours.append(keep)
    return contours


def draw(bits: set[tuple[int, int]], px: int):
    """A TrueType glyph with the bitmap's exact outline (see `outline`)."""
    pen = TTGlyphPen(None)
    for contour in outline(bits):
        pen.moveTo((contour[0][0] * px, contour[0][1] * px))
        for x, y in contour[1:]:
            pen.lineTo((x * px, y * px))
        pen.closePath()
    return pen.glyph()


def apply_pixel(
    font: TTFont, params: PixelParams, px: int, unicodes: set[int] | None = None
) -> int:
    """Restyle the glyphs in scope on the pixel grid; returns how many glyphs changed.

    Composite glyphs are flattened (their components may be shared with out-of-scope glyphs).
    """
    if params.is_identity():
        return 0
    glyf, hmtx = font["glyf"], font["hmtx"]
    cmap = font.getBestCmap()
    targets: dict[str, PixelParams] = {}
    for cp, name in cmap.items():
        if unicodes is not None and cp not in unicodes:
            continue
        p = params.for_glyph(is_hangul(cp))
        if not p.is_identity():
            targets[name] = p
    # Middle of the line in pixel rows (ascent and descent are whole pixels in a pixel font).
    pivot = (font["hhea"].ascent + font["hhea"].descent) // (2 * px)
    new = {}
    for name, p in targets.items():
        g = glyf[name]
        if not hmtx[name][0] or not (g.isComposite() or g.numberOfContours > 0):
            continue
        bits = transform(rasterize(_polygons(g, glyf), px), p, pivot)
        new[name] = draw(bits, px)
    for name, g in new.items():
        glyf[name] = g
        g.recalcBounds(glyf)
        hmtx[name] = (hmtx[name][0], getattr(g, "xMin", 0))
    for tag in ("hdmx", "LTSH", "VDMX"):
        if tag in font:
            del font[tag]
    return len(new)
