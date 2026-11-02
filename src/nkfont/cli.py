"""Command line entry point: `nkfont <command>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config


def _frange(spec: str) -> list[float]:
    start, stop, step = (float(x) for x in spec.split(":"))
    out, v = [], start
    while v <= stop + 1e-9:
        out.append(round(v, 4))
        v += step
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nkfont")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="download pinned upstream fonts into sources/")

    b = sub.add_parser("build", help="build master TTFs (Latin + Hangul)")
    b.add_argument("family", nargs="?", default="sans")
    b.add_argument("--weight", help="build only this weight, e.g. Regular")

    p = sub.add_parser("patch", help="Nerd Fonts patch masters with Docker (nf + nfm variants)")
    p.add_argument("masters", nargs="*", type=Path)

    c = sub.add_parser("check", help="run QA checks on font files")
    c.add_argument("fonts", nargs="+", type=Path)
    c.add_argument("--base", type=Path, help="Latin base font, for feature/width comparison")

    pr = sub.add_parser("proof", help="render a proof sheet PNG")
    pr.add_argument("fonts", nargs="+", type=Path)
    pr.add_argument("-o", "--output", type=Path, default=Path("proofs/proof.png"))
    pr.add_argument("--size", type=int, default=28)

    t = sub.add_parser("tune", help="render a parameter sweep of Hangul scale/dy for one weight")
    t.add_argument("family", nargs="?", default="sans")
    t.add_argument("--weight", default="Regular")
    t.add_argument("--scale", default=None, help="start:stop:step, e.g. 0.92:1.0:0.04")
    t.add_argument("--dy", default=None, help="start:stop:step in font units")
    t.add_argument("-o", "--output", type=Path, default=Path("proofs/tune.png"))

    args = ap.parse_args(argv)

    if args.cmd == "fetch":
        from .fetch import fetch_all

        for sid in fetch_all():
            print(f"ok  {sid}")
        return 0

    if args.cmd == "build":
        from .build import build_family

        for path in build_family(args.family, only=args.weight):
            print(path)
        return 0

    if args.cmd == "patch":
        from .patch import patch

        masters = args.masters or sorted((config.BUILD_DIR / "master").glob("*.ttf"))
        for path in patch(masters):
            print(path)
        return 0

    if args.cmd == "check":
        from .checks import run_all

        base = TTFont(args.base) if args.base else None
        failed = False
        for f in args.fonts:
            print(f"== {f}")
            for name, problems in run_all(TTFont(f), base).items():
                status = "ok " if not problems else "FAIL"
                print(f"  {status} {name} ({len(problems)})")
                for line in problems[:20]:
                    print(f"       {line}")
                failed |= bool(problems)
        return 1 if failed else 0

    if args.cmd == "proof":
        from .proof import render

        args.output.parent.mkdir(parents=True, exist_ok=True)
        render([(f.name, f) for f in args.fonts], size=args.size).save(args.output)
        print(args.output)
        return 0

    if args.cmd == "tune":
        from .build import build_master, hangul_params
        from .proof import render

        fam = config.family(args.family)
        weight = next(w for w in fam["weight"] if w["name"] == args.weight)
        base = fam.get("hangul", {})
        scales = _frange(args.scale) if args.scale else [base.get("scale", 0.96)]
        dys = _frange(args.dy) if args.dy else [base.get("dy", 0)]
        fonts = []
        for s in scales:
            for dy in dys:
                font = build_master(fam, weight, hangul_params(fam, scale=s, dy=dy))
                fonts.append((f"scale={s} dy={dy}", font))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        render(fonts).save(args.output)
        print(args.output)
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
