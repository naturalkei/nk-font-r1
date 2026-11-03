// nk-font prototype site. No build step: plain ES module, data from fonts.json / glyphs.json.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);

const FAMILY_INFO = {
  mono: { css: "NK Mono", cls: "nk-mono", latin: "JetBrains Mono", hangul: "D2Coding 한글", note: "터미널 대표 가족. 고정폭용으로 그린 한글이 두 칸을 꽉 채우고, 합자는 켜고 끌 수 있습니다." },
  pixel: { css: "NK Pixel", cls: "nk-pixel", latin: "Neo둥근모 Code", hangul: "Neo둥근모 Code", note: "16 px 비트맵 격자의 픽셀 터미널 글꼴. Nerd 아이콘 포함, 게임용 포맷도 준비 중입니다." },
  sans: { css: "NK Sans", cls: "nk-sans", text: true, latin: "IBM Plex Sans", hangul: "Source Han Sans KR (본고딕)", note: "일반 문서·UI·발표 자료용 비례폭 고딕. 기본 줄 높이 φ^5/6 = 1.493.", spec: "한글 Aa 2026", spec2: "회의록, 보고서, 슬라이드에\n어울리는 담백한 고딕." },
  serif: { css: "NK Serif", cls: "nk-serif", text: true, latin: "IBM Plex Serif", hangul: "Source Han Serif KR (본명조)", note: "보고서·논문·인쇄물용 비례폭 명조. NK Sans와 같은 Plex 뼈대라 제목·본문 짝으로 씁니다. 명조 한글은 한 단계 굵게 짝지었습니다. 기본 줄 높이 φ^5/6 = 1.493.", spec: "한글 Aa 1446", spec2: "제1장 연구의 목적과 범위\n본 보고서는 다음과 같이 구성된다." },
  novel: { css: "NK Novel", cls: "nk-novel", text: true, latin: "Crimson Text", hangul: "고운바탕", note: "책·소설·신문 본문용 비례폭 바탕. 기본 줄 높이 φ = 1.618.", spec: "한글 Aa 1987", spec2: "“그래, 다시 시작하자.” 그녀가\n창밖을 보며 말했다." },
  comics: { css: "NK Comics", cls: "nk-comics", text: true, latin: "Bagel Fat One · Gasoek One", hangul: "Bagel Fat One · Gasoek One (+ 본고딕 Heavy 보충)", note: "만화·웹툰 말풍선과 효과음용. 통통 튀는 Regular, 외치는 Black. 기본 줄 높이 √φ = 1.272.", spec: "쾅!! Aa ?!", spec2: "빨리 도망쳐!! WHAT?!\n잠깐만, 같이 가!" },
};
const isText = (id) => !!FAMILY_INFO[id]?.text;

// Terminal cell count, close enough to wcwidth for the characters used on this page.
function cells(ch) {
  const c = ch.codePointAt(0);
  if (c === 0x200b || (c >= 0x300 && c < 0x370)) return 0;
  if ((c >= 0x1100 && c <= 0x115f) || (c >= 0x2e80 && c <= 0xa4cf && c !== 0x303f) || (c >= 0xac00 && c <= 0xd7a3) ||
      (c >= 0xf900 && c <= 0xfaff) || (c >= 0xfe30 && c <= 0xfe4f) || (c >= 0xff00 && c <= 0xff60) || (c >= 0xffe0 && c <= 0xffe6)) return 2;
  return 1;
}
const width = (s) => [...s].reduce((n, ch) => n + cells(ch), 0);
const pad = (s, w) => s + " ".repeat(Math.max(0, w - width(s)));

/* ---------- theme ---------- */
const root = document.documentElement;
try { const t = localStorage.getItem("nk-theme"); if (t) root.dataset.theme = t; } catch {}
$("#themeBtn").onclick = () => {
  root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
  try { localStorage.setItem("nk-theme", root.dataset.theme); } catch {}
};

/* ---------- hero terminal ---------- */
function heroTerminal() {
  const S = (cls, t) => `<span class="${cls}">${esc(t)}</span>`;
  const rows = [["이름", "언어", "상태"], ["nk-font", "Python", "✔ 통과"], ["한글정렬", "Rust", "진행 중"], ["아이콘", " Rust", "✔ 통과"]];
  const w = [10, 10, 9];
  const line = (l, m, r) => l + w.map((n) => "─".repeat(n + 2)).join(m) + r;
  const table = [S("c-dim", line("┌", "┬", "┐"))];
  rows.forEach((row, i) => {
    table.push(S("c-dim", "│") + row.map((c, j) => " " + (i === 0 ? S("c-warm", pad(c, w[j])) : esc(pad(c, w[j]))) + " " + S("c-dim", "│")).join(""));
    if (i === 0) table.push(S("c-dim", line("├", "┼", "┤")));
  });
  table.push(S("c-dim", line("└", "┴", "┘")));
  const prompt = S("c-pl1", "  ") + S("c-pl1", "  ~/문서/프로젝트 ") + S("c-pl1e", "") +
                 S("c-pl2", "  main ✔ ") + S("c-pl2e", "") + "  " + S("c-dim", "took 2s   14:02");
  const ls = [
    ["drwxr-xr-x", " 5", "160", "디자인/", "c-blue", ""],
    ["-rw-r--r--", " 1", "2.4K", "README.md", "", ""],
    ["-rw-r--r--", " 1", "812", "설정.toml", "", ""],
    ["-rw-r--r--", " 1", "31K", "보고서_최종.pdf", "c-rose", ""],
    ["-rwxr-xr-x", " 1", "4.1K", "배포.sh", "c-acc", ""],
  ].map(([p, n, sz, name, cls, ic]) => `${S("c-dim", p)} ${n} nk  staff ${sz.padStart(5)} 11월  2 14:01 ${S(cls || "", ic + " " + name)}`);
  return [prompt, S("c-acc", "❯ ") + "ls -l", ...ls, "", S("c-acc", "❯ ") + "cat 진행상황.txt", ...table, S("c-acc", "❯ ") + '<span class="cur"> </span>'].join("\n");
}
$("#heroTerm").innerHTML = heroTerminal();
$("#heroGrid").onchange = (e) => $("#heroTerm").classList.toggle("grid-on", e.target.checked);

/* ---------- fonts from manifest ---------- */
let manifest = { families: [] };
async function loadManifest() {
  try { manifest = await (await fetch("fonts.json")).json(); } catch { return; }
  const css = [];
  for (const f of manifest.families) {
    const name = FAMILY_INFO[f.id]?.css || f.family;
    for (const w of f.webfonts) css.push(`@font-face{font-family:"${name}";src:url(${w.url}) format("woff2");font-weight:${w.weight};font-style:normal;font-display:swap}`);
  }
  const st = document.createElement("style"); st.textContent = css.join("\n"); document.head.appendChild(st);
  $("#buildInfo").textContent = `v${manifest.families[0]?.version || "0.1.0"} · ${manifest.built} · ${manifest.commit}`;
}

/* ---------- playground ---------- */
const play = { fam: "mono", weight: 400 };
function seg(el, items, current, onPick, role = "radio") {
  el.innerHTML = items.map(([v, label]) => `<button role="${role}" aria-${role === "radio" ? "checked" : "selected"}="${v === current}" data-v="${v}">${label}</button>`).join("");
  el.onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    el.querySelectorAll("button").forEach((x) => x.setAttribute(role === "radio" ? "aria-checked" : "aria-selected", x === b));
    onPick(b.dataset.v);
  };
}
function applyPlay() {
  const a = $("#playArea"), info = FAMILY_INFO[play.fam];
  a.style.fontFamily = `"${info.css}", var(--term)`;
  a.style.fontWeight = play.weight;
  a.classList.toggle("nk-pixel", play.fam === "pixel");
  let size = +$("#sizeR").value;
  if (play.fam === "pixel") size = Math.max(16, Math.round(size / 16) * 16); // integer pixel scale
  a.style.fontSize = size + "px"; $("#sizeV").textContent = size + "px";
  a.classList.toggle("grid-on", $("#playGrid").checked && !isText(play.fam));  // no cells in reading faces
  a.style.lineHeight = { novel: "1.618", comics: "1.272", sans: "1.493" }[play.fam] || "";
  a.style.fontFeatureSettings = $("#playLiga").checked ? "normal" : '"calt" 0, "liga" 0';
}
function initPlay() {
  seg($("#famSeg"), Object.entries(FAMILY_INFO).map(([id, i]) => [id, i.css]), play.fam, (v) => {
    play.fam = v;
    const fam = manifest.families.find((f) => f.id === v);
    const ws = fam ? fam.webfonts.map((w) => [String(w.weight), w.style]) : [["400", "Regular"]];
    if (!ws.find(([w]) => +w === play.weight)) play.weight = +ws[0][0];
    seg($("#wSeg"), ws, String(play.weight), (w) => { play.weight = +w; applyPlay(); });
    applyPlay();
  });
  seg($("#wSeg"), [["400", "Regular"], ["700", "Bold"]], "400", (w) => { play.weight = +w; applyPlay(); });
  if (innerWidth < 640) $("#sizeR").value = 24;
  for (const id of ["#sizeR", "#playGrid", "#playLiga"]) $(id).oninput = applyPlay;
  applyPlay();
}

/* ---------- stats & families & downloads ---------- */
const fmtMB = (b) => (b / 1048576).toFixed(1) + " MB";
function renderData() {
  const stats = [
    [manifest.glyph_count?.toLocaleString() ?? "24,000+", "NK Mono Nerd Font 글자 수"],
    [manifest.icon_count?.toLocaleString() ?? "10,000+", "Nerd Fonts 아이콘"],
    ["11,172", "현대 한글 음절 전부"],
    ["0", "폭 검사 오류 (빌드마다)"],
  ];
  $("#stats").innerHTML = stats.map(([b, s]) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`).join("");

  const fams = manifest.families.length ? manifest.families : Object.keys(FAMILY_INFO).map((id) => ({ id, family: FAMILY_INFO[id].css, webfonts: [], version: "0.1.0" }));
  const famCard = (f) => {
    const i = FAMILY_INFO[f.id];
    if (!i) return "";
    const glyphs = f.webfonts[0]?.glyphs?.toLocaleString() ?? "–";
    return `<article class="fam"><h3 class="${i.cls}">${f.family}<span class="kind">${i.text ? "비례폭" : "고정폭"}</span></h3>
      <div class="spec ${i.cls}">${i.spec || "한글 Aa 0O1lI"}</div>
      <div class="spec2 ${i.cls}">${i.spec2 || "fn 합계(값: i32) -> i32 { 값 * 2 }\n~/문서   main ✔"}</div>
      <p style="margin:0;color:var(--mute);font-size:14px">${i.note}</p>
      <dl><dt>영문</dt><dd>${i.latin}</dd><dt>한글</dt><dd>${i.hangul}</dd><dt>굵기</dt><dd>${f.webfonts.map((w) => w.style).join(", ") || "–"}</dd><dt>글리프</dt><dd>${glyphs}</dd></dl></article>`;
  };
  $("#famGrid").innerHTML = fams.filter((f) => !isText(f.id)).map(famCard).join("");
  $("#famGridText").innerHTML = fams.filter((f) => isText(f.id)).map(famCard).join("");

  $("#dlGrid").innerHTML = fams.map((f) => {
    const i = FAMILY_INFO[f.id], d = f.download;
    if (!i) return "";
    return `<article class="dl"><h3 class="${i.cls}">${f.family}</h3>
      <p>v${f.version} · ${d ? `${d.files}개 파일 · ${fmtMB(d.bytes)}` : "빌드 대기"}</p>
      <p>${i.text ? "읽기용 비례폭 TTF (Nerd 아이콘 없음)" : d?.nerd ? "Nerd Font · Nerd Font Mono · 마스터" : "마스터"}</p>
      ${d ? `<a class="btn" href="${d.url}" download>ZIP 내려받기</a>` : ""}</article>`;
  }).join("");
}

/* ---------- code samples ---------- */
const CODE = {
  Python: `# 한글 파일명을 열 너비에 맞춰 출력합니다
from wcwidth import wcswidth

def 맞춤(문자열: str, 너비: int) -> str:
    return 문자열 + " " * (너비 - wcswidth(문자열))

for 이름, 크기 in [("보고서.pdf", 31), ("README.md", 2)]:
    print(f"{맞춤(이름, 14)}│{크기:>4} KB")  # 열이 맞아야 합니다`,
  Rust: `// 셀 너비: 영문 1칸, 한글 2칸
use unicode_width::UnicodeWidthStr;

fn main() {
    let 목록 = ["가나다", "abc", "한글ab"];
    for 항목 in 목록 {
        println!("{:<8}│{}", 항목, 항목.width()); // 6, 3, 6
    }
}`,
  TypeScript: `// 터미널 프롬프트 조각
type 세그먼트 = { 아이콘: string; 글: string };

const 프롬프트: 세그먼트[] = [
  { 아이콘: "", 글: "~/문서/프로젝트" },
  { 아이콘: "", 글: "main" },
];
console.log(프롬프트.map((s) => \`\${s.아이콘} \${s.글}\`).join("  "));`,
  Shell: `#!/usr/bin/env bash
# 설치 확인: 폰트 목록에 NKMono가 보여야 합니다
fc-list | grep -i "NKMono" || echo "설치되지 않았습니다"

for 파일 in ~/문서/*.md; do
  printf "%-20s %s\\n" "$(basename "$파일")" "$(wc -l < "$파일")줄"
done`,
};
function highlight(src, lang) {
  const re = lang === "Python" || lang === "Shell"
    ? /(#[^\n]*)|("[^"\n]*"|'[^'\n]*')|\b(def|return|for|in|from|import|do|done|echo|printf|print)\b|\b(\d+)\b/g
    : /(\/\/[^\n]*)|("[^"\n]*"|`[^`]*`)|\b(fn|let|use|for|in|main|type|const|return)\b|\b(\d+)\b/g;
  let out = "", last = 0;
  for (const m of src.matchAll(re)) {
    out += esc(src.slice(last, m.index));
    const [t, c, s, k, n] = m;
    out += c ? `<i class="c">${esc(t)}</i>` : s ? `<span class="s">${esc(t)}</span>` : k ? `<span class="k">${t}</span>` : n ? `<span class="n">${t}</span>` : esc(t);
    last = m.index + t.length;
  }
  return out + esc(src.slice(last));
}
function initCode() {
  const show = (lang) => ($("#codeBox").innerHTML = highlight(CODE[lang], lang));
  seg($("#codeTabs"), Object.keys(CODE).map((k) => [k, k]), "Python", show, "tab");
  show("Python");
}

/* ---------- glyph explorer ---------- */
const GX_SETS = {
  hangul: ["한글 음절", (c) => c >= 0xac00 && c <= 0xd7a3],
  jamo: ["자모·전각", (c) => (c >= 0x3000 && c <= 0x318f) || (c >= 0xff00 && c <= 0xffef)],
  latin: ["영문·기호", (c) => c >= 0x21 && c < 0x2500],
  box: ["박스·블록", (c) => c >= 0x2500 && c <= 0x25ff],
  icons: ["Nerd 아이콘", (c) => (c >= 0xe000 && c <= 0xf8ff) || c >= 0xf0000],
};
const gx = { data: null, set: "hangul", list: [], shown: 0, cellOf: new Map() };
function gxInfo(cp) {
  const ch = String.fromCodePoint(cp), c = gx.cellOf.get(cp) ?? cells(ch);
  $("#gxBig").textContent = ch;
  $("#gxBig").style.backgroundSize = "";
  const name = gx.data?.icons?.[cp];
  $("#gxDl").innerHTML = `<dt>코드</dt><dd>U+${cp.toString(16).toUpperCase().padStart(4, "0")}</dd>
    <dt>터미널 폭</dt><dd>${c}칸 (advance ${c * (gx.data?.half || 600)})</dd>${name ? `<dt>아이콘</dt><dd>nf-${esc(name)}</dd>` : ""}
    <dt>HTML</dt><dd>&amp;#x${cp.toString(16).toUpperCase()};</dd>`;
  document.querySelectorAll("#gxGrid button").forEach((b) => b.setAttribute("aria-pressed", +b.dataset.cp === cp));
}
function gxRender(more = false) {
  const grid = $("#gxGrid");
  if (!more) { grid.innerHTML = ""; gx.shown = 0; }
  const next = gx.list.slice(gx.shown, gx.shown + 320);
  grid.insertAdjacentHTML("beforeend", next.map((cp) => `<button data-cp="${cp}" title="U+${cp.toString(16).toUpperCase()}">${String.fromCodePoint(cp)}</button>`).join(""));
  gx.shown += next.length;
  $("#gxMore").hidden = gx.shown >= gx.list.length;
}
function gxSelect(set) {
  gx.set = set;
  const test = GX_SETS[set][1];
  gx.list = [];
  if (gx.data) for (const [a, b] of gx.data.runs) for (let c = a; c <= b; c++) if (test(c)) gx.list.push(c);
  else for (let c = 0xac00; c < 0xac00 + 640; c++) if (test(c)) gx.list.push(c);
  if (!gx.data && set === "hangul") for (let c = 0xac00; c < 0xac00 + 640; c++) gx.list.push(c);
  gxRender();
}
async function initGlyphs() {
  seg($("#gxSeg"), Object.entries(GX_SETS).map(([k, [l]]) => [k, l]), "hangul", gxSelect, "tab");
  try {
    gx.data = await (await fetch("glyphs.json")).json();
    for (const [a, b, c] of gx.data.runs) for (let cp = a; cp <= b; cp++) gx.cellOf.set(cp, c);
  } catch {}
  gxSelect("hangul"); gxInfo(0xd55c);
  $("#gxGrid").onclick = (e) => { const b = e.target.closest("button"); if (b) gxInfo(+b.dataset.cp); };
  $("#gxMore").onclick = () => gxRender(true);
  $("#gxSearch").onchange = (e) => {
    const v = e.target.value.trim(); if (!v) return;
    const cp = /^u\+?[0-9a-f]{4,6}$/i.test(v) ? parseInt(v.replace(/^u\+?/i, ""), 16) : v.codePointAt(0);
    gxInfo(cp);
  };
}

/* ---------- pixel dialog typing ---------- */
function initPixel() {
  const lines = ["어서 오게, 모험가여! 오늘은 HP 포션이 3개에 120G라네.", "던전 3층에서 잃어버린 열쇠를 찾아 주겠나?", "한글도 16픽셀 격자에 딱 맞지. 자, 골라 보게."];
  const el = $("#pixelLine");
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  let li = 0, ci = 0;
  setInterval(() => {
    const t = lines[li];
    if (ci <= t.length) { el.textContent = t.slice(0, ci++); }
    else if (ci++ > t.length + 40) { li = (li + 1) % lines.length; ci = 0; }
  }, 55);
}

/* ---------- install snippets ---------- */
const OS = {
  macOS: `# 압축을 푼 폴더에서
cp NKMono-0.1.0/NKMonoNerdFont*.ttf ~/Library/Fonts/
# 또는 서체 관리자(Font Book)로 .ttf 파일을 드래그`,
  Linux: `mkdir -p ~/.local/share/fonts/nk-font
cp NKMono-0.1.0/NKMonoNerdFont*.ttf ~/.local/share/fonts/nk-font/
fc-cache -f && fc-list | grep NKMono`,
  Windows: `# PowerShell: .ttf를 선택하고 마우스 오른쪽 → "모든 사용자용으로 설치"
# 또는
Get-ChildItem .\\NKMono-0.1.0\\NKMonoNerdFont*.ttf | ForEach-Object {
  Copy-Item $_ "$env:LOCALAPPDATA\\Microsoft\\Windows\\Fonts\\" }`,
};
const APPS = {
  iTerm2: `Settings → Profiles → Text → Font: "NKMono Nerd Font" 14
☐ Use built-in Powerline glyphs   (끄면 폰트의 이음새를 그대로 씁니다)
Settings → Profiles → Text → Unicode: Ambiguous characters are double-width 끄기`,
  WezTerm: `-- ~/.wezterm.lua
local wezterm = require 'wezterm'
return {
  font = wezterm.font 'NKMono Nerd Font',
  font_size = 14.0,
  treat_east_asian_ambiguous_width_as_wide = false,
}`,
  kitty: `# ~/.config/kitty/kitty.conf
font_family      NKMono Nerd Font
bold_font        auto
font_size        14.0`,
  Alacritty: `# ~/.config/alacritty/alacritty.toml
[font]
normal = { family = "NKMono Nerd Font", style = "Regular" }
size = 14.0`,
  "VS Code": `// settings.json
"editor.fontFamily": "'NKMono Nerd Font', monospace",
"terminal.integrated.fontFamily": "'NKMono Nerd Font Mono'",
"editor.fontLigatures": true`,
  "Windows Terminal": `// settings.json → profiles.defaults
"font": { "face": "NKMono Nerd Font", "size": 13 }`,
  Starship: `# ~/.config/starship.toml — Nerd Font 기호 프리셋
# starship preset nerd-font-symbols -o ~/.config/starship.toml
format = "$os$directory$git_branch$git_status$character"`,
};
function initInstall() {
  const showOS = (k) => ($("#osBox").textContent = OS[k]);
  const showApp = (k) => ($("#appBox").textContent = APPS[k]);
  const guess = /Win/.test(navigator.platform) ? "Windows" : /Linux/.test(navigator.platform) ? "Linux" : "macOS";
  seg($("#osTabs"), Object.keys(OS).map((k) => [k, k]), guess, showOS, "tab"); showOS(guess);
  seg($("#appTabs"), Object.keys(APPS).map((k) => [k, k]), "iTerm2", showApp, "tab"); showApp("iTerm2");
  document.querySelectorAll(".copy").forEach((b) => (b.onclick = async () => {
    try { await navigator.clipboard.writeText($("#" + b.dataset.target).textContent); b.textContent = "복사됨"; }
    catch { b.textContent = "복사 실패"; }
    setTimeout(() => (b.textContent = "복사"), 1400);
  }));
}

/* ---------- boot ---------- */
initCode(); initInstall(); initPixel();
await loadManifest();
renderData(); initPlay(); initGlyphs();
