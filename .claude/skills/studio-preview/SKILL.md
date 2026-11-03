---
name: studio-preview
description: Launch NK Studio (/, /lab, /presets, /specimen) or the built site and take browser screenshots to confirm a UI or render change. Use when asked to run, open, preview or screenshot the studio, Glyph Lab, specimen, design notes, compare/tester pages or the Pages site.
---

# Previewing NK Studio and the site

Browser checks: the owner prefers **ego-browser**. Use it when the `ego-browser` command exists
(`command -v ego-browser`); otherwise (cloud sessions: it is not on npm/pip) use Playwright and
say so in the reply. The owner re-checks on their Mac.

1. Fonts first: `nkfont build <family> --weight Regular` (the pages read `build/master/`).
2. Studio: `nkfont studio --no-browser --port 8765` in the background
   (Bash `run_in_background`), wait for `curl -sf http://127.0.0.1:8765/` to answer.
   Pages: `/` (Hangul tuning), `/lab`, `/presets`, `/specimen`, `/site` (built site).
   `/api/save` writes `config/families/*.toml`: do not click Save unless asked.
3. Site only: `nkfont site` → `build/site/`, serve with `python -m http.server -d build/site 8000`.
   Pages: `index.html`, `compare.html`, `tester.html`, `design.html`.
4. Screenshot with Playwright (preinstalled in cloud sessions; no `playwright install`):
   ```bash
   node -e "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();
   const p=await b.newPage({viewport:{width:1280,height:900},deviceScaleFactor:2});
   await p.goto('http://127.0.0.1:8765/lab');await p.waitForLoadState('networkidle');
   await p.screenshot({path:'proofs/app/lab.png',fullPage:true});await b.close()})()"
   ```
   Use `deviceScaleFactor: 1` for screenshots only you read. Also check a 390 px wide viewport.
   Read the PNG yourself before describing it; check the console for errors (`p.on('console')`).
5. Screenshots for the owner go to `/mnt/project-files/proofs/<topic>/` and are attached to the
   reply; `proofs/` in the repo is git-ignored.
6. Stop the server when done. The desktop window (`nkfont app`, pywebview) needs a display:
   only the owner can run it, on macOS.
