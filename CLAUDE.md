# nk-nerd-font (nk-font)

OFL 1.1 Korean fonts. Terminal Nerd Font families **NK Mono** (flagship: JetBrains Mono + D2Coding Hangul)
and **NK Pixel**; proportional families (`kind = "text"`) **NK Sans** and **NK Serif** (documents),
**NK Novel** (books/news) and **NK Comics** (comic lettering).
Families, φ rules, weights and feature plans: `docs/FAMILIES.md`.
Primary goal: perfect grid alignment in terminals (Starship, zsh/Powerlevel10k, iTerm2, Linux
terminals). NK Pixel must also work in pixel-art games (Minecraft, Terraria) and game engines.

- Plan: `docs/PLAN.md` · Roadmap: `docs/ROADMAP.md` · Testing: `docs/TESTING.md` · Answer in Korean when talking to the owner.
- Copyright line for our work: `Copyright 2026 naturalk (nk-font)`.

## Commands
```bash
make setup            # .venv + nkfont CLI (the cloud session hook does this automatically)
nkfont fetch          # pinned upstream fonts -> sources/ (SHA256 checked, never committed)
nkfont build mono     # build/master/NKMono-*.ttf  (mono|pixel|sans|serif|novel|comics|all)
nkfont patch          # Docker Nerd Fonts patcher -> dist/NK*NerdFont*.ttf (terminal families only)
nkfont check FILES --base sources/JetBrainsMono-Regular.ttf [--master build/master/NKMono-Regular.ttf] [--kind text]
nkfont qa [--profile quick|ci|release]   # full automated pipeline + report (docs/TESTING.md)
nkfont diff OLD.ttf NEW.ttf              # what a change actually did
nkfont audit [FILES]  # fontbakery (optional `pip install -e ".[audit]"`, config/audit.toml);
                      #   also the qa `release` stage (`make qa-release FAMILY=mono`)
nkfont proof FILES -o proofs/proof.png
nkfont tune mono --scale 0.92:1.04:0.04 --dy -30:10:20
nkfont studio         # NK Studio web UI: live Hangul tuning, saves [hangul] in config/families
                      #   /lab = Glyph Lab: overlay vs JetBrains Mono/D2Coding, stems, slant, OT features
                      #   /presets = side-by-side style presets (config/presets/*.toml, never a build input)
                      #   /specimen = per-family specimen workbench (NK axes, φ type scale)
nkfont app            # same pages in a native window (pywebview, `pip install -e ".[app]"`);
                      #   --install-mac-app writes ~/Applications/NK Studio.app
                      #   /update = self-update: git pull --ff-only (stops on local edits), then restart
nkfont phi [FILES]    # golden-ratio proportion report (config/proportions.toml, shared by families)
nkfont site           # build/site: prototype site (WOFF2 + zips); deployed by .github/workflows/pages.yml
python -m pytest -q   # unit tests use synthetic fonts; real-font tests skip without sources/
ruff check src tests && ruff format --check src tests
```

## Invariants (do not break)
- Terminal families: advances are only `0 / 600 / 1200` (UPM 1000) and must equal wcwidth cell counts.
  Reading families (`kind = "text"`) are proportional, never Nerd-patched, and must cover all 11,172
  syllables; their line height comes from `[metrics] line_height` (`"phi"`, `"phi^0.5"`, see phi.py).
  `nkfont check` enforces it; `fit_terminal_widths` fixes base/patcher quirks.
- Never run the patcher with `--mono`/`-s`: it forces Hangul to one cell. Mono variant uses
  `--single-width-glyphs`.
- Keep the Latin base's line metrics (JetBrains Mono 1020/-300, lineGap 0, USE_TYPO_METRICS).
  `usWin*` must cover the real bbox. Re-apply `enforce_terminal_flags` after patching.
- Never import East Asian *Ambiguous* characters from the Hangul font; never overwrite Latin glyphs.
- U+1100–11FF conjoining jamo are out of scope until phase 2 (needs ljmo/vjmo/tjmo).
- Merge with fontTools into the Latin TTF so GSUB/GPOS survive; don't round-trip through FontForge.
- Reserved Font Names `Source`, `Pretendard`, `Plex`, `Neo둥근모`, `NeoDunggeunmo`, `Nanum`/`나눔`, `D2Coding` must not appear in our names.
- Only reverse contours of cubic (CFF) Hangul sources; TrueType sources keep their direction.
- NK Pixel (`kind = "pixel"`) is one source font renamed, not merged: width conflicts (Ambiguous
  symbols drawn two cells) are unmapped, never squeezed.
- All tunables live in `config/families/*.toml`; code reads them, never hard-codes them.
  Golden-ratio (φ) targets live in `config/proportions.toml`; on grid families the grid and Latin metrics
  win over φ (`locked`, reported only); proportional families (`grid = false`) skip `grid_only` rules. New `[hangul]` knobs must default
  to the identity so existing builds stay byte-identical.
- Pin every upstream input in `sources.lock` (URL + SHA256, patcher image tag + digest).

## Testing rule
Every feature PR adds the qa stage or test that verifies it; every bug fix adds a regression test
with the synthetic fixtures. Run `nkfont qa` before committing; CI runs `nkfont qa --profile ci`.
Design changes that alter renders need `nkfont qa --update-golden` and the new PNGs in the PR.

## Layout
`src/nkfont/` pipeline (merge, names, flags, checks, patch, proof, cli) · `config/` families and
ranges · `tests/` · `.claude/skills/` project skills (font-build, font-qa, font-tune, font-glyphs, font-release,
studio-preview) · `.claude/hooks/` session setup (venv + `nkfont fetch`) and ruff-format after edits.
Browser checks: ego-browser when installed, otherwise Playwright (cloud sessions).
