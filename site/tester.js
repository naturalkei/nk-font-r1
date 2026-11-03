// Tester: write code in NK fonts with live size / weight / line height / OpenType / editor theme.
import { $, esc, initTheme, getJSON, loadFonts, stack, seg } from "./common.js";
import { indentUnit, indent, outdent, newline } from "./editkeys.js";

initTheme();
const [manifest, data] = await Promise.all([getJSON("fonts.json"), getJSON("compare.json")]);
loadFonts(manifest, data);

const fonts = data?.fonts?.length
  ? data.fonts
  : (manifest?.families || []).map((f) => ({ id: f.id, name: f.family, role: "nk", css: f.family, features: [] }));
const weightsOf = (f) => {
  if (f.role === "reference") return f.webfonts.map((w) => w.weight).sort((a, b) => a - b);
  const m = manifest?.families?.find((x) => x.id === f.id);
  return m ? m.webfonts.map((w) => w.weight).sort((a, b) => a - b) : [400];
};

// Editor colour themes: classic open-source palettes (colour values only) plus NK's own.
const THEMES = {
  "NK 다크": { bg: "#0f100e", fg: "#e7e6df", bar: "#161714", line: "#262724", dim: "#77746b", k: "#b39cf0", s: "#f2a65a", c: "#6d6a62", n: "#53d3bd", f: "#ef7b7b", t: "#7cb8f0" },
  "NK 라이트": { bg: "#fffdf7", fg: "#1a1a17", bar: "#f1eee5", line: "#ddd9cc", dim: "#8f8b80", k: "#6b4fc4", s: "#b5651d", c: "#9a968b", n: "#137a69", f: "#b3413f", t: "#2f6db3" },
  Dracula: { bg: "#282a36", fg: "#f8f8f2", bar: "#21222c", line: "#343746", dim: "#6272a4", k: "#ff79c6", s: "#f1fa8c", c: "#6272a4", n: "#bd93f9", f: "#50fa7b", t: "#8be9fd" },
  Nord: { bg: "#2e3440", fg: "#d8dee9", bar: "#272c36", line: "#3b4252", dim: "#616e88", k: "#81a1c1", s: "#a3be8c", c: "#616e88", n: "#b48ead", f: "#88c0d0", t: "#8fbcbb" },
  "One Dark": { bg: "#282c34", fg: "#abb2bf", bar: "#21252b", line: "#3a3f4b", dim: "#5c6370", k: "#c678dd", s: "#98c379", c: "#5c6370", n: "#d19a66", f: "#61afef", t: "#e5c07b" },
  "Solarized Light": { bg: "#fdf6e3", fg: "#586e75", bar: "#eee8d5", line: "#e4ddc8", dim: "#93a1a1", k: "#859900", s: "#2aa198", c: "#93a1a1", n: "#d33682", f: "#268bd2", t: "#b58900" },
  Gruvbox: { bg: "#282828", fg: "#ebdbb2", bar: "#1d2021", line: "#3c3836", dim: "#928374", k: "#fb4934", s: "#b8bb26", c: "#928374", n: "#d3869b", f: "#fabd2f", t: "#83a598" },
};

const CODE = {
  TypeScript: `// 사용자 목록을 불러와 이름순으로 정렬합니다
type 사용자 = { id: number; 이름: string; 활성: boolean };

export async function 불러오기(url: string): Promise<사용자[]> {
  const res = await fetch(url);
  if (res.status !== 200) throw new Error("요청 실패: " + res.status);
  const 목록 = (await res.json()) as 사용자[];
  return 목록.filter((u) => u.활성 && u.id >= 0x10)
             .sort((a, b) => a.이름.localeCompare(b.이름, "ko"));
}`,
  Python: `# 한글 폭을 고려해 표를 출력합니다
from unicodedata import east_asian_width as eaw

def 칸수(s: str) -> int:
    return sum(2 if eaw(c) in "WF" else 1 for c in s)

def 표(행들: list[list[str]]) -> None:
    폭 = [max(칸수(r[i]) for r in 행들) for i in range(len(행들[0]))]
    for 행 in 행들:
        print(" | ".join(c + " " * (w - 칸수(c)) for c, w in zip(행, 폭)))

표([["이름", "점수"], ["nk-font", "100"], ["한글", "0.92"]])`,
  Rust: `// 터미널 셀 폭: 영문 1칸, 한글 2칸
use unicode_width::UnicodeWidthStr;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let 줄들 = ["fn → 함수", "let x = 0;", "// 주석도 정렬"];
    for 줄 in 줄들.iter() {
        let 폭 = 줄.width();
        println!("{:>2} │ {}", 폭, 줄);
    }
    assert!(줄들.len() != 0 && 1 <= 2);
    Ok(())
}`,
  Go: `package main

import "fmt"

// 상태 코드를 한글 메시지로 바꿉니다
func 메시지(code int) string {
	switch {
	case code >= 500:
		return "서버 오류"
	case code == 404:
		return "찾을 수 없음"
	}
	return "정상"
}

func main() { fmt.Println(메시지(404), "->", 0xFF) }`,
  Shell: `#!/usr/bin/env bash
# 빌드하고 결과를 확인합니다
set -euo pipefail

for 가족 in mono pixel; do
  nkfont build "$가족" && echo "✔ $가족 완료"
done
nkfont check dist/*.ttf --base sources/JetBrainsMono-Regular.ttf || exit 1
[[ -f build/site/compare.json ]] && echo "비교 데이터 준비됨"`,
  Markdown: `# nk-font 설치 안내

1. 압축을 풀고 **NKSans Nerd Font**를 설치합니다.
2. 터미널 설정에서 글꼴을 고릅니다.

> 한글은 두 칸, 영문은 한 칸. 아이콘까지 칸에 맞습니다.

| 이름     | 용도     |
|----------|----------|
| NK Sans  | 터미널   |
| NK Pixel | 게임     |`,
};

const RE = {
  hash: /(#.*$)|("[^"\n]*"|'[^'\n]*')|\b(def|return|for|in|from|import|if|else|then|do|done|set|and|or|not|None|True|False|local|fi)\b|\b(0x[0-9a-fA-F]+|\d+(?:\.\d+)?)\b|\b([A-Za-z_가-힣][\w가-힣]*)(?=\()/gm,
  slash: /(\/\/.*$)|("[^"\n]*"|'[^'\n]*'|`[^`\n]*`)|\b(const|let|type|export|async|await|function|return|if|throw|new|as|fn|use|for|in|mut|match|Ok|Err|Result|Box|dyn|package|import|func|switch|case|string|number|boolean|int|Promise)\b|\b(0x[0-9a-fA-F]+|\d+(?:\.\d+)?)\b|\b([A-Za-z_가-힣][\w가-힣]*)(?=[(!])/gm,
};
function highlight(src, lang) {
  if (lang === "Markdown") {
    return esc(src).replace(/^(#.*)$/gm, '<span class="k">$1</span>').replace(/(\*\*[^*]+\*\*)/g, '<span class="s">$1</span>')
      .replace(/^(&gt;.*)$/gm, '<span class="c">$1</span>').replace(/^(\d+\.)/gm, '<span class="n">$1</span>').replace(/([|])/g, '<span class="t">$1</span>');
  }
  const re = lang === "Python" || lang === "Shell" ? RE.hash : RE.slash;
  let out = "", last = 0;
  for (const m of src.matchAll(re)) {
    out += esc(src.slice(last, m.index));
    const [t, c, s, k, n, f] = m;
    const cls = c ? "c" : s ? "s" : k ? "k" : n ? "n" : f ? "f" : "";
    out += `<span class="${cls}">${esc(t)}</span>`;
    last = m.index + t.length;
  }
  return out + esc(src.slice(last));
}

const st = { font: fonts[0], weight: 400, lang: "TypeScript", theme: "NK 다크", on: new Set() };
try { const t = localStorage.getItem("nk-ed-theme"); if (THEMES[t]) st.theme = t; } catch {}

function applyStyle() {
  const code = $("#tCode"), gut = $("#tGutter");
  const size = +$("#tSize").value, lh = +$("#tLh").value / 100;
  $("#tSizeV").textContent = size; $("#tLhV").textContent = lh.toFixed(2);
  for (const el of [code, gut]) {
    el.style.fontFamily = stack(st.font);
    el.style.fontSize = size + "px";
    el.style.lineHeight = lh;
    el.style.fontWeight = st.weight;
  }
  code.classList.toggle("grid-on", $("#tGrid").checked);
  code.classList.toggle("nk-pixel", st.font.id === "pixel");
  const feats = (st.font.features || []).map((f) => `"${f.tag}" ${st.on.has(f.tag) ? 1 : 0}`);
  if (st.on.has("calt") === false && (st.font.features || []).some((f) => f.tag === "calt")) feats.push('"liga" 0');
  code.style.fontFeatureSettings = feats.length ? feats.join(", ") : "normal";
  const t = THEMES[st.theme], ed = $("#editor");
  for (const [k, v] of Object.entries(t)) ed.style.setProperty(`--ed-${k}`, v);
}

function setCode() {
  const src = CODE[st.lang];
  $("#tCode").innerHTML = highlight(src, st.lang);
  gutter();
}
function gutter() {
  const n = ($("#tCode").innerText.match(/\n/g) || []).length + 1;
  $("#tGutter").textContent = Array.from({ length: n }, (_, i) => i + 1).join("\n");
}

function features() {
  const list = st.font.features || [];
  $("#tFeatN").textContent = list.length ? `${list.length}개` : "";
  $("#tFeatNote").textContent = list.length ? "켠 기능만 코드에 적용됩니다. 합자(calt)는 글꼴 기본값으로 켜져 있습니다." : `${st.font.name}에는 켜고 끌 수 있는 OpenType 기능이 없습니다.`;
  st.on = new Set(list.filter((f) => f.tag === "calt").map((f) => f.tag));
  $("#tFeat").innerHTML = list.map((f) => `<label title="${esc(f.label)}"><input type="checkbox" data-tag="${f.tag}" ${st.on.has(f.tag) ? "checked" : ""}>
    <span class="s" style="font-family:${stack(st.font)};font-feature-settings:'${f.tag}' 1">${esc(f.sample.split(" ").slice(0, 3).join(" "))}</span>
    <span>${esc(f.label)}</span><code>${f.tag}</code></label>`).join("");
}

function pickFont(id) {
  st.font = fonts.find((f) => f.id === id);
  const ws = weightsOf(st.font);
  if (!ws.includes(st.weight)) st.weight = ws[0];
  seg($("#tWeight"), ws.map((w) => [String(w), w >= 700 ? "Bold" : "Regular"]), String(st.weight), (w) => { st.weight = +w; applyStyle(); });
  features();
  applyStyle();
}

seg($("#tFam"), fonts.map((f) => [f.id, f.name]), st.font.id, pickFont);
seg($("#tLang"), Object.keys(CODE).map((k) => [k, k]), st.lang, (v) => { st.lang = v; setCode(); }, "tab");
const themeEl = $("#tTheme");
themeEl.innerHTML = Object.entries(THEMES).map(([name, t]) => `<button type="button" role="radio" aria-checked="${name === st.theme}" data-v="${esc(name)}"><i style="background:linear-gradient(135deg,${t.bg} 50%,${t.k} 50%)"></i>${esc(name)}</button>`).join("");
themeEl.onclick = (e) => {
  const b = e.target.closest("button"); if (!b) return;
  st.theme = b.dataset.v;
  themeEl.querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", x === b));
  try { localStorage.setItem("nk-ed-theme", st.theme); } catch {}
  applyStyle();
};
$("#tFeat").onchange = (e) => {
  const tag = e.target.dataset.tag; if (!tag) return;
  e.target.checked ? st.on.add(tag) : st.on.delete(tag);
  applyStyle();
};
for (const id of ["#tSize", "#tLh", "#tGrid"]) $(id).oninput = applyStyle;
$("#tCode").oninput = gutter;

// Editor keys: Tab indents, Shift+Tab outdents, Enter keeps the indent. Esc releases Tab so
// keyboard users can still leave the editor (Esc, then Tab / Shift+Tab).
const codeEl = $("#tCode");
let released = false;
function offsetOf(node, off) {
  const r = document.createRange();
  r.selectNodeContents(codeEl);
  r.setEnd(node, off);
  return r.toString().length;
}
function getSel() {
  const s = getSelection();
  if (!s.rangeCount || !codeEl.contains(s.anchorNode)) return null;
  const r = s.getRangeAt(0);
  return { start: offsetOf(r.startContainer, r.startOffset), end: offsetOf(r.endContainer, r.endOffset) };
}
function pointAt(pos) {
  const walk = document.createTreeWalker(codeEl, NodeFilter.SHOW_TEXT);
  let last = null;
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    if (pos <= n.length) return [n, pos];
    pos -= n.length; last = n;
  }
  return last ? [last, last.length] : [codeEl, codeEl.childNodes.length];
}
function setSel(start, end) {
  const r = document.createRange();
  r.setStart(...pointAt(start));
  r.setEnd(...pointAt(end));
  const s = getSelection(); s.removeAllRanges(); s.addRange(r);
}
function apply(res) {
  // Simple insertions go through the browser so undo keeps working; block edits re-highlight.
  // Newlines are inserted as text by hand: insertText would add <br>/<div> in a contenteditable.
  if (res.insert != null && !res.insert.includes("\n") && document.execCommand("insertText", false, res.insert)) return;
  if (res.insert != null) {
    const r = getSelection().getRangeAt(0), node = document.createTextNode(res.insert);
    r.deleteContents(); r.insertNode(node);
    codeEl.normalize();
    setSel(res.start, res.end);
    gutter();
    return;
  }
  codeEl.innerHTML = highlight(res.text, st.lang);
  setSel(res.start, res.end);
  gutter();
}
codeEl.addEventListener("focus", () => { released = false; });
codeEl.addEventListener("keydown", (e) => {
  if (e.isComposing || e.keyCode === 229) return; // let the Hangul IME finish its syllable
  if (e.key === "Escape") { released = true; return; }
  if (["Shift", "Control", "Alt", "Meta"].includes(e.key)) return; // Esc, then Shift+Tab
  const wasReleased = released;
  released = false;
  if (e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.key === "Tab" && wasReleased) return; // default: move focus out of the editor
  if (e.key !== "Tab" && e.key !== "Enter") return;
  const sel = getSel(); if (!sel) return;
  e.preventDefault();
  const text = codeEl.textContent, unit = indentUnit(st.lang);
  if (e.key === "Enter") apply(newline(text, sel.start, sel.end));
  else apply((e.shiftKey ? outdent : indent)(text, sel.start, sel.end, unit));
});
// Paste as plain text so the editor never picks up markup from elsewhere.
codeEl.addEventListener("paste", (e) => {
  e.preventDefault();
  document.execCommand("insertText", false, e.clipboardData.getData("text/plain"));
});
if (innerWidth < 640) $("#tSize").value = 13;
pickFont(st.font.id);
setCode();
