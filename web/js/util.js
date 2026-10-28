// Small helpers shared by every view. No dependencies.

const SVG_NS = 'http://www.w3.org/2000/svg';

// ---- routes ----------------------------------------------------------------------------------
// The built site (site/build.py) has a real page per URL and marks <html data-router="path">;
// web/ served as-is keeps hash routes, so it still works from any static host and sub-path.
export const PATH_MODE = document.documentElement.dataset.router === 'path';
/** href for an in-site route: link('case/OS-0001') → /case/OS-0001 or #/case/OS-0001. */
export const link = (route = '') => (PATH_MODE ? '/' : '#/') + String(route).replace(/^[#/]+/, '');

/** Hyperscript for HTML. Children may be strings (inserted as text, never HTML), nodes, arrays, null. */
export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  applyAttrs(el, attrs);
  append(el, children);
  return el;
}

/** Hyperscript for SVG. */
export function s(tag, attrs, ...children) {
  const el = document.createElementNS(SVG_NS, tag);
  applyAttrs(el, attrs, true);
  append(el, children);
  return el;
}

function applyAttrs(el, attrs, isSvg = false) {
  if (!attrs) return;
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') el.setAttribute('class', v);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'text') el.textContent = v;
    else if (!isSvg && (k === 'value' || k === 'checked' || k === 'disabled')) el[k] = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
}

function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

export const isEmpty = (x) => x == null || (Array.isArray(x) && x.length === 0) || (typeof x === 'object' && !Array.isArray(x) && Object.keys(x).length === 0) || x === '';
export const arr = (x) => (Array.isArray(x) ? x : []);

// ---- time ------------------------------------------------------------------------------------
export const mjdToYear = (mjd) => 2000 + (mjd - 51544.5) / 365.25;
export const yearToMjd = (y) => (y - 2000) * 365.25 + 51544.5;
export const mjdToDate = (mjd) => new Date((mjd - 40587) * 86400000);
export const dateToMjd = (d) => d.getTime() / 86400000 + 40587;
export const isoDay = (d) => (d instanceof Date && !isNaN(d) ? d.toISOString().slice(0, 10) : '');
export const mjdToIso = (mjd) => isoDay(mjdToDate(mjd));

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const monthName = (i) => MONTHS[i];

/** "27 Oct 2026" from an ISO string or date; '' if unparseable. */
export function fmtDate(x) {
  if (!x) return '';
  const d = x instanceof Date ? x : new Date(String(x).length === 10 ? x + 'T00:00:00Z' : x);
  if (isNaN(d)) return String(x);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

// ---- numbers ---------------------------------------------------------------------------------
export const fmtInt = (n) => (n == null || isNaN(n) ? '–' : Math.round(n).toLocaleString('en-US'));
export function fmtNum(n, digits = 2) {
  if (n == null || n === '' || isNaN(n)) return '–';
  return Number(n).toFixed(digits).replace('-', '−');
}
export const fmtSigned = (n, digits = 2) => (n == null || isNaN(n) ? '–' : (n > 0 ? '+' : n < 0 ? '−' : '±') + Math.abs(n).toFixed(digits));
export const pct = (p, digits = 0) => (p == null || isNaN(p) ? '–' : `${(p * 100).toFixed(digits)}%`);
export const minus = (str) => String(str).replace(/-/g, '−');

/** RA (deg) as 08h 15m 23.30s */
export function fmtRA(deg) {
  if (deg == null) return '';
  let t = ((deg / 15) % 24 + 24) % 24;
  const hh = Math.floor(t); t = (t - hh) * 60;
  const mm = Math.floor(t); const ss = (t - mm) * 60;
  return `${String(hh).padStart(2, '0')}h ${String(mm).padStart(2, '0')}m ${ss.toFixed(2).padStart(5, '0')}s`;
}
/** Dec (deg) as −38° 59′ 23.3″ */
export function fmtDec(deg) {
  if (deg == null) return '';
  const sign = deg < 0 ? '−' : '+';
  let t = Math.abs(deg);
  const dd = Math.floor(t); t = (t - dd) * 60;
  const mm = Math.floor(t); const ss = (t - mm) * 60;
  return `${sign}${String(dd).padStart(2, '0')}° ${String(mm).padStart(2, '0')}′ ${ss.toFixed(1).padStart(4, '0')}″`;
}

// ---- stats -----------------------------------------------------------------------------------
export function quantile(sorted, q) {
  if (!sorted.length) return NaN;
  const pos = (sorted.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}
export const median = (xs) => quantile([...xs].sort((a, b) => a - b), 0.5);

/** Index of the element of sorted array `a` nearest to x. */
export function nearestIndex(a, x) {
  let lo = 0, hi = a.length - 1;
  if (hi < 0) return -1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (a[mid] < x) lo = mid; else hi = mid;
  }
  return Math.abs(a[lo] - x) <= Math.abs(a[hi] - x) ? lo : hi;
}
/** First index i with a[i] >= x. */
export function lowerBound(a, x) {
  let lo = 0, hi = a.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (a[mid] < x) lo = mid + 1; else hi = mid; }
  return lo;
}

/** Nice tick values covering [lo, hi], about `count` of them. */
export function niceTicks(lo, hi, count = 5) {
  if (!(hi > lo)) return Object.assign([lo], { step: 1 });
  const raw = (hi - lo) / Math.max(1, count);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((st) => st >= raw) || 10 * mag;
  const out = [];
  for (let v = Math.ceil(lo / step - 1e-9) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
  out.step = step;
  return out;
}
export const decimalsFor = (step) => Math.max(0, Math.min(4, -Math.floor(Math.log10(step) + 1e-9)));

// ---- misc ------------------------------------------------------------------------------------
export function hashCode(str) {
  let x = 0;
  for (const c of String(str)) x = (x * 31 + c.charCodeAt(0)) | 0;
  return Math.abs(x);
}

export async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = h('textarea', { style: { position: 'fixed', opacity: '0' } }, text);
    document.body.append(ta); ta.select();
    try { document.execCommand('copy'); } catch { /* ignore */ }
    ta.remove();
  }
  if (button) {
    const old = button.textContent;
    button.textContent = 'Copied';
    button.classList.add('is-copied');
    setTimeout(() => { button.textContent = old; button.classList.remove('is-copied'); }, 1600);
  }
}

/** Human label for a Strange Stars class key. */
export const klassLabel = (k) => (k ? String(k).replace(/_/g, ' ') : 'unclassified');

export function pretty(obj) {
  try { return JSON.stringify(obj, null, 2); } catch { return String(obj); }
}

/** Scroll to an element by id and flash it (in-page links can't use #fragments under hash routing). */
export function jumpTo(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
  el.classList.remove('flash');
  void el.offsetWidth;
  el.classList.add('flash');
}
