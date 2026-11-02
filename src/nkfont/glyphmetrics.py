"""Glyph geometry measurements for the Glyph Lab: stems, slant, sidebearings and ink.

Outlines are flattened to polygons and cut with scanlines using the nonzero winding rule (the
TrueType/CFF fill rule), so overlapping contours count once. Everything is pure fontTools and
works on any TTFont, which keeps it testable with the synthetic fixtures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

Point = tuple[float, float]
Polygon = list[Point]

# Curve subdivision steps; 12 keeps stem readings within ~0.5 unit on 1000-UPM outlines.
_STEPS = 12


class FlattenPen(BasePen):
    """Collects closed polygons, approximating curves with straight segments."""

    def __init__(self, glyphset=None, steps: int = _STEPS):
        super().__init__(glyphset)
        self.steps = steps
        self.polygons: list[Polygon] = []
        self._cur: Polygon = []

    def _moveTo(self, pt):
        self._flush()
        self._cur = [pt]

    def _lineTo(self, pt):
        self._cur.append(pt)

    def _qCurveToOne(self, p1, p2):
        p0 = self._cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            u = 1 - t
            self._cur.append(
                (
                    u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
                )
            )

    def _curveToOne(self, p1, p2, p3):
        p0 = self._cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            u = 1 - t
            a, b, c, d = u**3, 3 * u * u * t, 3 * u * t * t, t**3
            self._cur.append(
                (
                    a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
                )
            )

    def _closePath(self):
        self._flush()

    _endPath = _closePath

    def _flush(self):
        if len(self._cur) > 2:
            self.polygons.append(self._cur)
        self._cur = []


def _runs(polys: list[Polygon], c: float, axis: int) -> list[tuple[float, float]]:
    """Ink intervals where the line `axis-coordinate == c` crosses the outline (nonzero rule)."""
    other = 1 - axis
    hits: list[tuple[float, int]] = []
    for poly in polys:
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            if (a[axis] <= c < b[axis]) or (b[axis] <= c < a[axis]):
                t = (c - a[axis]) / (b[axis] - a[axis])
                hits.append((a[other] + t * (b[other] - a[other]), 1 if b[axis] > a[axis] else -1))
    hits.sort()
    out, wind, start = [], 0, 0.0
    for pos, d in hits:
        before = wind
        wind += d
        if before == 0 and wind != 0:
            start = pos
        elif before != 0 and wind == 0 and pos - start > 1e-6:
            out.append((start, pos))
    return out


def hruns(polys: list[Polygon], y: float) -> list[tuple[float, float]]:
    """Horizontal scanline at height y: ink runs (x0, x1). Their widths are vertical stems."""
    return _runs(polys, y, 1)


def vruns(polys: list[Polygon], x: float) -> list[tuple[float, float]]:
    """Vertical scanline at x: ink runs (y0, y1). Their heights are horizontal stems/bars."""
    return _runs(polys, x, 0)


def area(polys: list[Polygon]) -> float:
    """Ink area. Contours are wound opposite to their holes, so signed areas add up."""
    total = 0.0
    for p in polys:
        n = len(p)
        total += sum(p[i][0] * p[(i + 1) % n][1] - p[(i + 1) % n][0] * p[i][1] for i in range(n))
    return abs(total) / 2


def slant_fit(
    polys: list[Polygon], y0: float, y1: float, samples: int = 9, side: int = 0
) -> tuple[float, tuple[float, float, float, float]] | None:
    """Estimated stroke slant in degrees (positive leans right, like italics) and its axis.

    Fits a line (robust Theil-Sen median) through the centres of the leftmost (side=0) or
    rightmost (side=-1) ink run at heights between y0 and y1 and
    skips rows where that run is a bar rather than a stem (wider than 45% of the ink box and
    than a quarter of its height, so a lone stem such as "ㅣ" still counts).
    Returns (degrees, (x_at_y0, y0, x_at_y1, y1)) so the UI can draw the fitted axis.
    """
    pts = []
    xs = [x for p in polys for x, _ in p]
    if not xs:
        return None
    box_w = max(xs) - min(xs)
    limit = max(0.45 * box_w, 0.25 * (y1 - y0) / 0.7)
    for i in range(samples):
        y = y0 + (y1 - y0) * (i + 0.5) / samples
        r = hruns(polys, y)
        if r and (r[side][1] - r[side][0]) < limit:
            pts.append(((r[side][0] + r[side][1]) / 2, y))
    if len(pts) < 3:
        return None
    # Theil-Sen: the median of pairwise slopes ignores rows where another stroke cuts in.
    slopes = sorted((b[0] - a[0]) / (b[1] - a[1]) for i, a in enumerate(pts) for b in pts[i + 1 :])
    k = slopes[len(slopes) // 2]  # dx/dy
    offs = sorted(x - k * y for x, y in pts)
    mx, my = offs[len(offs) // 2], 0.0
    line = (mx + k * (y0 - my), y0, mx + k * (y1 - my), y1)
    return round(math.degrees(math.atan(k)), 2), tuple(round(v, 1) for v in line)


def slant(
    polys: list[Polygon], y0: float, y1: float, samples: int = 9, side: int = 0
) -> float | None:
    fit = slant_fit(polys, y0, y1, samples, side)
    return fit[0] if fit else None


@dataclass
class GlyphGeometry:
    name: str
    advance: int
    bounds: tuple[float, float, float, float] | None
    path: str  # SVG path data in font units, y up
    polygons: list[Polygon] = field(repr=False, default_factory=list)


def glyph_geometry(font: TTFont, glyph_name: str, scale: float = 1.0) -> GlyphGeometry:
    """Outline of one glyph, optionally scaled (e.g. to normalise every font to 1000 UPM)."""
    gs = font.getGlyphSet()
    glyph = gs[glyph_name]
    m = (scale, 0, 0, scale, 0, 0)
    svg = SVGPathPen(gs)
    glyph.draw(TransformPen(svg, m))
    flat = FlattenPen(gs)
    glyph.draw(TransformPen(flat, m))
    bp = BoundsPen(gs)
    glyph.draw(TransformPen(bp, m))
    return GlyphGeometry(
        glyph_name,
        round(font["hmtx"][glyph_name][0] * scale),
        bp.bounds,
        svg.getCommands(),
        flat.polygons,
    )


def measure_glyph(
    geo: GlyphGeometry, scan_y: list[float] | None = None, scan_x: list[float] | None = None
) -> dict:
    """Numbers shown in the Glyph Lab table. Units are the (normalised) font units of `geo`."""
    out: dict = {"advance": geo.advance, "ink": round(area(geo.polygons))}
    if geo.bounds is None:
        out.update(lsb=None, rsb=None, width=0, height=0, coverage=0.0, slant=None)
        out.update(
            slant_line=None, slant_r=None, slant_r_line=None, stem=None, bar=None, contrast=None
        )
        out["scan_y"] = [{"at": y, "runs": []} for y in scan_y or []]
        out["scan_x"] = [{"at": x, "runs": []} for x in scan_x or []]
        return out
    x0, y0, x1, y1 = geo.bounds
    h = y1 - y0
    out.update(
        xmin=round(x0),
        ymin=round(y0),
        xmax=round(x1),
        ymax=round(y1),
        lsb=round(x0),
        rsb=round(geo.advance - x1),
        width=round(x1 - x0),
        height=round(h),
        # Share of the ink box that is black: how "dark" the glyph reads next to others.
        coverage=round(out["ink"] / ((x1 - x0) * h), 3) if (x1 - x0) * h else 0.0,
    )
    # Left and right stroke axes: Latin "l" has one, Hangul "가" leans its ㄱ but not its ㅏ.
    for key, side in (("slant", 0), ("slant_r", -1)):
        fit = slant_fit(geo.polygons, y0 + 0.15 * h, y1 - 0.15 * h, side=side)
        out[key], out[f"{key}_line"] = fit if fit else (None, None)
    sy = scan_y if scan_y is not None else [round(y0 + h / 2)]
    sx = scan_x if scan_x is not None else [round((x0 + x1) / 2)]
    out["scan_y"] = [
        {"at": y, "runs": [[round(a, 1), round(b, 1)] for a, b in hruns(geo.polygons, y)]}
        for y in sy
    ]
    out["scan_x"] = [
        {"at": x, "runs": [[round(a, 1), round(b, 1)] for a, b in vruns(geo.polygons, x)]}
        for x in sx
    ]
    # Convenience readings: thinnest/thickest stem crossed by the scanlines.
    stems = [b - a for s in out["scan_y"] for a, b in s["runs"]]
    bars = [b - a for s in out["scan_x"] for a, b in s["runs"]]
    out["stem"] = round(min(stems), 1) if stems else None
    out["bar"] = round(min(bars), 1) if bars else None
    out["contrast"] = round(out["bar"] / out["stem"], 3) if stems and bars and out["stem"] else None
    return out


def font_guides(font: TTFont, scale: float = 1.0) -> dict:
    """Vertical guides of a font (ascent, descent, cap, x-height, Hangul box), scaled."""
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()

    def box(ch):
        name = cmap.get(ord(ch))
        if name is None:
            return None
        bp = BoundsPen(gs)
        gs[name].draw(bp)
        return bp.bounds and tuple(v * scale for v in bp.bounds)

    hhea = font["hhea"]
    g = {
        "upm": font["head"].unitsPerEm,
        "ascent": round(hhea.ascent * scale),
        "descent": round(hhea.descent * scale),
        "italic_angle": float(font["post"].italicAngle) if "post" in font else 0.0,
    }
    for key, ch in (("cap", "H"), ("x", "x"), ("han", "한")):
        b = box(ch)
        if b:
            g[f"{key}_left"], g[f"{key}_bottom"] = round(b[0]), round(b[1])
            g[f"{key}_right"], g[f"{key}_top"] = round(b[2]), round(b[3])
    zero = cmap.get(ord("0"))
    if zero:
        g["half"] = round(font["hmtx"][zero][0] * scale)
    return g


def harmony(font: TTFont, probes: dict) -> dict:
    """Latin vs. Hangul stroke weights (normalised units) and the grade that would match them."""
    cmap = font.getBestCmap()
    k = 1000 / font["head"].unitsPerEm

    def read(ch: str, axis: str) -> float | None:
        name = cmap.get(ord(ch)) if ch else None
        if name is None:
            return None
        geo = glyph_geometry(font, name, k)
        if geo.bounds is None:
            return None
        x0, y0, x1, y1 = geo.bounds
        runs = (
            hruns(geo.polygons, (y0 + y1) / 2)
            if axis == "h"
            else vruns(geo.polygons, (x0 + x1) / 2)
        )
        widths = [b - a for a, b in runs]
        if not widths:
            return None
        # The probes are simple strokes: the centre scanline crosses one stem or bar.
        return round(max(widths), 1)

    out = {
        "latin_stem": read(probes.get("latin_stem", "l"), "h"),
        "latin_bar": read(probes.get("latin_bar", "H"), "v"),
        "hangul_stem": read(probes.get("hangul_stem", "ㅣ"), "h"),
        "hangul_bar": read(probes.get("hangul_bar", "ㅡ"), "v"),
    }
    ls, hs, lb, hb = out["latin_stem"], out["hangul_stem"], out["latin_bar"], out["hangul_bar"]
    out["stem_ratio"] = round(hs / ls, 3) if ls and hs else None
    out["bar_ratio"] = round(hb / lb, 3) if lb and hb else None
    # Grade adds its value to every stroke's thickness, so the stem gap is the grade change.
    out["grade_delta"] = round(ls - hs, 1) if ls and hs else None
    return out


def single_substitutions(font: TTFont, tags: list[str]) -> dict[str, str]:
    """glyph -> alternate for the one-to-one (type 1) lookups of the given GSUB features.

    Enough to preview ssXX/cvXX/zero variants of a single glyph; ligatures and contextual rules
    are shown in the browser with font-feature-settings instead.
    """
    if not tags or "GSUB" not in font:
        return {}
    gsub = font["GSUB"].table
    if not gsub.FeatureList or not gsub.LookupList:
        return {}
    idx = sorted(
        {
            i
            for fr in gsub.FeatureList.FeatureRecord
            if fr.FeatureTag in tags
            for i in fr.Feature.LookupListIndex
        }
    )
    mapping: dict[str, str] = {}
    for i in idx:
        for st in _subtables(gsub.LookupList.Lookup[i]):
            if getattr(st, "mapping", None) and type(st).__name__ == "SingleSubst":
                for k, v in st.mapping.items():
                    mapping.setdefault(k, v)
    return mapping


def _subtables(lookup):
    for st in lookup.SubTable:
        if type(st).__name__ == "ExtensionSubst":
            yield st.ExtSubTable
        else:
            yield st


def gsub_features(font: TTFont) -> list[dict]:
    """GSUB feature tags with a UI name (for ssXX that carry one) and sample characters.

    Samples are the characters whose glyphs a feature's lookups touch, including lookups that
    contextual rules (calt) call, so the tester can show something for every feature.
    """
    if "GSUB" not in font or not font["GSUB"].table.FeatureList:
        return []
    gsub = font["GSUB"].table
    rev: dict[str, int] = {}
    for cp, name in sorted(font.getBestCmap().items(), reverse=True):
        rev[name] = cp
    name_table = font["name"] if "name" in font else None
    lookups = gsub.LookupList.Lookup if gsub.LookupList else []

    def inputs(li: int, seen: set[int]) -> set[str]:
        if li in seen or li >= len(lookups):
            return set()
        seen.add(li)
        out: set[str] = set()
        for st in _subtables(lookups[li]):
            kind = type(st).__name__
            if kind in ("SingleSubst",) and getattr(st, "mapping", None):
                out |= set(st.mapping)
            elif kind in ("AlternateSubst",) and getattr(st, "alternates", None):
                out |= set(st.alternates)
            elif kind == "LigatureSubst" and getattr(st, "ligatures", None):
                out |= set(st.ligatures)
            elif kind == "ChainContextSubst":
                for rec in getattr(st, "SubstLookupRecord", []) or []:
                    out |= inputs(rec.LookupListIndex, seen)
                for rs in getattr(st, "ChainSubRuleSet", []) or []:
                    for rule in getattr(rs, "ChainSubRule", []) or []:
                        for rec in rule.SubstLookupRecord:
                            out |= inputs(rec.LookupListIndex, seen)
        return out

    merged: dict[str, dict] = {}
    for fr in gsub.FeatureList.FeatureRecord:
        tag = fr.FeatureTag
        entry = merged.setdefault(tag, {"tag": tag, "name": None, "glyphs": set()})
        params = fr.Feature.FeatureParams
        if params is not None and name_table is not None and hasattr(params, "UINameID"):
            entry["name"] = entry["name"] or name_table.getDebugName(params.UINameID)
        for li in fr.Feature.LookupListIndex:
            entry["glyphs"] |= inputs(li, set())
    out = []
    for tag in sorted(merged):
        e = merged[tag]
        cps = sorted({rev[g] for g in e["glyphs"] if g in rev})
        out.append({"tag": tag, "name": e["name"], "sample": "".join(map(chr, cps[:24]))})
    return out
