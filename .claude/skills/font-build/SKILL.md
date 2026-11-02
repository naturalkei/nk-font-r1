---
name: font-build
description: Build, patch and package NK fonts (NK Sans/Serif/Pixel) with the nkfont pipeline. Use when asked to build fonts, add a weight or family, bump an upstream font, or change the Nerd Fonts patch step.
---

# Building NK fonts

1. Make sure the environment is ready: `.venv/bin/nkfont` exists (else `make setup`) and
   `nkfont fetch` succeeds. Docker must be running for the patch step (`docker info`; in a cloud
   session start it with `sudo dockerd &` if needed).
2. Build masters: `nkfont build <family> [--weight Regular]` → `build/master/`.
3. Patch: `nkfont patch` → `dist/<Family>NerdFont-*.ttf` and `<Family>NerdFontMono-*.ttf`.
   The patcher removes spaces from the family ("NKSans Nerd Font"); that is the Nerd Fonts
   convention, keep it.
4. Always finish with the `font-qa` skill before claiming a build works.

## Adding a weight
Add a `[[weight]]` block in `config/families/<family>.toml` with `latin`/`hangul` source ids,
then add those fonts to `sources.lock` (download once, put the real SHA256; never guess hashes).

## Bumping an upstream font or the patcher
Change the URL/tag in `sources.lock`, recompute SHA256 (`sha256sum`), rebuild, run QA, and
compare proofs before and after. For the patcher, pin both the image tag and its digest and note
the bundled font-patcher version (`docker run --rm --entrypoint sh IMAGE -c 'grep -m1 ^version /nerd/font-patcher'`).

## Never
- `--mono`/`-s` in the patcher (it shrinks Hangul to one cell).
- Commit files from `sources/`, `build/`, `dist/`.
- Put `Source`, `Pretendard` or `Plex` in a family/PostScript/file name.
