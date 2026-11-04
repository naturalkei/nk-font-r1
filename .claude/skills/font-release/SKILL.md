---
name: font-release
description: Cut an NK font release (version bump, release QA with fontbakery, terminal matrix, GitHub Release assets, Pages). Use when asked to release, tag, publish a pre-release, or prepare release notes for NK Mono/Pixel/Sans/Serif/Novel/Comics.
---

# Releasing NK fonts

A release is a git tag plus a GitHub Release. Pages redeploys only when the `release` branch moves
(`make release-pages` = `git push origin main:release`, step 6), never on a merge to main.
Tagging and publishing are outward-facing: confirm with the owner before pushing a tag.

1. **Version.** Bump `version` in each `config/families/<family>.toml` that changed (semver;
   `v0.x.y-alpha` while pre-1.0, docs/ROADMAP.md). `names.py` writes nameID 5 and
   `head.fontRevision` from it: they must agree (fontbakery `opentype/font_version`).
2. **Release QA per family:** `make qa-release FAMILY=<id>` (installs the optional `[audit]`
   extra, runs `nkfont qa --profile release`). Needs Docker for the patch stage. Read
   `reports/qa.md`; every stage must be pass/warn. New fontbakery findings fail: fix them or,
   with a reason, add them to `[warn_only]` in `config/audit.toml`.
3. **Manual terminal matrix:** tick the checklist at the end of `reports/qa.md` on real
   terminals (Starship, Powerlevel10k, iTerm2, GNOME Terminal, Konsole, kitty, Alacritty, WezTerm,
   Windows Terminal, VS Code). The owner does this on their Mac; ask, never tick for them.
4. **Assets:** `nkfont build all && nkfont patch && nkfont site`. Zip per family with
   `OFL.txt` and upstream notices (docs/PLAN.md §release). NK Pixel game packs are separate zips.
5. **Release notes:** what changed since the last tag (`git log <prev>..HEAD`, plus
   `nkfont diff old.ttf new.ttf` per family for glyph/metric changes), renamed names or
   features, known issues from `[warn_only]`.
6. **Publish** after the owner says go: tag `vX.Y.Z`, push the tag, create the GitHub Release
   (draft first) and attach the zips. Then update the site: `make release-pages` (fast-forwards
   `release` to `main`; `.github/workflows/pages.yml` rebuilds, Nerd-patches and deploys).

Never put Reserved Font Names in asset or file names; keep `Copyright 2026 naturalk (nk-font)`.
