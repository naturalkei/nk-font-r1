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
    b.add_argument("family", nargs="?", default="mono", help="family id, or 'all'")
    b.add_argument("--weight", help="build only this weight, e.g. Regular")

    p = sub.add_parser("patch", help="Nerd Fonts patch masters with Docker (nf + nfm variants)")
    p.add_argument("masters", nargs="*", type=Path)

    c = sub.add_parser("check", help="run QA checks on font files")
    c.add_argument("fonts", nargs="+", type=Path)
    c.add_argument("--base", type=Path, help="Latin base font, for feature/width comparison")
    c.add_argument("--master", type=Path, help="our unpatched master, to tell our glyphs apart")
    c.add_argument(
        "--kind",
        choices=["merge", "pixel", "text"],
        default="merge",
        help="text = proportional reading face (NK Novel, NK Comics): no terminal grid checks",
    )

    pr = sub.add_parser("proof", help="render a proof sheet PNG")
    pr.add_argument("fonts", nargs="+", type=Path)
    pr.add_argument("-o", "--output", type=Path, default=Path("proofs/proof.png"))
    pr.add_argument("--size", type=int, default=28)

    t = sub.add_parser("tune", help="render a parameter sweep of Hangul scale/dy for one weight")
    t.add_argument("family", nargs="?", default="mono")
    t.add_argument("--weight", default="Regular")
    t.add_argument("--scale", default=None, help="start:stop:step, e.g. 0.92:1.0:0.04")
    t.add_argument("--dy", default=None, help="start:stop:step in font units")
    t.add_argument("-o", "--output", type=Path, default=Path("proofs/tune.png"))

    q = sub.add_parser("qa", help="run the automated test pipeline and write a report")
    q.add_argument("--profile", choices=["quick", "ci", "release"], default="quick")
    q.add_argument("--family", default="mono")
    q.add_argument("--report-dir", type=Path, default=Path("reports"))
    q.add_argument("--update-golden", action="store_true", help="accept current renders")

    d = sub.add_parser("diff", help="structural diff of two font files")
    d.add_argument("old", type=Path)
    d.add_argument("new", type=Path)

    st = sub.add_parser("studio", help="local web UI for Hangul tuning (writes config/families)")
    st.add_argument("--host", default="127.0.0.1")
    st.add_argument("--port", type=int, default=8765)
    st.add_argument("--no-browser", action="store_true")

    ph = sub.add_parser("phi", help="golden-ratio proportion report (config/proportions.toml)")
    ph.add_argument("fonts", nargs="*", type=Path, help="font files; default build/master/*.ttf")

    w = sub.add_parser("webfont", help="convert TTF files to WOFF2")
    w.add_argument("fonts", nargs="+", type=Path)
    w.add_argument("-o", "--out-dir", type=Path, default=Path("build/webfonts"))

    si = sub.add_parser("site", help="assemble the prototype site into build/site")
    si.add_argument("-o", "--out", type=Path, default=None)

    args = ap.parse_args(argv)

    if args.cmd == "qa":
        from .qa import run

        report = run(args.profile, args.family, args.report_dir, args.update_golden)
        print(f"\nreport: {args.report_dir / 'qa.md'}  result: {'PASS' if report.ok else 'FAIL'}")
        return 0 if report.ok else 1

    if args.cmd == "diff":
        from .diff import diff_fonts, format_diff

        print(format_diff(diff_fonts(TTFont(args.old), TTFont(args.new))))
        return 0

    if args.cmd == "studio":
        from .studio.server import serve

        serve(args.host, args.port, open_browser=not args.no_browser)
        return 0

    if args.cmd == "phi":
        from .proportions import format_report, report_files

        files = args.fonts or sorted((config.BUILD_DIR / "master").glob("*.ttf"))
        if not files:
            print("no fonts: run `nkfont build` first or pass font files")
            return 1
        print(format_report(report_files(files)))
        return 0

    if args.cmd == "webfont":
        from .site import to_woff2

        for f in args.fonts:
            print(to_woff2(f, args.out_dir / f"{f.stem}.woff2"))
        return 0

    if args.cmd == "site":
        from .site import build_site

        print(build_site(args.out))
        return 0

    if args.cmd == "fetch":
        from .fetch import fetch_all

        for sid in fetch_all():
            print(f"ok  {sid}")
        return 0

    if args.cmd == "build":
        from .build import build_family

        ids = config.family_ids() if args.family == "all" else [args.family]
        for fid in ids:
            if args.family == "all" and config.family(fid).get("status") != "active":
                continue
            for path in build_family(fid, only=args.weight):
                print(path)
        return 0

    if args.cmd == "patch":
        from .build import is_terminal
        from .patch import patch

        masters = args.masters
        if not masters:
            # Only terminal families get Nerd Fonts icons; reading faces (kind = "text") don't.
            prefixes = [
                f["file_prefix"]
                for f in map(config.family, config.family_ids())
                if is_terminal(f) and f.get("status") == "active"
            ]
            masters = [
                m
                for m in sorted((config.BUILD_DIR / "master").glob("*.ttf"))
                if m.stem.split("-")[0] in prefixes
            ]
        for path in patch(masters):
            print(path)
        return 0

    if args.cmd == "check":
        from .checks import run_all

        base = TTFont(args.base) if args.base else None
        own = None
        if args.master and base is not None:
            own = set(TTFont(args.master).getBestCmap()) - set(base.getBestCmap())
        failed = False
        for f in args.fonts:
            print(f"== {f}")
            for name, problems in run_all(TTFont(f), base, own, kind=args.kind).items():
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
