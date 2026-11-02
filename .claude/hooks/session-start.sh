#!/bin/bash
# Prepare a Claude Code cloud session: Python venv with the nkfont CLI and pinned upstream fonts.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

hashes=.venv/.session-start.sha256
if ! sha256sum --check --status "$hashes" 2>/dev/null; then
  rm -f "$hashes"
  python3 -m venv .venv
  .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/python -m pip install -q -e ".[dev]"
  sha256sum .claude/hooks/session-start.sh pyproject.toml > "$hashes"
fi

# Upstream fonts (sources/ is git-ignored; fetch skips files whose SHA256 already matches).
.venv/bin/nkfont fetch >/dev/null

# The Nerd Fonts patcher runs in Docker; start the daemon if the CLI exists but no daemon runs.
if command -v docker >/dev/null && ! docker info >/dev/null 2>&1 && command -v dockerd >/dev/null; then
  (sudo -n dockerd >/tmp/dockerd.log 2>&1 &) || true
fi

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$PWD/.venv/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi
