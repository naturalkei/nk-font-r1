"""Style presets for side-by-side comparison (`nkfont studio` -> /presets, `nkfont app`).

A preset is a named combination of family, weight, Hangul tuning values and OpenType features,
plus whole-face `[style]` knobs (proportional families, see nkfont/style.py) or `[pixel]` grid
knobs (NK Pixel, see nkfont/pixelstyle.py).
Each one lives in `config/presets/<id>.toml` so presets are reviewable and shareable in git.
Presets never change a build: only `[hangul]` in config/families/*.toml does (Studio "save").

Every active family also appears as a read-only preset `saved:<family>` that mirrors its saved
config, so a fresh checkout already has something to compare.
"""

from __future__ import annotations

import math
import re
import tomllib
from pathlib import Path

from .. import config

# Hangul knobs a preset may override; same names as [hangul] in config/families/*.toml.
HANGUL_KEYS = ("scale", "dy", "center", "width", "slant", "grade", "stem", "tracking")
# Loose sanity bounds so a typo cannot produce a degenerate preview font.
_BOUNDS = {
    "scale": (0.5, 1.5),
    "dy": (-400, 400),
    "width": (0.5, 1.5),
    "slant": (-30, 30),
    "grade": (-80, 80),
    "stem": (-60, 60),
    "tracking": (-300, 300),
}
# Whole-face knobs of proportional (kind = "text") families: Latin and Hangul move together.
STYLE_KEYS = ("slant", "grade", "tracking", "bounce", "tilt", "seed")
_STYLE_BOUNDS = {
    "slant": (-15, 15),
    "grade": (-120, 80),
    "tracking": (-100, 200),
    "bounce": (0, 60),
    "tilt": (0, 8),
    "seed": (0, 9999),
}
# Pixel-grid knobs of NK Pixel (whole pixels only).
PIXEL_KEYS = ("bold", "heavy", "italic", "shadow", "dy", "hangul_dy", "scope")
_PIXEL_BOUNDS = {
    "bold": (-1, 1),
    "heavy": (0, 1),
    "italic": (0, 8),
    "shadow": (0, 1),
    "dy": (-4, 4),
    "hangul_dy": (-4, 4),
}
_PIXEL_SCOPES = ("all", "hangul", "latin")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
_FEATURE = re.compile(r"^[a-z0-9]{4}$")
SAVED_PREFIX = "saved:"


def presets_dir(root: Path = config.ROOT) -> Path:
    return root / "config" / "presets"


def slugify(label: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48].strip("-")
    return s


def _toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _toml_num(v: float) -> str:
    if float(v).is_integer():
        return str(int(v)) if not isinstance(v, float) else f"{v:.1f}"
    return f"{float(v):.4f}".rstrip("0").rstrip(".")


def dumps(preset: dict) -> str:
    """Serialise a validated preset; the layout is fixed so git diffs stay small."""
    lines = [
        "# NK style preset (nkfont studio -> /presets). Compared side by side; not a build input.",
        f"label = {_toml_str(preset['label'])}",
        f"family = {_toml_str(preset['family'])}",
        f"weight = {_toml_str(preset['weight'])}",
    ]
    if preset.get("note"):
        lines.append(f"note = {_toml_str(preset['note'])}")
    feats = ", ".join(_toml_str(f) for f in preset.get("features", []))
    lines.append(f"features = [{feats}]")
    hangul = preset.get("hangul", {})
    if hangul:
        lines += ["", "[hangul]"]
        for key in HANGUL_KEYS:
            if key not in hangul:
                continue
            v = hangul[key]
            lines.append(f"{key} = {_toml_str(v) if key == 'center' else _toml_num(v)}")
    for table, keys in (("style", STYLE_KEYS), ("pixel", PIXEL_KEYS)):
        values = preset.get(table, {})
        if values:
            lines += ["", f"[{table}]"]
            for key in keys:
                if key in values:
                    v = values[key]
                    lines.append(f"{key} = {_toml_str(v) if isinstance(v, str) else _toml_num(v)}")
    return "\n".join(lines) + "\n"


def _numbers(table: str, values: dict, bounds: dict, ints: tuple[str, ...]) -> dict:
    out = {}
    for key, v in (values or {}).items():
        if v is None or v == "":
            continue
        if key not in bounds:
            raise ValueError(f"unknown {table} key {key!r}")
        x = float(v)
        lo, hi = bounds[key]
        if not math.isfinite(x) or not lo <= x <= hi:
            raise ValueError(f"{table}.{key} = {v} is outside {lo}..{hi}")
        out[key] = int(round(x)) if key in ints else round(x, 4)
    return out


def validate(data: dict, root: Path = config.ROOT) -> dict:
    """Return a clean preset dict or raise ValueError with a message for the UI."""
    label = str(data.get("label", "")).strip()
    if not label:
        raise ValueError("preset needs a label")
    pid = str(data.get("id") or slugify(label))
    if not pid:  # e.g. a label in Hangul only
        pid = _free_id("preset", root)
    if pid.startswith(SAVED_PREFIX) or not _ID.match(pid):
        raise ValueError(f"bad preset id {pid!r}: use a-z, 0-9 and '-'")
    fid = str(data.get("family", ""))
    if fid not in config.family_ids(root):
        raise ValueError(f"unknown family {fid!r}")
    fam = config.family(fid, root)
    weights = [w["name"] for w in fam["weight"]]
    weight = str(data.get("weight") or weights[0])
    if weight not in weights:
        raise ValueError(f"{fam['family']} has no weight {weight!r} ({', '.join(weights)})")
    feats = []
    for f in data.get("features") or []:
        if not _FEATURE.match(str(f)):
            raise ValueError(f"bad OpenType feature tag {f!r}")
        if f not in feats:
            feats.append(str(f))
    hangul = {}
    for key, v in (data.get("hangul") or {}).items():
        if v is None or v == "":
            continue
        if key not in HANGUL_KEYS:
            raise ValueError(f"unknown hangul key {key!r}")
        if key == "center":
            if v not in ("advance", "bbox"):
                raise ValueError("center must be 'advance' or 'bbox'")
            hangul[key] = v
            continue
        x = float(v)
        lo, hi = _BOUNDS[key]
        if not math.isfinite(x) or not lo <= x <= hi:
            raise ValueError(f"hangul.{key} = {v} is outside {lo}..{hi}")
        hangul[key] = int(round(x)) if key in ("dy", "tracking") else round(x, 4)
    kind = fam.get("kind", "merge")
    style = _numbers("style", data.get("style"), _STYLE_BOUNDS, ("seed", "tracking"))
    if style and kind != "text":
        raise ValueError('[style] is for proportional (kind = "text") families only')
    raw_pixel = dict(data.get("pixel") or {})
    scope = raw_pixel.pop("scope", None)
    pixel = _numbers("pixel", raw_pixel, _PIXEL_BOUNDS, tuple(_PIXEL_BOUNDS))
    if scope not in (None, ""):
        if scope not in _PIXEL_SCOPES:
            raise ValueError(f"pixel.scope must be one of {', '.join(_PIXEL_SCOPES)}")
        pixel["scope"] = scope
    if pixel and kind != "pixel":
        raise ValueError('[pixel] is for pixel (kind = "pixel") families only')
    out = {"id": pid, "label": label[:80], "family": fid, "weight": weight, "features": feats}
    note = str(data.get("note") or "").strip()
    if note:
        out["note"] = note[:200]
    if hangul:
        out["hangul"] = hangul
    if style:
        out["style"] = style
    if pixel:
        out["pixel"] = pixel
    return out


def _free_id(base: str, root: Path) -> str:
    d = presets_dir(root)
    n = 1
    while (d / f"{base}-{n}.toml").exists():
        n += 1
    return f"{base}-{n}"


def saved_presets(root: Path = config.ROOT) -> list[dict]:
    """One read-only preset per active family: its saved config/families/<id>.toml values."""
    out = []
    for fid in config.family_ids(root):
        fam = config.family(fid, root)
        if fam.get("status") != "active":
            continue
        h = fam.get("hangul", {})
        out.append(
            {
                "id": f"{SAVED_PREFIX}{fid}",
                "label": f"{fam['family']} (저장값)",
                "family": fid,
                "weight": fam["weight"][0]["name"],
                "features": [],
                "hangul": {k: h[k] for k in HANGUL_KEYS if k in h},
                **({"style": dict(fam["style"])} if fam.get("style") else {}),
                **({"pixel": dict(fam["pixel"])} if fam.get("pixel") else {}),
                "readonly": True,
            }
        )
    return out


def load(root: Path = config.ROOT) -> list[dict]:
    """User presets (config/presets/*.toml, by file name) after the saved-family presets."""
    out = saved_presets(root)
    d = presets_dir(root)
    for path in sorted(d.glob("*.toml")) if d.is_dir() else []:
        with path.open("rb") as f:
            data = tomllib.load(f)
        try:
            out.append(validate({**data, "id": path.stem}, root))
        except ValueError as exc:  # keep the page usable; show what is wrong
            out.append({"id": path.stem, "label": path.stem, "error": str(exc)})
    return out


def save(data: dict, root: Path = config.ROOT) -> dict:
    """Write a preset. Without an `id` it is new: a taken id gets a number, never overwritten."""
    preset = validate(data, root)
    d = presets_dir(root)
    if not data.get("id") and (d / f"{preset['id']}.toml").exists():
        preset["id"] = _free_id(preset["id"], root)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{preset['id']}.toml").write_text(dumps(preset), encoding="utf-8")
    return preset


def delete(pid: str, root: Path = config.ROOT) -> None:
    if not _ID.match(pid):
        raise ValueError(f"bad preset id {pid!r}")
    path = presets_dir(root) / f"{pid}.toml"
    if not path.exists():
        raise ValueError(f"no preset {pid!r}")
    path.unlink()
