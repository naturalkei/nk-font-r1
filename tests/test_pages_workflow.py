"""GitHub Pages deploys only from the `release` branch, never on merges to main."""

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "pages.yml"


def _trigger_block() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    return re.search(r"^on:\n((?:[ #].*\n|\n)*)", text, re.M).group(1)


def test_pages_push_trigger_is_release_only():
    block = _trigger_block()
    assert re.findall(r"branches:\s*\[(.*?)\]", block) == ["release"]
    assert "pull_request" not in block


def test_manual_pages_run_is_limited_to_release():
    text = WORKFLOW.read_text(encoding="utf-8")
    build = text.split("\n  build:\n", 1)[1].split("\n  deploy:\n", 1)[0]
    assert "if: github.ref == 'refs/heads/release'" in build
    assert "run: nkfont patch" in build
