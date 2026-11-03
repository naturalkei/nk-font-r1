#!/bin/bash
# PostToolUse (Edit|Write): ruff-format the Python file Claude just changed, so `nkfont qa` lint
# never fails on formatting. Silent no-op for other files or when the venv is missing.
set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}"
file=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
case "$file" in
  *.py) ;;
  *) exit 0 ;;
esac
[ -x .venv/bin/ruff ] && [ -f "$file" ] || exit 0
.venv/bin/ruff format -q "$file" >/dev/null 2>&1 || true
.venv/bin/ruff check -q --fix --select I "$file" >/dev/null 2>&1 || true
exit 0
