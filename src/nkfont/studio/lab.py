"""Glyph Lab core: compare NK glyphs with reference fonts, measure strokes, tune and save.

Fonts are addressed by id:
  nk-edit    NK family built with the parameters being edited (only the requested characters)
  nk-saved   NK family built from config/families/<family>.toml (full build, cached)
  ref:<id>   a reference font from config/lab.toml, at the selected weight
  ref:local:<id>  a local-only reference from config/local_fonts.toml (installed, not fetched)
Every outline is normalised to 1000 UPM so fonts with other UPMs line up.
"""

from __future__ import annotations

import io
import threading
import tomllib
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont

from .. import config
from ..build import build_master, hangul_params
from ..glyphmetrics import (
    font_guides,
    glyph_geometry,
    gsub_features,
    harmony,
    measure_glyph,
    single_substitutions,
)
from ..proportions import evaluate, load_rules, proportion_metrics
from . import controls as core_controls

# Unicode blocks shown in the glyph browser (name, first, last). Covers what NK fonts carry.
BLOCKS = [
    ("Basic Latin", 0x0020, 0x007F),
    ("Latin-1 Supplement", 0x00A0, 0x00FF),
    ("Latin Extended-A", 0x0100, 0x017F),
    ("Latin Extended-B", 0x0180, 0x024F),
    ("IPA / Spacing Modifiers", 0x0250, 0x02FF),
    ("Greek and Coptic", 0x0370, 0x03FF),
    ("Cyrillic", 0x0400, 0x04FF),
    ("Latin Extended Additional", 0x1E00, 0x1EFF),
    ("General Punctuation", 0x2000, 0x206F),
    ("Super/Subscripts, Currency", 0x2070, 0x20CF),
    ("Letterlike / Number Forms", 0x2100, 0x218F),
    ("Arrows", 0x2190, 0x21FF),
    ("Mathematical Operators", 0x2200, 0x22FF),
    ("Misc Technical", 0x2300, 0x23FF),
    ("Box Drawing", 0x2500, 0x257F),
    ("Block Elements", 0x2580, 0x259F),
    ("Geometric Shapes", 0x25A0, 0x25FF),
    ("Misc Symbols / Dingbats", 0x2600, 0x27BF),
    ("Braille / Arrows-B / Math", 0x27C0, 0x2BFF),
    ("CJK Symbols and Punctuation", 0x3000, 0x303F),
    ("Hangul Compatibility Jamo", 0x3130, 0x318F),
    ("Enclosed CJK / Compatibility", 0x3200, 0x33FF),
    ("Hangul Syllables", 0xAC00, 0xD7A3),
    ("Private Use (Nerd Fonts)", 0xE000, 0xF8FF),
    ("Halfwidth and Fullwidth Forms", 0xFF00, 0xFFEF),
]

UPM = 1000


def lab_config(root: Path = config.ROOT) -> dict:
    path = root / "config" / "lab.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


@lru_cache(maxsize=16)
def _load(path: str) -> TTFont:
    return TTFont(path, fontNumber=0)


class Lab:
    def __init__(self, root: Path = config.ROOT):
        self.root = root
        self._full: dict[tuple, tuple[TTFont, bytes]] = {}
        self._lock = threading.Lock()

    # ---- catalogue -------------------------------------------------------------------------
    def info(self) -> dict:
        cfg = lab_config(self.root)
        srcs = config.sources(self.root)
        refs = []
        for r in cfg.get("reference", []):
            weights = {k: v for k, v in r.items() if k not in ("id", "label") and v in srcs}
            available = {k: v for k, v in weights.items() if srcs[v].path.exists()}
            refs.append(
                {
                    "id": f"ref:{r['id']}",
                    "label": r["label"],
                    "weights": sorted(available),
                    "missing": not available,
                }
            )
        for lf in config.local_fonts(self.root).values():
            available = lf.available(self.root)
            files = ", ".join(sorted({n for v in lf.weights.values() for n in v}))
            refs.append(
                {
                    "id": f"ref:local:{lf.id}",
                    "label": lf.label,
                    "weights": sorted(available),
                    "missing": not available,
                    "local": True,
                    "hint": f"로컬 전용: {files} 를 설치하거나 sources/local/ 에 두세요",
                }
            )
        return {
            "references": refs,
            "presets": cfg.get("preset", []),
            "blocks": [{"name": n, "start": a, "end": b} for n, a, b in BLOCKS],
        }

    def _ref_path(self, ref_id: str, weight: str) -> Path:
        cfg = lab_config(self.root)
        rid = ref_id.removeprefix("ref:")
        if rid.startswith("local:"):
            lf = config.local_fonts(self.root)[rid.removeprefix("local:")]
            available = lf.available(self.root)
            if not available:
                raise FileNotFoundError(f"local reference {lf.id} is not installed")
            return available.get(weight) or next(iter(available.values()))
        r = next(x for x in cfg.get("reference", []) if x["id"] == rid)
        srcs = config.sources(self.root)
        sid = r.get(weight) or next(
            v for k, v in r.items() if k not in ("id", "label") and srcs[v].path.exists()
        )
        return srcs[sid].path

    # ---- NK builds ---------------------------------------------------------------------------
    def nk_full(self, family: str, weight: str) -> tuple[TTFont, bytes]:
        """Full NK build from the saved config, cached until the config changes."""
        fam = config.family(family, self.root)
        key = (family, weight, repr(sorted(fam.get("hangul", {}).items())))
        with self._lock:
            if key not in self._full:
                w = next(x for x in fam["weight"] if x["name"] == weight)
                font = build_master(fam, w)
                buf = io.BytesIO()
                font.save(buf)
                data = buf.getvalue()
                self._full = {k: v for k, v in self._full.items() if k[:2] != key[:2]}
                self._full[key] = (TTFont(io.BytesIO(data)), data)
            return self._full[key]

    def nk_edit(self, family: str, weight: str, chars: str, params: dict) -> TTFont:
        fam = config.family(family, self.root)
        w = next(x for x in fam["weight"] if x["name"] == weight)
        if fam.get("kind") == "pixel":
            return self.nk_full(family, weight)[0]
        srcs = config.sources(self.root)
        hp = hangul_params(fam, **{k: v for k, v in params.items() if v is not None})
        probes = set(chars) | set("0Hx한") | set(lab_config(self.root).get("harmony", {}).values())
        return build_master(
            fam,
            w,
            hp,
            ranges=[(ord(c), ord(c)) for c in probes],
            latin=TTFont(io.BytesIO(srcs[w["latin"]].path.read_bytes())),
            hangul=_load(str(srcs[w["hangul"]].path)),
            fill=_load(str(srcs[w["fill"]].path)) if w.get("fill") else None,
        )

    def font(self, fid: str, family: str, weight: str, chars: str = "", params=None) -> TTFont:
        if fid == "nk-edit":
            return self.nk_edit(family, weight, chars, params or {})
        if fid == "nk-saved":
            return self.nk_full(family, weight)[0]
        return _load(str(self._ref_path(fid, weight)))

    def font_bytes(self, fid: str, family: str, weight: str) -> bytes:
        if fid == "nk-saved":
            return self.nk_full(family, weight)[1]
        return self._ref_path(fid, weight).read_bytes()

    # ---- queries -----------------------------------------------------------------------------
    def charset(self, family: str, weight: str) -> list[dict]:
        cmap = self.nk_full(family, weight)[0].getBestCmap()
        out = []
        for name, a, b in BLOCKS:
            cps = [cp for cp in range(a, b + 1) if cp in cmap]
            if cps:
                out.append({"name": name, "cps": cps})
        return out

    def features(self, fid: str, family: str, weight: str) -> list[dict]:
        return gsub_features(self.font(fid, family, weight))

    def glyphs(self, req: dict) -> dict:
        family, weight = req["family"], req["weight"]
        chars = req.get("chars", "")
        params = req.get("params") or {}
        feats = req.get("features") or []
        scan_y = req.get("scan_y")
        scan_x_rel = req.get("scan_x")  # share of each glyph's ink width, 0..1
        probes = lab_config(self.root).get("harmony", {})
        rules = load_rules(self.root)
        fam = config.family(family, self.root)
        out = {}
        for fid in req.get("fonts", ["nk-edit"]):
            try:
                if fid == "nk-saved" and req.get("partial"):
                    # Saved values, but only the requested glyphs: no full build (core view).
                    font = self.nk_edit(family, weight, chars, {})
                else:
                    font = self.font(fid, family, weight, chars, params)
            except (StopIteration, KeyError, FileNotFoundError) as exc:
                out[fid] = {"error": f"{type(exc).__name__}: {exc}"}
                continue
            k = UPM / font["head"].unitsPerEm
            cmap = font.getBestCmap()
            subst = single_substitutions(font, feats)
            items = []
            for ch in chars:
                name = cmap.get(ord(ch))
                if name is None:
                    items.append({"char": ch, "missing": True})
                    continue
                name = subst.get(name, name)
                geo = glyph_geometry(font, name, k)
                sx = None
                if scan_x_rel is not None and geo.bounds:
                    x0, _, x1, _ = geo.bounds
                    sx = [round(x0 + (x1 - x0) * float(r)) for r in scan_x_rel]
                m = measure_glyph(geo, scan_y, sx)
                items.append({"char": ch, "glyph": name, "path": geo.path, **m})
            guides, harm = font_guides(font, k), harmony(font, probes)
            out[fid] = {
                "guides": guides,
                "harmony": harm,
                "proportions": evaluate(proportion_metrics(guides, harm), rules, fam),
                "glyphs": items,
            }
        return out

    # ---- core view: design targets -> raw params -------------------------------------------
    def core(self, family: str) -> dict:
        """Control glyphs, controls and read-only checks for the default (core) view."""
        return core_controls.load_controls(self.root, config.family(family, self.root))

    def core_metrics(self, family: str, weight: str, params: dict) -> dict:
        """Proportion metrics of an edit build (only the probe glyphs), plus `han_center`."""
        font = self.nk_edit(family, weight, "Hx한", params)
        k = UPM / font["head"].unitsPerEm
        guides = font_guides(font, k)
        harm = harmony(font, lab_config(self.root).get("harmony", {}))
        return core_controls.with_centre(proportion_metrics(guides, harm), guides)

    def solve(self, req: dict) -> dict:
        """POST /api/lab/solve: {family, weight, params, targets} -> derived params."""
        family, weight = req["family"], req["weight"]
        core = self.core(family)
        fam = config.family(family, self.root)
        given = {k: v for k, v in (req.get("params") or {}).items() if v is not None}
        # Start from the full parameter set (saved [hangul] + defaults) so nothing starts at 0.
        hp = hangul_params(fam, **given)
        start = {k: getattr(hp, k) for k in core_controls.PARAM_BOUNDS}
        start["center"] = hp.center
        out = core_controls.solve(
            core["controls"],
            req.get("targets") or {},
            start,
            lambda p: self.core_metrics(family, weight, p),
        )
        out["checks"] = [
            r
            for r in evaluate(out["metrics"], load_rules(self.root), fam)
            if r["id"] in core["checks"]
        ]
        return out
