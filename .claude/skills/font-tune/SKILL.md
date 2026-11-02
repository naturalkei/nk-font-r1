---
name: font-tune
description: Fine-tune NK font parameters (Hangul scale, vertical offset, weight mapping) systematically with sweeps and proof sheets. Use when asked to adjust Hangul size/position/weight or compare design variants.
---

# Tuning NK fonts

All tunables live in `config/families/<family>.toml` under `[hangul]` (and per `[[weight]]`).
Never hard-code a tuned number in Python.

1. Sweep: `nkfont tune <family> --weight Regular --scale 0.92:1.04:0.04 --dy -30:10:20 -o proofs/tune.png`
   (builds in memory, nothing is written to build/).
2. Read the PNG and compare: Hangul height vs Latin cap height (target ~1.15–1.25×), optical
   vertical centre vs caps, stroke weight vs Latin, spacing inside the 2-cell grid.
3. Check small sizes too: add `--size 14` style renders via `nkfont proof --size 14`.
4. Write the chosen values to the TOML with a one-line comment on why, rebuild, run `font-qa`.
5. Put before/after proofs in the PR description.

Reference numbers (Source Han Sans KR at UPM 1000): Hangul advance 920, outline ≈ x 50–870,
y −77–834. JetBrains Mono: cap height 730, x-height 550, line 1020/−300.
