// Design notes page: draws design.json (measured by `nkfont site` from the real outlines) as an
// ink notebook page or as a font editor's outline view. Coordinates are font units (UPM 1000),
// y up in the data; the SVG flips them (Y) so text stays upright.
import { $, $$, esc, initTheme, getJSON, loadFonts, seg, NK_CSS } from "./common.js";

initTheme();
const [manifest, data] = await Promise.all([getJSON("fonts.json"), getJSON("design.json")]);
if (!data || !data.families?.length) {
  $("#main").insertAdjacentHTML("afterbegin", '<p class="cmp-empty">design.json이 없습니다. <code>nkfont site</code>로 빌드한 사이트에서 열어 주세요.</p>');
  throw new Error("design.json missing");
}
loadFonts(manifest, null);

const PHI = data.phi;
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const st = { fam: data.families[0].id, idx: 0, view: "note", sel: null };
const fam = () => data.families.find((f) => f.id === st.fam);
const glyph = () => fam().glyphs[Math.min(st.idx, fam().glyphs.length - 1)];
const Y = (y) => -y;
const r1 = (v) => Math.round(v * 10) / 10;
const fmt = (v, d = 0) => (v == null ? "–" : Number(v).toLocaleString("ko-KR", { maximumFractionDigits: d, minimumFractionDigits: d }));
const fontOf = (f) => `'${NK_CSS[f.id] || f.family}'`;

// Shared <defs>: hatch pattern for the inked strokes, a pen wobble filter, arrowheads.
document.body.insertAdjacentHTML("beforeend", `<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
  <pattern id="dn-hatch" patternUnits="userSpaceOnUse" width="26" height="26" patternTransform="rotate(-38)">
    <rect class="n-hatch-bg" width="26" height="26"/><line class="n-hatch-line" x1="0" y1="0" x2="0" y2="26"/></pattern>
  <filter id="dn-rough" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="7"/>
    <feDisplacementMap in="SourceGraphic" scale="9" xChannelSelector="R" yChannelSelector="G"/></filter>
  <marker id="dn-head" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
    <path d="M0 0L10 5L0 10" fill="none" stroke="var(--mark)" stroke-width="2" stroke-linejoin="round"/></marker>
</defs></svg>`);

/* ---------- geometry helpers ---------- */
// Smooth closed curve through ring points (Catmull-Rom as cubic Béziers).
function smooth(pts) {
  const p = pts.slice(0, -1), n = p.length;
  let d = `M${p[0][0]} ${Y(p[0][1])}`;
  for (let i = 0; i < n; i++) {
    const a = p[(i - 1 + n) % n], b = p[i], c = p[(i + 1) % n], e = p[(i + 2) % n];
    const c1 = [b[0] + (c[0] - a[0]) / 6, b[1] + (c[1] - a[1]) / 6], c2 = [c[0] - (e[0] - b[0]) / 6, c[1] - (e[1] - b[1]) / 6];
    d += `C${r1(c1[0])} ${r1(Y(c1[1]))} ${r1(c2[0])} ${r1(Y(c2[1]))} ${c[0]} ${Y(c[1])}`;
  }
  return d;
}
function smoothOpen(p) {
  let d = `M${r1(p[0][0])} ${r1(Y(p[0][1]))}`;
  for (let i = 0; i < p.length - 1; i++) {
    const a = p[Math.max(0, i - 1)], b = p[i], c = p[i + 1], e = p[Math.min(p.length - 1, i + 2)];
    const c1 = [b[0] + (c[0] - a[0]) / 6, b[1] + (c[1] - a[1]) / 6], c2 = [c[0] - (e[0] - b[0]) / 6, c[1] - (e[1] - b[1]) / 6];
    d += `C${r1(c1[0])} ${r1(Y(c1[1]))} ${r1(c2[0])} ${r1(Y(c2[1]))} ${r1(c[0])} ${r1(Y(c[1]))}`;
  }
  return d;
}
const poly = (pts) => pts.map((p, i) => `${i ? "L" : "M"}${r1(p[0])} ${r1(Y(p[1]))}`).join("");
const unit = (a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1; return [dx / l, dy / l]; };
// Left-hand normal in y-up space: a bar written rightwards gets its arrow above, a stem written
// downwards gets it on the right, like the margin arrows of a hand-drawn note.
const normal = ([dx, dy]) => [-dy, dx];

// Offset a polyline sideways (mitred at corners) and trim its ends a little.
function offsetPath(s, dist) {
  const p = s.curve ? s.pts.slice(0, -1) : s.pts;
  if (s.curve) {
    // A ring's arrow runs outside the bowl for seven eighths of the way round.
    const cx = p.reduce((t, q) => t + q[0], 0) / p.length, cy = p.reduce((t, q) => t + q[1], 0) / p.length;
    const out = s.pts.map(([x, y]) => { const l = Math.hypot(x - cx, y - cy) || 1; return [x + ((x - cx) / l) * dist, y + ((y - cy) / l) * dist]; });
    return smoothOpen(out.slice(0, Math.round(out.length * 0.88)));
  }
  const out = p.map((q, i) => {
    const a = i ? normal(unit(p[i - 1], q)) : null, b = i < p.length - 1 ? normal(unit(q, p[i + 1])) : null;
    let n = a && b ? [a[0] + b[0], a[1] + b[1]] : a || b;
    const l = Math.hypot(n[0], n[1]) || 1, k = a && b ? Math.max(0.5, (n[0] * a[0] + n[1] * a[1]) / l) : 1;
    n = [n[0] / l / k, n[1] / l / k];
    return [q[0] + n[0] * dist, q[1] + n[1] * dist];
  });
  return poly(out);
}

function strokeD(s) { return s.curve ? smooth(s.pts) : poly(s.pts); }

// Where the stroke's thickness was read: middle of its longest segment (east side for a ring).
function measureAt(s) {
  if (s.curve) {
    const east = s.pts.reduce((m, q) => (q[0] > m[0] ? q : m), s.pts[0]);
    return { c: east, n: [1, 0] };
  }
  let best = [s.pts[0], s.pts[1]];
  for (let i = 1; i < s.pts.length - 1; i++) if (Math.hypot(s.pts[i + 1][0] - s.pts[i][0], s.pts[i + 1][1] - s.pts[i][1]) > Math.hypot(best[1][0] - best[0][0], best[1][1] - best[0][1])) best = [s.pts[i], s.pts[i + 1]];
  const c = [(best[0][0] + best[1][0]) / 2, (best[0][1] + best[1][1]) / 2];
  return { c, n: normal(unit(best[0], best[1])) };
}

/* ---------- drawing ---------- */
function frame(f, g) {
  const gd = f.guides;
  const top = Math.max(gd.ascent, g.box[3]) + 120, bot = Math.min(gd.descent, g.box[1]) - 190;
  const left = Math.min(0, g.box[0]) - 190, right = Math.max(g.adv, g.box[2]) + 250;
  return { left, right, top, bot, w: right - left, h: top - bot };
}

function guides(f, g, fr, opts) {
  const gd = f.guides, out = [];
  const rows = [["어센더", gd.ascent], ["디센더", gd.descent], ["기준선", 0]];
  if (gd.cap_top) rows.push(["대문자 H", gd.cap_top]);
  if (gd.x_top) rows.push(["x높이", gd.x_top]);
  const han = 0xac00 <= g.ch.codePointAt(0) && g.ch.codePointAt(0) <= 0xd7a3;
  if (han && gd.han_top != null) rows.push(["한글 상단", gd.han_top], ["한글 하단", gd.han_bottom]);
  rows.sort((a, b) => b[1] - a[1]);
  let lastY = -Infinity;
  for (const [label, y] of rows) {
    out.push(`<line class="n-guide" x1="${fr.left + 60}" x2="${fr.right - 20}" y1="${Y(y)}" y2="${Y(y)}"/>`);
    const ly = Math.max(Y(y) - 8, lastY + 30); lastY = ly;
    out.push(`<text class="n-guide-label" x="${fr.right - 26}" y="${ly}" text-anchor="end">${label} ${fmt(y)}</text>`);
  }
  // Cell walls: terminal families sit on a 600-unit grid; reading faces just show the advance.
  const walls = f.kind === "text" || !gd.half ? [0, g.adv] : Array.from({ length: Math.round(g.adv / gd.half) + 1 }, (_, i) => i * gd.half);
  for (const x of walls) out.push(`<line class="n-guide" x1="${x}" x2="${x}" y1="${Y(fr.top - 40)}" y2="${Y(fr.bot + 90)}"/>`);
  if (opts.labels) out.push(`<text class="n-guide-label" x="${g.adv / 2}" y="${Y(fr.top - 70)}" text-anchor="middle">${f.kind === "text" ? `폭 ${fmt(g.adv)}` : `${g.cells}칸 · ${fmt(g.adv)}`}</text>`);
  return out.join("");
}

// Golden-section construction grid over the ink box, plus a faint 50-unit ruling in note mode.
function grid(f, g, fr, opts) {
  const [x0, y0, x1, y1] = g.box, out = [];
  if (opts.note) {
    for (let y = Math.ceil(fr.bot / 50) * 50; y <= fr.top; y += 50) out.push(`<line class="n-rule" x1="${fr.left}" x2="${fr.right}" y1="${Y(y)}" y2="${Y(y)}"/>`);
  }
  const a = 1 / (PHI * PHI), b = 1 / PHI, ext = 46;
  const xs = [x0, x0 + (x1 - x0) * a, x0 + (x1 - x0) * b, x1], ys = [y0, y0 + (y1 - y0) * a, y0 + (y1 - y0) * b, y1];
  for (const x of xs) out.push(`<line class="n-grid" x1="${r1(x)}" x2="${r1(x)}" y1="${Y(y1 + ext)}" y2="${Y(y0 - ext)}"/>`);
  for (const y of ys) out.push(`<line class="n-grid" x1="${x0 - ext}" x2="${x1 + ext}" y1="${r1(Y(y))}" y2="${r1(Y(y))}"/>`);
  if (opts.labels) {
    out.push(`<text class="n-phi" x="${r1((xs[0] + xs[1]) / 2)}" y="${Y(y1 + ext + 14)}" text-anchor="middle">1/φ²</text>`);
    out.push(`<text class="n-phi" x="${r1((xs[1] + xs[3]) / 2)}" y="${Y(y1 + ext + 14)}" text-anchor="middle">1/φ</text>`);
  }
  return out.join("");
}

function dims(f, g, fr) {
  const [x0, y0, x1, y1] = g.box, out = [];
  const tick = (x, y, h = 16) => `<line class="n-dim" x1="${x}" x2="${x}" y1="${Y(y) - h}" y2="${Y(y) + h}"/>`;
  const vtick = (x, y, w = 16) => `<line class="n-dim" x1="${x - w}" x2="${x + w}" y1="${Y(y)}" y2="${Y(y)}"/>`;
  const yb = fr.bot + 110, ys = fr.bot + 50, xl = fr.left + 90;
  out.push(`<line class="n-dim" x1="${x0}" x2="${x1}" y1="${Y(yb)}" y2="${Y(yb)}"/>${tick(x0, yb)}${tick(x1, yb)}`);
  out.push(`<text class="n-dim-label" x="${(x0 + x1) / 2}" y="${Y(yb) - 14}" text-anchor="middle">${fmt(x1 - x0)}</text>`);
  out.push(`<line class="n-dim" x1="0" x2="${g.adv}" y1="${Y(ys)}" y2="${Y(ys)}"/>${tick(0, ys)}${tick(g.adv, ys)}${tick(x0, ys, 9)}${tick(x1, ys, 9)}`);
  out.push(`<text class="n-dim-label" x="${x0 / 2}" y="${Y(ys) + 34}" text-anchor="middle">${fmt(g.lsb)}</text><text class="n-dim-label" x="${(x1 + g.adv) / 2}" y="${Y(ys) + 34}" text-anchor="middle">${fmt(g.rsb)}</text>`);
  out.push(`<line class="n-dim" x1="${xl}" x2="${xl}" y1="${Y(y0)}" y2="${Y(y1)}"/>${vtick(xl, y0)}${vtick(xl, y1)}`);
  out.push(`<text class="n-dim-label" x="${xl - 14}" y="${Y((y0 + y1) / 2)}" text-anchor="middle" transform="rotate(-90 ${xl - 14} ${Y((y0 + y1) / 2)})">${fmt(y1 - y0)}</text>`);
  // Stroke thickness, read across each stroke where it was measured.
  for (const s of g.strokes) {
    if (!s.w) continue;
    const { c, n } = measureAt(s), h = s.w / 2;
    const a = [c[0] - n[0] * h, c[1] - n[1] * h], b = [c[0] + n[0] * h, c[1] + n[1] * h];
    const t = [-n[1] * 12, n[0] * 12];
    out.push(`<path class="n-dim" d="M${r1(a[0])} ${r1(Y(a[1]))}L${r1(b[0])} ${r1(Y(b[1]))}M${r1(a[0] - t[0])} ${r1(Y(a[1] - t[1]))}L${r1(a[0] + t[0])} ${r1(Y(a[1] + t[1]))}M${r1(b[0] - t[0])} ${r1(Y(b[1] - t[1]))}L${r1(b[0] + t[0])} ${r1(Y(b[1] + t[1]))}"/>`);
    const lx = c[0] - n[0] * (h + 30), ly = c[1] - n[1] * (h + 30);
    out.push(`<text class="n-dim-label" x="${r1(lx)}" y="${r1(Y(ly) + 9)}" text-anchor="middle">${fmt(s.w)}</text>`);
  }
  return out.join("");
}

function order(g, opts) {
  const out = [];
  for (const s of g.strokes) {
    const off = (s.w || 60) / 2 + 44;
    const d = offsetPath(s, off);
    out.push(`<path class="n-arrow dn-anim" data-n="${s.n}" d="${d}" marker-end="url(#dn-head)"${opts.note ? ' filter="url(#dn-rough)"' : ""}/>`);
    if (opts.labels) {
      const p0 = s.pts[0], dir = unit(s.pts[0], s.pts[1]), nn = s.curve ? [0, 1] : normal(dir);
      const lx = p0[0] + nn[0] * (off + 30) - dir[0] * 34, ly = p0[1] + nn[1] * (off + 30) - dir[1] * 34;
      out.push(`<text class="n-num dn-anim-num" data-n="${s.n}" x="${r1(lx)}" y="${r1(Y(ly) + 16)}" text-anchor="middle">${s.n}</text>`);
    }
  }
  return out.join("");
}

// Font editor point view: handles, on-curve squares, off-curve circles, implied points, starts.
function points(g) {
  const out = [], marks = [], quad = fam().curves !== "cubic";
  g.contours.forEach((c, ci) => {
    const n = c.length;
    for (let i = 0; i < n; i++) {
      const a = c[i], b = c[(i + 1) % n];
      if (!a[2] || !b[2]) out.push(`<line class="o-handle" x1="${a[0]}" y1="${Y(a[1])}" x2="${b[0]}" y2="${Y(b[1])}"/>`);
      if (!a[2] && !b[2] && quad) marks.push(`<circle class="o-implied" cx="${r1((a[0] + b[0]) / 2)}" cy="${r1(Y((a[1] + b[1]) / 2))}" r="5"/>`);
    }
    c.forEach((p, i) => {
      const sel = st.sel && st.sel[0] === ci && st.sel[1] === i ? " is-sel" : "";
      marks.push(p[2]
        ? `<rect class="o-on${sel}" data-c="${ci}" data-i="${i}" x="${p[0] - 9}" y="${Y(p[1]) - 9}" width="18" height="18"/>`
        : `<circle class="o-off${sel}" data-c="${ci}" data-i="${i}" cx="${p[0]}" cy="${Y(p[1])}" r="8"/>`);
    });
    // Start point and contour direction, as editors mark them.
    const [p, q] = [c[0], c[1 % n]], [ux, uy] = unit(p, q), [nx, ny] = normal([ux, uy]);
    const tip = [p[0] + ux * 34, p[1] + uy * 34];
    marks.push(`<path class="o-start" d="M${r1(tip[0])} ${r1(Y(tip[1]))}L${r1(p[0] + nx * 13)} ${r1(Y(p[1] + ny * 13))}L${r1(p[0] - nx * 13)} ${r1(Y(p[1] - ny * 13))}Z"/>`);
  });
  if (st.sel) {
    const c = g.contours[st.sel[0]], i = st.sel[1], n = c.length;
    // Highlight the segment that starts here: up to the next on-curve point.
    const seg = [c[i]];
    for (let k = 1; k <= n; k++) { const p = c[(i + k) % n]; seg.push(p); if (p[2]) break; }
    out.push(`<path class="o-sel" d="${segPath(seg)}"/>`);
    const p = c[i];
    marks.push(`<text class="o-coord" x="${p[0] + 18}" y="${Y(p[1]) - 18}">${fmt(p[0], p[0] % 1 ? 1 : 0)}, ${fmt(p[1], p[1] % 1 ? 1 : 0)}</text>`);
  }
  return out.join("") + marks.join("");
}

// One TrueType/CFF segment: a line, a quadratic run with implied on-curve points, or a cubic.
function segPath(seg) {
  const [a, ...rest] = seg;
  let d = `M${a[0]} ${Y(a[1])}`;
  const offs = rest.slice(0, -1), b = rest[rest.length - 1];
  if (!offs.length) return d + `L${b[0]} ${Y(b[1])}`;
  if (fam().curves === "cubic" && offs.length === 2) return d + `C${offs[0][0]} ${Y(offs[0][1])} ${offs[1][0]} ${Y(offs[1][1])} ${b[0]} ${Y(b[1])}`;
  for (let k = 0; k < offs.length; k++) {
    const o = offs[k], nxt = k < offs.length - 1 ? [(o[0] + offs[k + 1][0]) / 2, (o[1] + offs[k + 1][1]) / 2] : b;
    d += `Q${o[0]} ${Y(o[1])} ${r1(nxt[0])} ${r1(Y(nxt[1]))}`;
  }
  return d;
}

function svg(f, g, opts) {
  const fr = frame(f, g);
  const parts = [];
  if (opts.grid) parts.push(grid(f, g, fr, opts));
  if (opts.guide) parts.push(guides(f, g, fr, opts));
  if (opts.note) {
    parts.push(`<path class="n-pencil" d="${g.path}" transform="scale(1,-1)"/>`);
    parts.push(`<g ${opts.animate ? 'mask="url(#dn-reveal)"' : ""}><path class="n-glyph" d="${g.path}" transform="scale(1,-1)" filter="url(#dn-rough)"/></g>`);
    if (opts.animate) {
      const m = g.strokes.map((s) => `<path class="dn-mask" data-n="${s.n}" d="${strokeD(s)}" fill="none" stroke="#fff" stroke-width="${r1((s.w || 80) * 2.4 + 40)}" stroke-linecap="round" stroke-linejoin="round"/>`).join("");
      parts.unshift(`<defs><mask id="dn-reveal" maskUnits="userSpaceOnUse" x="${fr.left}" y="${-fr.top}" width="${fr.w}" height="${fr.h}"><rect class="dn-mask-all" x="${fr.left}" y="${-fr.top}" width="${fr.w}" height="${fr.h}" fill="#fff" opacity="0"/>${m}</mask></defs>`);
    }
  } else {
    parts.push(`<path class="n-glyph" d="${g.path}" transform="scale(1,-1)"/>`);
  }
  if (opts.measure) parts.push(dims(f, g, fr));
  if (opts.order && g.strokes.length) parts.push(order(g, opts));
  if (!opts.note && opts.points) parts.push(points(g));
  const label = `${f.family} ‘${g.ch}’ 설계 노트`;
  return `<svg viewBox="${fr.left} ${-fr.top} ${fr.w} ${fr.h}" role="img" aria-label="${esc(label)}" preserveAspectRatio="xMidYMid meet">${parts.join("")}</svg>`;
}

/* ---------- stroke-order animation ---------- */
let anims = [];
function play() {
  anims.forEach((a) => a.cancel());
  anims = [];
  const root = $("#canvas svg");
  if (!root || reduce) return;
  const per = 700, gap = 220;
  $$(".dn-anim", root).forEach((p) => {
    const n = +p.dataset.n, len = p.getTotalLength();
    p.style.strokeDasharray = `${len} ${len}`;
    anims.push(p.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: per, delay: (n - 1) * (per + gap), fill: "backwards", easing: "ease-in-out" }));
  });
  $$(".dn-anim-num", root).forEach((t) => {
    const n = +t.dataset.n;
    anims.push(t.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, delay: (n - 1) * (per + gap), fill: "backwards" }));
  });
  $$(".dn-mask", root).forEach((p) => {
    const n = +p.dataset.n, len = p.getTotalLength() + 1;
    p.style.strokeDasharray = `${len} ${len}`;
    anims.push(p.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: per, delay: (n - 1) * (per + gap), fill: "backwards", easing: "ease-in-out" }));
  });
  const all = $(".dn-mask-all", root), count = $$(".dn-mask", root).length;
  if (all) anims.push(all.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500, delay: count * (per + gap), fill: "forwards" }));
}

/* ---------- page ---------- */
const lay = () => ({ grid: $("#layGrid").checked, guide: $("#layGuide").checked, order: $("#layOrder").checked, measure: $("#layMeasure").checked, points: $("#layPoints").checked });

function drawMain(animate = true) {
  const f = fam(), g = glyph();
  const note = st.view === "note";
  $("#sheet").className = `dn-sheet ${note ? "is-note" : "is-outline"}`;
  $("#layPointsWrap").hidden = note;
  $("#replay").hidden = !note || !g.strokes.length;
  $("#canvas").innerHTML = svg(f, g, { ...lay(), note, labels: true, animate: note && animate && lay().order && g.strokes.length > 0 });
  const on = g.contours.reduce((t, c) => t + c.filter((p) => p[2]).length, 0), all = g.contours.reduce((t, c) => t + c.length, 0);
  $("#hint").innerHTML = note
    ? (g.strokes.length ? `획 ${g.strokes.length}개를 순서대로 씁니다. 번호와 화살표는 쓰는 방향, 숫자는 그 자리에서 잰 획 두께(단위: 1/1000 em)입니다.` : "이 가족의 그림은 골격과 달라 획 순서를 생략했습니다. 윤곽선과 치수는 실제 값입니다.")
    : `윤곽선 ${g.contours.length}개 · 온커브 <b>${on}</b> · 오프커브 <b>${all - on}</b>. 점을 누르면 좌표와 그 점에서 시작하는 구간이 표시됩니다.`;
  if (note && animate) requestAnimationFrame(play);
  notes(f, g);
}

function notes(f, g) {
  const on = g.contours.reduce((t, c) => t + c.filter((p) => p[2]).length, 0), all = g.contours.reduce((t, c) => t + c.length, 0);
  const ws = g.strokes.map((s) => s.w).filter(Boolean);
  const ratio = (r) => `<li class="${r.on ? "on" : ""}"><span>${esc(r.label)}</span><span class="v">${fmt(r.value, 3)}</span><small>${r.on ? "✓ " : ""}가장 가까운 눈금 ${esc(r.phi)} = ${fmt(r.target, 3)} · ${r.dev >= 0 ? "+" : ""}${fmt(r.dev * 100, 1)}%</small></li>`;
  $("#notes").innerHTML = `
    <h2 class="dn-title"><span class="big" style="font-family:${fontOf(f)}">${esc(g.ch)}</span><span class="rom">${esc(g.title)}</span></h2>
    <p class="dn-note">${esc(g.note)}</p>
    <dl class="dn-dl">
      <dt>가족</dt><dd>${esc(f.family)} · ${esc(g.name)}</dd>
      <dt>글자 폭</dt><dd>${fmt(g.adv)}${f.kind === "text" || !g.cells ? "" : ` (${g.cells}칸)`}</dd>
      <dt>잉크 상자</dt><dd>${fmt(g.box[2] - g.box[0])} × ${fmt(g.box[3] - g.box[1])} · 여백 ${fmt(g.lsb)} / ${fmt(g.rsb)}</dd>
      <dt>획 두께</dt><dd>${ws.length ? `${fmt(Math.min(...ws))} ~ ${fmt(Math.max(...ws))}` : g.stem ? `세로 ${fmt(g.stem)} · 가로 ${fmt(g.bar)}` : "–"}</dd>
      <dt>회색도</dt><dd>잉크 상자의 ${fmt((g.coverage || 0) * 100)}%</dd>
      <dt>윤곽선</dt><dd>${g.contours.length}개 · 점 ${all} (온 ${on} / 오프 ${all - on})</dd>
    </dl>
    ${g.strokes.length ? `<p class="dn-h">획 순서와 두께</p><ol class="dn-strokes">${g.strokes.map((s) => `<li><b>${s.n}</b> ${s.w ? fmt(s.w) : "–"}</li>`).join("")}</ol>` : '<p class="dn-muted">이 가족에서는 획 순서 골격이 그림과 맞지 않아 생략했습니다.</p>'}
    <p class="dn-h">φ 눈금과 비교</p>
    <ul class="dn-ratios">${g.ratios.map(ratio).join("")}</ul>`;
}

function cards() {
  const f = fam();
  $("#cards").innerHTML = f.glyphs.map((g, i) => `<button type="button" class="dn-card is-note" role="option" aria-selected="${i === st.idx}" data-i="${i}" aria-label="${esc(g.ch)} ${esc(g.title)}">${svg(f, g, { grid: true, guide: false, order: true, measure: false, note: true, labels: false })}<span>${esc(g.title)} · ${esc(g.ch)}</span></button>`).join("");
}

$("#cards").onclick = (e) => {
  const b = e.target.closest(".dn-card"); if (!b) return;
  st.idx = +b.dataset.i; st.sel = null;
  $$(".dn-card").forEach((c) => c.setAttribute("aria-selected", c === b));
  drawMain();
  $("#stage").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
};
$("#canvas").onclick = (e) => {
  const p = e.target.closest("[data-c]"); if (!p) return;
  const sel = [+p.dataset.c, +p.dataset.i];
  st.sel = st.sel && st.sel[0] === sel[0] && st.sel[1] === sel[1] ? null : sel;
  drawMain(false);
};
for (const id of ["layGrid", "layGuide", "layOrder", "layMeasure", "layPoints"]) $(`#${id}`).onchange = () => drawMain(false);
$("#replay").onclick = () => drawMain(true);

seg($("#famSeg"), data.families.map((f) => [f.id, esc(f.family)]), st.fam, (v) => { st.fam = v; st.sel = null; cards(); drawMain(); });
seg($("#viewSeg"), [["note", "손그림 노트"], ["outline", "아웃라인"]], st.view, (v) => { st.view = v; st.sel = null; drawMain(); });
cards();
drawMain();
