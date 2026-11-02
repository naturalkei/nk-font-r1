"""Studio core: preview builds, metric measurement and config write-back. No HTTP here."""

from __future__ import annotations

import base64
import io
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from .. import config
from ..build import build_master, hangul_params

DEFAULT_TEXT = (
    "가나다라마바사 한글 ABCD abcd 0O1lI\n"
    "다람쥐 헌 쳇바퀴에 타고파 0123456789\n"
    "~/문서/프로젝트 ❯ git:(main) ✔\n"
    'if (x != y) { return "값"; } // 주석'
)

# Probe glyphs for the rule-based guides: Latin cap/x height and the Hangul extremes.
_PROBES = {"cap": "H", "x": "x", "han_top": "한", "han_low": "를", "han_mid": "가"}


@dataclass
class Preview:
    font_b64: str
    metrics: dict


def _bounds(font: TTFont, ch: str) -> tuple[float, float, float, float] | None:
    name = font.getBestCmap().get(ord(ch))
    if name is None:
        return None
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    gs[name].draw(pen)
    return pen.bounds


def measure(font: TTFont) -> dict:
    """Vertical guides in font units, plus Hangul/Latin ratios used by the tuning rules."""
    hhea = font["hhea"]
    m = {
        "upm": font["head"].unitsPerEm,
        "ascent": hhea.ascent,
        "descent": hhea.descent,
        "half": font["hmtx"][font.getBestCmap()[ord("0")]][0],
    }
    for key, ch in _PROBES.items():
        b = _bounds(font, ch)
        if b:
            m[f"{key}_bottom"], m[f"{key}_top"] = round(b[1]), round(b[3])
            m[f"{key}_left"], m[f"{key}_right"] = round(b[0]), round(b[2])
    if "cap_top" in m and "han_mid_top" in m:
        han_h = m["han_mid_top"] - m["han_mid_bottom"]
        m["hangul_to_cap"] = round(han_h / m["cap_top"], 3)
        # Optical centre of Hangul vs. centre of Latin capitals: 0 means aligned.
        m["center_offset"] = round(
            (m["han_mid_top"] + m["han_mid_bottom"]) / 2 - m["cap_top"] / 2, 1
        )
    return m


@lru_cache(maxsize=8)
def _source_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _font_from(path: Path, lazy: bool = False) -> TTFont:
    return TTFont(io.BytesIO(_source_bytes(path)), lazy=lazy)


class Studio:
    def __init__(self, root: Path = config.ROOT):
        self.root = root
        self._hangul_cache: dict[str, TTFont] = {}

    def families(self) -> list[dict]:
        out = []
        for fid in config.family_ids(self.root):
            fam = config.family(fid, self.root)
            if fam.get("status") != "active":
                continue
            out.append(
                {
                    "id": fid,
                    "family": fam["family"],
                    "kind": fam.get("kind", "merge"),
                    "weights": [w["name"] for w in fam["weight"]],
                    "hangul": fam.get("hangul", {}),
                }
            )
        return out

    def _hangul(self, source_id: str) -> TTFont:
        # The Hangul source is only read during merging, so one parsed copy can be shared.
        if source_id not in self._hangul_cache:
            self._hangul_cache[source_id] = _font_from(config.sources(self.root)[source_id].path)
        return self._hangul_cache[source_id]

    def build_preview(
        self, family: str, weight: str, text: str = DEFAULT_TEXT, **params
    ) -> Preview:
        fam = config.family(family, self.root)
        w = next(x for x in fam["weight"] if x["name"] == weight)
        chars = set(text) | set(_PROBES.values()) | {"0"}
        if fam.get("kind") == "pixel":
            font = build_master(fam, w)
        else:
            srcs = config.sources(self.root)
            hp = hangul_params(fam, **{k: v for k, v in params.items() if v is not None})
            ranges = [(ord(c), ord(c)) for c in chars]
            font = build_master(
                fam,
                w,
                hp,
                ranges=ranges,
                latin=_font_from(srcs[w["latin"]].path),
                hangul=self._hangul(w["hangul"]),
            )
        metrics = measure(font)
        opts = subset.Options()
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        opts.hinting = False
        sub = subset.Subsetter(opts)
        sub.populate(unicodes={ord(c) for c in chars})
        sub.subset(font)
        buf = io.BytesIO()
        font.save(buf)
        return Preview(base64.b64encode(buf.getvalue()).decode(), metrics)


logging.getLogger("fontTools.subset").setLevel(logging.WARNING)

_KEYS = ("scale", "dy", "center")


def update_hangul_config(family: str, values: dict, root: Path = config.ROOT) -> Path:
    """Rewrite `scale`, `dy`, `center` inside [hangul] of config/families/<family>.toml.

    Only the value tokens change; comments and layout stay, so diffs stay reviewable.
    """
    path = root / "config" / "families" / f"{family}.toml"
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^\[hangul\]\s*$(.*?)(?=^\[|\Z)", text, flags=re.M | re.S)
    if not m:
        raise ValueError(f"{path} has no [hangul] table")
    body = m.group(1)
    for key in _KEYS:
        if key not in values or values[key] is None:
            continue
        v = values[key]
        if key == "scale":
            token = f"{float(v):.3f}".rstrip("0").rstrip(".")
        elif key == "dy":
            token = str(int(round(float(v))))
        else:
            if v not in ("advance", "bbox"):
                raise ValueError("center must be 'advance' or 'bbox'")
            token = f'"{v}"'
        pat = re.compile(rf"^({key}\s*=\s*)([^#\n]*?)(\s*(#.*)?)$", flags=re.M)
        if pat.search(body):
            body = pat.sub(lambda mm, t=token: f"{mm.group(1)}{t}{mm.group(3)}", body, count=1)
        else:
            body = body.rstrip("\n") + f"\n{key} = {token}\n\n"
    new = text[: m.start(1)] + body + text[m.end(1) :]
    path.write_text(new, encoding="utf-8")
    return path
