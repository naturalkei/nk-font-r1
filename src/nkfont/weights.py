"""Thin (100) to ExtraBold (800): weight names, stem measurement and weight synthesis.

Every family lists its weights in `config/families/<id>.toml` as `[[weight]]` tables. A weight
uses real upstream masters where the upstream ships that weight; where it does not, the build
derives it from the nearest master by offsetting the outline edges (`offset_outline`, like a GRAD
axis: advances never change):

  latin_grade = -40     Latin outlines thinned (or thickened) by 40 units at UPM 1000
  hangul_grade = 12     Hangul grade added on top of [hangul].grade (overrides matching)

`[weights] match = "stem+bar"` keeps Hangul and Latin from drifting apart across weights: each
weight's Hangul grade is solved so that Hangul stem / Latin stem equals the reference weight's
ratio (the designer-tuned Regular), and the change of horizontal strokes so that the bar
ratio holds too ("stem" solves the stem grade only). `[weights] contrast` is that
share for Latin synthesis and for "stem" (serif and myeongjo faces keep their hairlines with a
low value).

No knob is set by default, so a family without `[weights]` builds exactly as before.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont

from .glyphmetrics import glyph_geometry, hruns, vruns
from .merge import embolden

# OpenType usWeightClass for the standard names (OpenType spec, OS/2 table).
WEIGHT_CLASSES = {
    "Thin": 100,
    "ExtraLight": 200,
    "Light": 300,
    "Regular": 400,
    "Medium": 500,
    "SemiBold": 600,
    "Bold": 700,
    "ExtraBold": 800,
    "Black": 900,
}
# The range every family ships (the brief: Thin through ExtraBold).
STANDARD = tuple(n for n, c in WEIGHT_CLASSES.items() if c <= 800)

# Probe glyphs: simple strokes whose centre scanline crosses exactly one stem or bar.
PROBES = {"latin_stem": "l", "latin_bar": "H", "hangul_stem": "ㅣ", "hangul_bar": "ㅡ"}


def settings(fam: dict) -> dict:
    return fam.get("weights", {})


def reference_name(fam: dict) -> str:
    return settings(fam).get("reference", "Regular")


def default_weight(fam: dict) -> str:
    """The weight tools open first: Regular if the family has one."""
    names = [w["name"] for w in fam["weight"]]
    return "Regular" if "Regular" in names else names[0]


def sorted_weights(fam: dict) -> list[dict]:
    """Weights in usWeightClass order (Thin first), for display."""
    return sorted(fam["weight"], key=lambda w: w["weight_class"])


def stroke(font: TTFont, ch: str, axis: str = "h") -> float | None:
    """Width of the stroke the centre scanline crosses, in units at UPM 1000.

    axis "h": horizontal scanline, a vertical stem's width; "v": vertical scanline, a bar.
    """
    name = font.getBestCmap().get(ord(ch))
    if name is None:
        return None
    geo = glyph_geometry(font, name, 1000 / font["head"].unitsPerEm)
    if geo.bounds is None:
        return None
    x0, y0, x1, y1 = geo.bounds
    runs = hruns(geo.polygons, (y0 + y1) / 2) if axis == "h" else vruns(geo.polygons, (x0 + x1) / 2)
    widths = [b - a for a, b in runs]
    return max(widths) if widths else None


@lru_cache(maxsize=64)
def _source_stroke(path: str, mtime: float, ch: str, axis: str) -> float | None:
    return stroke(TTFont(path, lazy=True), ch, axis)


def source_stroke(path: Path, ch: str, axis: str = "h") -> float | None:
    """`stroke` of an upstream file, cached (the solver asks for the same few glyphs often)."""
    return _source_stroke(str(path), path.stat().st_mtime, ch, axis)


def hangul_scale(fam: dict) -> float:
    """Horizontal scale merge_hangul applies to a 1000-UPM Hangul source (stems are vertical)."""
    h = fam.get("hangul", {})
    return h.get("scale", 0.96) * h.get("width", 1.0)


def latin_stroke(fam: dict, weight: dict, srcs: dict, axis: str = "h") -> float | None:
    """Latin stem ("h") or bar ("v") of a weight, after its latin_grade (UPM 1000 units)."""
    cfg = settings(fam)
    ch = cfg.get("latin_probe", "l") if axis == "h" else cfg.get("latin_bar_probe", "H")
    s = source_stroke(srcs[weight["latin"]].path, ch, axis)
    if s is None:
        return None
    g = weight.get("latin_grade", 0.0)
    return s + (g if axis == "h" else g * cfg.get("contrast", 1.0))


def hangul_stroke(fam: dict, weight: dict, srcs: dict, axis: str = "h") -> float | None:
    """Hangul stem ("h") or bar ("v") after the merge's scale, before any grade (UPM 1000)."""
    cfg = settings(fam)
    ch = cfg.get("hangul_probe", "ㅣ") if axis == "h" else cfg.get("hangul_bar_probe", "ㅡ")
    s = source_stroke(srcs[weight["hangul"]].path, ch, axis)
    if s is None:
        return None
    h = fam.get("hangul", {})
    return s * (hangul_scale(fam) if axis == "h" else h.get("scale", 0.96))


def latin_stem(fam: dict, weight: dict, srcs: dict) -> float | None:
    return latin_stroke(fam, weight, srcs, "h")


def hangul_stem(fam: dict, weight: dict, srcs: dict) -> float | None:
    return hangul_stroke(fam, weight, srcs, "h")


def hangul_weight(fam: dict, weight: dict, srcs: dict) -> tuple[float, float | None]:
    """(grade to add to [hangul].grade, vertical grade or None) for this weight's Hangul.

    An explicit `hangul_grade` wins. `[weights] match = "stem"` solves the grade so that
    Hangul stem / Latin stem equals the reference weight's ratio; "stem+bar" also solves the
    vertical amount (horizontal strokes) so the bar ratio holds too. None means "grade times
    the family contrast". The reference weight always gets (0, None): it builds as before.
    """
    cfg = settings(fam)
    if "hangul_grade" in weight:
        return float(weight["hangul_grade"]), weight.get("hangul_grade_y")
    match = cfg.get("match", "none")
    if match not in ("stem", "stem+bar") or weight["name"] == reference_name(fam):
        return 0.0, None
    ref = next(w for w in fam["weight"] if w["name"] == reference_name(fam))
    g0 = fam.get("hangul", {}).get("grade", 0.0)
    keep = cfg.get("min_keep", 0.35)
    lr, hr = latin_stroke(fam, ref, srcs), hangul_stroke(fam, ref, srcs)
    lw, hw = latin_stroke(fam, weight, srcs), hangul_stroke(fam, weight, srcs)
    if None in (lr, hr, lw, hw) or not lr:
        return 0.0, None
    delta = (hr + g0) / lr * lw - hw - g0
    # Thinning past most of a stroke would erase hairlines: keep at least `min_keep` of it.
    delta = round(max(delta, -(1 - keep) * hw), 1)
    # A real master that already matches within `deadband` units is left exactly as drawn.
    dead = cfg.get("deadband", 3.0)
    if abs(delta) < dead:
        delta = 0.0
    if match != "stem+bar":
        return delta, None
    lbr, hbr = latin_stroke(fam, ref, srcs, "v"), hangul_stroke(fam, ref, srcs, "v")
    lbw, hbw = latin_stroke(fam, weight, srcs, "v"), hangul_stroke(fam, weight, srcs, "v")
    if None in (lbr, hbr, lbw, hbw) or not lbr:
        return delta, None
    contrast = cfg.get("contrast", 1.0)
    target = (hbr + g0 * contrast) / lbr * lbw
    dy = round(max(target - hbw, -(1 - keep) * hbw), 1)
    if abs(dy - delta * contrast) < dead:
        return delta, None
    return delta, dy


def hangul_grade_delta(fam: dict, weight: dict, srcs: dict) -> float:
    return hangul_weight(fam, weight, srcs)[0]


def thin_hinting(font: TTFont) -> None:
    """Drop TrueType hinting; moved outlines would be distorted by the old instructions."""
    for tag in ("fpgm", "prep", "cvt ", "hdmx", "LTSH", "VDMX"):
        if tag in font:
            del font[tag]
    glyf = font["glyf"]
    for name in font.getGlyphOrder():
        g = glyf[name]
        if hasattr(g, "program"):
            g.program.fromBytecode(b"")
    if "gasp" in font:  # unhinted: smooth at every size
        font["gasp"].gaspRange = {0xFFFF: 0x000F}
    font["maxp"].maxSizeOfInstructions = 0


def merged_outline(draw, glyph_set=None):
    """Draw `draw(pen)` into one overlap-free path (skia-pathops): components and overlapping
    contours become one outline, so moving its edges cannot open gaps between parts."""
    import pathops

    path = pathops.Path()
    pen = path.getPen(glyphSet=glyph_set)
    draw(pen)
    try:
        return pathops.simplify(path, clockwise=path.clockwise)
    except pathops.PathOpsError:  # skia bug with near-coincident float points: round first
        rounded = _rounded(path)
        return pathops.simplify(rounded, clockwise=rounded.clockwise)


def _rounded(path):
    import pathops

    out = pathops.Path()
    path.draw(_RoundingPen(out.getPen()))
    return out


def offset_outline(path, amount: float):
    """Grow (amount > 0) or shrink every stroke of an overlap-free pathops Path by `amount`.

    A true geometric offset: a stroke of width |amount| along the outline is added (union) or
    cut away (difference), so curves and joins stay clean even when the move is a large share
    of the stroke (moving points along their normals folds tight curves over themselves).
    The input's contour direction is kept.
    """
    import pathops

    cw = path.clockwise
    if abs(amount) < 0.5:
        return path
    ring = pathops.Path()
    path.draw(ring.getPen())
    ring.stroke(abs(amount), pathops.LineCap.BUTT_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    ring.convertConicsToQuads()  # round joins are conics; path ops take quads and cubics
    kind = pathops.PathOp.UNION if amount > 0 else pathops.PathOp.DIFFERENCE
    try:
        return pathops.op(path, ring, kind, clockwise=cw)
    except pathops.PathOpsError:  # skia's near-coincident point bug: retry on integers
        return pathops.op(_rounded(path), _rounded(ring), kind, clockwise=cw)


def split_offset(ax: float, ay: float) -> tuple[float, float, float]:
    """(isotropic, residual x, residual y) for a stem change `ax` and bar change `ay`.

    The geometric offset (offset_outline) takes the part both axes share, the smaller move,
    so thin joins and hairlines are never cut by more than the lighter axis needs; the rest
    is a one-axis point move (`merge.embolden`), which is safe along straight stems and bars.
    """
    iso = (ax if abs(ax) <= abs(ay) else ay) if ax * ay > 0 else 0.0
    return iso, ax - iso, ay - iso


class _RoundingPen:
    def __init__(self, pen):
        self.pen = pen

    def __getattr__(self, name):
        method = getattr(self.pen, name)

        def call(*pts):
            return method(*[(round(p[0]), round(p[1])) if isinstance(p, tuple) else p for p in pts])

        return call if name in ("moveTo", "lineTo", "curveTo", "qCurveTo") else method


def synthesize(font: TTFont, amount: float, contrast: float = 1.0) -> None:
    """Embolden (amount > 0) or thin every outline of a TrueType font by `amount` (UPM 1000).

    Horizontal strokes change by `amount * contrast`. Composites are decomposed and overlaps
    merged first, so parts cannot pull apart. Advances stay; left side bearings follow the new
    outlines.
    """
    if not amount:
        return
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    k = font["head"].unitsPerEm / 1000
    gs = font.getGlyphSet()
    glyf, hmtx = font["glyf"], font["hmtx"]
    new = {}
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.numberOfContours == 0:
            continue
        pen = TTGlyphPen(None)
        iso, rx, ry = split_offset(amount * k, amount * k * contrast)
        try:
            path = offset_outline(merged_outline(gs[name].draw, gs), iso)
            path.draw(Cu2QuPen(pen, max_err=1.0))
            new[name] = pen.glyph()
            embolden(new[name], rx, amount_y=ry)
        except Exception:  # skia could not combine this outline: move its points instead
            if g.numberOfContours < 0:
                continue  # composite: its components are offset themselves
            embolden(g, amount * k, contrast)
            new[name] = g
    for name, g in new.items():
        glyf[name] = g
    for name in font.getGlyphOrder():
        g = glyf[name]
        g.recalcBounds(glyf)
        adv, _ = hmtx[name]
        hmtx[name] = (adv, getattr(g, "xMin", 0))
    thin_hinting(font)


def pixel_bold(font: TTFont, px: int) -> int:
    """Bitmap-style bold for a pixel face: every vertical stroke `px` font units (one pixel)
    wider, horizontal strokes untouched, outlines kept on the pixel grid.

    The extra pixel goes to the right, or to the left when the right side would leave the
    cell; a glyph that already fills its cell on both sides stays as drawn, so no ink ever
    crosses into the next terminal cell. Returns the number of glyphs left unchanged that way.
    """
    glyf, hmtx = font["glyf"], font["hmtx"]
    kept = 0
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.numberOfContours <= 0:
            continue
        g.recalcBounds(glyf)
        adv = hmtx[name][0]
        if g.xMax + px <= adv:
            dx = px // 2
        elif g.xMin - px >= 0:
            dx = -(px // 2)
        else:
            kept += 1
            continue
        embolden(g, px, 0.0)
        g.coordinates.translate((dx, 0))
    for name in font.getGlyphOrder():
        g = glyf[name]
        g.recalcBounds(glyf)
        hmtx[name] = (hmtx[name][0], getattr(g, "xMin", 0))
    thin_hinting(font)
    return kept


def harmony_row(font: TTFont) -> dict:
    """Latin and Hangul stems and bars of a built master (UPM 1000) and their ratios."""
    out = {
        "latin_stem": stroke(font, PROBES["latin_stem"], "h"),
        "latin_bar": stroke(font, PROBES["latin_bar"], "v"),
        "hangul_stem": stroke(font, PROBES["hangul_stem"], "h"),
        "hangul_bar": stroke(font, PROBES["hangul_bar"], "v"),
    }
    ls, lb, hs, hb = (out[k] for k in ("latin_stem", "latin_bar", "hangul_stem", "hangul_bar"))
    out["stem_ratio"] = round(hs / ls, 3) if hs and ls else None
    out["bar_ratio"] = round(hb / lb, 3) if hb and lb else None
    for k in ("latin_stem", "latin_bar", "hangul_stem", "hangul_bar"):
        out[k] = None if out[k] is None else round(out[k], 1)
    return out


def check_weight_ladder(
    rows: list[tuple[str, int, dict]], tol: dict | None = None, independent=()
) -> list[str]:
    """Problems in a family's weights: (style, usWeightClass, harmony_row) in any order.

    - every stroke reading must grow with the weight class (Thin lighter than Light ...)
    - the Hangul/Latin stem ratio must stay within `tol["stem"]` of the reference (Regular)
      ratio, and the bar ratio within `tol["bar"]`: Hangul must not drift lighter or darker
      than the Latin next to it as the weight changes. Weights in `independent` pair other
      sources of their own (NK Comics Black = Gasoek One) and skip the ratio comparison.
    """
    tol = {"stem": 0.10, "bar": 0.20, **(tol or {})}
    problems = []
    rows = sorted(rows, key=lambda r: r[1])
    for key in ("latin_stem", "hangul_stem", "latin_bar", "hangul_bar"):
        prev = None
        for style, _, row in rows:
            v = row.get(key)
            if v is None:
                continue
            if prev and v < prev[1] - 0.5:
                problems.append(f"{key}: {style} {v} is lighter than {prev[0]} {prev[1]}")
            prev = (style, v)
    ref = next((r for r in rows if r[0] == "Regular"), rows[0] if rows else None)
    if ref is None:
        return problems
    for key, t in (("stem_ratio", tol["stem"]), ("bar_ratio", tol["bar"])):
        base = ref[2].get(key)
        if not base:
            continue
        for style, _, row in rows:
            v = row.get(key)
            if v is None or style in independent:
                continue
            drift = v / base - 1
            if abs(drift) > t:
                problems.append(
                    f"{key}: {style} {v} vs {ref[0]} {base} ({drift:+.0%}, limit ±{t:.0%})"
                )
    return problems


def check_weight_names(font: TTFont, legacy: bool = True) -> list[str]:
    """usWeightClass, style names and the bold bits agree for one font.

    `legacy` also checks the RIBBI naming of our masters (nameID 1/2); the Nerd Fonts patcher
    writes its own legacy names, so patched fonts are checked without it.
    """
    problems = []
    name = font["name"]
    style = name.getDebugName(17) or name.getDebugName(2) or ""
    cls = font["OS/2"].usWeightClass
    want = WEIGHT_CLASSES.get(style.replace(" Italic", "").replace("Italic", "") or "Regular")
    if want is not None and cls != want:
        problems.append(f"{style}: usWeightClass {cls}, expected {want}")
    bold = style in ("Bold", "Bold Italic")
    if bool(font["OS/2"].fsSelection & 0x20) != bold:
        problems.append(f"{style}: fsSelection BOLD bit is {'set' if not bold else 'clear'}")
    if bool(font["head"].macStyle & 1) != bold:
        problems.append(f"{style}: head.macStyle bold bit is {'set' if not bold else 'clear'}")
    if legacy and style not in ("Regular", "Bold", "Italic", "Bold Italic"):
        legacy = name.getDebugName(2)
        if legacy not in ("Regular", "Italic"):
            problems.append(f"{style}: legacy style (nameID 2) is {legacy!r}, not Regular")
        fam1, fam16 = name.getDebugName(1), name.getDebugName(16)
        if fam1 != f"{fam16} {style}":
            problems.append(f"{style}: legacy family (nameID 1) {fam1!r} != '{fam16} {style}'")
    return problems
