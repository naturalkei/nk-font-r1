# nk-nerd-font (nk-font)

OFL 1.1 Korean fonts. Terminal Nerd Font families **NK Mono** (flagship: JetBrains Mono + D2Coding Hangul)
and **NK Pixel**; proportional families (`kind = "text"`) **NK Sans** and **NK Serif** (documents),
**NK Novel** (books/news) and **NK Comics** (comic lettering).
Families, φ rules, weights and feature plans: `docs/FAMILIES.md`. Every family ships Thin 100 – ExtraBold 800
(`[weights]` + `[[weight]]`, `src/nkfont/weights.py`; Pixel: Regular + bitmap Bold); missing upstream weights are
derived with `latin_grade`, and `match = "stem+bar"` keeps Hangul/Latin stroke ratios at Regular's in every weight.
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
                      #   /lab = Glyph Lab core view: control glyphs (noHO 한국을를) + a few design targets
                      #     (height, width, stem, centre... config/lab.toml [core]); the solver derives [hangul]
                      #     every save is a numbered version in config/versions/<family>.toml (restorable)
                      #   /lab/advanced = overlay vs JetBrains Mono/D2Coding, stems, scanlines, OT features
                      #   /presets = side-by-side style presets (config/presets/*.toml, never a build input;
                      #     [hangul], plus [style] for text families and [pixel] for NK Pixel), with harmony QA
                      #   /specimen = per-family specimen workbench (NK axes, φ type scale)
nkfont app            # same pages in a native window (pywebview, `pip install -e ".[app]"`);
                      #   --install-mac-app writes ~/Applications/NK Studio.app
                      #   /update = self-update: git pull --ff-only (stops on local edits), then restart
nkfont phi [FILES]    # golden-ratio proportion report (config/proportions.toml, shared by families)
nkfont presets [FAMILY|ID ...] [--proof DIR]   # Hangul/Latin harmony + distinctness QA of every preset
                      #   (config/preset_qa.toml bands; also the qa stage "preset harmony")
nkfont site           # build/site: prototype site (WOFF2 + zips); deployed by .github/workflows/pages.yml
                      #   only on push to the `release` branch (`make release-pages` = git push origin main:release),
                      #   never on merges to main
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
- Reserved Font Names `Source`, `Pretendard`, `Plex`, `Neo둥근모`, `NeoDunggeunmo`, `Nanum`/`나눔`, `D2Coding`, `Mulmaru`/`물마루` must not appear in our names.
- Only reverse contours of cubic (CFF) Hangul sources; TrueType sources keep their direction.
- NK Pixel (`kind = "pixel"`) is one source font renamed, not merged: width conflicts (Ambiguous
  symbols drawn two cells) are unmapped, never squeezed.
- All tunables live in `config/families/*.toml`; code reads them, never hard-codes them.
  Golden-ratio (φ) targets live in `config/proportions.toml`; on grid families the grid and Latin metrics
  win over φ (`locked`, reported only); proportional families (`grid = false`) skip `grid_only` rules. New `[hangul]` knobs must default
  to the identity so existing builds stay byte-identical. The same holds for `[style]` (text families: one transform
  for Latin and Hangul together, src/nkfont/style.py) and `[pixel]` (NK Pixel: whole-pixel bitmap knobs that never
  close a one-pixel gap, src/nkfont/pixelstyle.py).
- Every preset in `config/presets/` must stay inside its Hangul/Latin harmony bands and be distinct from
  every other preset of its family (`distinct` knob steps and rendered `look` difference, `nkfont presets`).
- A family whose Latin source draws its own Hangul can re-import it (`[hangul] replace = true`) and fill the
  missing syllables from a second source (weight `fill`, `[fill]` relative knobs, per-weight `fill_adjust`).
- Pin every upstream input in `sources.lock` (URL + SHA256, patcher image tag + digest).
  Reference fonts whose terms don't clearly allow redistribution (e.g. 만화진흥원체/KOMACON) go in
  `config/local_fonts.toml` instead: found on the owner's disk, shown in the Lab, never committed,
  fetched, merged or put on the site.

## Testing rule
Every feature PR adds the qa stage or test that verifies it; every bug fix adds a regression test
with the synthetic fixtures. Run `nkfont qa` before committing; CI runs `nkfont qa --profile ci`.
Design changes that alter renders need `nkfont qa --update-golden` and the new PNGs in the PR.

## Layout
`src/nkfont/` pipeline (merge, names, flags, checks, patch, proof, cli) · `config/` families and
ranges · `tests/` · `.claude/skills/` project skills (font-build, font-qa, font-tune, font-glyphs, font-release,
studio-preview) · `.claude/hooks/` session setup (venv + `nkfont fetch`) and ruff-format after edits.
Browser checks: ego-browser when installed, otherwise Playwright (cloud sessions).
