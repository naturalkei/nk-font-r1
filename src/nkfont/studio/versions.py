"""Numbered versions of each family's saved [hangul] values (Glyph Lab "버전").

Every "save to build config" in the studio appends a version to `config/versions/<family>.toml`
(v1, v2, ...) with a time, a note and the full [hangul] values it wrote. Any version can be
loaded into the editor or restored, which writes its values back to config/families/<family>.toml
and records the restore as a new version, so history only grows and nothing is lost.

The files are plain TOML kept in git: reviewable, diffable, and never read by a build.
"""

from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import fields
from pathlib import Path

from .. import config
from ..merge import HangulParams
from .core import _SAVE_KEYS, update_hangul_config
from .presets import _toml_num, _toml_str

# Identity values: restoring a version that never set a key puts the key back to these.
DEFAULTS = {f.name: f.default for f in fields(HangulParams) if f.name in _SAVE_KEYS}


def versions_path(family: str, root: Path = config.ROOT) -> Path:
    if family not in config.family_ids(root):
        raise ValueError(f"unknown family {family!r}")
    return root / "config" / "versions" / f"{family}.toml"


def load(family: str, root: Path = config.ROOT) -> list[dict]:
    """Versions of a family, oldest first ([] when nothing was saved from the studio yet)."""
    path = versions_path(family, root)
    if not path.exists():
        return []
    with path.open("rb") as f:
        return tomllib.load(f).get("version", [])


def saved_hangul(family: str, root: Path = config.ROOT) -> dict:
    """The [hangul] keys the studio manages, as config/families/<family>.toml has them now."""
    h = config.family(family, root).get("hangul", {})
    return {k: h[k] for k in _SAVE_KEYS if k in h}


def _dump_version(v: dict) -> str:
    lines = [
        "",
        "[[version]]",
        f"n = {v['n']}",
        f"saved_at = {_toml_str(v['saved_at'])}",
    ]
    if v.get("note"):
        lines.append(f"note = {_toml_str(v['note'])}")
    if v.get("restored_from"):
        lines.append(f"restored_from = {v['restored_from']}")
    lines.append("[version.hangul]")
    for k in _SAVE_KEYS:
        if k in v["hangul"]:
            val = v["hangul"][k]
            lines.append(f"{k} = {_toml_str(val) if k == 'center' else _toml_num(val)}")
    return "\n".join(lines) + "\n"


def _append(family: str, entry: dict, root: Path) -> dict:
    path = versions_path(family, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            f"# {family}: saved [hangul] versions (nkfont studio -> /lab). Not a build input;\n"
            "# restore one in the Glyph Lab, or copy its values to config/families by hand.\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as f:
        f.write(_dump_version(entry))
    return entry


def record(
    family: str,
    note: str = "",
    restored_from: int | None = None,
    root: Path = config.ROOT,
    now: dt.datetime | None = None,
) -> dict:
    """Append the family's current saved [hangul] as the next version and return it.

    Skipped (returns the last version) when nothing changed since the last one.
    """
    hist = load(family, root)
    current = saved_hangul(family, root)
    if hist and hist[-1].get("hangul", {}) == current and not restored_from:
        return hist[-1]
    stamp = (now or dt.datetime.now()).replace(microsecond=0).isoformat(sep=" ")
    entry = {
        "n": (hist[-1]["n"] + 1) if hist else 1,
        "saved_at": stamp,
        "note": str(note or "").strip()[:200],
        "hangul": current,
    }
    if restored_from:
        entry["restored_from"] = int(restored_from)
    return _append(family, entry, root)


def save(family: str, values: dict, note: str = "", root: Path = config.ROOT) -> dict:
    """Studio save: keep the pre-studio values as v1 the first time, write, record a version."""
    if not load(family, root):
        record(family, "스튜디오 저장 전 값", root=root)
    path = update_hangul_config(family, values, root)
    v = record(family, note, root=root)
    return {"saved": str(path.relative_to(root)), "version": v}


def restore(family: str, n: int, root: Path = config.ROOT) -> dict:
    """Write version `n` back to the family config; recorded as a new version."""
    v = next((x for x in load(family, root) if x["n"] == int(n)), None)
    if v is None:
        raise ValueError(f"{family} has no version {n}")
    values = dict(v.get("hangul", {}))
    for k in saved_hangul(family, root):  # keys the old version did not set go back to identity
        values.setdefault(k, DEFAULTS[k])
    path = update_hangul_config(family, values, root)
    entry = record(family, f"v{n} 복원", restored_from=int(n), root=root)
    return {"saved": str(path.relative_to(root)), "version": entry}
