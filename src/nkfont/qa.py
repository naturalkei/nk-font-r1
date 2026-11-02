"""Test automation: one command that runs every check a change needs and writes a report.

Profiles grow from fast to thorough:
  quick    lint, unit tests, Regular master build, font checks, reproducibility, golden images,
           golden-ratio proportion report (advisory)
  ci       quick + all weights, real-font tests, Nerd Fonts patch (Docker), checks on patched fonts
  release  ci + manual terminal-matrix checklist in the report
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from fontTools.ttLib import TTFont

from . import config

PROFILES = ("quick", "ci", "release")
MATRIX = [
    "Starship (Nerd Font Symbols preset): separators and Korean path",
    "zsh + Powerlevel10k: `p10k configure` icon test",
    "iTerm2: built-in Powerline glyphs on/off, ambiguous width off, NFC normalisation",
    "macOS Terminal.app",
    "GNOME Terminal (VTE)",
    "Konsole",
    "kitty",
    "Alacritty",
    "WezTerm",
    "Windows Terminal (ClearType 12-14px)",
    "VS Code integrated terminal and editor",
    "JetBrains IDE",
]


@dataclass
class Stage:
    name: str
    status: str = "pending"  # pass, fail, warn, skip
    seconds: float = 0.0
    details: list[str] = field(default_factory=list)


@dataclass
class Report:
    profile: str
    family: str
    stages: list[Stage] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.status in ("pass", "warn", "skip") for s in self.stages)


class Runner:
    def __init__(self, profile: str, family: str, report_dir: Path, update_golden: bool):
        self.report = Report(profile, family)
        self.report_dir = report_dir
        self.update_golden = update_golden
        self.masters: list[Path] = []
        self.patched: list[Path] = []

    def stage(self, name, fn) -> Stage:
        st = Stage(name)
        print(f"-> {name}", flush=True)
        t0 = time.monotonic()
        try:
            fn(st)
            if st.status == "pending":
                st.status = "pass"
        except Exception as exc:  # a crashing stage is a failed stage, keep going
            st.status = "fail"
            st.details.append(f"{type(exc).__name__}: {exc}")
        st.seconds = round(time.monotonic() - t0, 1)
        print(f"   {st.status.upper()} ({st.seconds}s)", flush=True)
        for line in st.details[:10]:
            print(f"     {line}")
        self.report.stages.append(st)
        return st

    # ---- stages -------------------------------------------------------------------------

    def lint(self, st: Stage) -> None:
        for cmd in (
            ["ruff", "check", "src", "tests"],
            ["ruff", "format", "--check", "src", "tests"],
        ):
            r = _run([sys.executable, "-m", *cmd])
            if r.returncode:
                st.status = "fail"
                st.details += r.stdout.strip().splitlines()[-15:]

    def unit_tests(self, st: Stage, slow: bool) -> None:
        args = [sys.executable, "-m", "pytest", "-q"] + ([] if slow else ["-m", "not slow"])
        r = _run(args)
        st.details.append(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "no output")
        if r.returncode:
            st.status = "fail"
            st.details += r.stdout.strip().splitlines()[-20:-1]

    def fetch(self, st: Stage) -> None:
        from .fetch import fetch_all

        st.details.append(f"{len(fetch_all())} upstream fonts verified")

    def build(self, st: Stage, only: str | None) -> None:
        from .build import build_family

        self.masters = build_family(self.report.family, only=only)
        st.details += [p.name for p in self.masters]

    def font_checks(self, st: Stage, files: list[Path]) -> None:
        from .checks import check_overflow, inherited_codepoints, run_all

        fam = config.family(self.report.family)
        kind = fam.get("kind", "merge")
        # The family's own Latin base (or the single pixel source) is the comparison point.
        srcs = config.sources()
        bases = {}
        for w in fam["weight"]:  # weights may use different Latin sources (NK Comics Black)
            sid = w.get("latin") or w["source"]
            bases[w["name"].replace(" ", "")] = TTFont(srcs[sid].path)
        first = next(iter(bases.values()))
        own = None
        if self.masters:  # code points our merge added; patcher additions are not ours
            own = set(TTFont(self.masters[0]).getBestCmap()) - set(first.getBestCmap())
        for f in files:
            font = TTFont(f)
            base = bases.get(f.stem.split("-")[-1], first)
            for name, problems in run_all(font, base, own, kind=kind).items():
                for p in problems[:5]:
                    st.details.append(f"{f.name} {name}: {p}")
                if problems:
                    st.status = "fail"
            if kind == "text":
                continue  # proportional: no cells to overflow
            warnings = check_overflow(font, inherited_codepoints(font, base, own))[1]
            if warnings and st.status != "fail":
                st.status = "warn"
            if warnings:
                st.details.append(f"{f.name} overflow warnings (inherited/PUA): {len(warnings)}")

    def reproducible(self, st: Stage) -> None:
        from .build import build_family

        if not self.masters:
            st.status = "skip"
            return
        target = self.masters[0]
        weight = target.stem.split("-")[-1]
        with tempfile.TemporaryDirectory() as tmp:
            again = build_family(self.report.family, out_dir=Path(tmp), only=weight)[0]
            a, b = _sha(target), _sha(again)
        st.details.append(f"{target.name} {a[:12]} vs rebuild {b[:12]}")
        if a != b:
            st.status = "fail"

    def golden(self, st: Stage, files: list[Path]) -> None:
        from .golden import compare, render_golden

        text = config.family(self.report.family).get("kind") == "text"
        for f in files:
            res = compare(
                f.stem,
                render_golden(f, text=text),
                update=self.update_golden,
                out_dir=self.report_dir / "golden-diff",
            )
            st.details.append(f"{res.name}: {res.status} {res.detail}".rstrip())
            if res.status == "fail":
                st.status = "fail"
            elif res.status in ("new", "updated") and st.status == "pending":
                st.status = "warn"

    def proportions(self, st: Stage) -> None:
        """Golden-ratio rules (config/proportions.toml). Advisory: off-target is a warning."""
        from .proportions import report_files

        if not self.masters:
            st.status = "skip"
            return
        fam = config.family(self.report.family)
        for name, results in report_files(self.masters, fam=fam):
            for r in results:
                if r["actual"] is None or r["locked"] or r["ok"]:
                    continue
                st.status = "warn"
                st.details.append(
                    f"{name} {r['id']}: {r['actual']:.3f} vs {r['expr']}={r['target']:.3f} "
                    f"({r['deviation']:+.1%}) -> {r['drives'] or 'source design'}"
                )

    def patch(self, st: Stage) -> None:
        if config.family(self.report.family).get("kind") == "text":
            st.status = "skip"
            st.details.append("reading face: no Nerd Fonts icons by design")
            return
        if not shutil.which("docker") or _run(["docker", "info"]).returncode:
            st.status = "skip"
            st.details.append("docker daemon not available")
            return
        from .patch import patch

        self.patched = patch(self.masters)
        st.details += [p.name for p in self.patched]

    def proof(self, st: Stage) -> None:
        from .proof import render

        files = self.masters + self.patched
        if not files:
            st.status = "skip"
            return
        out = self.report_dir / "proof.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        render([(f.name, f) for f in files]).save(out)
        self.report.artifacts.append(str(out))

    # ---- orchestration ------------------------------------------------------------------

    def run(self) -> Report:
        p = self.report.profile
        thorough = p in ("ci", "release")
        self.stage("lint", self.lint)
        self.stage("fetch upstream fonts", self.fetch)
        self.stage(
            "unit tests" + (" + real fonts" if thorough else ""),
            lambda st: self.unit_tests(st, slow=thorough),
        )
        self.stage("build masters", lambda st: self.build(st, None if thorough else "Regular"))
        self.stage("font checks (masters)", lambda st: self.font_checks(st, self.masters))
        self.stage("reproducible build", self.reproducible)
        self.stage("golden images (masters)", lambda st: self.golden(st, self.masters))
        self.stage("golden-ratio proportions", self.proportions)
        if thorough:
            self.stage("nerd fonts patch", self.patch)
            if self.patched:
                self.stage("font checks (patched)", lambda st: self.font_checks(st, self.patched))
        self.stage("proof sheet", self.proof)
        return self.report


def write_report(report: Report, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "qa.json").write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    icon = {"pass": "✅", "warn": "⚠️", "skip": "⏭️", "fail": "❌", "pending": "…"}
    lines = [
        f"## nkfont qa · {report.family} · profile `{report.profile}`",
        "",
        f"**Result: {'PASS' if report.ok else 'FAIL'}**",
        "",
        "| Stage | Result | Time | Details |",
        "| --- | --- | --- | --- |",
    ]
    for s in report.stages:
        details = "<br>".join(d.replace("|", "\\|") for d in s.details[:6])
        lines.append(f"| {s.name} | {icon[s.status]} {s.status} | {s.seconds}s | {details} |")
    if report.profile == "release":
        lines += ["", "### Manual terminal matrix", ""] + [f"- [ ] {m}" for m in MATRIX]
    md = "\n".join(lines) + "\n"
    path = report_dir / "qa.md"
    path.write_text(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(md)
    return path


def run(profile: str, family: str, report_dir: Path, update_golden: bool = False) -> Report:
    if profile not in PROFILES:
        raise SystemExit(f"unknown profile {profile!r}; choose from {PROFILES}")
    report = Runner(profile, family, report_dir, update_golden).run()
    write_report(report, report_dir)
    return report


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=config.ROOT, capture_output=True, text=True)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
