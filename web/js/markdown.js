// A tiny, safe Markdown renderer. It builds DOM nodes directly (never innerHTML), so any HTML in
// the source is shown as text. Supports: headings, paragraphs, blockquotes, ordered/unordered
// lists (one level of nesting), fenced code, inline code, bold, italic, links, tables, rules.

import { h } from './util.js';

const SAFE_URL = /^(https?:\/\/|mailto:|#\/|\.{0,2}\/|[\w.-]+(\/|$))/i;

const INLINE = [
  { re: /`([^`]+)`/, make: (m) => h('code', null, m[1]) },
  { re: /\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/, make: (m) => link(m[2], inline(m[1])) },
  { re: /<(https?:\/\/[^>\s]+)>/, make: (m) => link(m[1], m[1]) },
  { re: /\*\*([^*]+?)\*\*|__([^_]+?)__/, make: (m) => h('strong', null, inline(m[1] ?? m[2])) },
  { re: /(?<![\w*])\*(?!\s)([^*]+?)\*(?!\w)|(?<![\w_])_(?!\s)([^_]+?)_(?!\w)/, make: (m) => h('em', null, inline(m[1] ?? m[2])) },
  { re: /(?<![("\w])(https?:\/\/[^\s<>()]+[^\s<>().,;:!?'"])/, make: (m) => link(m[1], m[1]) },
];

function link(url, children) {
  if (!SAFE_URL.test(url) || /^javascript:/i.test(url)) return h('span', null, children);
  const external = /^https?:/i.test(url);
  return h('a', { href: url, ...(external ? { rel: 'noopener noreferrer', target: '_blank' } : {}) }, children);
}

// Optional citation rules, active only while a renderer passes `cite` handlers:
//   [C3] or [C11, C12]  -> claim links          (K3, K4) or (K36-K38) -> ledger receipts
let CITE = null;
const CITE_RULES = [
  { re: /\[(C\d+(?:\s*,\s*C\d+)*)\]/, make: (m) => CITE.claims(m[1].split(/\s*,\s*/)) },
  { re: /\((K\d+(?:\s*[-–]\s*K?\d+)?(?:\s*,\s*K\d+(?:\s*[-–]\s*K?\d+)?)*)\)/, make: (m) => CITE.receipts(m[1].split(/\s*,\s*/)) },
];

export function inline(text) {
  const out = [];
  let rest = String(text ?? '');
  const rules = CITE ? [...CITE_RULES, ...INLINE] : INLINE;
  while (rest) {
    let best = null;
    for (const rule of rules) {
      const m = rule.re.exec(rest);
      if (m && (best === null || m.index < best.m.index)) best = { m, rule };
    }
    if (!best) { out.push(rest); break; }
    if (best.m.index > 0) out.push(rest.slice(0, best.m.index));
    out.push(best.rule.make(best.m));
    rest = rest.slice(best.m.index + best.m[0].length);
  }
  return out;
}

const isTableSep = (line) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line);
const cells = (line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
const LIST_RE = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;

export function renderMarkdown(src, { headingOffset = 1, cite = null } = {}) {
  const prev = CITE;
  CITE = cite;
  try { return render(src, headingOffset); } finally { CITE = prev; }
}

function render(src, headingOffset) {
  const root = h('div', { class: 'md' });
  const lines = String(src ?? '').replace(/\r\n?/g, '\n').split('\n');
  let i = 0;
  const para = [];
  const flush = () => {
    if (para.length) root.append(h('p', null, inline(para.join(' '))));
    para.length = 0;
  };

  while (i < lines.length) {
    const line = lines[i];
    // fenced code
    const fence = line.match(/^\s*(```|~~~)\s*([\w+-]*)/);
    if (fence) {
      flush();
      const body = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith(fence[1])) body.push(lines[i++]);
      i++;
      root.append(h('pre', { class: 'md-code', 'data-lang': fence[2] || null }, h('code', null, body.join('\n'))));
      continue;
    }
    if (!line.trim()) { flush(); i++; continue; }
    // heading
    const hd = line.match(/^(#{1,6})\s+(.*?)\s*#*\s*$/);
    if (hd) {
      flush();
      const level = Math.min(6, hd[1].length + headingOffset);
      root.append(h(`h${level}`, null, inline(hd[2])));
      i++;
      continue;
    }
    // rule
    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) { flush(); root.append(h('hr')); i++; continue; }
    // table
    if (line.includes('|') && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      flush();
      const head = cells(line);
      const aligns = cells(lines[i + 1]).map((c) => (c.endsWith(':') ? (c.startsWith(':') ? 'center' : 'right') : null));
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]));
      root.append(h('div', { class: 'md-table' }, h('table', null,
        h('thead', null, h('tr', null, head.map((c, k) => h('th', { style: aligns[k] ? { textAlign: aligns[k] } : null }, inline(c))))),
        h('tbody', null, rows.map((r) => h('tr', null, head.map((_, k) => h('td', { style: aligns[k] ? { textAlign: aligns[k] } : null }, inline(r[k] ?? '')))))),
      )));
      continue;
    }
    // blockquote
    if (/^\s*>/.test(line)) {
      flush();
      const body = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) body.push(lines[i++].replace(/^\s*>\s?/, ''));
      const bq = render(body.join('\n'), headingOffset);
      root.append(h('blockquote', null, [...bq.childNodes]));
      continue;
    }
    // list
    const li = line.match(LIST_RE);
    if (li) {
      flush();
      const { node, next } = parseList(lines, i);
      root.append(node);
      i = next;
      continue;
    }
    para.push(line.trim());
    i++;
  }
  flush();
  return root;
}

function parseList(lines, start) {
  const first = lines[start].match(LIST_RE);
  const indent = first[1].length;
  const ordered = /\d/.test(first[2]);
  const list = h(ordered ? 'ol' : 'ul');
  if (ordered && parseInt(first[2], 10) !== 1) list.setAttribute('start', parseInt(first[2], 10));
  let i = start;
  let item = null;
  let text = [];
  const close = () => { if (item) { item.prepend(...inline(text.join(' '))); list.append(item); } item = null; text = []; };
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      // a blank line ends the list unless the next line continues it
      const nxt = lines[i + 1];
      if (nxt && LIST_RE.test(nxt) && nxt.match(LIST_RE)[1].length >= indent) { i++; continue; }
      break;
    }
    const m = line.match(LIST_RE);
    if (m && m[1].length === indent) {
      close();
      item = h('li');
      text = [m[3]];
      i++;
    } else if (m && m[1].length > indent && item) {
      const sub = parseList(lines, i);
      item.append(sub.node);
      i = sub.next;
    } else if (!m && item && /^\s+/.test(line)) {
      text.push(line.trim());
      i++;
    } else break;
  }
  close();
  return { node: list, next: i };
}
