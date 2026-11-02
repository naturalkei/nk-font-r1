---
name: font-qa
description: Verify NK font builds for terminal compatibility (cell widths, metrics, names, OpenType features) and produce proof sheets. Use after any build or pipeline change, before committing or opening a PR.
---

# NK font QA

Run all of these and report the actual output; a build is "working" only when every one passes.

1. Unit + real-font tests: `python -m pytest -q` (real-font tests skip if `sources/` is empty;
   run `nkfont fetch` so they actually run).
2. Lint: `ruff check src tests && ruff format --check src tests`.
3. Font checks: `nkfont check build/master/*.ttf dist/*.ttf --base sources/JetBrainsMono-Regular.ttf`
   - `widths`: every mapped code point's advance equals wcwidth × 600 (0/600/1200).
   - `metrics`: isFixedPitch, Panose 2/9, xAvgCharWidth 600, hhea == typo, lineGap 0,
     USE_TYPO_METRICS, usWin covers bbox.
   - `names`: no Reserved Font Names outside copyright/license records.
   - `features`: no GSUB feature of the Latin base was lost.
4. Proof: `nkfont proof <fonts> -o proofs/proof.png`, then look at the image (Read tool) and
   check that Hangul sits on the 2-cell grid, box drawing connects, and ligatures render.

When a width check fails, decide by source:
- Latin base or patcher quirk → extend `fit_terminal_widths` in `src/nkfont/flags.py`.
- Imported Hangul-font glyph → fix selection in `src/nkfont/merge.py` (`cell_width`).
Add a regression test in `tests/test_pipeline.py` with the synthetic fixtures.

Manual terminal matrix before a release (docs/PLAN.md §6.3): Starship, Powerlevel10k, iTerm2,
GNOME Terminal, Konsole, kitty, Alacritty, WezTerm, Windows Terminal, VS Code.
