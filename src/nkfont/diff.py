"""Structural diff of two font builds, for reviewing what a change actually did."""

from __future__ import annotations

from fontTools.ttLib import TTFont


def _names(f: TTFont) -> dict[int, str]:
    return {r.nameID: r.toUnicode() for r in f["name"].names if r.platformID == 3}


def _features(f: TTFont) -> set[str]:
    if "GSUB" not in f:
        return set()
    return {r.FeatureTag for r in f["GSUB"].table.FeatureList.FeatureRecord}


def _metrics(f: TTFont) -> dict[str, object]:
    os2, hhea = f["OS/2"], f["hhea"]
    return {
        "unitsPerEm": f["head"].unitsPerEm,
        "hhea": (hhea.ascent, hhea.descent, hhea.lineGap),
        "typo": (os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap),
        "win": (os2.usWinAscent, os2.usWinDescent),
        "xAvgCharWidth": os2.xAvgCharWidth,
        "isFixedPitch": f["post"].isFixedPitch,
        "panose": (os2.panose.bFamilyType, os2.panose.bProportion),
        "numGlyphs": f["maxp"].numGlyphs,
    }


def _outline_sig(f: TTFont, name: str) -> tuple:
    g = f["glyf"][name]
    if getattr(g, "numberOfContours", 0) == 0:
        return ()
    coords, ends, _ = g.getCoordinates(f["glyf"])
    return tuple(coords), tuple(ends)


def diff_fonts(old: TTFont, new: TTFont, sample: int = 15) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    oc, nc = old.getBestCmap(), new.getBestCmap()

    added = sorted(set(nc) - set(oc))
    removed = sorted(set(oc) - set(nc))
    out["cmap"] = (
        [f"+{len(added)} code points, -{len(removed)} code points"] if added or removed else []
    )
    out["cmap"] += [f"  + U+{cp:04X}" for cp in added[:sample]]
    out["cmap"] += [f"  - U+{cp:04X}" for cp in removed[:sample]]

    adv, outline = [], []
    both_glyf = "glyf" in old and "glyf" in new
    for cp in sorted(set(oc) & set(nc)):
        a_old, a_new = old["hmtx"][oc[cp]][0], new["hmtx"][nc[cp]][0]
        if a_old != a_new:
            adv.append(f"U+{cp:04X} advance {a_old} -> {a_new}")
        elif both_glyf and _outline_sig(old, oc[cp]) != _outline_sig(new, nc[cp]):
            outline.append(cp)
    out["advances"] = adv[:sample] + (
        [f"... {len(adv) - sample} more"] if len(adv) > sample else []
    )
    out["outlines"] = [f"{len(outline)} glyph outlines changed"] if outline else []
    out["outlines"] += [f"  U+{cp:04X}" for cp in outline[:sample]]

    mo, mn = _metrics(old), _metrics(new)
    out["metrics"] = [f"{k}: {mo[k]} -> {mn[k]}" for k in mo if mo[k] != mn[k]]

    no, nn = _names(old), _names(new)
    out["names"] = [
        f"nameID {i}: {no.get(i)!r} -> {nn.get(i)!r}"
        for i in sorted(set(no) | set(nn))
        if no.get(i) != nn.get(i)
    ]

    fo, fn = _features(old), _features(new)
    out["features"] = [f"- {t}" for t in sorted(fo - fn)] + [f"+ {t}" for t in sorted(fn - fo)]
    return out


def format_diff(result: dict[str, list[str]]) -> str:
    lines = []
    for section, items in result.items():
        lines.append(f"[{section}] {'no change' if not items else ''}".rstrip())
        lines += [f"  {i}" for i in items]
    return "\n".join(lines)
