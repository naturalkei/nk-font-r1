"""Design notes for the showcase site (site/design.html): how a glyph is built, from its outline.

For every family and every glyph in config/design.toml this writes, into design.json:
  - the outline (SVG path) and its on/off-curve points, as a font editor shows them;
  - the metric guides (baseline, x-height, cap height, Hangul box, ascent, descent, cells);
  - stroke skeletons snapped onto the real strokes, with each stroke's measured thickness, for the
    numbered stroke-order animation;
  - notes whose numbers are measured here and matched to the shared golden-ratio scale.
Everything is pure fontTools (glyphmetrics), so the synthetic fixture fonts can test it.
"""

from __future__ import annotations

import json
import math
import tomllib
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from . import config
from .glyphmetrics import font_guides, glyph_geometry, hruns, measure_glyph, vruns
from .phi import PHI

Point = tuple[float, float]


def load_design_config(root: Path = config.ROOT) -> dict:
    with (root / "config" / "design.toml").open("rb") as f:
        return tomllib.load(f)


def outline_points(font: TTFont, glyph_name: str, scale: float = 1.0) -> list[list[list]]:
    """Contours as [x, y, on] points in drawing order (y up), like a font editor's point view.

    TrueType contours list their quadratic off-curve points; implied on-curve points between two
    off-curve points are not stored, so they are not listed (the page marks them). CFF contours
    list both cubic handles. Composite glyphs are decomposed.
    """
    gs = font.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[glyph_name].draw(TransformPen(rec, (scale, 0, 0, scale, 0, 0)))
    contours: list[list[list]] = []
    cur: list[list] = []

    def add(pt, on):
        cur.append([round(pt[0], 1), round(pt[1], 1), on])

    for op, args in rec.value:
        if op == "moveTo":
            cur = []
            add(args[0], True)
        elif op == "lineTo":
            add(args[0], True)
        elif op in ("qCurveTo", "curveTo"):
            *offs, last = args
            for p in offs:
                add(p, False)
            if last is not None:
                add(last, True)
        elif op in ("closePath", "endPath"):
            if cur and len(cur) > 1 and cur[-1][:2] == cur[0][:2] and cur[-1][2]:
                cur.pop()  # closing point repeats the start
            if cur:
                contours.append(cur)
            cur = []
    if cur:
        contours.append(cur)
    return contours


def _centres(polys, x: float, y: float) -> list[tuple[float, Point, float]]:
    """Candidate stroke centres near (x, y): (distance, snapped point, stroke thickness)."""
    out = []
    for a, b in hruns(polys, y):  # vertical stroke crossing: move along x
        cx = (a + b) / 2
        out.append((abs(cx - x), (cx, y), b - a))
    for a, b in vruns(polys, x):  # horizontal stroke crossing: move along y
        cy = (a + b) / 2
        out.append((abs(cy - y), (x, cy), b - a))
    return out


def snap(polys, pt: Point, radius: float) -> tuple[Point, bool]:
    """Move `pt` onto the centre line of the nearest stroke, or leave it if none is near.

    A point already on ink moves only across the stroke it sits in; the thinner crossing (the
    stroke's real thickness) wins over the long run along the stroke.
    """
    x, y = pt
    cands = _centres(polys, x, y)
    inside = [c for c in cands if _contains(polys, x, y, c)]
    if inside:
        best = min(inside, key=lambda c: c[2])
        return best[1], True
    near = [c for c in cands if c[0] <= radius]
    if not near:
        return pt, False
    return min(near, key=lambda c: c[0])[1], True


def _contains(polys, x: float, y: float, cand) -> bool:
    (sx, sy), w = cand[1], cand[2]
    return abs(sx - x) + abs(sy - y) <= w / 2 + 1e-6


def _run_at(runs, c: float) -> float | None:
    for lo, hi in runs:
        if lo - 1 <= c <= hi + 1:
            return hi - lo
    return None


def thickness(polys, a: Point, b: Point) -> float | None:
    """Stroke thickness across the segment a-b, perpendicular to it.

    Read at a few points along the middle of the segment and keep the thinnest: where another
    stroke joins (a junction, a serif) the cut is wider than the stroke itself. A diagonal band
    cut by a level line (width hw) and a plumb line (height vw) is hw*vw/sqrt(hw^2 + vw^2) thick.
    """
    dx, dy = b[0] - a[0], b[1] - a[1]
    if not (dx or dy):
        return None
    readings = []
    for t in (0.3, 0.4, 0.5, 0.6, 0.7):
        x, y = a[0] + t * dx, a[1] + t * dy
        hw, vw = _run_at(hruns(polys, y), x), _run_at(vruns(polys, x), y)
        cuts = [c for c in (hw, vw) if c]
        if hw and vw and abs(dx) > 0.1 * abs(dy) and abs(dy) > 0.1 * abs(dx):
            cuts.append(hw * vw / math.hypot(hw, vw))
        # The thinnest cut is the stroke: a stem's plumb cut runs along it, a bar's level one too.
        r = min(cuts) if cuts else None
        if r:
            readings.append(r)
    return round(min(readings), 1) if readings else None


AXIS_TOL = 0.06  # a segment within this share of the ink box of level/plumb is a bar/stem


def _line(polys, kind: str, a: Point, b: Point, radius: float) -> tuple[float, float] | None:
    """Centre and thickness of the bar (kind "h") or stem ("v") the segment a-b lies on.

    Cuts across the segment at a few points along it and keeps the crossing whose centre is
    nearest the segment; the thinnest crossing at that centre is the stroke's thickness.
    """
    # Each cut votes for the stroke centre nearest the segment; the median vote wins, so one
    # cut through a junction (where the stroke widens into another) does not pull the line.
    votes = []
    for t in (0.5, 0.35, 0.65, 0.2, 0.8):
        if kind == "h":
            near, runs = (a[1] + b[1]) / 2, vruns(polys, a[0] + t * (b[0] - a[0]))
        else:
            near, runs = (a[0] + b[0]) / 2, hruns(polys, a[1] + t * (b[1] - a[1]))
        cs = [(lo + hi) / 2 for lo, hi in runs if abs((lo + hi) / 2 - near) <= radius]
        if cs:
            votes.append(min(cs, key=lambda c: abs(c - near)))
    if not votes:
        return None
    c0 = sorted(votes)[len(votes) // 2]
    # Thickness: thinnest crossing that stays on this stroke (junctions read wider).
    widths = []
    for t in (0.3, 0.4, 0.5, 0.6, 0.7):
        if kind == "h":
            runs = vruns(polys, a[0] + t * (b[0] - a[0]))
        else:
            runs = hruns(polys, a[1] + t * (b[1] - a[1]))
        widths += [hi - lo for lo, hi in runs if lo - 1 <= c0 <= hi + 1]
    return c0, min(widths) if widths else 0.0


def _extent(polys, kind: str, centre: float, along: float) -> tuple[float, float] | None:
    """Ink run along the stroke's centre line that contains `along`: where the stroke ends."""
    runs = hruns(polys, centre) if kind == "h" else vruns(polys, centre)
    for lo, hi in runs:
        if lo - 1 <= along <= hi + 1:
            return lo, hi
    return None


def place_stroke(polys, spec: dict, bounds, radius: float) -> dict:
    """Fit a skeleton from config/design.toml onto the real strokes of a glyph.

    Level and plumb segments snap as a whole onto the centre line of their bar or stem (so a bar
    stays level), corners take the x of their stem and the y of their bar, and free ends run to
    where the ink ends. Diagonal-only points snap to the nearest stroke centre. A `ring` (u, v,
    ru, rv) is traced around its counter with rays, counter-clockwise from the top.
    """
    x0, y0, x1, y1 = bounds
    w, h = x1 - x0, y1 - y0
    if "ring" in spec:
        return _ring(polys, spec["ring"], bounds, radius)
    uv = spec["pts"]
    pts = [(x0 + u * w, y0 + v * h) for u, v in uv]
    kinds = []
    for (u0, v0), (u1, v1) in zip(uv, uv[1:], strict=False):
        kinds.append("h" if abs(v1 - v0) <= AXIS_TOL else "v" if abs(u1 - u0) <= AXIS_TOL else "d")
    lines: list[tuple[float, float] | None] = []
    misses = 0
    for i, k in enumerate(kinds):
        ln = _line(polys, k, pts[i], pts[i + 1], radius) if k != "d" else None
        if k != "d" and ln is None:
            misses += 1  # keep the segment level/plumb where the config put it
            ax = 1 if k == "h" else 0
            ln = ((pts[i][ax] + pts[i + 1][ax]) / 2, 0.0)
        lines.append(ln)
    out = []
    for i, (x, y) in enumerate(pts):
        adj = [j for j in (i - 1, i) if 0 <= j < len(kinds)]
        nx = next((lines[j][0] for j in adj if kinds[j] == "v" and lines[j]), None)
        ny = next((lines[j][0] for j in adj if kinds[j] == "h" and lines[j]), None)
        if nx is None and ny is None:
            (nx, ny), ok = snap(polys, (x, y), radius)
            misses += not ok
        out.append([nx if nx is not None else x, ny if ny is not None else y])
    # Free ends of bars and stems stop where their ink stops (half a stroke in from the edge).
    for end, j in ((0, 0), (len(out) - 1, len(kinds) - 1)):
        if j < 0 or kinds[j] == "d" or not lines[j]:
            continue
        kind, (centre, thick) = kinds[j], lines[j]
        ax = 0 if kind == "h" else 1
        other = out[1 if end == 0 else -2][ax]
        mid = (out[end][ax] + other) / 2
        ext = _extent(polys, kind, centre, mid)
        if ext:
            lo, hi = ext
            inset = min(thick / 2, (hi - lo) / 4) if thick else 0
            out[end][ax] = lo + inset if out[end][ax] < other else hi - inset
    # Thickness of the stroke's body: its longest segment, read away from the joints.
    seg = max(zip(out, out[1:], strict=False), key=lambda s: math.dist(s[0], s[1]))
    return {
        "pts": [[round(x, 1), round(y, 1)] for x, y in out],
        "curve": False,
        "w": thickness(polys, tuple(seg[0]), tuple(seg[1])),
        "misses": misses,
    }


def _ray(polys, cx: float, cy: float, ang: float, inner: float, limit: float):
    """First ink run along a ray from (cx, cy) that reaches past `inner`: (centre, length).

    From inside a counter the first run is the bowl's own wall; `inner` skips a dot or slash
    drawn inside the counter (as in a dotted zero).
    """
    dx, dy = math.cos(ang), math.sin(ang)
    inside, start, r = False, 0.0, 0.0
    while r < limit:
        x, y = cx + dx * r, cy + dy * r
        hit = any(lo <= x <= hi for lo, hi in hruns(polys, y))
        if hit and not inside:
            inside, start = True, r
        elif not hit and inside:
            inside = False
            if r > inner:
                return (start + r) / 2, r - start
        r += 2.0
    return None


def _counter(polys, cx: float, cy: float) -> tuple[float, float]:
    """Centre of the bowl around (cx, cy), between its nearest walls on each side.

    Ink straddling the guess (the dot or slash inside a zero) is not a wall and is skipped.
    """

    def walls(runs, c):
        left = [hi for lo, hi in runs if hi < c]
        right = [lo for lo, hi in runs if lo > c]
        return (max(left) + min(right)) / 2 if left and right else c

    x = walls(hruns(polys, cy), cx)
    y = walls(vruns(polys, x), cy)
    return walls(hruns(polys, y), x), y


def _ring(polys, ring, bounds, radius: float) -> dict:
    x0, y0, x1, y1 = bounds
    w, h = x1 - x0, y1 - y0
    cu, cv, ru, rv = ring
    cx, cy = _counter(polys, x0 + cu * w, y0 + cv * h)
    pts, widths, misses = [], [], 0
    n = 24
    for i in range(n + 1):
        ang = math.pi / 2 + 2 * math.pi * i / n  # top, then counter-clockwise
        ex = math.hypot(ru * w * math.cos(ang), rv * h * math.sin(ang))
        hit = _ray(polys, cx, cy, ang, 0.6 * ex, ex + radius)
        if hit is None:
            misses += 1
            d = ex
        else:
            d = hit[0]
            if i % (n // 4) == 0 and i < n:  # level and plumb rays cross the bowl square on
                widths.append(hit[1])
        pts.append([round(cx + math.cos(ang) * d, 1), round(cy + math.sin(ang) * d, 1)])
    return {
        "pts": pts,
        "curve": True,
        "w": round(min(widths), 1) if widths else None,
        "misses": misses,
    }


def phi_step(value: float | None, tol: float = 0.02, divisions: int = 6) -> dict | None:
    """Nearest step of the shared scale phi^(step/divisions) and how far `value` is from it."""
    if not value or value <= 0:
        return None
    step = round(divisions * math.log(value) / math.log(PHI))
    target = PHI ** (step / divisions)
    dev = value / target - 1
    return {"step": step, "target": round(target, 3), "dev": round(dev, 4), "on": abs(dev) <= tol}


def _phi_label(step: int, divisions: int = 6) -> str:
    if step == 0:
        return "1"
    g = math.gcd(abs(step), divisions)
    num, den = step // g, divisions // g
    return "φ" if (num, den) == (1, 1) else f"φ^{num}" if den == 1 else f"φ^({num}/{den})"


def ratio_note(label: str, value: float | None, tol: float) -> dict | None:
    st = phi_step(value, tol)
    if st is None:
        return None
    return {
        "label": label,
        "value": round(value, 3),
        "phi": _phi_label(st["step"]),
        "target": st["target"],
        "dev": st["dev"],
        "on": st["on"],
    }


def glyph_note(font: TTFont, ch: str, spec: dict, guides: dict, page: dict) -> dict | None:
    cmap = font.getBestCmap()
    name = cmap.get(ord(ch))
    if name is None:
        return None
    k = 1000 / font["head"].unitsPerEm
    geo = glyph_geometry(font, name, k)
    if geo.bounds is None:
        return None
    x0, y0, x1, y1 = geo.bounds
    w, h = x1 - x0, y1 - y0
    radius = page.get("snap_radius", 0.16) * max(w, h)
    strokes, misses = [], 0
    for i, st in enumerate(spec.get("strokes", []), 1):
        placed = place_stroke(geo.polygons, st, geo.bounds, radius)
        misses += placed.pop("misses")
        strokes.append({"n": i, **placed})
    if misses > page.get("max_misses", 2):
        strokes = []  # the skeleton does not fit this family's drawing: show no stroke order
    m = measure_glyph(geo)
    tol = page.get("phi_tolerance", 0.02)
    widths = [s["w"] for s in strokes if s["w"]]
    ratios = []
    hangul = 0xAC00 <= ord(ch) <= 0xD7A3
    if hangul and guides.get("cap_top"):
        ratios.append(ratio_note("높이 / 대문자 높이", h / guides["cap_top"], tol))
    ratios.append(ratio_note("잉크 폭 / 높이", w / h if h else None, tol))
    if widths and len(widths) > 1:
        ratios.append(ratio_note("가장 굵은 획 / 가장 가는 획", max(widths) / min(widths), tol))
    if guides.get("half"):
        cells = round(geo.advance / guides["half"])
        fill = w / geo.advance if geo.advance else None
        ratios.append(ratio_note("잉크 폭 / 글자 폭", fill, tol))
    else:
        cells = None
    return {
        "ch": ch,
        "title": spec.get("title", ch),
        "note": spec.get("note", ""),
        "name": name,
        "adv": geo.advance,
        "cells": cells,
        "box": [round(x0), round(y0), round(x1), round(y1)],
        "path": geo.path,
        "contours": outline_points(font, name, k),
        "strokes": strokes,
        "misses": misses,
        "lsb": m["lsb"],
        "rsb": m["rsb"],
        "ink": m["ink"],
        "coverage": m["coverage"],
        "stem": m["stem"],
        "bar": m["bar"],
        "slant": m["slant"],
        "ratios": [r for r in ratios if r],
    }


def family_notes(font: TTFont, cfg: dict) -> dict:
    page = cfg.get("page", {})
    k = 1000 / font["head"].unitsPerEm
    guides = font_guides(font, k)
    glyphs = []
    for spec in cfg.get("glyph", []):
        g = glyph_note(font, spec["ch"], spec, guides, page)
        if g:
            glyphs.append(g)
    # TrueType outlines are quadratic (implied on-curve points), CFF ones cubic.
    curves = "quadratic" if "glyf" in font else "cubic"
    return {"guides": guides, "curves": curves, "glyphs": glyphs}


def build_design(out: Path, fonts: dict[str, dict], root: Path = config.ROOT) -> dict:
    """Write design.json into the site directory `out`.

    `fonts` maps family id -> {"family", "path" (Regular TTF), "kind"}.
    """
    cfg = load_design_config(root)
    order = cfg.get("page", {}).get("families", [])
    rank = {fid: i for i, fid in enumerate(order)}
    families = []
    for fid, info in sorted(fonts.items(), key=lambda kv: rank.get(kv[0], len(order))):
        entry = {"id": fid, "family": info["family"], "kind": info.get("kind", "merge")}
        entry.update(family_notes(TTFont(info["path"]), cfg))
        families.append(entry)
    data = {"phi": PHI, "families": families}
    (out / "design.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return data
