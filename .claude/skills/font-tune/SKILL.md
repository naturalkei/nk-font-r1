---
name: font-tune
description: Fine-tune NK font parameters (Hangul scale, offset, width, slant, grade, weight mapping) with the Glyph Lab, golden-ratio rules, sweeps and proof sheets. Use when asked to adjust Hangul size/position/weight/slant or compare against JetBrains Mono, D2Coding and other fonts.
---

# Tuning NK fonts

All tunables live in `config/families/<family>.toml` under `[hangul]` (and per `[[weight]]`).
Never hard-code a tuned number in Python.

0. Tune by targets, not numbers: the Glyph Lab's default view (`nkfont studio` -> /lab) shows the
   control glyphs (n o H O, 한 국 을 를) and a few design variables declared in `config/lab.toml`
   `[core]` (Hangul height × caps, width × height, stem × Latin, optical centre, slant, tracking).
   Each is a *target*; `studio/controls.py` solves the raw `[hangul]` values that meet all of them
   at once, so moving one keeps the others. Add a control there, never a hard-coded number.
   Measure: `nkfont phi` (golden-ratio rules from `config/proportions.toml`, shared by every
   family) and the advanced lab (`/lab/advanced`): overlay NK glyphs on
   JetBrains Mono / D2Coding, read stems on scanlines, stroke slant, side bearings, ink coverage,
   and toggle OpenType features. `[hangul]` knobs: `scale`, `dy`, `center`, `width` (horizontal
   ratio), `slant` (degrees, italics), `grade` (stroke weight in units, advances unchanged).
   The grid wins over phi: locked rules are only reported.
1. Sweep: `nkfont tune <family> --weight Regular --scale 0.92:1.04:0.04 --dy -30:10:20 -o proofs/tune.png`
   (builds in memory, nothing is written to build/).
2. Read the PNG and compare: Hangul height vs Latin cap height (target ~1.15–1.25×), optical
   vertical centre vs caps, stroke weight vs Latin, spacing inside the 2-cell grid.
3. Check small sizes too: add `--size 14` style renders via `nkfont proof --size 14`.
4. Write the chosen values to the TOML with a one-line comment on why, rebuild, run `font-qa`.
5. Put before/after proofs in the PR description.

Reference numbers (Source Han Sans KR at UPM 1000): Hangul advance 920, outline ≈ x 50–870,
y −77–834. JetBrains Mono: cap height 730, x-height 550, line 1020/−300.
