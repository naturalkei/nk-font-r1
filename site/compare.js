// Benchmark page: renders compare.json (measured by `nkfont site`) next to live web fonts.
import { $, esc, initTheme, getJSON, loadFonts, stack, seg, cells, pad } from "./common.js";

initTheme();
const [manifest, data] = await Promise.all([getJSON("fonts.json"), getJSON("compare.json")]);
if (!data) {
  $("#main").insertAdjacentHTML("afterbegin", '<p class="cmp-empty">compare.json이 없습니다. <code>nkfont site</code>로 빌드한 사이트에서 열어 주세요.</p>');
  throw new Error("compare.json missing");
}
loadFonts(manifest, data);

const NK_NAMES = { sans: "NK Sans", serif: "NK Serif", pixel: "NK Pixel" };
const nkFonts = data.fonts.filter((f) => f.role === "nk");
const refs = data.fonts.filter((f) => f.role === "reference");
let fam = (nkFonts.find((f) => f.id === "sans") || nkFonts[0]).id;
const lineup = () => [nkFonts.find((f) => f.id === fam), ...refs];
const fmt = (v, d = 0) => (v == null ? "–" : Number(v).toLocaleString("ko-KR", { maximumFractionDigits: d, minimumFractionDigits: d }));
const COLORS = ["var(--acc)", "var(--warm)", "var(--rose)", "var(--violet)"];

/* ---------- legend ---------- */
function legend() {
  $("#legend").innerHTML = lineup().map((f, i) => `<span class="chip ${i ? "" : "chip-nk"}" style="font-family:${stack(f)}">${esc(f.name)}${f.version ? ` <small>${esc(f.version)}</small>` : ""}</span>`).join("");
}

/* ---------- verdict cards ---------- */
// [title, value(font), higher-is-better, format, note(font)]
const VERDICT = [
  ["터미널 폭 불일치", (f) => f.grid.mismatches, false, (v) => fmt(v), "글자 폭 ≠ 터미널 칸 수(wcwidth). 0이어야 커서와 글자가 어긋나지 않습니다.",
    (f) => (f.grid.ambiguous_wide ? `애매한 폭 ${fmt(f.grid.ambiguous_wide)}자를 두 칸으로 그림: ${esc(f.grid.ambiguous_examples.slice(0, 10))}` : "")],
  ["현대 한글 음절", (f) => f.coverage.hangul_syllables, true, (v) => fmt(v), "11,172자 전부 있어야 시스템 글꼴로 대체되지 않습니다.", (f) => (f.coverage.hangul_syllables ? "" : "한글 없음 → 시스템 글꼴로 대체")],
  ["Nerd Fonts 아이콘", (f) => f.coverage.icons, true, (v) => fmt(v), "Powerline·Devicons·Font Awesome 등 사설 영역(PUA) 글리프 수.", () => ""],
  ["OpenType 기능", (f) => f.features.length, true, (v) => fmt(v), "합자, 빗금 0, 문자 변형 등 켜고 끌 수 있는 기능 수.", (f) => (f.features.length ? "" : "기능 없음")],
  ["줄 사이 틈", (f) => f.metrics.line_gap, false, (v) => fmt(v), "lineGap이 0이어야 Powerline 화살표와 박스 문자가 위아래로 이어집니다.", (f) => `줄 높이 ${fmt(f.metrics.line_height, 2)}em`],
];

function verdict() {
  const fonts = lineup();
  $("#verdictGrid").innerHTML = VERDICT.map(([title, get, higher, f, note, sub]) => {
    const vals = fonts.map(get);
    const best = higher ? Math.max(...vals) : Math.min(...vals);
    const max = Math.max(...vals, 1);
    const rows = fonts.map((font, i) => {
      const v = vals[i];
      const len = higher ? v / max : 1 - v / max;
      const win = v === best;
      return `<div class="vrow ${i ? "" : "is-nk"} ${win ? "win" : ""}">
        <span class="vname">${esc(font.name)}</span>
        <span class="vbar"><i style="width:${Math.max(2, len * 100).toFixed(1)}%"></i></span>
        <b class="vval">${f(v)}${win ? ' <span class="crown" aria-label="최고">★</span>' : ""}</b>
        ${sub(font) ? `<span class="vsub">${sub(font)}</span>` : ""}
      </div>`;
    }).join("");
    return `<article class="vcard"><h3>${title}</h3><p>${note}</p>${rows}</article>`;
  }).join("");
}

/* ---------- terminal panes ---------- */
// Lines are lists of [text, class] segments; the Powerline prompt uses U+E0B0 separators.
function terminalText() {
  const rows = [["파일", "상태", "줄"], ["main.rs", "① 통과", "128"], ["설정.toml", "② 경고 …", "42"], ["한글정렬.py", "③ 실패 → 재시도", "7"]];
  const w = [12, 18, 4];
  const line = (l, m, r) => l + w.map((n) => "─".repeat(n + 2)).join(m) + r;
  const out = [line("┌", "┬", "┐")];
  rows.forEach((row, i) => {
    out.push("│" + row.map((c, j) => " " + pad(c, w[j]) + " │").join(""));
    if (i === 0) out.push(line("├", "┼", "┤"));
  });
  out.push(line("└", "┴", "┘"));
  const prompt = [[" ~/문서/nk-font ", "pl1"], ["", "pl1e"], [" main ✔ ", "pl2"], ["", "pl2e"]];
  return [prompt, [["❯ cargo test --release · 3개", ""]], ...out.map((t) => [[t, ""]]), [["❯ echo \"합계: 3건 · 소요 2.1초\"", ""]]];
}

// Terminals give every character a fixed box of wcwidth cells, whatever the glyph's own width.
// Each character gets such a box here; canvas measures the glyph actually drawn (including
// system fallback) so overflowing and fallback glyphs can be flagged per character.
function terminal() {
  const lines = terminalText();
  $("#termCmp").innerHTML = lineup().map((f, i) => `
    <figure class="tpane ${i ? "" : "is-nk"}" data-css="${esc(f.css)}">
      <figcaption><b>${esc(f.name)}</b><span class="tstat">측정 중…</span></figcaption>
      <pre class="tbody grid-on" style="font-family:${stack(f)}">${lines.map((segs) => segs.map(([t, cls]) => [...t].map((ch) => `<span class="tc ${cls}" style="width:${cells(ch)}ch">${esc(ch)}</span>`).join("")).join("")).join("\n")}</pre>
      <p class="tkey"><span class="k-over">칸을 넘침</span><span class="k-fb">글꼴에 없음(대체)</span></p>
    </figure>`).join("");
  document.fonts.ready.then(measureTerminal);
  setTimeout(measureTerminal, 1500);
}

const ctx = document.createElement("canvas").getContext("2d");
function measureTerminal() {
  for (const pane of document.querySelectorAll(".tpane")) {
    const pre = pane.querySelector(".tbody");
    const px = parseFloat(getComputedStyle(pre).fontSize);
    ctx.font = `${px}px '${pane.dataset.css}', monospace`;
    const cell = ctx.measureText("0").width;
    // compare.json lists which demo characters the font really has; others are fallback glyphs.
    const has = data.fonts.find((f) => f.css === pane.dataset.css)?.has ?? "";
    const missing = (ch) => ch.codePointAt(0) > 0x7e && !has.includes(ch);
    let over = 0, fb = 0;
    const seen = new Set();
    pane.querySelectorAll(".tc").forEach((c) => {
      const ch = c.textContent;
      if (ch === " ") return;
      const want = cells(ch) * cell, got = ctx.measureText(ch).width;
      const isFb = missing(ch);
      const isOver = !isFb && got > want + cell * 0.25;
      c.classList.toggle("over", isOver);
      c.classList.toggle("fb", isFb);
      if ((isOver || isFb) && !seen.has(ch)) { seen.add(ch); isOver ? over++ : fb++; }
    });
    const st = pane.querySelector(".tstat");
    st.textContent = over + fb ? `✗ ${[over && `넘침 ${over}종`, fb && `대체 ${fb}종`].filter(Boolean).join(" · ")}` : "✓ 모든 글자가 제 칸에";
    st.className = "tstat " + (over ? "bad" : fb ? "warn" : "ok");
  }
}

/* ---------- overlay specimens ---------- */
function overlaySVG(font, spec) {
  const upm = font.metrics.upm;
  const adv = Math.max(...spec.glyphs.map((g) => g.adv), upm * 0.6);
  const top = upm * 1.0, h = upm * 1.3;
  const paths = spec.glyphs.map((g, i) => `<path d="${g.d}" transform="translate(${(adv - g.adv) / 2} 0)" fill="${COLORS[i]}" fill-opacity=".42" stroke="${COLORS[i]}" stroke-width="${upm / 140}"/>`).join("");
  return `<svg viewBox="0 ${-top} ${adv} ${h}" role="img" aria-label="${esc(font.name)} 겹친 글자"><line x1="0" x2="${adv}" y1="0" y2="0" class="base"/>${paths}</svg>`;
}

function specimens() {
  const fonts = lineup();
  const head = `<div class="srow shead"><span></span>${fonts.map((f, i) => `<span class="${i ? "" : "is-nk"}">${esc(f.name)}</span>`).join("")}</div>`;
  $("#specTable").innerHTML = head + data.groups.map((g) => {
    const best = Math.max(...fonts.map((f) => f.specimens[g.id].distinct ?? -1));
    const cellsHtml = fonts.map((f, i) => {
      const s = f.specimens[g.id];
      const score = s.distinct;
      const body = s.missing.length
        ? `<div class="smiss">${s.glyphs.length ? overlaySVG(f, s) : ""}<p>${s.missing.map(esc).join(" ")} 글리프 없음<br><small>시스템 글꼴로 대체됩니다</small></p></div>`
        : overlaySVG(f, s);
      return `<div class="scell ${i ? "" : "is-nk"}">${body}
        <div class="sscore ${score != null && score === best ? "win" : ""}"><span>변별도</span><i><b style="width:${((score ?? 0) * 100).toFixed(0)}%"></b></i><em>${score == null ? "–" : score.toFixed(2)}</em></div></div>`;
    }).join("");
    const key = g.chars.map((c, i) => `<span style="color:${COLORS[i]}">${esc(c)}</span>`).join(" ");
    return `<div class="srow"><div class="slabel"><b class="skey nk-sans">${key}</b><span>${esc(g.note)}</span></div>${cellsHtml}</div>`;
  }).join("");
}

/* ---------- Latin / Hangul balance ---------- */
function balanceSVG(f) {
  const m = f.metrics, G = f.guides, upm = m.upm, k = upm / 1000;
  const glyphs = [G.H, G.g, G.han].filter(Boolean);
  let x = 0;
  const parts = glyphs.map((g) => { const p = `<path d="${g.d}" transform="translate(${x} 0)"/>`; x += g.adv; return p; }).join("");
  const W = Math.max(x, 1), top = upm * 1.0;
  const guide = (y, cls, label) => (y == null ? "" : `<line x1="0" x2="${W}" y1="${-y * k}" y2="${-y * k}" class="${cls}"/><text x="${W}" y="${-y * k - 12 * k}" class="gl">${label}</text>`);
  const hb = m.hangul_top != null ? `<rect x="${x - G.han.adv}" width="${G.han.adv}" y="${-m.hangul_top * k}" height="${(m.hangul_top - m.hangul_bottom) * k}" class="hbox"/>` : "";
  return `<svg viewBox="0 ${-top} ${W} ${upm * 1.35}" role="img" aria-label="${esc(f.name)} 한글 영문 비례">${hb}
    ${guide(0, "g0", "기준선")}${guide(m.x_height, "g1", "x")}${guide(m.cap_height, "g2", "H")}<g class="ink">${parts}</g></svg>`;
}

function rangeBar(v, lo, hi, min, max) {
  if (v == null) return '<span class="rb rb-na">한글 없음</span>';
  const pos = (x) => Math.min(100, Math.max(0, ((x - min) / (max - min)) * 100));
  const ok = v >= lo && v <= hi;
  return `<span class="rb"><i class="rb-ok" style="left:${pos(lo)}%;width:${pos(hi) - pos(lo)}%"></i><b class="${ok ? "ok" : "bad"}" style="left:${pos(v)}%"></b></span><em class="${ok ? "ok" : "bad"}">${v.toFixed(2)}</em>`;
}

function balance() {
  $("#balanceGrid").innerHTML = lineup().map((f, i) => {
    const m = f.metrics;
    return `<article class="bcard ${i ? "" : "is-nk"}"><h3>${esc(f.name)}</h3>${balanceSVG(f)}
      <dl>
        <dt>획 굵기 한글 ㅣ / 영문 H</dt><dd>${rangeBar(m.stem_ratio, 0.9, 1.1, 0.6, 1.4)}</dd>
        <dt>회색도 한글 / 영문</dt><dd>${rangeBar(m.density_ratio, 0.85, 1.25, 0.5, 1.5)}</dd>
        <dt>한글 높이 / 대문자</dt><dd>${rangeBar(m.hangul_height_ratio, 1.1, 1.3, 0.9, 1.5)}</dd>
        <dt>한글 중심 − 대문자 중심</dt><dd><em>${m.hangul_center_offset == null ? "–" : `${m.hangul_center_offset > 0 ? "+" : ""}${fmt(m.hangul_center_offset)}`}</em> 단위</dd>
      </dl></article>`;
  }).join("");
}

/* ---------- OpenType features ---------- */
function features() {
  const nk = lineup()[0];
  $("#featCount").innerHTML = lineup().map((f) => `<span><b>${esc(f.name)}</b> ${f.features.length}개</span>`).join(" · ");
  $("#otGrid").innerHTML = nk.features.length ? nk.features.map((ft) => {
    const label = esc(ft.label) + (ft.label.startsWith("문자 변형") || ft.label.startsWith("스타일 세트") ? ` <span class="ot-chars">${esc([...ft.chars].slice(0, 6).join(""))}</span>` : "");
    return `<div class="ot" data-tag="${ft.tag}">
      <span class="ot-head"><span>${label}</span><code>${ft.tag}</code></span>
      <span class="ot-pair" style="font-family:${stack(nk)}">
        <span class="ot-off" style="font-feature-settings:'${ft.tag}' 0">${esc(ft.sample)}</span>
        <span class="ot-on" style="font-feature-settings:'${ft.tag}' 1">${esc(ft.sample)}</span>
      </span><span class="ot-cap"><span>끔</span><span>켬</span></span></div>`;
  }).join("") : '<p class="note">이 가족에는 켜고 끌 기능이 없습니다.</p>';
}

/* ---------- all numbers ---------- */
// [label, get, better: "hi" | "lo" | "near1" | null, digits]
const ROWS = [
  ["터미널 폭 불일치", (f) => f.grid.mismatches, "lo", 0],
  ["애매한 폭을 두 칸으로", (f) => f.grid.ambiguous_wide, "lo", 0],
  ["코드포인트", (f) => f.coverage.codepoints, null, 0],
  ["현대 한글 음절", (f) => f.coverage.hangul_syllables, "hi", 0],
  ["한글 자모(호환)", (f) => f.coverage.hangul_jamo, "hi", 0],
  ["Nerd 아이콘(PUA)", (f) => f.coverage.icons, "hi", 0],
  ["한국어 기호(①※★→ 등 40자)", (f) => f.coverage.kr_symbols, "hi", 0],
  ["OpenType 기능", (f) => f.features.length, "hi", 0],
  ["반각 폭", (f) => f.metrics.half, null, 0],
  ["한글 칸 수", (f) => f.metrics.hangul_cells, null, 2],
  ["어센더 / 디센더", (f) => `${fmt(f.metrics.ascent)} / ${fmt(f.metrics.descent)}`, null],
  ["lineGap", (f) => f.metrics.line_gap, "lo", 0],
  ["x높이", (f) => f.metrics.x_height, null, 0],
  ["대문자 높이", (f) => f.metrics.cap_height, null, 0],
  ["x높이 / 대문자", (f) => f.metrics.x_ratio, null, 3],
  ["영문 기둥 굵기(H)", (f) => f.metrics.latin_stem, null, 0],
  ["한글 기둥 굵기(ㅣ)", (f) => f.metrics.hangul_stem, null, 0],
  ["굵기 비 한글/영문", (f) => f.metrics.stem_ratio, "near1", 3],
  ["회색도 영문", (f) => f.metrics.density_latin, null, 3],
  ["회색도 한글", (f) => f.metrics.density_hangul, null, 3],
  ["회색도 비 한글/영문", (f) => f.metrics.density_ratio, "near1", 3],
  ["한글 잉크 폭 / 칸", (f) => f.metrics.hangul_width_ratio, null, 3],
  ...data.groups.map((g) => [`변별도 ${g.title}`, (f) => f.specimens[g.id].distinct, "hi", 2]),
];

function numbers() {
  const fonts = lineup();
  const head = `<thead><tr><th></th>${fonts.map((f, i) => `<th class="${i ? "" : "is-nk"}">${esc(f.name)}</th>`).join("")}</tr></thead>`;
  const body = ROWS.map(([label, get, better, d]) => {
    const vals = fonts.map(get);
    const nums = vals.filter((v) => typeof v === "number");
    let best = null;
    if (better && nums.length > 1) {
      const score = (v) => (better === "hi" ? v : better === "lo" ? -v : -Math.abs(v - 1));
      best = nums.reduce((a, b) => (score(b) > score(a) ? b : a));
    }
    return `<tr><th>${esc(label)}</th>${vals.map((v, i) => `<td class="${i ? "" : "is-nk"} ${v === best ? "best" : ""}">${typeof v === "number" ? fmt(v, d) : v ?? "–"}</td>`).join("")}</tr>`;
  }).join("");
  $("#numTable").innerHTML = head + `<tbody>${body}</tbody>`;
}

/* ---------- to-do and references ---------- */
function todo() {
  const nk = lineup()[0];
  $("#todoList").innerHTML = (nk.todo || []).length
    ? nk.todo.map((t) => `<li>${esc(t)}</li>`).join("")
    : "<li>측정한 항목에서는 부족한 점이 없습니다.</li>";
}
function refInfo() {
  $("#refInfo").innerHTML = refs.map((r) => `<p><b>${esc(r.name)} ${esc(r.version)}</b> · ${esc(r.license)} · <a href="${esc(r.homepage)}">${esc(r.homepage.replace(/^https?:\/\//, ""))}</a><br><small>${esc(r.copyright || "")}</small> · <a href="fonts/ref/LICENSE-${r.id}.txt">라이선스</a></p>`).join("");
}

function render() { legend(); verdict(); terminal(); specimens(); balance(); features(); numbers(); todo(); }
seg($("#famSeg"), nkFonts.map((f) => [f.id, NK_NAMES[f.id] || f.name]), fam, (v) => { fam = v; render(); });
refInfo();
render();
