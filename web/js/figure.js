// The hero figure: panels stacked on one shared time axis.
//   (a) optical photometry   (b) NEOWISE infrared   (c) W1−W2 colour per visit   (d) TESS, if any
// Hand-written SVG. Dense series are drawn as a single <path> (round-capped zero-length segments),
// sparse series as circles with error bars. Hover shows a crosshair and a readout of every series
// at that date; drag (mouse) to zoom the time axis, double-click or "All" to reset.

import {
  h, s, mjdToYear, yearToMjd, mjdToIso, mjdToDate, dateToMjd, niceTicks, decimalsFor, nearestIndex,
  lowerBound, fmtNum, fmtInt, monthName, arr, minus,
} from './util.js';

const fmtCompact = (n) => (n == null ? '' : n >= 1e5 ? `${Math.round(n / 1000)}k` : n >= 1e4 ? `${(n / 1000).toFixed(1)}k` : fmtInt(n));

// ---- identity: colour follows the photometric band, shape follows the photometric system ------
// AAVSO band codes: Johnson-Cousins U B V R I; CV/CR = unfiltered with V/R zero point; TB/TG/TR =
// DSLR tri-colour; SG/SR/SI = Sloan; "Vis." = visual (eye) estimates, ±0.1–0.3 mag.
const BAND_INK = {
  B: 'B', V: 'V', g: 'V', G: 'V', R: 'R', r: 'R', I: 'I', i: 'I', W1: 'W1', W2: 'W2',
  TB: 'B', TG: 'V', TR: 'R', SG: 'V', SR: 'R', SI: 'I', CV: 'V', CR: 'R', U: 'x1', J: 'x2', H: 'x3',
};
const FALLBACK_INK = ['x1', 'x2', 'x3'];
const SHAPE_BY_SURVEY = { 'ASAS-SN': 'triangle', ASASSN: 'triangle', ZTF: 'diamond' };
const SHAPE_BY_BAND = { R: 'square', r: 'square', I: 'square', i: 'square', W2: 'square', TB: 'triangle', TG: 'triangle', TR: 'triangle', SG: 'diamond', SR: 'diamond', SI: 'diamond' };
const WAVELENGTH = {
  U: 0.36, B: 0.44, TB: 0.45, g: 0.48, SG: 0.48, TG: 0.53, V: 0.55, CV: 0.55, 'Vis.': 0.56, G: 0.6, TR: 0.6, r: 0.62, SR: 0.62,
  R: 0.64, CR: 0.64, i: 0.75, SI: 0.75, I: 0.8, z: 0.9, J: 1.25, H: 1.65, W1: 3.4, W2: 4.6, W3: 12, W4: 22,
};
const BAND_NOTE = { W1: '3.4 µm', W2: '4.6 µm' };
const BAND_NAME = {
  CV: 'CV (clear, V zero-point)', CR: 'CR (clear, R zero-point)', TB: 'TB (DSLR blue)', TG: 'TG (DSLR green)', TR: 'TR (DSLR red)',
  SG: "g′ (Sloan)", SR: "r′ (Sloan)", SI: "i′ (Sloan)",
};
const JOHNSON = new Set(['U', 'B', 'V', 'R', 'I']);
const V_LIKE = new Set(['V', 'Vis.', 'CV', 'TG', 'g', 'G']);
const DENSE = 160; // visible points above which a series is drawn as dots without error bars
const isVisual = (band) => /vis\.?$/i.test(band);

function styleFor(band, survey, fallbackIdx) {
  if (isVisual(band)) return { color: 'var(--c-vis)', shape: 'circle' };
  if (survey === 'TESS') return { color: 'var(--c-tess)', shape: 'circle' };
  const ink = BAND_INK[band] ?? FALLBACK_INK[fallbackIdx % FALLBACK_INK.length];
  return { color: `var(--c-${ink})`, shape: SHAPE_BY_SURVEY[survey] ?? SHAPE_BY_BAND[band] ?? 'circle' };
}

function labelFor(survey, band) {
  if (isVisual(band)) return `${survey} visual${band.length > 4 ? ` (${band.replace(/-?Vis\.?$/i, '').toLowerCase()})` : ''}`;
  if (survey === 'TESS') return 'TESS';
  return `${survey} ${BAND_NAME[band] ?? band}`.trim();
}

// ---- data preparation -------------------------------------------------------------------------
export function prepareSeries(payload) {
  const raw = payload?.series ?? {};
  let fb = 0;
  const list = Object.entries(raw).map(([key, ser]) => {
    const t = arr(ser.t), mag = arr(ser.mag), err = arr(ser.err);
    const idx = t.map((_, i) => i).filter((i) => Number.isFinite(t[i]) && Number.isFinite(mag[i])).sort((a, b) => t[a] - t[b]);
    const band = ser.band ?? key.split(':')[1] ?? key;
    const survey = ser.survey ?? key.split(':')[0] ?? '';
    const isFallback = !(band in BAND_INK) && !isVisual(band);
    const st = styleFor(band, survey, isFallback ? fb++ : 0);
    const fl = ser.flagged ?? {};
    const fidx = arr(fl.t).map((_, i) => i).filter((i) => Number.isFinite(fl.t[i]) && Number.isFinite(arr(fl.mag)[i]));
    const kind = isVisual(band) ? 'visual' : survey === 'AAVSO' && !JOHNSON.has(band) ? 'other' : 'primary';
    return {
      key, band, survey, kind, unit: ser.unit ?? 'mag', nRaw: ser.n_raw, binned: ser.binned_days ?? null,
      mjd: idx.map((i) => t[i]), t: idx.map((i) => mjdToYear(t[i])), v: idx.map((i) => mag[i]), e: idx.map((i) => (isVisual(band) ? 0 : err[i] ?? 0)),
      flagged: {
        n: fl.n ?? fidx.length,
        mjd: fidx.map((i) => fl.t[i]), t: fidx.map((i) => mjdToYear(fl.t[i])), v: fidx.map((i) => fl.mag[i]),
        why: fidx.map((i) => arr(fl.why)[i] ?? 'flagged'),
      },
      ...st,
      label: labelFor(survey, band),
      short: isVisual(band) ? 'vis' : band,
    };
  }).filter((x) => x.t.length); // series with no usable points (only flagged rows) are not plotted
  list.sort((a, b) => (WAVELENGTH[a.band] ?? 50) - (WAVELENGTH[b.band] ?? 50) || a.key.localeCompare(b.key));
  return list;
}

/** Which series start hidden: visual estimates when CCD V exists; exotic AAVSO bands when Johnson exists. */
export function defaultHidden(series) {
  const hidden = new Set();
  const optical = series.filter((x) => x.survey !== 'NEOWISE' && x.survey !== 'TESS');
  const hasCcdV = optical.some((x) => x.kind !== 'visual' && (x.band === 'V' || x.band === 'g'));
  const hasPrimary = optical.some((x) => x.kind === 'primary');
  for (const x of optical) {
    if (x.kind === 'visual' && hasCcdV) hidden.add(x.key);
    if (x.kind === 'other' && hasPrimary) hidden.add(x.key);
  }
  return hidden;
}

/** Gaia DR3 G and BP−RP → V (Riello et al. 2021), valid for −0.5 < BP−RP < 5. */
export function gaiaV(gaia) {
  const G = gaia?.G, c = gaia?.bp_rp;
  if (!Number.isFinite(G) || !Number.isFinite(c) || c < -0.5 || c > 5) return null;
  return G - (-0.02704 + 0.01424 * c - 0.2156 * c * c + 0.01426 * c * c * c);
}
export const GAIA_EPOCH = [56863, 57901]; // DR3 observing window, 2014-07-25 → 2017-05-28

/** Pair W1/W2 visits whose times agree within 1 day into a W1−W2 colour series. */
export function colourSeries(w1, w2) {
  if (!w1 || !w2 || !w1.t.length || !w2.t.length) return null;
  const out = { mjd: [], t: [], v: [], e: [], w1: [], w2: [] };
  for (let i = 0; i < w1.mjd.length; i++) {
    const j = nearestIndex(w2.mjd, w1.mjd[i]);
    if (j < 0 || Math.abs(w2.mjd[j] - w1.mjd[i]) > 1) continue;
    out.mjd.push((w1.mjd[i] + w2.mjd[j]) / 2);
    out.t.push(mjdToYear((w1.mjd[i] + w2.mjd[j]) / 2));
    out.v.push(w1.v[i] - w2.v[j]);
    out.e.push(Math.hypot(w1.e[i] || 0, w2.e[j] || 0));
    out.w1.push(w1.v[i]); out.w2.push(w2.v[j]);
  }
  if (!out.t.length) return null;
  return {
    key: 'W1−W2', band: 'W1−W2', survey: 'NEOWISE', kind: 'primary', unit: 'mag', mjd: out.mjd, t: out.t, v: out.v, e: out.e,
    pairs: out, flagged: { n: 0, mjd: [], t: [], v: [], why: [] }, color: 'var(--c-colour)', shape: 'circle',
    label: 'NEOWISE W1 − W2', short: 'W1−W2', derived: true,
  };
}

/** Why there is no infrared panel, in one honest line (or null if NEOWISE was never queried). */
export function neowiseNote(payload) {
  const prov = payload?.provenance?.neowise;
  const keys = Object.keys(payload?.series ?? {}).filter((k) => k.startsWith('NEOWISE'));
  if (!prov && !keys.length) return null;
  const whys = keys.flatMap((k) => arr(payload.series[k]?.flagged?.why));
  const satCheck = arr(payload?.skeptic?.checks).find((c) => c.id === 'wise_saturation');
  const saturated = whys.some((w) => /saturat/i.test(w)) || (satCheck && satCheck.status === 'fail');
  if (saturated) return 'NEOWISE: no usable visits — the star saturates the detector (W1 < 8).';
  if (prov?.status === 'unavailable') return 'NEOWISE: the archive was unavailable when this case was fetched.';
  if (prov?.status === 'empty' || !prov?.rows_raw) return 'NEOWISE: no detections at this position.';
  const bright = Number.isFinite(payload?.context?.gaia?.G) && payload.context.gaia.G < 10;
  return `NEOWISE: no usable visits — all ${fmtInt(prov.rows_raw)} exposures failed the quality cuts${bright ? ' (for a star this bright, usually saturation: W1 < 8)' : ''}.`;
}

export function buildPanels(series, payload) {
  const isTess = (x) => x.survey === 'TESS' || x.unit === 'relative mag';
  const isIR = (x) => !isTess(x) && (x.survey === 'NEOWISE' || /^W\d$/.test(x.band));
  const optical = series.filter((x) => !isTess(x) && !isIR(x));
  const ir = series.filter(isIR);
  const panels = [];
  const surveys = (xs) => [...new Set(xs.map((x) => x.survey))].join(', ');
  const bands = (xs) => [...new Set(xs.filter((x) => x.kind === 'primary').map((x) => x.band))].join(' ');
  if (optical.length) panels.push({ id: 'optical', title: 'Optical', sub: `${surveys(optical)} ${bands(optical)}`.trim(), axis: 'mag', inverted: true, series: optical, weight: 1 });
  if (ir.length) panels.push({ id: 'ir', title: 'Infrared', sub: `NEOWISE ${ir.map((x) => x.band + (BAND_NOTE[x.band] ? ` (${BAND_NOTE[x.band]})` : '')).join(', ')}`, axis: 'mag', inverted: true, series: ir, weight: 0.66 });
  else {
    const note = neowiseNote(payload);
    if (note && panels.length) panels.push({ id: 'ir', title: 'Infrared', sub: 'NEOWISE', axis: 'mag', inverted: true, series: [], empty: note, fixedH: 34 });
  }
  const w1 = ir.find((x) => x.band === 'W1'), w2 = ir.find((x) => x.band === 'W2');
  const col = colourSeries(w1, w2);
  if (col) panels.push({ id: 'colour', title: 'Colour', sub: 'W1 − W2 per NEOWISE visit', axis: 'colour', inverted: false, series: [col], weight: 0.44 });
  return panels;
}

/** TESS points split into sectors: by context.tess.sectors windows when present, else at gaps > 5 days. */
export function tessSectors(series, payload) {
  const tess = series.find((x) => x.survey === 'TESS');
  if (!tess) return null;
  const meta = Object.entries(payload?.context?.tess?.sectors ?? {})
    .map(([n, m]) => ({ n, t0: m.t_start, t1: m.t_end })).filter((m) => Number.isFinite(m.t0) && Number.isFinite(m.t1)).sort((a, b) => a.t0 - b.t0);
  const chunks = [];
  if (meta.length) {
    for (const m of meta) chunks.push({ name: `S${m.n}`, t0: m.t0, t1: m.t1, idx: [], fidx: [] });
    const find = (t) => chunks.find((c) => t >= c.t0 - 1 && t <= c.t1 + 1);
    tess.mjd.forEach((t, i) => find(t)?.idx.push(i));
    tess.flagged.mjd.forEach((t, i) => find(t)?.fidx.push(i));
  } else {
    let cur = null;
    tess.mjd.forEach((t, i) => {
      if (!cur || t - tess.mjd[i - 1] > 5) { cur = { name: '', t0: t, t1: t, idx: [], fidx: [] }; chunks.push(cur); }
      cur.idx.push(i); cur.t1 = t;
    });
    tess.flagged.mjd.forEach((t, i) => chunks.find((c) => t >= c.t0 - 1 && t <= c.t1 + 1)?.fidx.push(i));
  }
  return { ser: tess, chunks: chunks.filter((c) => c.idx.length || c.fidx.length) };
}

// ---- tick helpers -------------------------------------------------------------------------------
function xTicks(y0, y1, plotW) {
  const span = y1 - y0;
  const maxN = Math.max(3, Math.floor(plotW / 62));
  const major = [], minor = [];
  for (const st of [1, 2, 5, 10, 20, 25, 50, 100]) {
    if (span / st <= maxN && span >= 2.2) {
      for (let y = Math.ceil(y0 / st) * st; y <= y1; y += st) major.push({ v: y, label: String(y) });
      const mst = st === 1 ? 0.25 : st === 2 ? 1 : st === 25 ? 5 : st / 5;
      for (let y = Math.ceil(y0 / mst) * mst; y <= y1; y += mst) minor.push(y);
      return { major, minor };
    }
  }
  if (span >= 0.12) {
    const d0 = mjdToDate(yearToMjd(y0)), d1 = mjdToDate(yearToMjd(y1));
    const months = (d1.getUTCFullYear() - d0.getUTCFullYear()) * 12 + d1.getUTCMonth() - d0.getUTCMonth();
    const st = [1, 2, 3, 6].find((m) => months / m <= maxN) ?? 12;
    let y = d0.getUTCFullYear(), m = d0.getUTCMonth() + 1;
    for (let k = 0; k < 400; k++, m++) {
      if (m > 11) { m = 0; y++; }
      const v = mjdToYear(dateToMjd(new Date(Date.UTC(y, m, 1))));
      if (v > y1) break;
      if (v < y0) continue;
      minor.push(v);
      if (m % st === 0) major.push({ v, label: m === 0 ? String(y) : monthName(m) });
    }
    if (major.length && !/^\d{4}$/.test(major[0].label)) major[0].label += ` ${mjdToDate(yearToMjd(major[0].v)).getUTCFullYear()}`;
    return { major, minor };
  }
  const m0 = yearToMjd(y0), m1 = yearToMjd(y1);
  const st = [1, 2, 5, 10, 15].find((d) => (m1 - m0) / d <= maxN) ?? 30;
  for (let m = Math.ceil(m0 / st) * st; m <= m1; m += st) {
    const d = mjdToDate(m);
    major.push({ v: mjdToYear(m), label: `${d.getUTCDate()} ${monthName(d.getUTCMonth())}` });
  }
  return { major, minor };
}

// ---- marks -----------------------------------------------------------------------------------
function dotPath(xs, ys, shape, r) {
  const parts = [];
  const f = (n) => Math.round(n * 10) / 10;
  if (shape === 'triangle') {
    const a = r * 1.25;
    for (let i = 0; i < xs.length; i++) parts.push(`M${f(xs[i])} ${f(ys[i] - a)}l${f(a)} ${f(a * 1.7)}h${f(-2 * a)}z`);
  } else if (shape === 'diamond') {
    const a = r * 1.3;
    for (let i = 0; i < xs.length; i++) parts.push(`M${f(xs[i])} ${f(ys[i] - a)}l${f(a)} ${f(a)}l${f(-a)} ${f(a)}l${f(-a)} ${f(-a)}z`);
  } else {
    for (let i = 0; i < xs.length; i++) parts.push(`M${f(xs[i])} ${f(ys[i])}h0`);
  }
  return parts.join('');
}

function shapeMark(shape, x, y, r, attrs) {
  if (shape === 'square') return s('rect', { x: x - r * 0.9, y: y - r * 0.9, width: r * 1.8, height: r * 1.8, ...attrs });
  if (shape === 'triangle' || shape === 'diamond') return s('path', { d: dotPath([x], [y], shape, r), ...attrs });
  return s('circle', { cx: x, cy: y, r, ...attrs });
}

/** Legend/tooltip key: a short line with the series marker on it. */
export function keyIcon(ser, { w = 22, hgt = 12 } = {}) {
  const el = s('svg', { width: w, height: hgt, viewBox: `0 0 ${w} ${hgt}`, class: 'key', 'aria-hidden': 'true' });
  el.append(s('line', { x1: 1, x2: w - 1, y1: hgt / 2, y2: hgt / 2, style: `stroke:${ser.color}`, 'stroke-width': 2, 'stroke-linecap': 'round' }));
  el.append(shapeMark(ser.shape, w / 2, hgt / 2, 3.4, { style: `fill:${ser.color};stroke:var(--fig-bg)`, 'stroke-width': 1.5 }));
  return el;
}

// ---- the figure ------------------------------------------------------------------------------
export function createFigure(payload, { annotations = [], caseId = '' } = {}) {
  const series = prepareSeries(payload);
  const panels = buildPanels(series, payload);
  const tess = tessSectors(series, payload);
  const root = h('figure', { class: 'fig', 'data-fig': 'timeline' });
  if (!panels.length && !tess) {
    root.append(h('div', { class: 'fig-empty' }, h('p', null, 'No light curves have been fetched for this case yet.'),
      h('p', { class: 'muted' }, 'Ask your agent to run the fetch tools; the figure will appear here.')));
    return root;
  }
  const gV = gaiaV(payload?.context?.gaia);

  const todayY = mjdToYear(dateToMjd(new Date()));
  const annoT = annotations.flatMap((a) => [a.start, a.end, ...(a.baseline ?? [])]).filter(Number.isFinite).map(mjdToYear);
  const hiddenAtStart = defaultHidden(series);
  // "Full record" spans whatever is currently shown, so hidden visual estimates from 1784 don't stretch the axis.
  const extentOf = (keep) => {
    const ts = panels.flatMap((p) => p.series.filter(keep).flatMap((x) => [x.t[0], x.t[x.t.length - 1]])).filter(Number.isFinite);
    const lo = ts.length ? Math.min(...ts) : todayY - 1, hi = Math.max(...ts, todayY, ...annoT);
    const pad = Math.min(0.5, Math.max(0.05, (hi - lo) * 0.015));
    return [lo - pad, hi + pad];
  };
  const full = extentOf((x) => !hiddenAtStart.has(x.key));
  // Long records (R CrB's visual estimates start in 1784) open on the modern era; "Full record" is a click away.
  const LONG = 25, SINCE = 2010;
  const isLong = full[1] - full[0] > LONG && full[1] > SINCE + 3;
  const modern = [Math.max(full[0], SINCE - 0.3), full[1]];
  const initial = isLong ? modern : full;

  const state = { x0: initial[0], x1: initial[1], hidden: new Set(hiddenAtStart), showFlagged: false, hover: null };
  const fullNow = () => extentOf((x) => !state.hidden.has(x.key));
  const plotted = [...panels.flatMap((p) => p.series), ...(tess ? [tess.ser] : [])];
  const nFlagged = plotted.reduce((n, x) => n + (x.flagged.t.length || 0), 0);
  const nFlaggedTotal = plotted.reduce((n, x) => n + (x.flagged.n || 0), 0);

  // ---- controls: legend (toggles), extra bands tucked away, zoom presets, flagged toggle ----
  const legend = h('div', { class: 'fig-legend', role: 'group', 'aria-label': 'Series (click to hide or show)' });
  const extra = h('div', { class: 'fig-legend fig-legend-extra', role: 'group', 'aria-label': 'More series', hidden: true });
  const legendSeries = panels.flatMap((p) => p.series.filter((x) => !x.derived));
  const startHidden = new Set(state.hidden);
  const legendBtns = [];
  for (const ser of legendSeries) {
    const b = h('button', { class: `legend-item ${ser.kind === 'visual' ? 'is-visual' : ''}`, type: 'button', 'aria-pressed': String(!state.hidden.has(ser.key)),
      title: `${ser.label}: ${fmtInt(ser.nRaw ?? ser.t.length)} measurements${ser.binned ? `, plotted as ${ser.binned}-day medians` : ''}. Click to hide/show.` },
    keyIcon(ser), h('span', { class: 'legend-label' }, ser.label), h('span', { class: 'legend-n' }, fmtCompact(ser.nRaw ?? ser.t.length)));
    b.addEventListener('click', () => {
      if (state.hidden.has(ser.key)) state.hidden.delete(ser.key); else state.hidden.add(ser.key);
      b.setAttribute('aria-pressed', String(!state.hidden.has(ser.key)));
      render();
    });
    legendBtns.push(b);
    (startHidden.has(ser.key) ? extra : legend).append(b);
  }
  if (extra.childElementCount) {
    const n = extra.childElementCount;
    const more = h('button', { type: 'button', class: 'legend-more', 'aria-expanded': 'false' }, `+ ${n} more band${n > 1 ? 's' : ''}`);
    more.addEventListener('click', () => {
      extra.hidden = !extra.hidden;
      more.setAttribute('aria-expanded', String(!extra.hidden));
      more.textContent = extra.hidden ? `+ ${n} more band${n > 1 ? 's' : ''}` : '− fewer bands';
    });
    legend.append(more);
  }

  const presets = [];
  const span = (r) => `${Math.floor(r[0] + 0.3)}–${Math.floor(r[1])}`;
  if (isLong) presets.push({ label: `Since ${SINCE}`, range: () => modern }, { label: () => `Full record ${span(fullNow())}`, range: fullNow });
  else presets.push({ label: 'All', range: fullNow });
  const ext = (xs) => { const ts = xs.flatMap((x) => [x.t[0], x.t[x.t.length - 1]]).filter(Number.isFinite); return ts.length ? [Math.min(...ts), Math.max(...ts)] : null; };
  for (const p of panels.filter((p) => p.id === 'ir' || (p.id === 'optical' && !isLong))) {
    const e = ext(p.series.filter((x) => !startHidden.has(x.key)));
    if (!e) continue;
    const w = Math.max(0.1, (e[1] - e[0]) * 0.04);
    const r = [e[0] - w, Math.min(full[1], e[1] + w)];
    const ref = isLong ? modern : full;
    if ((r[1] - r[0]) / (ref[1] - ref[0]) < 0.85) presets.push({ label: `${p.id === 'ir' ? 'NEOWISE' : p.series[0].survey} years`, range: () => r });
  }
  const rangeLabel = h('span', { class: 'fig-range mono', 'aria-live': 'polite' });
  const labelOf = (p) => (typeof p.label === 'function' ? p.label() : p.label);
  const presetBtns = presets.map((p) => {
    const b = h('button', { type: 'button', class: 'chip' }, labelOf(p));
    b.addEventListener('click', () => { const r = p.range(); state.x0 = r[0]; state.x1 = r[1]; render(); });
    return b;
  });
  const flagBox = h('input', { type: 'checkbox', id: `flag-${caseId}`, disabled: nFlagged === 0 });
  flagBox.addEventListener('change', () => { state.showFlagged = flagBox.checked; render(); });
  const flagLabel = h('label', { class: 'fig-flag', for: `flag-${caseId}`, title: nFlagged ? 'Upper limits, discrepant points and quality-flagged data, drawn as hollow grey rings' : 'No points were flagged in this case' },
    flagBox, h('span', null, nFlagged ? `show flagged points (${fmtInt(nFlaggedTotal)})` : 'no flagged points'));

  const controls = h('div', { class: 'fig-controls' }, legend, extra);
  const tools = h('div', { class: 'fig-controls fig-controls-below' },
    h('div', { class: 'fig-tools' },
      h('span', { class: 'fig-tools-label' }, 'Time'), ...presetBtns, rangeLabel,
      h('span', { class: 'fig-hint' }, matchMedia('(pointer: fine)').matches ? 'drag to zoom · double-click to reset' : 'tap for values'),
      flagLabel));

  const plot = h('div', { class: 'fig-plot' });
  const tip = h('div', { class: 'fig-tip', role: 'status', 'aria-live': 'polite', hidden: true });
  plot.append(tip);
  const tessBox = tess ? h('div', { class: 'tess-strip' }) : null;
  root.append(controls, panels.length ? plot : null, panels.length ? tools : null, tessBox);

  let svgEl = null, geom = null;

  function visible(ser) { return !state.hidden.has(ser.key); }
  const gaiaShown = (panel) => gV != null && panel.id === 'optical' && panel.series.some((x) => visible(x) && V_LIKE.has(x.band));

  function yDomain(panel) {
    if (panel.empty) return [0, 1];
    let lo = Infinity, hi = -Infinity;
    for (const ser of panel.series) {
      if (!visible(ser)) continue;
      const a = lowerBound(ser.t, state.x0), b = lowerBound(ser.t, state.x1);
      const sparse = b - a <= DENSE;
      for (let i = a; i < b; i++) {
        const e = sparse ? ser.e[i] || 0 : 0;
        lo = Math.min(lo, ser.v[i] - e); hi = Math.max(hi, ser.v[i] + e);
      }
      if (state.showFlagged) {
        for (let i = 0; i < ser.flagged.t.length; i++) {
          if (ser.flagged.t[i] < state.x0 || ser.flagged.t[i] > state.x1) continue;
          lo = Math.min(lo, ser.flagged.v[i]); hi = Math.max(hi, ser.flagged.v[i]);
        }
      }
    }
    if (panel.id === 'colour' && Number.isFinite(lo)) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
    if (gaiaShown(panel) && Number.isFinite(lo)) { lo = Math.min(lo, gV); hi = Math.max(hi, gV); }
    if (!Number.isFinite(lo)) {
      // nothing visible in range: fall back to the full extent so the frame still has an axis
      const all = panel.series.flatMap((x) => x.v);
      if (!all.length) return [0, 1];
      lo = Math.min(...all); hi = Math.max(...all);
    }
    if (hi - lo < 0.02) { lo -= 0.05; hi += 0.05; }
    const p = (hi - lo) * 0.09;
    return [lo - p, hi + p];
  }

  function render() {
    if (tessBox) renderTess();
    if (!panels.length) return;
    const W = Math.max(300, plot.clientWidth || root.clientWidth || 800);
    const compact = W < 640;
    const ml = compact ? 42 : 56, mr = compact ? 26 : 40, titleH = compact ? 26 : 24, gap = 14, bottom = 30;
    const unit = compact ? 230 : 256;
    const plotW = W - ml - mr;
    const X = (t) => ml + ((t - state.x0) / (state.x1 - state.x0)) * plotW;
    const Xinv = (px) => state.x0 + ((px - ml) / plotW) * (state.x1 - state.x0);

    // prediction windows: lay their labels out in rows above the figure so none collide
    const windows = [];
    for (const a of annotations) {
      if (!Number.isFinite(a.start) || !Number.isFinite(a.end)) continue;
      const s0 = mjdToYear(a.start), s1 = mjdToYear(a.end);
      if (!(s1 > state.x0 && s0 < state.x1)) continue;
      const xa = X(Math.max(s0, state.x0)), xb = X(Math.min(s1, state.x1));
      const cx = (xa + xb) / 2, half = a.id.length * 3.6 + 4;
      const lo = Math.max(cx - half, Math.min(xa, cx - half)), hi = Math.max(cx + half, xb);
      let row = 0;
      while (windows.some((w) => w.row === row && w.lo < hi + 4 && lo < w.hi + 4)) row++;
      windows.push({ a, xa, xb, cx, lo, hi, row });
    }
    const rows = windows.length ? Math.max(...windows.map((w) => w.row)) + 1 : 0;
    const top = rows ? 10 + rows * 14 : 4;
    let y = top;
    const pg = panels.map((p, i) => {
      const ph = p.empty ? (compact ? 50 : 34) : Math.round(unit * p.weight);
      const g = { p, y0: y + titleH, h: ph, index: i };
      y = g.y0 + ph + gap;
      g.dom = yDomain(p);
      return g;
    });
    const H = y - gap + bottom;
    for (const g of pg) {
      const [d0, d1] = g.dom;
      g.Y = g.p.inverted ? (v) => g.y0 + ((v - d0) / (d1 - d0)) * g.h : (v) => g.y0 + g.h - ((v - d0) / (d1 - d0)) * g.h;
    }
    geom = { W, H, ml, mr, plotW, pg, X, Xinv, compact, top };

    const svg = s('svg', { class: 'fig-svg', width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': describe() });
    const defs = s('defs');
    svg.append(defs);
    for (const g of pg) {
      defs.append(s('clipPath', { id: `clip-${caseId}-${g.p.id}` }, s('rect', { x: ml, y: g.y0, width: plotW, height: g.h })));
    }
    const { major, minor } = xTicks(state.x0, state.x1, plotW);
    const inRange = (t) => t >= state.x0 && t <= state.x1;

    // panel frames, grid, y ticks, titles
    for (const g of pg) {
      const grp = s('g', { class: `panel panel-${g.p.id}` });
      const letter = 'abcdefg'[g.index];
      if (g.p.empty) {
        grp.append(s('rect', { class: 'frame is-empty', x: ml + 0.5, y: g.y0 + 0.5, width: plotW - 1, height: g.h - 1 }));
        const [l1, l2] = compact && g.p.empty.includes(' — ') ? g.p.empty.split(' — ') : [g.p.empty, null];
        grp.append(s('text', { class: 'empty-note', x: ml + 10, y: g.y0 + g.h / 2 + (l2 ? -8 : 0), 'dominant-baseline': 'central' }, l1,
          l2 ? s('tspan', { x: ml + 10, dy: 16 }, l2.charAt(0).toUpperCase() + l2.slice(1)) : null));
        grp.append(s('text', { class: 'panel-letter', x: ml, y: g.y0 - 8 }, letter));
        grp.append(s('text', { class: 'panel-title', x: ml + 14, y: g.y0 - 8 }, g.p.title, compact ? null : s('tspan', { class: 'panel-sub', dx: 9 }, g.p.sub)));
        svg.append(grp);
        continue;
      }
      const [d0, d1] = g.dom;
      const yt = niceTicks(d0, d1, Math.max(3, Math.round(g.h / 46)));
      const dec = decimalsFor(yt.step);
      for (const t of major) grp.append(s('line', { class: 'grid', x1: X(t.v), x2: X(t.v), y1: g.y0, y2: g.y0 + g.h }));
      for (const v of yt) {
        const yy = g.Y(v);
        if (yy < g.y0 + 1 || yy > g.y0 + g.h - 1) continue;
        grp.append(s('line', { class: 'grid', x1: ml, x2: ml + plotW, y1: yy, y2: yy }));
        grp.append(s('line', { class: 'tick', x1: ml, x2: ml + 5, y1: yy, y2: yy }));
        grp.append(s('line', { class: 'tick', x1: ml + plotW - 5, x2: ml + plotW, y1: yy, y2: yy }));
        grp.append(s('text', { class: 'tick-label', x: ml - 7, y: yy, 'text-anchor': 'end', 'dominant-baseline': 'central' }, minus(v.toFixed(dec))));
      }
      if (g.p.id === 'colour' && 0 > d0 && 0 < d1) grp.append(s('line', { class: 'zero', x1: ml, x2: ml + plotW, y1: g.Y(0), y2: g.Y(0) }));
      grp.append(s('rect', { class: 'frame', x: ml + 0.5, y: g.y0 + 0.5, width: plotW - 1, height: g.h - 1 }));
      for (const t of major) {
        grp.append(s('line', { class: 'tick', x1: X(t.v), x2: X(t.v), y1: g.y0 + g.h, y2: g.y0 + g.h - 5 }));
        grp.append(s('line', { class: 'tick', x1: X(t.v), x2: X(t.v), y1: g.y0, y2: g.y0 + 5 }));
      }
      for (const t of minor) grp.append(s('line', { class: 'tick minor', x1: X(t), x2: X(t), y1: g.y0 + g.h, y2: g.y0 + g.h - 3 }));
      // title row, left-aligned so the right side stays clear for annotations:
      // "a  Optical  AAVSO B V R I  ·  mag, brighter ↑"
      const ty = g.y0 - 8;
      const dir = g.p.id === 'colour' ? 'redder ↑' : g.p.axis === 'relative mag' ? 'rel. mag, brighter ↑' : 'mag, brighter ↑';
      grp.append(s('text', { class: 'panel-letter', x: ml, y: ty }, letter));
      grp.append(s('text', { class: 'panel-title', x: ml + 14, y: ty }, g.p.title,
        compact ? null : s('tspan', { class: 'panel-sub', dx: 9 }, g.p.sub),
        s('tspan', { class: 'panel-dir', dx: compact ? 8 : 12 }, dir)));
      svg.append(grp);
    }

    // annotations: baselines (light shade, deduplicated), prediction windows (dashed edges), today
    const annoG = s('g', { class: 'annos' });
    const yTop = pg[0].y0, yBot = pg[pg.length - 1].y0 + pg[pg.length - 1].h;
    const baselines = new Map();
    for (const a of annotations) {
      if (!Array.isArray(a.baseline) || a.baseline.length !== 2) continue;
      const k = a.baseline.join('-');
      if (!baselines.has(k)) baselines.set(k, { b: a.baseline, ids: [] });
      baselines.get(k).ids.push(a.id);
    }
    for (const { b, ids } of baselines.values()) {
      const b0 = mjdToYear(b[0]), b1 = mjdToYear(b[1]);
      if (!(b1 > state.x0 && b0 < state.x1)) continue;
      const xa = X(Math.max(b0, state.x0)), xb = X(Math.min(b1, state.x1));
      for (const g of pg) annoG.append(s('rect', { class: 'anno-baseline', x: xa, y: g.y0, width: Math.max(1, xb - xa), height: g.h }));
      if (xb - xa > 34) annoG.append(s('text', { class: 'anno-label baseline', x: xa + 4, y: yTop + 12 }, `baseline ${ids.join(' ')}`));
    }
    for (const w of windows) {
      const ly = top - 6 - w.row * 14;
      for (const g of pg) annoG.append(s('rect', { class: `anno-window ${w.a.resolved ? 'is-resolved' : ''}`, x: w.xa, y: g.y0, width: Math.max(1.5, w.xb - w.xa), height: g.h }));
      for (const g of pg) for (const xx of [w.xa, w.xb]) annoG.append(s('line', { class: 'anno-edge', x1: xx, x2: xx, y1: g.y0, y2: g.y0 + g.h }));
      annoG.append(s('path', { class: 'anno-bracket', d: `M${w.xa} ${top + 2}V${top - 2}H${w.xb}V${top + 2}` }));
      if (w.row > 0) annoG.append(s('line', { class: 'anno-leader', x1: w.cx, x2: w.cx, y1: ly + 2, y2: top - 2 }));
      annoG.append(s('text', { class: 'anno-label', x: w.cx, y: ly, 'text-anchor': 'middle' }, w.a.id));
    }
    let gaiaLabel = null;
    const og = pg.find((g) => gaiaShown(g.p));
    if (og) {
      const yy = og.Y(gV);
      const e0 = mjdToYear(GAIA_EPOCH[0]), e1 = mjdToYear(GAIA_EPOCH[1]);
      const clipG = s('g', { 'clip-path': `url(#clip-${caseId}-${og.p.id})` });
      clipG.append(s('line', { class: 'gaia-ext', x1: ml, x2: ml + plotW, y1: yy, y2: yy }));
      if (e1 > state.x0 && e0 < state.x1) clipG.append(s('line', { class: 'gaia-epoch', x1: X(Math.max(e0, state.x0)), x2: X(Math.min(e1, state.x1)), y1: yy, y2: yy }));
      annoG.append(clipG);
      const text = `Gaia 2014–17 mean (V-equiv.) ${gV.toFixed(2)}`;
      const tw = text.length * 5.9;
      let lx = e1 > state.x0 && e0 < state.x1 ? Math.max(ml + 6, X(Math.max(e0, state.x0))) : ml + 6;
      lx = Math.min(lx, ml + plotW - tw - 6);
      const below = yy - og.y0 < 16;
      gaiaLabel = s('text', { class: 'gaia-label', x: Math.max(ml + 6, lx), y: below ? yy + 13 : yy - 5 }, text);
    }
    if (inRange(todayY)) {
      annoG.append(s('line', { class: 'today', x1: X(todayY), x2: X(todayY), y1: yTop, y2: yBot }));
      annoG.append(s('text', { class: 'today-label', x: X(todayY) - 4, y: yBot - 5, 'text-anchor': 'end' }, 'today'));
    }

    // series
    const marksG = s('g', { class: 'marks' });
    for (const g of pg) {
      const pgG = s('g', { 'clip-path': `url(#clip-${caseId}-${g.p.id})` });
      const labels = [];
      for (const ser of g.p.series) {
        if (!visible(ser)) continue;
        const a = Math.max(0, lowerBound(ser.t, state.x0) - 1), b = Math.min(ser.t.length, lowerBound(ser.t, state.x1) + 1);
        const n = b - a;
        const xs = [], ys = [];
        for (let i = a; i < b; i++) { xs.push(X(ser.t[i])); ys.push(g.Y(ser.v[i])); }
        if (ser.kind === 'visual') {
          pgG.append(s('path', { class: 'dots vis', d: dotPath(xs, ys, 'circle', 1.2), style: `stroke:${ser.color};fill:none`, 'stroke-width': 2.4, 'stroke-linecap': 'round' }));
        } else if (n > DENSE) {
          const r = compact ? 1.45 : 1.7;
          const d = dotPath(xs, ys, ser.shape, r);
          const st = ser.shape === 'circle' || ser.shape === 'square' ? `stroke:${ser.color};fill:none` : `fill:${ser.color};stroke:none`;
          pgG.append(s('path', { class: 'dots', d, style: st, 'stroke-width': r * 2, 'stroke-linecap': ser.shape === 'square' ? 'square' : 'round' }));
        } else {
          // sparse: faint connecting line, error bars, ringed markers
          if (n > 1 && (ser.survey === 'NEOWISE' || ser.derived)) {
            pgG.append(s('path', { class: 'connect', d: xs.map((x, i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(''), style: `stroke:${ser.color}` }));
          }
          let eb = '';
          for (let i = a; i < b; i++) {
            const e = ser.e[i];
            if (!(e > 0)) continue;
            const x = X(ser.t[i]), y1 = g.Y(ser.v[i] - e), y2 = g.Y(ser.v[i] + e);
            if (Math.abs(y2 - y1) < 1) continue;
            eb += `M${x.toFixed(1)} ${y1.toFixed(1)}V${y2.toFixed(1)}M${(x - 2.5).toFixed(1)} ${y1.toFixed(1)}h5M${(x - 2.5).toFixed(1)} ${y2.toFixed(1)}h5`;
          }
          if (eb) pgG.append(s('path', { class: 'errbar', d: eb, style: `stroke:${ser.color}` }));
          const r = n > 60 ? 2.6 : compact ? 3.2 : 3.8;
          for (let i = 0; i < xs.length; i++) pgG.append(shapeMark(ser.shape, xs[i], ys[i], r, { class: 'pt', style: `fill:${ser.color}` }));
        }
        // direct label at the right end of the visible series
        const last = Math.min(b, ser.t.length) - 1;
        if (last >= a && !ser.derived && ser.kind !== 'visual') {
          const k0 = Math.max(a, last - 12);
          const vals = ser.v.slice(k0, last + 1).sort((p, q) => p - q);
          labels.push({ ser, y: g.Y(vals[vals.length >> 1]), x: X(ser.t[last]) });
        }
      }
      // flagged points: hollow grey marks
      if (state.showFlagged) {
        for (const ser of g.p.series) {
          if (!visible(ser) || !ser.flagged.t.length) continue;
          let d = '';
          for (let i = 0; i < ser.flagged.t.length; i++) {
            if (!inRange(ser.flagged.t[i])) continue;
            const x = X(ser.flagged.t[i]), yy = g.Y(ser.flagged.v[i]);
            d += `M${(x - 2.6).toFixed(1)} ${yy.toFixed(1)}a2.6 2.6 0 1 0 5.2 0a2.6 2.6 0 1 0 -5.2 0`;
          }
          if (d) pgG.append(s('path', { class: 'flagged', d }));
        }
      }
      marksG.append(pgG);
      // place labels in the right margin; skip one that would collide (the legend still names it)
      const placed = [];
      for (const L of labels.sort((p, q) => p.y - q.y)) {
        if (L.y < g.y0 - 2 || L.y > g.y0 + g.h + 2) continue;
        if (placed.some((p) => Math.abs(p - L.y) < 12)) continue;
        placed.push(L.y);
        marksG.append(s('text', { class: 'direct-label', x: ml + plotW + 6, y: L.y, 'dominant-baseline': 'central' }, L.ser.short));
      }
    }

    // x axis labels under the last panel
    const axisG = s('g', { class: 'xaxis' });
    const last = pg[pg.length - 1];
    let lastRight = -Infinity;
    for (const t of major) {
      const xx = X(t.v);
      const w = t.label.length * 7;
      if (xx - w / 2 < lastRight + 6 || xx < ml - 4 || xx > ml + plotW + 4) continue;
      lastRight = xx + w / 2;
      axisG.append(s('text', { class: 'tick-label x', x: xx, y: last.y0 + last.h + 17, 'text-anchor': 'middle' }, t.label));
    }

    // interaction layer
    const cross = s('line', { class: 'crosshair', y1: yTop, y2: yBot, visibility: 'hidden' });
    const hiG = s('g', { class: 'hi' });
    const brush = s('rect', { class: 'brush', y: yTop, height: yBot - yTop, width: 0, visibility: 'hidden' });
    const overlay = s('rect', { class: 'overlay', x: ml, y: yTop - 14, width: plotW, height: yBot - yTop + 14, tabindex: 0, 'aria-label': 'Light curve. Use left and right arrow keys to step through observations.' });
    svg.append(annoG, marksG, gaiaLabel, axisG, cross, hiG, brush, overlay);

    Object.assign(geom, { cross, hiG, brush, overlay });
    svgEl?.remove();
    svgEl = svg;
    plot.prepend(svg);
    wire(overlay);

    rangeLabel.textContent = `${fmtYear(state.x0)} – ${fmtYear(state.x1)}`;
    presetBtns.forEach((b, i) => {
      const r = presets[i].range();
      b.textContent = labelOf(presets[i]);
      b.classList.toggle('is-on', Math.abs(r[0] - state.x0) < 1e-6 && Math.abs(r[1] - state.x1) < 1e-6);
    });
    if (state.hover != null) showAt(state.hover);
  }

  function fmtYear(y) { return mjdToIso(yearToMjd(y)).slice(0, 7); }

  // ---- TESS: one small multiple per sector, each on its own 27-day axis, sharing one y-range ----
  const tessTip = tessBox ? h('div', { class: 'fig-tip', hidden: true }) : null;
  function renderTess() {
    const { ser, chunks } = tess;
    const W = Math.max(280, tessBox.clientWidth || root.clientWidth || 800);
    const compact = W < 640;
    const axisW = 40, gapX = compact ? 10 : 14, titleH = 18, ph = compact ? 64 : 72, gapY = 12;
    const minW = compact ? 150 : 180;
    const cols = Math.max(1, Math.min(chunks.length, Math.floor((W - axisW + gapX) / (minW + gapX))));
    const w = (W - axisW - (cols - 1) * gapX) / cols;
    const rows = Math.ceil(chunks.length / cols);
    const H = rows * (titleH + ph + gapY);
    let lo = Infinity, hi = -Infinity;
    for (const c of chunks) {
      for (const i of c.idx) { lo = Math.min(lo, ser.v[i]); hi = Math.max(hi, ser.v[i]); }
      if (state.showFlagged) for (const i of c.fidx) { lo = Math.min(lo, ser.flagged.v[i]); hi = Math.max(hi, ser.flagged.v[i]); }
    }
    if (!Number.isFinite(lo)) { lo = -0.01; hi = 0.01; }
    const padY = Math.max(0.002, (hi - lo) * 0.12); lo -= padY; hi += padY;
    const svg = s('svg', { class: 'fig-svg tess-svg', width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': `TESS light curve in ${chunks.length} sectors, relative magnitude, brighter up` });
    const yt = niceTicks(lo, hi, 4);
    const dec = decimalsFor(yt.step);
    chunks.forEach((c, k) => {
      const col = k % cols, row = Math.floor(k / cols);
      const x0 = axisW + col * (w + gapX), y0 = row * (titleH + ph + gapY) + titleH;
      const m0 = c.t0 - 0.5, m1 = c.t1 + 0.5;
      const X = (m) => x0 + ((m - m0) / (m1 - m0)) * w;
      const Y = (v) => y0 + ((v - lo) / (hi - lo)) * ph;
      const g = s('g', { class: 'tess-mini' });
      for (const v of yt) {
        const yy = Y(v);
        if (yy < y0 + 1 || yy > y0 + ph - 1) continue;
        g.append(s('line', { class: 'grid', x1: x0, x2: x0 + w, y1: yy, y2: yy }));
        if (col === 0) g.append(s('text', { class: 'tick-label', x: x0 - 6, y: yy, 'text-anchor': 'end', 'dominant-baseline': 'central' }, minus((v > 0 ? '+' : '') + v.toFixed(dec))));
      }
      g.append(s('rect', { class: 'frame', x: x0 + 0.5, y: y0 + 0.5, width: w - 1, height: ph - 1 }));
      const d0 = mjdToDate(c.t0), d1 = mjdToDate(c.t1);
      const dates = compact || w < 200 ? `${monthName(d0.getUTCMonth())} ${d0.getUTCFullYear()}`
        : `${d0.getUTCDate()} ${monthName(d0.getUTCMonth())}–${d1.getUTCDate()} ${monthName(d1.getUTCMonth())} ${d1.getUTCFullYear()}`;
      g.append(s('text', { class: 'tess-title', x: x0, y: y0 - 6 }, c.name ? s('tspan', { class: 'tess-sector' }, `TESS ${c.name}`) : s('tspan', { class: 'tess-sector' }, 'TESS'), s('tspan', { dx: 6 }, dates)));
      const xs = c.idx.map((i) => X(ser.mjd[i])), ys = c.idx.map((i) => Y(ser.v[i]));
      if (xs.length > 1) g.append(s('path', { class: 'connect', d: xs.map((x, i) => `${i && ser.mjd[c.idx[i]] - ser.mjd[c.idx[i - 1]] < 1.6 ? 'L' : 'M'}${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(''), style: `stroke:${ser.color}` }));
      g.append(s('path', { class: 'dots', d: dotPath(xs, ys, 'circle', 1.8), style: `stroke:${ser.color};fill:none`, 'stroke-width': 3.6, 'stroke-linecap': 'round' }));
      if (state.showFlagged && c.fidx.length) {
        let d = '';
        for (const i of c.fidx) {
          const x = X(ser.flagged.mjd[i]), yy = Y(ser.flagged.v[i]);
          if (x < x0 || x > x0 + w) continue;
          d += `M${(x - 2.4).toFixed(1)} ${yy.toFixed(1)}a2.4 2.4 0 1 0 4.8 0a2.4 2.4 0 1 0 -4.8 0`;
        }
        if (d) g.append(s('path', { class: 'flagged', d }));
      }
      const hiG = s('g', { class: 'hi' });
      const ov = s('rect', { class: 'overlay', x: x0, y: y0, width: w, height: ph });
      ov.addEventListener('pointermove', (ev) => {
        const r = svg.getBoundingClientRect();
        const m = m0 + ((ev.clientX - r.left - x0) / w) * (m1 - m0);
        const sub = c.idx.map((i) => ser.mjd[i]);
        if (!sub.length) return;
        const j = c.idx[nearestIndex(sub, m)];
        hiG.replaceChildren(s('circle', { class: 'hi-pt', cx: X(ser.mjd[j]), cy: Y(ser.v[j]), r: 4, style: `fill:${ser.color}` }));
        tessTip.replaceChildren(
          h('div', { class: 'tip-head' }, h('strong', null, mjdToIso(ser.mjd[j])), h('span', { class: 'mono muted' }, `MJD ${ser.mjd[j].toFixed(2)}`)),
          h('div', { class: 'tip-row' }, keyIcon(ser, { w: 14, hgt: 10 }), h('strong', { class: 'mono' }, fmtNum(ser.v[j], 4)), h('span', { class: 'tip-label' }, `TESS ${c.name} Δmag${ser.binned ? `, ${ser.binned}-d median` : ''}`)));
        tessTip.hidden = false;
        const px = X(ser.mjd[j]);
        const tw = tessTip.offsetWidth || 200;
        tessTip.style.left = `${px + 12 + tw > W ? px - 12 - tw : px + 12}px`;
        tessTip.style.top = `${y0 + ph + 4}px`;
      });
      ov.addEventListener('pointerleave', () => { hiG.replaceChildren(); tessTip.hidden = true; });
      g.append(hiG, ov);
      svg.append(g);
    });
    const letter = 'abcdefg'[panels.length];
    tessBox.replaceChildren(
      h('p', { class: 'tess-head' }, h('span', { class: 'panel-letter-html' }, letter), h('strong', null, 'TESS'),
        h('span', { class: 'mono muted' }, ` ${chunks.length} sector${chunks.length > 1 ? 's' : ''}, each on its own ~27-day axis · Δmag vs. sector median · brighter ↑`)),
      h('div', { class: 'tess-plot' }, svg, tessTip));
  }

  function describe() {
    const parts = panels.map((p) => p.empty ? p.empty : `${p.title}: ${p.series.map((x) => `${x.label} (${x.t.length} points, ${fmtYear(x.t[0])} to ${fmtYear(x.t[x.t.length - 1])})`).join('; ')}`);
    return `Light curves on a shared time axis. ${parts.join('. ')}. Magnitude axes are inverted so brighter is up.`;
  }

  // ---- hover / keyboard / brush ----
  function nearestIn(panelGeom, t) {
    let best = null;
    for (const ser of panelGeom.p.series) {
      if (!visible(ser) || !ser.t.length) continue;
      const i = nearestIndex(ser.t, t);
      const d = Math.abs(ser.t[i] - t);
      if (!best || d < best.d) best = { ser, i, d };
    }
    return best;
  }

  function showAt(t, panelIdx = null) {
    const { X, pg, cross, hiG, ml, plotW } = geom;
    if (t < state.x0 || t > state.x1) { hide(); return; }
    state.hover = t;
    cross.setAttribute('x1', X(t)); cross.setAttribute('x2', X(t)); cross.setAttribute('visibility', 'visible');
    hiG.replaceChildren();
    const pxDays = (state.x1 - state.x0) * 365.25 / plotW;
    const rows = [];
    for (const g of pg) {
      for (const ser of g.p.series) {
        if (!visible(ser) || !ser.t.length) continue;
        const i = nearestIndex(ser.t, t);
        const dd = Math.abs(ser.t[i] - t) * 365.25;
        const sparse = ser.t.length <= DENSE;
        const tol = Math.max(0.75, pxDays * (sparse ? 10 : 4));
        if (dd <= tol && ser.t[i] >= state.x0 && ser.t[i] <= state.x1) {
          hiG.append(shapeMark(ser.shape, X(ser.t[i]), g.Y(ser.v[i]), 4.5, { class: 'hi-pt', style: `fill:${ser.color}` }));
          rows.push({ ser, value: ser.v[i], err: ser.e[i], mjd: ser.mjd[i], pair: ser.pairs ? { w1: ser.pairs.w1[i], w2: ser.pairs.w2[i] } : null });
        }
        if (state.showFlagged && ser.flagged.t.length) {
          const j = nearestIndex(ser.flagged.t, t);
          if (Math.abs(ser.flagged.t[j] - t) * 365.25 <= Math.max(0.75, pxDays * 4)) {
            hiG.append(s('circle', { class: 'hi-flag', cx: X(ser.flagged.t[j]), cy: g.Y(ser.flagged.v[j]), r: 4.5 }));
            rows.push({ ser, value: ser.flagged.v[j], mjd: ser.flagged.mjd[j], why: ser.flagged.why[j] });
          }
        }
      }
    }
    const mjd = yearToMjd(t);
    tip.replaceChildren(
      h('div', { class: 'tip-head' }, h('strong', null, mjdToIso(mjd)), h('span', { class: 'mono muted' }, `MJD ${mjd.toFixed(2)}`)),
      rows.length ? h('div', { class: 'tip-rows' }, rows.map((r) => h('div', { class: `tip-row ${r.why ? 'is-flagged' : ''}` },
        r.why ? h('span', { class: 'key-flag', 'aria-hidden': 'true' }) : keyIcon(r.ser, { w: 14, hgt: 10 }),
        h('strong', { class: 'mono' }, fmtNum(r.value, 3), r.err > 0 ? h('span', { class: 'pm' }, ` ± ${fmtNum(r.err, 3)}`) : null),
        h('span', { class: 'tip-label' }, r.ser.label, r.why ? ` · flagged: ${r.why}` : '',
          Math.abs(r.mjd - mjd) > 0.6 ? h('span', { class: 'muted' }, ` · ${mjdToIso(r.mjd)}`) : null),
      ))) : h('div', { class: 'tip-empty muted' }, 'no observation within a few days'),
    );
    tip.hidden = false;
    // position: beside the crosshair, flipping near the right edge
    const px = X(t);
    const tw = tip.offsetWidth || 220;
    const left = px + 14 + tw > geom.W ? px - 14 - tw : px + 14;
    tip.style.left = `${Math.max(4, left)}px`;
    const ty = panelIdx != null ? pg[panelIdx].y0 : pg[0].y0;
    tip.style.top = `${Math.max(0, Math.min(ty, geom.H - (tip.offsetHeight || 80) - 4))}px`;
  }

  function hide() {
    state.hover = null;
    if (!geom?.cross) return;
    geom.cross.setAttribute('visibility', 'hidden');
    geom.hiG.replaceChildren();
    tip.hidden = true;
  }

  function panelAt(py) {
    const { pg } = geom;
    let idx = 0;
    for (let i = 0; i < pg.length; i++) if (py >= pg[i].y0 - 20) idx = i;
    return idx;
  }

  function snap(px, py) {
    const t = geom.Xinv(px);
    const idx = panelAt(py);
    let best = nearestIn(geom.pg[idx], t);
    // if this panel has nothing nearby, try every panel
    if (!best || best.d * 365.25 > 30 * (state.x1 - state.x0) * 365.25 / geom.plotW) {
      for (const g of geom.pg) { const b = nearestIn(g, t); if (b && (!best || b.d < best.d)) best = b; }
    }
    return { t: best ? best.ser.t[best.i] : t, idx };
  }

  let drag = null;
  function wire(overlay) {
    const local = (ev) => { const r = svgEl.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; };
    overlay.addEventListener('pointermove', (ev) => {
      const [px, py] = local(ev);
      if (drag) {
        const a = Math.max(geom.ml, Math.min(drag, px)), b = Math.min(geom.ml + geom.plotW, Math.max(drag, px));
        geom.brush.setAttribute('x', a); geom.brush.setAttribute('width', b - a); geom.brush.setAttribute('visibility', 'visible');
      }
      const { t, idx } = snap(px, py);
      showAt(t, idx);
    });
    overlay.addEventListener('pointerleave', () => { if (!drag) hide(); });
    overlay.addEventListener('pointerdown', (ev) => {
      if (ev.pointerType === 'touch') { const [px, py] = local(ev); const { t, idx } = snap(px, py); showAt(t, idx); return; }
      if (ev.button !== 0) return;
      drag = local(ev)[0];
      overlay.setPointerCapture(ev.pointerId);
    });
    overlay.addEventListener('pointerup', (ev) => {
      if (drag == null) return;
      const px = local(ev)[0];
      const a = Math.min(drag, px), b = Math.max(drag, px);
      drag = null;
      geom.brush.setAttribute('visibility', 'hidden');
      if (b - a > 8) {
        const t0 = geom.Xinv(Math.max(geom.ml, a)), t1 = geom.Xinv(Math.min(geom.ml + geom.plotW, b));
        if (t1 - t0 > 2 / 365.25) { state.x0 = t0; state.x1 = t1; state.hover = null; render(); }
      }
    });
    overlay.addEventListener('dblclick', () => { const r = presets[0].range(); state.x0 = r[0]; state.x1 = r[1]; state.hover = null; render(); });
    overlay.addEventListener('keydown', (ev) => {
      if (!['ArrowLeft', 'ArrowRight', 'Escape', 'Home', 'End'].includes(ev.key)) return;
      ev.preventDefault();
      if (ev.key === 'Escape') { hide(); return; }
      const times = [...new Set(geom.pg.flatMap((g) => g.p.series.filter(visible).flatMap((x) => x.t.filter((v) => v >= state.x0 && v <= state.x1))))].sort((p, q) => p - q);
      if (!times.length) return;
      let i = state.hover == null ? -1 : nearestIndex(times, state.hover);
      if (ev.key === 'Home') i = 0; else if (ev.key === 'End') i = times.length - 1;
      else i = Math.max(0, Math.min(times.length - 1, i + (ev.key === 'ArrowRight' ? (ev.shiftKey ? 10 : 1) : (ev.shiftKey ? -10 : -1))));
      if (i < 0) i = 0;
      showAt(times[i]);
    });
    overlay.addEventListener('blur', hide);
  }

  // ---- re-render on resize ----
  let lastW = 0;
  const ro = new ResizeObserver(() => {
    const w = (panels.length ? plot : tessBox).clientWidth;
    if (Math.abs(w - lastW) < 2) return;
    lastW = w;
    requestAnimationFrame(render);
  });
  ro.observe(panels.length ? plot : tessBox);
  requestAnimationFrame(() => { lastW = (panels.length ? plot : tessBox).clientWidth; render(); });

  root._series = series;
  root._panels = panels;
  return root;
}

// ---- table view twin + CSV --------------------------------------------------------------------
export function figureTable(payload) {
  const series = prepareSeries(payload);
  const panels = buildPanels(series, payload);
  if (!series.length) return null;
  const rows = series.map((x) => {
    const sorted = [...x.v].sort((a, b) => a - b);
    return h('tr', null,
      h('td', null, h('span', { class: 'cell-key' }, keyIcon(x, { w: 16, hgt: 10 }), x.label)),
      h('td', { class: 'num' }, fmtInt(x.nRaw ?? x.t.length)),
      h('td', { class: 'num' }, fmtInt(x.t.length), x.binned ? h('span', { class: 'muted' }, ` (${x.binned}-d bins)`) : ''),
      h('td', { class: 'num' }, x.t.length ? `${mjdToIso(x.mjd[0])} → ${mjdToIso(x.mjd[x.mjd.length - 1])}` : '–'),
      h('td', { class: 'num' }, x.t.length ? fmtNum(sorted[sorted.length >> 1], 3) : '–'),
      h('td', { class: 'num' }, x.t.length ? `${fmtNum(sorted[0], 2)} – ${fmtNum(sorted[sorted.length - 1], 2)}` : '–'),
      h('td', { class: 'num' }, fmtInt(x.flagged.n)),
    );
  });
  const summary = h('table', { class: 'data-table' },
    h('thead', null, h('tr', null, ['Series', 'Measurements', 'Plotted', 'Span', 'Median', 'Range', 'Flagged'].map((c) => h('th', null, c)))),
    h('tbody', null, rows));
  const parts = [h('div', { class: 'table-scroll' }, summary)];
  const col = panels.find((p) => p.id === 'colour');
  if (col) {
    const c = col.series[0];
    parts.push(h('h4', { class: 'table-title' }, 'NEOWISE visits (W1, W2 and the W1 − W2 colour)'));
    parts.push(h('div', { class: 'table-scroll' }, h('table', { class: 'data-table' },
      h('thead', null, h('tr', null, ['Date', 'MJD', 'W1', 'W2', 'W1 − W2'].map((x) => h('th', null, x)))),
      h('tbody', null, c.mjd.map((m, i) => h('tr', null,
        h('td', { class: 'num' }, mjdToIso(m)), h('td', { class: 'num' }, m.toFixed(2)),
        h('td', { class: 'num' }, fmtNum(c.pairs.w1[i], 3)), h('td', { class: 'num' }, fmtNum(c.pairs.w2[i], 3)),
        h('td', { class: 'num' }, fmtNum(c.v[i], 3), h('span', { class: 'muted' }, ` ± ${fmtNum(c.e[i], 3)}`))))))));
  }
  return parts;
}

export function seriesCsv(payload) {
  const lines = ['series,survey,band,mjd,year,mag,err,flag'];
  for (const [key, x] of Object.entries(payload?.series ?? {})) {
    const t = arr(x.t), m = arr(x.mag), e = arr(x.err);
    for (let i = 0; i < t.length; i++) lines.push([key, x.survey, x.band, t[i], mjdToYear(t[i]).toFixed(4), m[i], e[i] ?? '', ''].join(','));
    const f = x.flagged ?? {};
    for (let i = 0; i < arr(f.t).length; i++) lines.push([key, x.survey, x.band, f.t[i], mjdToYear(f.t[i]).toFixed(4), f.mag?.[i] ?? '', '', JSON.stringify(f.why?.[i] ?? 'flagged')].join(','));
  }
  return lines.join('\n');
}
