"""Tester code editor: Tab indents instead of moving focus (site/editkeys.js, run with node)."""

import json
import shutil
import subprocess

import pytest

from nkfont import config

SITE = config.ROOT / "site"
NODE = shutil.which("node")


def run_js(body: str):
    mod = (SITE / "editkeys.js").as_uri()
    src = f'import * as k from "{mod}";\nconsole.log(JSON.stringify(({body})));'
    cmd = [NODE, "--input-type=module", "-e", src]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_tab_inserts_unit_at_caret():
    r = run_js('k.indent("ab", 1, 1, "  ")')
    assert r == {"text": "a  b", "start": 3, "end": 3, "insert": "  "}
    assert run_js('k.indentUnit("Go")') == "\t"
    assert run_js('k.indentUnit("Python")') == "    "
    assert run_js('k.indentUnit("TypeScript")') == "  "


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_tab_indents_every_selected_line():
    # "a\nb\nc" with b..c selected through the end of c
    r = run_js('k.indent("a\\nb\\nc", 2, 5, "  ")')
    assert r == {"text": "a\n  b\n  c", "start": 2, "end": 9}
    # a selection ending at the start of a line leaves that line alone
    r = run_js('k.indent("a\\nb\\nc", 0, 4, "\\t")')
    assert r["text"] == "\ta\n\tb\nc"
    # blank lines stay blank
    assert run_js('k.indent("a\\n\\nb", 0, 4, "  ")')["text"] == "  a\n\n  b"


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_shift_tab_outdents_one_level():
    r = run_js('k.outdent("    x\\n  y\\nz", 6, 9, "    ")')
    assert r["text"] == "    x\ny\nz"
    assert (r["start"], r["end"]) == (6, 7)
    r = run_js('k.outdent("\\t\\tgo", 2, 2, "\\t")')
    assert r == {"text": "\tgo", "start": 1, "end": 1}
    r = run_js('k.outdent("      x", 7, 7, "  ")')
    assert r["text"] == "    x"


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_enter_keeps_indent():
    r = run_js('k.newline("  if x:", 7, 7)')
    assert r == {"text": "  if x:\n  ", "start": 10, "end": 10, "insert": "\n  "}


def test_tester_wires_tab_and_escape():
    js = (SITE / "tester.js").read_text()
    assert 'from "./editkeys.js"' in js
    assert 'e.key === "Tab"' in js and 'e.key === "Escape"' in js
    assert 'aria-describedby="tKeys"' in (SITE / "tester.html").read_text()
