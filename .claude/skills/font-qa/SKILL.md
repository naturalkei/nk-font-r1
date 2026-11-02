---
name: font-qa
description: Verify NK font builds for terminal compatibility (cell widths, metrics, names, OpenType features) and produce proof sheets. Use after any build or pipeline change, before committing or opening a PR.
---

# NK font QA

Run the automated pipeline and report its actual output; a build is "working" only when it passes.

1. `nkfont qa` (quick, ~15 s) after every change; `nkfont qa --profile ci` (~3 min, needs Docker
   for the patch stage) before a PR. Read `reports/qa.md`; failures exit with code 1.
   Stages: lint, upstream SHA256, unit (+ real-font) tests, master build, font checks (widths,
   ink overflow, metrics, names, features), reproducible build, golden images, Nerd patch +
   patched checks, proof sheet. See docs/TESTING.md.
2. Golden failure: open `reports/golden-diff/*.diff.png` (red = old, green = new). If the change
   is intended, `nkfont qa --update-golden` and commit the new PNGs; otherwise fix the code.
3. `nkfont diff old.ttf new.ttf` to explain what changed (cmap, advances, outlines, metrics, names).
4. Look at `reports/proof.png` (Read tool): Hangul on the 2-cell grid, box drawing connects.

When a width check fails, decide by source:
- Latin base or patcher quirk → extend `fit_terminal_widths` in `src/nkfont/flags.py`.
- Imported Hangul-font glyph → fix selection in `src/nkfont/merge.py` (`cell_width`).
Overflow errors on glyphs we import → adjust `fit`/scale in the family TOML or `merge.py`.
Add a regression test in `tests/` with the synthetic fixtures (`tests/conftest.py`).

Manual terminal matrix before a release (docs/PLAN.md §6.3): Starship, Powerlevel10k, iTerm2,
GNOME Terminal, Konsole, kitty, Alacritty, WezTerm, Windows Terminal, VS Code.
