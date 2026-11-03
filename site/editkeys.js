// Code-editor key logic for the tester: Tab indents, Shift+Tab outdents, Enter keeps the indent.
// Pure functions on (text, selection start, selection end) so they can be tested without a browser.

// Indent unit per sample language (Go is gofmt-style tabs).
const UNITS = { Go: "\t", Python: "    ", Rust: "    " };
export const indentUnit = (lang) => UNITS[lang] ?? "  ";

const lineStart = (text, i) => text.lastIndexOf("\n", i - 1) + 1;

// Start offsets of the lines a selection touches. A selection that ends right at the start of a
// line (after selecting whole lines) does not touch that last line.
function selectedLines(text, start, end) {
  const last = end > start && lineStart(text, end) === end ? end - 1 : end;
  const out = [];
  for (let i = lineStart(text, start); ; ) {
    out.push(i);
    const nl = text.indexOf("\n", i);
    if (nl < 0 || nl >= last) return out;
    i = nl + 1;
  }
}

// Tab: a caret (or a selection inside one line) gets the unit typed in; a multi-line selection
// indents every touched non-empty line and stays selected.
export function indent(text, start, end, unit) {
  if (!text.slice(start, end).includes("\n")) {
    const at = start + unit.length;
    return { text: text.slice(0, start) + unit + text.slice(end), start: at, end: at, insert: unit };
  }
  const lines = selectedLines(text, start, end).filter((ls) => ls < text.length && text[ls] !== "\n");
  if (!lines.length) return { text, start, end };
  let out = text;
  for (const ls of [...lines].reverse()) out = out.slice(0, ls) + unit + out.slice(ls);
  const shift = (pos) => pos + unit.length * lines.filter((ls) => ls < pos).length;
  return { text: out, start: shift(start), end: shift(end) };
}

// Shift+Tab: remove one level (a tab, or up to the unit's width in spaces) from every touched line.
export function outdent(text, start, end, unit) {
  const width = unit === "\t" ? 4 : unit.length;
  const cuts = [];
  for (const ls of selectedLines(text, start, end)) {
    let n = 0;
    if (text[ls] === "\t") n = 1;
    else while (n < width && text[ls + n] === " ") n++;
    if (n) cuts.push([ls, n]);
  }
  const shift = (pos) => cuts.reduce((p, [ls, n]) => p - Math.max(0, Math.min(n, pos - ls)), pos);
  let out = text;
  for (const [ls, n] of [...cuts].reverse()) out = out.slice(0, ls) + out.slice(ls + n);
  return { text: out, start: shift(start), end: shift(end) };
}

// Enter: new line with the current line's leading whitespace.
export function newline(text, start, end) {
  const ls = lineStart(text, start);
  const insert = "\n" + text.slice(ls, start).match(/^[ \t]*/)[0];
  const at = start + insert.length;
  return { text: text.slice(0, start) + insert + text.slice(end), start: at, end: at, insert };
}
