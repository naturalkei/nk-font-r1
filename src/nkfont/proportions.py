"""Golden-ratio (phi) proportion rules: measure, compare with a phi modular scale, snap params.

Rules live in config/proportions.toml and are shared by every family. A rule's target is
phi ** (step / divisions). Locked rules (Latin metrics, the terminal grid) are only reported;
rules with `drives` can be met by changing one [hangul] parameter, never an advance.
"""

from __future__ import annotations

import math
import tomllib
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config
from .glyphmetrics import font_guides, harmony

PHI = (1 + math.sqrt(5)) / 2
DEFAULT_PROBES = {"latin_stem": "l", "latin_bar": "H", "hangul_stem": "ㅣ", "hangul_bar": "ㅡ"}


def load_rules(root: Path = config.ROOT) -> dict:
    with (root / "config" / "proportions.toml").open("rb") as f:
        return tomllib.load(f)


def phi_target(step: float, divisions: int) -> float:
    return PHI ** (step / divisions)


def nearest_step(value: float, divisions: int) -> int:
    """The phi-scale step closest to `value` (useful when choosing a new rule's step)."""
    return round(math.log(value, PHI) * divisions)


def proportion_metrics(guides: dict, harm: dict) -> dict:
    """Named measurements (1000-UPM units) that rules can use as numerator/denominator."""
    m = {
        "upm": 1000,
        "cap_height": guides.get("cap_top"),
        "x_height": guides.get("x_top"),
        "line_height": guides["ascent"] - guides["descent"],
        "cell": guides.get("half"),
        "han_cell": 2 * guides["half"] if guides.get("half") else None,
        **{k: harm.get(k) for k in ("latin_stem", "latin_bar", "hangul_stem", "hangul_bar")},
    }
    if guides.get("han_top") is not None:
        m["han_height"] = guides["han_top"] - guides["han_bottom"]
        m["han_width"] = guides["han_right"] - guides["han_left"]
    return m


def font_metrics(font: TTFont, probes: dict | None = None) -> dict:
    k = 1000 / font["head"].unitsPerEm
    return proportion_metrics(font_guides(font, k), harmony(font, probes or DEFAULT_PROBES))


def on_grid(fam: dict | None) -> bool:
    """True for terminal (cell-grid) families. Proportional text families such as a document
    Sans set `grid = false` (or `kind = "text"`, or [hangul] advance = "proportional")."""
    if not fam:
        return True
    if "grid" in fam:
        return bool(fam["grid"])
    return fam.get("kind") != "text" and fam.get("hangul", {}).get("advance") != "proportional"


def evaluate(metrics: dict, rules: dict, fam: dict | None = None) -> list[dict]:
    """Compare metrics with every rule that applies to the family.

    Rules marked `grid_only` are skipped for proportional families; `locked = "grid"` locks a
    rule only on grid families (elsewhere it is reported as a plain, non-driving target).
    """
    sc = rules.get("scale", {})
    div = sc.get("divisions", 6)
    grid = on_grid(fam)
    out = []
    for r in rules.get("rule", []):
        if r.get("grid_only") and not grid:
            continue
        locked = r.get("locked", False)
        locked = grid if locked == "grid" else bool(locked)
        num, den = metrics.get(r["numerator"]), metrics.get(r["denominator"])
        target = phi_target(r["step"], div)
        tol = r.get("tolerance", sc.get("tolerance", 0.015))
        item = {
            "id": r["id"],
            "label": r.get("label", r["id"]),
            "expr": f"φ^({r['step']}/{div})",
            "target": round(target, 4),
            "tolerance": tol,
            "drives": r.get("drives"),
            "locked": locked,
            "actual": None,
            "deviation": None,
            "ok": None,
        }
        if num is not None and den:
            actual = num / den
            dev = actual / target - 1
            item.update(
                actual=round(actual, 4),
                deviation=round(dev, 4),
                ok=abs(dev) <= tol,
                nearest=nearest_step(actual, div),
                num=num,
                den=den,
            )
        out.append(item)
    return out


def snap(params: dict, results: list[dict], only: str | None = None) -> dict:
    """New [hangul] parameters that move each driving rule onto its target.

    `scale` and `width` scale the measured ratio linearly; `grade` adds its value to stroke
    thickness, so the stem gap is added directly.
    """
    p = dict(params)
    for r in results:
        if r["locked"] or not r["drives"] or r["actual"] is None or (only and r["id"] != only):
            continue
        key = r["drives"]
        if key in ("scale", "width"):
            p[key] = round(p.get(key, 1.0) * r["target"] / r["actual"], 4)
        elif key == "grade":
            p[key] = round(p.get(key, 0.0) + (r["target"] * r["den"] - r["num"]), 1)
    return p


def report_files(
    paths: list[Path], root: Path = config.ROOT, fam: dict | None = None
) -> list[tuple[str, list[dict]]]:
    """Evaluate built font files, e.g. the masters `nkfont qa` just built."""
    rules = load_rules(root)
    return [(Path(p).name, evaluate(font_metrics(TTFont(p)), rules, fam)) for p in paths]


def format_report(rows: list[tuple[str, list[dict]]]) -> str:
    lines = []
    for name, results in rows:
        lines.append(f"== {name}")
        for r in results:
            if r["actual"] is None:
                lines.append(f"  --   {r['label']}: not measurable")
                continue
            mark = "lock" if r["locked"] else ("ok  " if r["ok"] else "off ")
            hint = f" -> {r['drives']}" if r["drives"] and not r["ok"] else ""
            lines.append(
                f"  {mark} {r['label']}: {r['actual']:.3f} vs {r['expr']}={r['target']:.3f}"
                f" ({r['deviation']:+.1%}){hint}"
            )
    return "\n".join(lines)
