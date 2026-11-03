---
name: font-glyphs
description: Add or fix glyph coverage in NK fonts (missing Korean-document symbols like ※★①, new Unicode ranges, empty or inked whitespace glyphs). Use when asked to add characters, fill a coverage gap from the benchmark page, or fix a glyph fontbakery/nkfont check reports.
---

# Adding glyphs to NK fonts

Coverage decisions are width decisions first. Work out the cell count before touching outlines.

1. **Find the gap.** `nkfont qa` benchmark stage lists `todo:` notes; `src/nkfont/compare.py`
   `KR_SYMBOLS` is the Korean-document symbol set. For one font:
   `python -c "from fontTools.ttLib import TTFont; c=TTFont('build/master/NKMono-Regular.ttf').getBestCmap(); print([ch for ch in '※★' if ord(ch) not in c])"`.
2. **Classify each code point** with `unicodedata.east_asian_width` and `wcwidth.wcwidth`:
   - `W`/`F` → 2 cells, `H`/`Na`/`N` → 1 cell: can come from the Hangul source via a
     `[[range]]` in `config/ranges.toml` (`cell_width` in `merge.py` picks the advance).
   - `A` (Ambiguous: ※ ★ ① ○ → · …) → **never** import from the Hangul font (CLAUDE.md
     invariant). Terminals draw them 1 cell in a non-CJK locale. Options, in order:
     a) the Latin base already has it (keep it); b) a 1-cell drawing from another OFL source
     pinned in `sources.lock`; c) draw it in our own code (a small outline builder, numbers in
     a config TOML). Ask the owner before (b) or (c): it is a design and licence decision.
   - NK Pixel: conflicting widths are unmapped, never squeezed.
   - Reading families (`kind = "text"`): no cell rule, advance is the source's.
3. **Never overwrite** a glyph the Latin base already maps (`select_codepoints` only adds).
4. **Whitespace and empty letters.** Space-like code points (U+3000, U+00A0, U+2000–200A) must
   have no contours; a letter (`L*` category) must have ink. fontbakery `whitespace_ink` /
   `empty_letters` catch both (`nkfont audit`).
5. **Test.** Add a synthetic-font regression test in `tests/` (fixtures in `tests/conftest.py`)
   that asserts the advance and presence/absence of contours, then run the `font-qa` skill.
   A visible change needs `nkfont qa --update-golden` and the PNGs in the PR.
