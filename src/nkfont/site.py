"""Assemble the static prototype site: copy site/, convert fonts to WOFF2, zip downloads.

`nkfont site` -> build/site/ (deployable to GitHub Pages as is), including compare.json and the
reference web fonts for the benchmark page (nkfont.compare).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config

README = """{family} {version} (prototype)
================================

Files
-----
{prefix}NerdFont-*.ttf      Nerd Font: icons may take two cells where the terminal allows.
{prefix}NerdFontMono-*.ttf  Nerd Font Mono: every icon one cell. Hangul still two cells.
{prefix}-*.ttf              Master without Nerd Fonts icons.

Terminal setup: pick "{nf_family}" (or "{nf_family} Mono") as the font.

License
-------
SIL Open Font License 1.1, see OFL.txt. {copyright}
Nerd Fonts icons keep the licenses of their icon sets (https://github.com/ryanoasis/nerd-fonts).
"""


def to_woff2(src: Path, dest: Path) -> Path:
    font = TTFont(src)
    font.flavor = "woff2"
    dest.parent.mkdir(parents=True, exist_ok=True)
    font.save(dest)
    return dest


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=config.ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _family_files(fam: dict) -> dict[str, list[Path]]:
    prefix = fam["file_prefix"]
    master = sorted((config.BUILD_DIR / "master").glob(f"{prefix}-*.ttf"))
    nf = sorted(config.DIST_DIR.glob(f"{prefix}NerdFont-*.ttf"))
    nfm = sorted(config.DIST_DIR.glob(f"{prefix}NerdFontMono-*.ttf"))
    return {"master": master, "nf": nf, "nfm": nfm}


def glyph_index(font: TTFont) -> dict:
    """Code point runs with their cell counts, plus Nerd icon names (PUA) for the explorer."""
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    half = hmtx[cmap[ord("0")]][0]
    runs: list[list[int]] = []  # [start, end, cells]
    icons: dict[str, str] = {}
    for cp in sorted(cmap):
        cells = round(hmtx[cmap[cp]][0] / half)
        if runs and runs[-1][1] == cp - 1 and runs[-1][2] == cells:
            runs[-1][1] = cp
        else:
            runs.append([cp, cp, cells])
        if 0xE000 <= cp <= 0xF8FF or cp >= 0xF0000:
            name = cmap[cp]
            if not name.startswith("uni") and not name.startswith("u"):
                icons[str(cp)] = name
    return {"half": half, "runs": runs, "icons": icons}


def build_site(
    out: Path | None = None, families=("sans", "serif", "pixel"), compare: bool = True
) -> Path:
    out = out or config.BUILD_DIR / "site"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(config.ROOT / "site", out)
    manifest = {
        "built": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "commit": _git_sha(),
        "families": [],
    }
    for fid in families:
        fam = config.family(fid)
        if fam.get("status") != "active":
            continue
        files = _family_files(fam)
        if not files["master"]:
            raise SystemExit(f"{fid}: no masters in build/master; run `nkfont build {fid}` first")
        web = files["nf"] or files["master"]  # prefer icons on the site
        entry = {
            "id": fid,
            "family": fam["family"],
            "version": fam["version"],
            "kind": fam.get("kind", "merge"),
            "webfonts": [],
            "download": None,
        }
        for f in web:
            style = f.stem.split("-")[-1]
            dest = to_woff2(f, out / "fonts" / f"{f.stem}.woff2")
            font = TTFont(f)
            entry["webfonts"].append(
                {
                    "style": style,
                    "weight": font["OS/2"].usWeightClass,
                    "url": f"fonts/{dest.name}",
                    "bytes": dest.stat().st_size,
                    "glyphs": len(font.getGlyphOrder()),
                }
            )
        zip_name = f"{fam['file_prefix']}-{fam['version']}.zip"
        zip_path = out / "downloads" / zip_name
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        nf_family = f"{fam['family'].replace(' ', '')} Nerd Font"
        readme = README.format(
            family=fam["family"],
            version=fam["version"],
            prefix=fam["file_prefix"],
            nf_family=nf_family,
            copyright=fam.get("copyright", ""),
        )
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files["nf"] + files["nfm"] + files["master"]:
                z.write(f, f"{zip_path.stem}/{f.name}")
            z.write(config.ROOT / "OFL.txt", f"{zip_path.stem}/OFL.txt")
            z.writestr(f"{zip_path.stem}/README.txt", readme)
        entry["download"] = {
            "url": f"downloads/{zip_name}",
            "bytes": zip_path.stat().st_size,
            "files": len(files["nf"] + files["nfm"] + files["master"]),
            "nerd": bool(files["nf"]),
        }
        manifest["families"].append(entry)
    if compare:
        from .compare import build_compare

        nk = {}
        for entry in manifest["families"]:
            files = _family_files(config.family(entry["id"]))
            web = files["nf"] or files["master"]
            regular = [f for f in web if f.stem.endswith("-Regular")] or web
            nk[entry["id"]] = {"family": entry["family"], "path": regular[0]}
        build_compare(out, nk)
    sans_nf = _family_files(config.family("sans"))["nf"]
    if sans_nf:
        idx = glyph_index(TTFont(sans_nf[0]))
        (out / "glyphs.json").write_text(json.dumps(idx, separators=(",", ":")))
        manifest["glyph_count"] = sum(r[1] - r[0] + 1 for r in idx["runs"])
        manifest["icon_count"] = sum(
            r[1] - r[0] + 1 for r in idx["runs"] if 0xE000 <= r[0] <= 0xF8FF or r[0] >= 0xF0000
        )
    (out / "fonts.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    (out / ".nojekyll").write_text("")
    return out
