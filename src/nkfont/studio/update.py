"""Self-update for the NK Studio app: fast-forward the checkout and reinstall when needed.

The app runs straight from the repository (editable install), so an update is `git pull`:
  check()  fetch the upstream branch and report how far behind/ahead the checkout is
  apply()  `git pull --ff-only`, then `pip install -e .[app]` only if pyproject.toml changed
It never merges, rebases, stashes or discards: a dirty tree or local commits stop the update
with a message, so nothing the user wrote is touched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .. import config


class UpdateError(RuntimeError):
    pass


def _git(root: Path, *args: str, timeout: float = 60) -> str:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f"git {args[0]}: {exc}") from exc
    if out.returncode != 0:
        raise UpdateError(f"git {' '.join(args)}: {out.stderr.strip() or out.stdout.strip()}")
    return out.stdout.strip()


def status(root: Path = config.ROOT, fetch: bool = True) -> dict:
    """Where the checkout stands against its upstream branch (after a fetch by default)."""
    if not (root / ".git").exists():
        raise UpdateError(f"{root} is not a git checkout")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    try:
        upstream = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    except UpdateError as exc:
        raise UpdateError(f"branch {branch!r} has no upstream to update from") from exc
    if fetch:
        remote, _, rbranch = upstream.partition("/")
        _git(root, "fetch", "--quiet", remote, rbranch, timeout=120)
    behind, ahead = (
        int(x) for x in _git(root, "rev-list", "--left-right", "--count", "@{u}...HEAD").split()
    )
    log = _git(root, "log", "--format=%h %s", "-n", "20", "HEAD..@{u}") if behind else ""
    # Porcelain lines are "XY path"; the output is stripped, so split instead of slicing.
    # Untracked files (e.g. new presets) don't block: a fast-forward refuses by itself to
    # overwrite one.
    porcelain = _git(root, "status", "--porcelain", "--untracked-files=no").splitlines()
    dirty = [line.split(None, 1)[-1] for line in porcelain]
    return {
        "branch": branch,
        "upstream": upstream,
        "head": _git(root, "rev-parse", "--short", "HEAD"),
        "behind": behind,
        "ahead": ahead,
        "dirty": dirty,
        "commits": log.splitlines(),
        "can_update": behind > 0 and ahead == 0 and not dirty,
    }


def apply(root: Path = config.ROOT, reinstall: bool = True) -> dict:
    """Fast-forward to upstream. Returns what changed; raises UpdateError when it must not."""
    st = status(root)
    if not st["behind"]:
        return {"updated": False, "head": st["head"], "message": "이미 최신입니다"}
    if st["dirty"]:
        files = ", ".join(st["dirty"][:5])
        raise UpdateError(f"커밋하지 않은 변경이 있어 업데이트하지 않았습니다: {files}")
    if st["ahead"]:
        raise UpdateError(
            f"로컬 커밋 {st['ahead']}개가 {st['upstream']}에 없습니다: 직접 pull/merge 하세요"
        )
    old = _git(root, "rev-parse", "HEAD")
    _git(root, "merge", "--ff-only", "--quiet", "@{u}")
    new = _git(root, "rev-parse", "HEAD")
    changed = _git(root, "diff", "--name-only", old, new).splitlines()
    reinstalled = False
    if reinstall and "pyproject.toml" in changed:
        cmd = [sys.executable, "-m", "pip", "install", "-q", "-e", ".[app]"]
        out = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
        if out.returncode != 0:
            raise UpdateError(f"pip install failed: {out.stderr.strip()[-400:]}")
        reinstalled = True
    return {
        "updated": True,
        "from": old[:7],
        "head": new[:7],
        "files": len(changed),
        "reinstalled": reinstalled,
        "message": f"{st['behind']}개 커밋을 받았습니다. 다시 시작하면 반영됩니다.",
    }
