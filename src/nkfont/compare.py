"""Measure NK fonts against popular coding fonts for the benchmark page (site/compare.html).

Everything here is computed from the real outlines, so the page shows numbers, not claims:
terminal-width mismatches, Hangul coverage, Latin/Hangul proportions, stroke weight balance,
typographic colour, OpenType features, and overlay specimens with a distinctness score.
"""

from __future__ import annotations

import io
import unicodedata
from functools import lru_cache
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont

from . import config
from .checks import check_widths, is_pua
from .merge import half_width

REGISTERED = {
    "calt": "문맥 대체(합자)",
    "liga": "표준 합자",
    "dlig": "선택 합자",
    "case": "대문자용 기호",
    "zero": "빗금 0",
    "frac": "분수",
    "sups": "위 첨자",
    "subs": "아래 첨자",
    "sinf": "과학 아래 첨자",
    "ordn": "서수",
    "numr": "분자",
    "dnom": "분모",
    "salt": "대체 글자",
    "onum": "옛 숫자",
}
# Features that are plumbing rather than something a user toggles.
HIDDEN = {"aalt", "ccmp", "locl", "ljmo", "vjmo", "tjmo", "dist", "mark", "mkmk", "kern"}
# Sample text for features whose effect is contextual (ligatures) rather than per glyph.
CONTEXT_SAMPLES = {
    "calt": "-> => != === <= >= |> <!-- www 0xFF",
    "ss03": ";; ;;; :: ::: ... !! ??",
    "liga": "fi fl ff",
    "dlig": "-> => != ===",
    "frac": "1/2 3/4",
    "sups": "x2 m3",
    "subs": "H2O",
    "sinf": "H2O",
    "ordn": "1a 2o",
    "case": "(H) [A] {X} -:",
}


def load_compare_config(root: Path = config.ROOT) -> dict:
    import tomllib

    with (root / "config" / "compare.toml").open("rb") as f:
        return tomllib.load(f)


def font_bytes(font: TTFont) -> bytes:
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


@lru_cache(maxsize=64)
def _pil_font(data: bytes, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(io.BytesIO(data), px)


def glyph_name(font: TTFont, ch: str) -> str | None:
    return font.getBestCmap().get(ord(ch))


def bounds(font: TTFont, ch: str) -> tuple[float, float, float, float] | None:
    name = glyph_name(font, ch)
    if name is None:
        return None
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    gs[name].draw(pen)
    return pen.bounds


def glyph_svg(font: TTFont, ch: str) -> dict | None:
    """Outline as an SVG path in font units, y pointing down with the baseline at 0."""
    name = glyph_name(font, ch)
    if name is None:
        return None
    gs = font.getGlyphSet()
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.0f}")
    gs[name].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
    return {"ch": ch, "adv": font["hmtx"][name][0], "d": pen.getCommands()}


def raster(data: bytes, text: str, px: int, width: int, ascent: int, descent: int) -> Image.Image:
    """Render `text` with its baseline at `ascent` px into a width x (ascent+descent) canvas."""
    img = Image.new("L", (max(1, width), max(1, ascent + descent)), 0)
    ImageDraw.Draw(img).text((0, ascent), text, font=_pil_font(data, px), fill=255, anchor="ls")
    return img


def ink(img: Image.Image) -> float:
    """Ink area in pixels (antialiased coverage counts fractionally)."""
    return sum(i * n for i, n in enumerate(img.histogram())) / 255


def iou(a: Image.Image, b: Image.Image) -> float:
    union = ink(ImageChops.lighter(a, b))
    return ink(ImageChops.darker(a, b)) / union if union else 1.0


def _scale(font: TTFont, px: int) -> float:
    return px / font["head"].unitsPerEm


def stem_width(font: TTFont, data: bytes, ch: str, y_units: float, px: int = 500) -> float | None:
    """Width (font units) of the first ink run on the scanline `y_units` above the baseline."""
    if glyph_name(font, ch) is None:
        return None
    s = _scale(font, px)
    upm = font["head"].unitsPerEm
    img = raster(data, ch, px, int(2 * upm * s), int(upm * s), int(0.4 * upm * s))
    row = int(upm * s - y_units * s)
    line = [img.getpixel((x, row)) for x in range(img.width)]
    run, best = 0.0, 0.0
    for v in line:
        if v >= 128:
            run += 1
        elif run:
            best = run
            break
    best = best or run
    return round(best / s, 1) if best else None


def density(font: TTFont, data: bytes, text: str, px: int) -> float | None:
    """Share of each character cell covered by ink (typographic colour), 0..1."""
    cmap = font.getBestCmap()
    chars = [c for c in text if ord(c) in cmap]
    if len(chars) < len(text) / 2:
        return None
    s = _scale(font, px)
    hhea = font["hhea"]
    asc, desc = int(hhea.ascent * s), int(-hhea.descent * s)
    total, area = 0.0, 0.0
    for c in chars:
        adv = font["hmtx"][cmap[ord(c)]][0] * s
        img = raster(data, c, px, int(adv) + 2, asc, desc)
        total += ink(img)
        area += adv * (asc + desc)
    return round(total / area, 4) if area else None


def _single_keys(lookup, lookups) -> set[str]:
    keys: set[str] = set()
    for sub in lookup.SubTable:
        if lookup.LookupType == 7:
            sub = sub.ExtSubTable
        kind = getattr(sub, "LookupType", lookup.LookupType)
        if kind == 1:
            keys |= set(sub.mapping)
        elif kind == 3:
            keys |= set(sub.alternates)
        elif kind == 6:
            for rec in getattr(sub, "SubstLookupRecord", None) or []:
                keys |= _single_keys(lookups[rec.LookupListIndex], lookups)
            for rs in getattr(sub, "ChainSubRuleSet", None) or []:
                for rule in (rs.ChainSubRule if rs else []) or []:
                    for rec in rule.SubstLookupRecord:
                        keys |= _single_keys(lookups[rec.LookupListIndex], lookups)
    return keys


def features(font: TTFont) -> list[dict]:
    """User-facing GSUB features with their UI label and the characters they change."""
    if "GSUB" not in font:
        return []
    table = font["GSUB"].table
    lookups = table.LookupList.Lookup
    rev: dict[str, str] = {}
    for cp, g in sorted(font.getBestCmap().items(), reverse=True):
        if cp < 0x3000:
            rev[g] = chr(cp)
    name_table = font["name"]
    out: dict[str, dict] = {}
    for rec in table.FeatureList.FeatureRecord:
        tag = rec.FeatureTag
        if tag in HIDDEN or tag in out:
            continue
        label = None
        params = rec.Feature.FeatureParams
        nid = getattr(params, "UINameID", None) or getattr(params, "FeatUILabelNameID", None)
        if nid:
            label = name_table.getDebugName(nid)
        keys: set[str] = set()
        for i in rec.Feature.LookupListIndex:
            keys |= _single_keys(lookups[i], lookups)
        chars = "".join(sorted({rev[k] for k in keys if k in rev}, key=ord))
        if tag.startswith("ss"):
            default = f"스타일 세트 {int(tag[2:])}"
        elif tag.startswith("cv"):
            default = f"문자 변형 {int(tag[2:])}"
        else:
            default = REGISTERED.get(tag, tag)
        sample = CONTEXT_SAMPLES.get(tag) or " ".join(c for c in chars[:10] if not c.isspace())
        if not sample:
            continue
        out[tag] = {"tag": tag, "label": label or default, "chars": chars[:40], "sample": sample}
    return sorted(out.values(), key=lambda f: (f["tag"][:2] in ("ss", "cv"), f["tag"]))


def is_icon(cp: int, glyph: str) -> bool:
    """Powerline or a named (Nerd Fonts) icon. Unnamed PUA such as old-Hangul PUA is not."""
    if not is_pua(cp):
        return False
    return 0xE0A0 <= cp <= 0xE0D7 or not (glyph.startswith("uni") or glyph.startswith("u"))


# Symbols common in Korean documents and terminal output (lists, notes, units).
KR_SYMBOLS = "①②③④⑤⑥⑦⑧⑨⑩※★☆○●◎□■△▲▽▼◆◇→←↑↓↔℃㈜№·…‰°±×÷"


def coverage(font: TTFont) -> dict:
    cmap = font.getBestCmap()
    return {
        "kr_symbols": sum(1 for c in KR_SYMBOLS if ord(c) in cmap),
        "kr_symbols_total": len(KR_SYMBOLS),
        "kr_symbols_missing": "".join(c for c in KR_SYMBOLS if ord(c) not in cmap),
        "codepoints": len(cmap),
        "hangul_syllables": sum(1 for cp in cmap if 0xAC00 <= cp <= 0xD7A3),
        "hangul_jamo": sum(1 for cp in cmap if 0x3131 <= cp <= 0x318E),
        "icons": sum(1 for cp, g in cmap.items() if is_icon(cp, g)),
        "box_drawing": sum(1 for cp in cmap if 0x2500 <= cp <= 0x259F),
    }


def grid(font: TTFont) -> dict:
    """Terminal-grid conformance: advances vs wcwidth, and Ambiguous characters drawn wide."""
    problems = check_widths(font)
    half = half_width(font)
    hmtx, cmap = font["hmtx"], font.getBestCmap()
    amb_wide = [
        cp
        for cp, g in cmap.items()
        if unicodedata.east_asian_width(chr(cp)) == "A" and hmtx[g][0] == 2 * half
    ]
    return {
        "mismatches": len(problems),
        "examples": problems[:6],
        "ambiguous_wide": len(amb_wide),
        "ambiguous_examples": "".join(chr(c) for c in sorted(amb_wide)[:16]),
    }


def metrics(font: TTFont, data: bytes, cfg: dict) -> dict:
    upm = font["head"].unitsPerEm
    k = 1000 / upm  # normalise to 1000 UPM so fonts compare directly
    half = half_width(font)
    hhea, os2 = font["hhea"], font["OS/2"]
    x, cap = bounds(font, "x"), bounds(font, "H")
    probe = cfg.get("hangul_probe", "한")
    han = bounds(font, probe)
    cap_h = cap[3] if cap else os2.sCapHeight
    x_h = x[3] if x else os2.sxHeight
    latin_stem = stem_width(font, data, "H", cap_h * 0.3)
    jamo_stem = stem_width(font, data, "ㅣ", cap_h * 0.5)
    px = cfg.get("raster_px", 128)
    d_lat = density(font, data, cfg["latin_sample"], px)
    d_han = density(font, data, cfg["hangul_sample"], px)
    han_adv = font["hmtx"][glyph_name(font, probe)][0] if han else None

    def n(v):
        return None if v is None else round(v * k, 1)

    return {
        "upm": upm,
        "half": n(half),
        "ascent": n(hhea.ascent),
        "descent": n(hhea.descent),
        "line_gap": n(hhea.lineGap),
        "line_height": round((hhea.ascent - hhea.descent + hhea.lineGap) / upm, 3),
        "x_height": n(x_h),
        "cap_height": n(cap_h),
        "x_ratio": round(x_h / cap_h, 3) if cap_h else None,
        "hangul_cells": round(han_adv / half, 2) if han_adv else None,
        "hangul_top": n(han[3]) if han else None,
        "hangul_bottom": n(han[1]) if han else None,
        "hangul_height_ratio": round((han[3] - han[1]) / cap_h, 3) if han and cap_h else None,
        "hangul_center_offset": n((han[3] + han[1]) / 2 - cap_h / 2) if han else None,
        "hangul_width_ratio": round((han[2] - han[0]) / han_adv, 3) if han else None,
        "latin_stem": n(latin_stem),
        "hangul_stem": n(jamo_stem),
        "stem_ratio": round(jamo_stem / latin_stem, 3) if jamo_stem and latin_stem else None,
        "density_latin": d_lat,
        "density_hangul": d_han,
        "density_ratio": round(d_han / d_lat, 3) if d_han and d_lat else None,
    }


def specimen_group(font: TTFont, data: bytes, chars: list[str], px: int) -> dict:
    s = _scale(font, px)
    upm = font["head"].unitsPerEm
    glyphs = [glyph_svg(font, c) for c in chars]
    present = [c for c, g in zip(chars, glyphs, strict=True) if g]
    imgs = {}
    for c in present:
        imgs[c] = raster(data, c, px, int(2.2 * upm * s), int(upm * s), int(0.4 * upm * s))
    best, pair = None, None
    for i, a in enumerate(present):
        for b in present[i + 1 :]:
            d = 1 - iou(imgs[a], imgs[b])
            if best is None or d < best:
                best, pair = d, [a, b]
    return {
        "glyphs": [g for g in glyphs if g],
        "missing": [c for c, g in zip(chars, glyphs, strict=True) if not g],
        "distinct": round(best, 3) if best is not None and len(present) == len(chars) else None,
        "closest": pair,
    }


def measure_font(font: TTFont, cfg: dict, groups: list[dict]) -> dict:
    data = font_bytes(font)
    px = cfg.get("raster_px", 128)
    cmap = font.getBestCmap()
    return {
        "has": "".join(c for c in dict.fromkeys(cfg.get("probe_chars", "")) if ord(c) in cmap),
        "metrics": metrics(font, data, cfg),
        "coverage": coverage(font),
        "grid": grid(font),
        "features": features(font),
        "specimens": {g["id"]: specimen_group(font, data, g["chars"], px) for g in groups},
        "guides": {
            k: glyph_svg(font, c)
            for k, c in (("H", "H"), ("g", "g"), ("han", cfg.get("hangul_probe", "한")))
        },
    }


def ofl_body(text: str) -> str:
    """The OFL text without our copyright block: a reference font's notice must name only its own
    authors, so cut everything before the license's own header."""
    i = text.find("This Font Software is licensed")
    return text[i:] if i >= 0 else text


def refs_for(nk_id: str, refs: dict[str, dict]) -> dict[str, dict]:
    """The references compared with one NK family: those without `nk`, or that list it."""
    return {k: r for k, r in refs.items() if not r.get("nk") or nk_id in r["nk"]}


def improvement_notes(nk: dict, refs: dict[str, dict]) -> list[str]:
    """Honest to-do list: where an NK font does not (yet) stand out against the references."""
    notes = []
    m = nk["metrics"]
    for rid, ref in refs.items():
        if ref["specimens"] and all(
            nk["specimens"][g]["glyphs"] == ref["specimens"][g]["glyphs"]
            for g in ("il1", "zero")
            if g in nk["specimens"] and g in ref["specimens"]
        ):
            notes.append(
                f"영문 글리프가 {rid}와 같습니다: 영문만 보면 차이가 없으니 한글·아이콘·격자 외에 "
                "NK 고유의 영문 변형(스타일 세트)이 필요합니다."
            )
    if m.get("stem_ratio") and not 0.9 <= m["stem_ratio"] <= 1.1:
        notes.append(
            f"한글 ㅣ 획 굵기가 영문 H 기둥의 {m['stem_ratio']:.2f}배입니다: 0.9~1.1 안으로 맞추면 "
            "섞어 쓸 때 회색도가 고릅니다."
        )
    if m.get("density_ratio") and not 0.85 <= m["density_ratio"] <= 1.25:
        notes.append(
            f"한글 회색도가 영문의 {m['density_ratio']:.2f}배입니다: 1.0 근처가 이상적입니다."
        )
    if m.get("hangul_center_offset") is not None and abs(m["hangul_center_offset"]) > 40:
        notes.append(
            f"한글 중심이 대문자 중심보다 {m['hangul_center_offset']:+.0f} 단위 어긋나 있습니다."
        )
    cov = nk["coverage"]
    if cov["kr_symbols_missing"]:
        notes.append(
            f"한국어 문서에 흔한 기호 {len(cov['kr_symbols_missing'])}개가 없습니다"
            f"({cov['kr_symbols_missing']}): 시스템 글꼴로 대체됩니다. "
            "대부분 애매한 폭 기호라 한 칸 너비로 새로 그려야 합니다"
            "(한글 글꼴에서 가져오면 두 칸이 됨)."
        )
    if m.get("hangul_width_ratio") and m["hangul_width_ratio"] < 0.75:
        notes.append(
            f"한글 잉크가 두 칸 폭의 {m['hangul_width_ratio']:.0%}만 차지해 글자 사이가 성겨 "
            "보입니다: 80% 이상이면 영문과 같은 밀도로 읽힙니다."
        )
    seen = set()
    for spec in nk["specimens"].values():
        if spec["distinct"] is not None and spec["distinct"] < 0.25:
            a, b = spec["closest"]
            if (a, b) in seen:
                continue
            seen.add((a, b))
            notes.append(f"'{a}'와 '{b}'의 겹침이 큽니다(변별도 {spec['distinct']:.2f}).")
    return notes


def build_compare(out: Path, nk_fonts: dict[str, dict], root: Path = config.ROOT) -> dict:
    """Write compare.json and the reference web fonts into the site directory `out`.

    `nk_fonts` maps family id -> {"family", "path" (Regular TTF used on the site)}.
    """
    from .site import to_woff2

    cfg = load_compare_config(root)
    mcfg, groups = cfg["metrics"], cfg["group"]
    srcs = config.sources(root)
    order = cfg.get("nk_order", [])
    rank = {fid: i for i, fid in enumerate(order)}
    fonts = []
    for fid, info in sorted(nk_fonts.items(), key=lambda kv: rank.get(kv[0], len(order))):
        entry = {"id": fid, "name": info["family"], "role": "nk", "css": info["family"]}
        entry.update(measure_font(TTFont(info["path"]), mcfg, groups))
        fonts.append(entry)
    refs = {}
    for ref in cfg.get("reference", []):
        regular = srcs[ref["weights"]["400"]].path
        if not regular.exists():
            raise SystemExit(f"{ref['id']}: {regular.name} missing; run `nkfont fetch`")
        webfonts = []
        for weight, sid in sorted(ref["weights"].items()):
            src = srcs[sid].path
            dest = to_woff2(src, out / "fonts" / "ref" / f"{src.stem}.woff2")
            webfonts.append(
                {
                    "weight": int(weight),
                    "url": f"fonts/ref/{dest.name}",
                    "bytes": dest.stat().st_size,
                }
            )
        font = TTFont(regular)
        entry = {
            "id": ref["id"],
            "name": ref["name"],
            "role": "reference",
            "css": f"Ref {ref['name']}",
            "version": ref["version"],
            "license": ref["license"],
            "homepage": ref["homepage"],
            "nk": ref.get("nk"),  # NK families this reference is shown with (None = all)
            # the upstream LICENSE line when the name table lacks one (Neo둥근모)
            "copyright": ref.get("copyright") or font["name"].getDebugName(0),
            "webfonts": webfonts,
        }
        entry.update(measure_font(font, mcfg, groups))
        fonts.append(entry)
        refs[ref["name"]] = entry
        notice = (
            f"{ref['name']} {ref['version']}\n{entry['copyright']}\n"
            f"License: {ref['license']}\n{ref['homepage']}\n\n"
        )
        (out / "fonts" / "ref" / f"LICENSE-{ref['id']}.txt").write_text(
            notice + ofl_body((root / "OFL.txt").read_text())
        )
    for f in fonts:
        if f["role"] == "nk":
            f["todo"] = improvement_notes(f, refs_for(f["id"], refs))
    data = {
        "groups": [{k: g[k] for k in ("id", "title", "note", "chars")} for g in groups],
        "fonts": fonts,
    }
    import json

    (out / "compare.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return data
