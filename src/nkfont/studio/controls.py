"""Core design controls: a few design targets that every Hangul glyph is derived from.

This is how type designers keep a font consistent: they do not tune numbers glyph by glyph, they
fix a handful of control glyphs (n o H O, 한 국 을 를) and a handful of variables (height, width,
stem weight, optical centre, slant, spacing) and let everything else follow.

The Glyph Lab's default view shows those variables as *targets in design terms* ("Hangul height
= 1.17 × cap height", "Hangul stem = 0.92 × Latin stem"). `solve` turns targets into the raw
[hangul] build parameters (scale, width, grade, dy, ...) by measuring a small preview build and
correcting, a few rounds. The raw numbers stay in config/families/*.toml as before, so builds and
saved values are unchanged; only the way they are chosen is new.

Controls are declared in config/lab.toml ([core] and [[core.control]]); a control with a `rule`
takes its golden-ratio target and tolerance from config/proportions.toml.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path

from .. import config
from ..proportions import load_rules, on_grid, phi_target

# Raw [hangul] parameters a control may drive, with the bounds the solver keeps them in.
PARAM_BOUNDS = {
    "scale": (0.6, 1.4),
    "width": (0.6, 1.4),
    "grade": (-60.0, 60.0),
    "dy": (-300.0, 300.0),
    "slant": (-20.0, 20.0),
    "tracking": (-200.0, 200.0),
}
_ROUND = {"scale": 4, "width": 4, "grade": 1, "dy": 0, "slant": 1, "tracking": 0}


def _lab_toml(root: Path) -> dict:
    with (root / "config" / "lab.toml").open("rb") as f:
        return tomllib.load(f)


def load_controls(root: Path = config.ROOT, fam: dict | None = None) -> dict:
    """Control glyphs and controls for one family, targets resolved from the phi rules."""
    core = _lab_toml(root).get("core", {})
    rules = {r["id"]: r for r in load_rules(root).get("rule", [])}
    sc = load_rules(root).get("scale", {})
    div = sc.get("divisions", 6)
    grid = on_grid(fam)
    out = []
    for c in core.get("control", []):
        if c.get("text_only") and grid:
            continue
        item = {
            "id": c["id"],
            "label": c["label"],
            "hint": c.get("hint", ""),
            "unit": c.get("unit", ""),
            "drives": c.get("drives") or c.get("param"),
            "solve": c.get("solve", "direct" if c.get("param") else "mul"),
            "min": c["range"][0],
            "max": c["range"][1],
            "step": c.get("step", 0.005),
        }
        if "rule" in c:
            r = rules[c["rule"]]
            item.update(
                numerator=r["numerator"],
                denominator=r["denominator"],
                phi=round(phi_target(r["step"], div), 4),
                expr=f"φ^({r['step']}/{div})",
                tolerance=r.get("tolerance", sc.get("tolerance", 0.015)),
                rule=c["rule"],
            )
        elif "numerator" in c:
            item.update(
                numerator=c["numerator"],
                denominator=c.get("denominator"),
                phi=c.get("target"),
                tolerance=c.get("tolerance", 2),  # units when there is no denominator
            )
        out.append(item)
    checks = [r for r in core.get("checks", []) if r in rules]
    return {
        "latin": core.get("latin", "noHO"),
        "hangul": core.get("hangul", "한국을를"),
        "controls": out,
        "checks": checks,
    }


def with_centre(metrics: dict, guides: dict) -> dict:
    """Add `han_center`: optical centre of Hangul minus centre of the capitals (0 = aligned)."""
    m = dict(metrics)
    if guides.get("han_top") is not None and guides.get("cap_top"):
        m["han_center"] = round(
            (guides["han_top"] + guides["han_bottom"]) / 2 - guides["cap_top"] / 2, 1
        )
    return m


def value(control: dict, metrics: dict) -> float | None:
    """The control's current value, read from measurements (None if a probe is missing)."""
    num = metrics.get(control.get("numerator"))
    if num is None:
        return None
    den = control.get("denominator")
    if not den:
        return float(num)
    d = metrics.get(den)
    return num / d if d else None


def _within(control: dict, actual: float, target: float) -> bool:
    if control.get("denominator"):
        # Half the rule's tolerance: tight enough to pass, loose enough to stop on rounded outlines.
        return abs(actual - target) <= abs(target) * control.get("tolerance", 0.015) / 2
    return abs(actual - target) <= 1.0  # one unit: outlines are rounded to whole units


def _clamp(key: str, v: float) -> float:
    lo, hi = PARAM_BOUNDS.get(key, (-1e9, 1e9))
    return round(max(lo, min(hi, v)), _ROUND.get(key, 4))


def solve(
    controls: list[dict],
    targets: dict,
    params: dict,
    measure: Callable[[dict], dict],
    max_rounds: int = 8,
) -> dict:
    """Find raw [hangul] params that meet `targets` ({control id: value}).

    `measure(params)` builds a preview and returns metrics (see `with_centre`). Each round moves
    every driving parameter by the error it causes: `mul` scales it (height and width are
    proportional to scale and width), `add` shifts it (grade adds to stems, dy moves the centre).
    Direct controls (slant, tracking) are copied. Returns params, final metrics and per-control
    results.
    """
    p = dict(params)
    by_id = {c["id"]: c for c in controls}
    for cid, t in targets.items():
        c = by_id.get(cid)
        if c and c["solve"] == "direct" and t is not None:
            p[c["drives"]] = _clamp(c["drives"], float(t))
    driven = [c for c in controls if c["solve"] != "direct" and targets.get(c["id"]) is not None]
    metrics = measure(p)
    rounds = 0
    while rounds < max_rounds:
        rounds += 1
        moved = False
        for c in driven:
            t, actual = float(targets[c["id"]]), value(c, metrics)
            if actual is None or _within(c, actual, t):
                continue
            key = c["drives"]
            cur = float(p.get(key, 0.0))
            if c["solve"] == "mul":
                new = cur * t / actual if actual else cur
            else:  # add: the error in measured units (times the denominator for ratios)
                den = metrics.get(c["denominator"]) if c.get("denominator") else 1.0
                new = cur + (t - actual) * (den or 1.0)
            new = _clamp(key, new)
            if new != cur:
                p[key], moved = new, True
        if not moved:
            break
        metrics = measure(p)
    results = []
    for c in controls:
        direct = c["solve"] == "direct"
        actual = p.get(c["drives"]) if direct else value(c, metrics)
        t = targets.get(c["id"])
        met = None
        if not direct and t is not None and actual is not None:
            met = met_target(c, actual, float(t))
        results.append(
            {
                "id": c["id"],
                "actual": None if actual is None else round(actual, 4),
                "target": t,
                "met": met,
            }
        )
    return {"params": p, "metrics": metrics, "rounds": rounds, "results": results}


def met_target(control: dict, actual: float, target: float) -> bool:
    """Close enough for the UI: within the rule's tolerance (or 1.5 units without one)."""
    if control.get("denominator"):
        return abs(actual - target) <= abs(target) * control.get("tolerance", 0.015)
    return abs(actual - target) <= 1.5
