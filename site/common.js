// Shared by the sub pages (compare, tester): theme toggle, font loading, small UI helpers.
export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];
export const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

export const NK_CSS = { mono: "NK Mono", sans: "NK Sans", serif: "NK Serif", pixel: "NK Pixel" };

export function initTheme() {
  const root = document.documentElement;
  try { const t = localStorage.getItem("nk-theme"); if (t) root.dataset.theme = t; } catch {}
  const btn = $("#themeBtn");
  if (btn) btn.onclick = () => {
    root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
    try { localStorage.setItem("nk-theme", root.dataset.theme); } catch {}
  };
}

export async function getJSON(url) {
  try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch { return null; }
}

// @font-face for NK families (fonts.json) and reference fonts (compare.json).
export function loadFonts(manifest, compare) {
  const css = [];
  for (const f of manifest?.families || []) {
    const name = NK_CSS[f.id] || f.family;
    for (const w of f.webfonts) css.push(`@font-face{font-family:"${name}";src:url(${w.url}) format("woff2");font-weight:${w.weight};font-display:swap}`);
  }
  for (const f of compare?.fonts || []) {
    if (f.role !== "reference") continue;
    for (const w of f.webfonts) css.push(`@font-face{font-family:"${f.css}";src:url(${w.url}) format("woff2");font-weight:${w.weight};font-display:swap}`);
  }
  const st = document.createElement("style");
  st.textContent = css.join("\n");
  document.head.appendChild(st);
}

// Font stack for a compare.json font: references get a generic fallback only, so missing
// Hangul shows up exactly as it would in a terminal (system fallback).
export const stack = (f) => `'${f.css}', monospace`;

export function seg(el, items, current, onPick, role = "radio") {
  const attr = role === "radio" ? "aria-checked" : "aria-selected";
  el.innerHTML = items.map(([v, label]) => `<button type="button" role="${role}" ${attr}="${v === current}" data-v="${esc(v)}">${label}</button>`).join("");
  el.onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    el.querySelectorAll("button").forEach((x) => x.setAttribute(attr, x === b));
    onPick(b.dataset.v);
  };
}

// Terminal cell count for the characters these pages use (matches wcwidth for them).
export function cells(ch) {
  const c = ch.codePointAt(0);
  if (c === 0x200b || (c >= 0x300 && c < 0x370)) return 0;
  if ((c >= 0x1100 && c <= 0x115f) || (c >= 0x2e80 && c <= 0xa4cf && c !== 0x303f) || (c >= 0xac00 && c <= 0xd7a3) ||
      (c >= 0xf900 && c <= 0xfaff) || (c >= 0xfe30 && c <= 0xfe4f) || (c >= 0xff00 && c <= 0xff60) || (c >= 0xffe0 && c <= 0xffe6)) return 2;
  return 1;
}
export const width = (s) => [...s].reduce((n, ch) => n + cells(ch), 0);
export const pad = (s, w) => s + " ".repeat(Math.max(0, w - width(s)));
