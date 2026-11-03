"""fontbakery audit: the community font checker as an extra opinion on top of `nkfont check`.

fontbakery is optional (`pip install -e ".[audit]"`); without it the qa stage is skipped.
Configuration (profile, excluded checks, known findings that only warn) is config/audit.toml.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import config

BAD = ("FAIL", "ERROR", "FATAL")


@dataclass(frozen=True)
class Finding:
    status: str  # FAIL / ERROR / FATAL as fontbakery reports it
    check: str  # fontbakery check id, e.g. "opentype/font_version"
    font: str
    code: str
    message: str
    known: bool  # listed in [warn_only]: a warning, not a failure


def load_audit_config(root: Path = config.ROOT) -> dict:
    return config._load(root / "config" / "audit.toml")


def available() -> bool:
    return shutil.which("fontbakery") is not None


def _check_id(key) -> str:
    # key = ["<Section: ...>", "<FontBakeryCheck:opentype/font_version>", [["font", 0]]]
    raw = key[1] if isinstance(key, list) and len(key) > 1 else str(key)
    return raw.split(":", 1)[-1].rstrip(">")


def parse_report(data: dict, cfg: dict) -> list[Finding]:
    """Failures from a fontbakery --json report, marked known if listed in [warn_only]."""
    warn_only = cfg.get("warn_only", {})
    out = []
    for section in data.get("sections", []):
        for chk in section.get("checks", []):
            if chk.get("result") not in BAD:
                continue
            cid = _check_id(chk.get("key"))
            log = next((lg for lg in chk.get("logs", []) if lg.get("status") in BAD), {})
            msg = log.get("message", {})
            if isinstance(msg, str):
                msg = {"code": "", "message": msg}
            text = " ".join(str(msg.get("message", "")).split())
            known = cid in warn_only or cid.rsplit("/", 1)[-1] in warn_only
            out.append(
                Finding(
                    chk["result"],
                    cid,
                    Path(chk.get("filename", "")).name,
                    msg.get("code", ""),
                    text,
                    known,
                )
            )
    return out


def families(files: list[Path]) -> dict[str, list[Path]]:
    """Group files by family file prefix (NKMono, NKMonoNerdFont, ...).

    fontbakery's family checks compare every file it gets, so mixing families reports noise.
    """
    groups: dict[str, list[Path]] = {}
    for f in files:
        groups.setdefault(f.stem.split("-")[0], []).append(f)
    return groups


def run_fontbakery(files: list[Path], cfg: dict | None = None) -> list[Finding]:
    cfg = cfg or load_audit_config()
    found = []
    for group in families(files).values():
        found += _run_one(group, cfg)
    return found


def _run_one(files: list[Path], cfg: dict) -> list[Finding]:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "fontbakery.json"
        cmd = ["fontbakery", f"check-{cfg.get('profile', 'universal')}", "--skip-network"]
        for cid in cfg.get("exclude", []):
            cmd += ["-x", cid]
        cmd += ["--json", str(out), *map(str, files)]
        # Exit code is non-zero whenever a check fails; the JSON report is the result.
        subprocess.run(cmd, capture_output=True, text=True)
        if not out.exists():
            raise RuntimeError("fontbakery wrote no report: " + " ".join(cmd))
        return parse_report(json.loads(out.read_text()), cfg)


def format_findings(findings: list[Finding]) -> list[str]:
    lines = []
    for f in findings:
        tag = f"{f.status} (known)" if f.known else f.status
        lines.append(f"{f.font} {f.check}: {tag} [{f.code}] {f.message[:160]}")
    return lines
