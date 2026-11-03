"""Hangul/Latin harmony QA for every style preset (`nkfont presets`, qa stage "preset harmony").

A preset may push a family anywhere inside its character, but Hangul and Latin must still read
as one face. Each preset is built (the same preview build the /presets page shows) and measured
over sample words in both scripts:

  height    Hangul ink height ÷ Latin cap height (H)                     size
  centre    Hangul ink centre − cap centre, 1000-UPM units               vertical alignment
  weight    Hangul mean stroke width ÷ Latin mean stroke width           stroke weight
            (mean stroke width = 2 × ink area ÷ outline length, over the sample words)
  contrast  Hangul (bar ÷ stem) ÷ Latin (bar ÷ stem); bars and stems are the median ink runs
            of vertical and horizontal scanlines through the sample words  stroke contrast
  colour    Hangul ink density ÷ Latin ink density (ink ÷ advance box)    typographic colour
  slant     Hangul stem angle − Latin stem angle (ㅣ vs l, or ㅏ vs I), degrees  lean
  spacing   Hangul side-bearing share ÷ Latin side-bearing share         proportional families
  grid      terminal families: advances not 0 / half / full              cell grid
  overflow  ink outside the advance box (1000-UPM units; NK Pixel: whole pixels)
  pixels    NK Pixel: points off the pixel grid
  split     NK Pixel: shape knobs (bold, heavy, italic, shadow) applied to one script only
  gaps      NK Pixel: share of the one-pixel white gaps between strokes (를's bars, m's stems)
            that survive, per script, the lower of the two
  broken    contours that turned inside out (e.g. too much negative grade)

Hand-lettering wobble ([style] bounce / tilt) is random per glyph by design and a pixel italic
shifts every glyph alike, so size, weight and lean are measured on the same preset without
them; overflow, grid and broken use the real build.
Allowed bands live in config/preset_qa.toml per family kind; values are 1000-UPM units.
"""

from __future__ import annotations

import base64
import io
import math
import statistics
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config
from .glyphmetrics import area, font_guides, glyph_geometry, hruns, vruns

LATIN_WORDS = "Hamburgefontsiv"
HANGUL_WORDS = "다람쥐헌쳇바퀴에타고파한국을를"
QA_TEXT = "H x l I ㅣ ㅏ ㅡ 0 " + LATIN_WORDS + " " + HANGUL_WORDS
WOBBLE = ("bounce", "tilt")
PIXEL_SHAPE = ("bold", "heavy", "italic", "shadow")


def load_bands(root: Path = config.ROOT) -> dict:
    with (root / "config" / "preset_qa.toml").open("rb") as f:
        return tomllib.load(f)


def _geos(font: TTFont, text: str):
    k = 1000 / font["head"].unitsPerEm
    cmap = font.getBestCmap()
    for ch in text:
        name = cmap.get(ord(ch))
        if name is not None:
            geo = glyph_geometry(font, name, k)
            if geo.advance and geo.bounds is not None:
                yield geo


def script_stats(font: TTFont, text: str) -> dict:
    """Stroke width, bar/stem runs, ink density and side-bearing share of `text`'s glyphs."""
    ink = perim = box = gap = adv = 0.0
    stems: list[float] = []
    bars: list[float] = []
    for geo in _geos(font, text):
        ink += area(geo.polygons)
        perim += sum(math.dist(p[i], p[i - 1]) for p in geo.polygons for i in range(len(p)))
        box += geo.advance * 1000
        x0, y0, x1, y1 = geo.bounds
        gap += geo.advance - (x1 - x0)
        adv += geo.advance
        for i in range(1, 8):
            stems += [b - a for a, b in hruns(geo.polygons, y0 + (y1 - y0) * i / 8)]
            bars += [b - a for a, b in vruns(geo.polygons, x0 + (x1 - x0) * i / 8)]

    def typical(runs):
        # Long runs follow a stroke instead of crossing it: keep the shorter two thirds.
        runs = sorted(runs)[: max(1, len(runs) * 2 // 3)]
        return statistics.median(runs) if runs else None

    return {
        "stroke": 2 * ink / perim if perim else None,
        "stem": typical(stems),
        "bar": typical(bars),
        "density": ink / box if box else None,
        "gap": gap / adv if adv else None,
    }


def _stem_angle(font: TTFont, chars: str) -> float | None:
    """Lean of a single-stem probe in degrees (positive leans right).

    Fits the centre of the widest ink run on rows between 20 % and 80 % of the ink height with
    a Theil-Sen median, so it works for heavy display faces too (glyphmetrics.slant_fit skips
    runs as wide as the glyph). The first probe that has an outline is used.
    """
    for ch in chars:
        geo = next(_geos(font, ch), None)
        if geo is None:
            continue
        _, y0, _, y1 = geo.bounds
        pts = []
        for i in range(9):
            y = y0 + (y1 - y0) * (0.2 + 0.6 * i / 8)
            runs = hruns(geo.polygons, y)
            if runs:
                a, b = max(runs, key=lambda r: r[1] - r[0])
                pts.append(((a + b) / 2, y))
        if len(pts) < 3:
            continue
        slopes = sorted(
            (q[0] - p[0]) / (q[1] - p[1]) for i, p in enumerate(pts) for q in pts[i + 1 :]
        )
        return round(math.degrees(math.atan(slopes[len(slopes) // 2])), 2)
    return None


def _signed_areas(font: TTFont, name: str) -> list[float]:
    glyf = font["glyf"]
    coords, ends, _ = glyf[name].getCoordinates(glyf)
    out, start = [], 0
    for end in ends:
        pts = [coords[i] for i in range(start, end + 1)]
        n = len(pts)
        out.append(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(n)) / 2)
        start = end + 1
    return out


def broken_contours(base: TTFont, styled: TTFont, text: str) -> int:
    """Contours whose winding flipped (or collapsed) between the plain and the styled build.

    Only for outline transforms: pixel restyling redraws whole glyphs (pixelstyle.outline keeps
    the winding right), so run() skips it for NK Pixel.
    """
    if "glyf" not in base or "glyf" not in styled:
        return 0
    bc, sc = base.getBestCmap(), styled.getBestCmap()
    n = 0
    for ch in set(text):
        a, b = bc.get(ord(ch)), sc.get(ord(ch))
        if a is None or b is None:
            continue
        sa, sb = _signed_areas(base, a), _signed_areas(styled, b)
        if len(sa) != len(sb):
            continue  # pixel restyling redraws glyphs; there is nothing to pair
        n += sum(1 for x, y in zip(sa, sb, strict=True) if x and (y == 0 or (x > 0) != (y > 0)))
    return n


def _gap_count(font: TTFont, text: str, px: int) -> int:
    """White runs with ink on both sides, along every row and column of `text`'s bitmaps."""
    from .pixelstyle import _polygons, rasterize

    glyf, cmap = font["glyf"], font.getBestCmap()
    n = 0
    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        bits = rasterize(_polygons(glyf[name], glyf), px)
        for axis in (0, 1):
            lines: dict[int, list[int]] = {}
            for pt in bits:
                lines.setdefault(pt[1 - axis], []).append(pt[axis])
            for pos in lines.values():
                pos.sort()
                n += sum(1 for a, b in zip(pos, pos[1:], strict=False) if b - a > 1)
    return n


def pixel_gaps(
    base: TTFont, styled: TTFont, px: int, texts: tuple[str, ...] = (LATIN_WORDS, HANGUL_WORDS)
) -> float:
    """Share of `base`'s one-pixel-or-wider gaps still open in `styled`, worst script first."""
    kept = []
    for text in texts:
        before = _gap_count(base, text, px)
        kept.append(_gap_count(styled, text, px) / before if before else 1.0)
    return round(min(kept), 3)


def _ratio(a, b, nd: int = 3):
    return round(a / b, nd) if a is not None and b else None


def measure(font: TTFont, kind: str, px: int | None = None) -> dict:
    """Size, weight, colour and lean of Hangul relative to Latin (see the module docstring)."""
    k = 1000 / font["head"].unitsPerEm
    g = font_guides(font, k)
    m: dict = {}
    if "han_top" in g and "cap_top" in g:
        cap_h = g["cap_top"] - g["cap_bottom"]
        m["height"] = _ratio(g["han_top"] - g["han_bottom"], cap_h)
        m["centre"] = round(
            (g["han_top"] + g["han_bottom"]) / 2 - (g["cap_top"] + g["cap_bottom"]) / 2, 1
        )
    lat, han = script_stats(font, LATIN_WORDS), script_stats(font, HANGUL_WORDS)
    m["weight"] = _ratio(han["stroke"], lat["stroke"])
    if lat["bar"] and lat["stem"] and han["bar"] and han["stem"]:
        m["contrast"] = round((han["bar"] / han["stem"]) / (lat["bar"] / lat["stem"]), 3)
    m["colour"] = _ratio(han["density"], lat["density"])
    if kind == "text":
        m["spacing"] = _ratio(han["gap"], lat["gap"])
    if kind != "pixel":  # pixel italics are applied to every glyph alike (see `split`)
        a_l, a_h = _stem_angle(font, "lIi"), _stem_angle(font, "ㅣㅏ")
        m["slant"] = round(a_h - a_l, 2) if a_l is not None and a_h is not None else None
    return m


def grid_metrics(font: TTFont, kind: str, px: int | None = None) -> dict:
    """Cell grid, overflow and pixel-grid numbers of the real (wobbly) build."""
    k = 1000 / font["head"].unitsPerEm
    g = font_guides(font, k)
    half = g.get("half")
    overflow, grid_bad, off_grid = 0.0, 0, 0
    for ch in sorted(set(QA_TEXT) - {" "}):
        geo = next(_geos(font, ch), None)
        if geo is None:
            continue
        overflow = max(overflow, -geo.bounds[0], geo.bounds[2] - geo.advance)
        if kind in ("merge", "pixel") and half:
            want = 2 * half if ord(ch) >= 0x1100 else half
            grid_bad += abs(geo.advance - want) > 1
        if px and "glyf" in font:
            name = font.getBestCmap()[ord(ch)]
            coords = font["glyf"][name].getCoordinates(font["glyf"])[0]
            off_grid += sum(1 for x, y in coords if x % px or y % px)
    m = {"overflow": round(overflow / (k * px), 2) if px else round(overflow, 1)}
    if kind in ("merge", "pixel"):
        m["grid"] = grid_bad
    if px:
        m["pixels"] = off_grid
    return m


@dataclass
class Check:
    key: str
    value: float | None
    lo: float | None
    hi: float | None

    @property
    def ok(self) -> bool:
        if self.value is None:
            return True  # not measurable (e.g. a family without Latin crossbars): reported only
        return (self.lo is None or self.value >= self.lo) and (
            self.hi is None or self.value <= self.hi
        )


@dataclass
class Result:
    preset: dict
    metrics: dict
    checks: list[Check] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and all(c.ok for c in self.checks)


def evaluate(metrics: dict, bands: dict) -> list[Check]:
    out = []
    for key, band in bands.items():
        lo, hi = (band if isinstance(band, list) else (None, band))[:2]
        out.append(Check(key, metrics.get(key), lo, hi))
    return out


class Checker:
    """Measures presets one at a time; keeps the plain builds it compares against."""

    def __init__(self, root: Path = config.ROOT, studio=None):
        from .studio.core import Studio

        self.root = root
        self.studio = studio or Studio(root)
        self.bands = load_bands(root)
        self._plain: dict[tuple[str, str], TTFont] = {}

    def _build(self, p: dict, style: dict | None, pixel: dict | None) -> TTFont:
        prev = self.studio.build_preview(
            p["family"], p["weight"], QA_TEXT, style=style, pixel=pixel, **p.get("hangul", {})
        )
        return TTFont(io.BytesIO(base64.b64decode(prev.font_b64)))

    def check(self, p: dict) -> Result:
        """Measure one (validated) preset against its family's bands."""
        if "error" in p:
            return Result(p, {}, error=p["error"])
        fam = config.family(p["family"], self.root)
        kind = fam.get("kind", "merge")
        px = fam.get("grid", {}).get("units_per_pixel") if kind == "pixel" else None
        style, pixel = p.get("style") or {}, p.get("pixel") or {}
        try:
            font = self._build(p, style, pixel)
            steady = font
            if any(style.get(k) for k in WOBBLE):
                steady = self._build(p, {**style, **{k: 0 for k in WOBBLE}}, pixel)
            elif pixel.get("italic"):
                # A stair-step italic cuts every scanline into one-pixel pieces; it moves every
                # glyph alike (see `split`), so measure the upright build.
                steady = self._build(p, style, {**pixel, "italic": 0})
            m = measure(steady, kind, px)
            m.update(grid_metrics(font, kind, px))
            key = (p["family"], p["weight"])
            if key not in self._plain:
                self._plain[key] = self._build(
                    {**p, "hangul": {}},
                    {k: 0 for k in ("slant", "grade", "tracking", *WOBBLE)},
                    {k: 0 for k in (*PIXEL_SHAPE, "dy", "hangul_dy")},
                )
            if kind == "pixel":
                shaped = any(pixel.get(k) for k in PIXEL_SHAPE)
                m["split"] = int(shaped and pixel.get("scope", "all") != "all")
                m["broken"] = 0
                m["gaps"] = pixel_gaps(self._plain[key], steady, px)
            else:
                m["broken"] = broken_contours(self._plain[key], font, QA_TEXT)
        except Exception as exc:  # report, keep going
            return Result(p, {}, error=f"{type(exc).__name__}: {exc}")
        b = self.bands
        band = {**b.get("all", {}), **b.get(kind, {}), **b.get(p["family"], {})}
        return Result(p, m, evaluate(m, band))


def as_dict(r: Result) -> dict:
    """JSON for the /presets page."""
    return {
        "id": r.preset.get("id"),
        "ok": r.ok,
        "error": r.error,
        "metrics": r.metrics,
        "checks": [
            {"key": c.key, "value": c.value, "lo": c.lo, "hi": c.hi, "ok": c.ok} for c in r.checks
        ],
    }


def run(root: Path = config.ROOT, only: list[str] | None = None) -> list[Result]:
    """Build and measure every preset (and every saved family) against its kind's bands."""
    from .studio import presets as presets_mod

    checker = Checker(root)
    return [
        checker.check(p)
        for p in presets_mod.load(root)
        if not only or p.get("family") in only or p["id"] in only
    ]


COLUMNS = ("height", "centre", "weight", "contrast", "colour", "slant", "spacing", "overflow")


def _fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, float) and not math.isclose(v, round(v)):
        return f"{v:.3f}".rstrip("0").rstrip(".") if abs(v) < 10 else f"{v:.1f}"
    return str(int(v)) if isinstance(v, float) else str(v)


def format_table(results: list[Result], markdown: bool = False) -> str:
    """One row per preset; a failing value is marked with `!`."""
    head = ["preset", "family", *COLUMNS, "result"]
    rows = []
    for r in results:
        if r.error:
            rows.append(
                [r.preset["id"], r.preset.get("family", "?"), *[""] * len(COLUMNS), r.error]
            )
            continue
        checks = {c.key: c for c in r.checks}
        cells = []
        for col in COLUMNS:
            c = checks.get(col)
            v = _fmt(r.metrics.get(col))
            cells.append(v + ("!" if c and not c.ok else ""))
        bad = [c.key for c in r.checks if not c.ok]
        rows.append(
            [
                r.preset["id"],
                r.preset["family"],
                *cells,
                "ok" if not bad else "FAIL " + ",".join(bad),
            ]
        )
    if markdown:
        lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join(lines)
    widths = [max(len(str(x)) for x in col) for col in zip(head, *rows, strict=True)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    return "\n".join(fmt.format(*row) for row in [head, *rows])


def gating(results: list[Result]) -> list[Result]:
    """Failures that fail the qa stage: preset files only. Saved families (saved:<id>) are
    reported with the same bands but changed through the Glyph Lab, not here."""
    from .studio.presets import SAVED_PREFIX

    return [r for r in results if not r.ok and not r.preset["id"].startswith(SAVED_PREFIX)]


PROOF_TEXT = "다람쥐 헌 쳇바퀴에 Hamburg 0O1lI 한국을를"


def proof_sheet(results: list[Result], root: Path = config.ROOT, size: int = 36):
    """One row per preset: the sample in that preset, its id and harmony numbers (a PIL image).

    Labels are ASCII (PIL's default font has no Hangul); the /presets page shows the names.
    """
    from PIL import Image, ImageDraw, ImageFont

    from .studio.core import Studio

    studio = Studio(root)
    label = ImageFont.load_default()
    rows = []
    for r in results:
        if r.error:
            continue
        p = r.preset
        prev = studio.build_preview(
            p["family"],
            p["weight"],
            PROOF_TEXT,
            style=p.get("style"),
            pixel=p.get("pixel"),
            **p.get("hangul", {}),
        )
        f = ImageFont.truetype(io.BytesIO(base64.b64decode(prev.font_b64)), size)
        asc, desc = f.getmetrics()
        img = Image.new("RGB", (int(f.getlength(PROOF_TEXT)) + 40, asc + desc + 34), "white")
        d = ImageDraw.Draw(img)
        nums = "  ".join(f"{c}={_fmt(r.metrics.get(c))}" for c in COLUMNS if c in r.metrics)
        mark = "ok" if r.ok else "FAIL " + ",".join(c.key for c in r.checks if not c.ok)
        d.text((10, 4), f"{p['id']} [{p['weight']}]  {mark}   {nums}", fill=(120, 0, 0), font=label)
        d.text((10, 22), PROOF_TEXT, fill="black", font=f)
        rows.append(img)
    if not rows:
        return None
    sheet = Image.new("RGB", (max(i.width for i in rows), sum(i.height for i in rows)), "white")
    y = 0
    for img in rows:
        sheet.paste(img, (0, y))
        y += img.height
    return sheet
