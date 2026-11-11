// The tsky's answer: one hindsight packet as a picture. Ink = what the agent was shown, cobalt = what was
// held back, and every forecast drawn as a line the tsky had to clear (or stay clear of).
import { h, s, mjdToIso, fmtNum, pct } from './util.js';
import { agentShort } from './pages.js';

const W = 920, H = 300, M = { l: 44, r: 16, t: 22, b: 30 };
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const mjdOf = (y, m) => Date.UTC(y, m, 1) / 86400000 + 40587;

function timeTicks(lo, hi) {
  const span = hi - lo;
  const step = span > 2600 ? 24 : span > 1300 ? 12 : span > 650 ? 6 : span > 320 ? 3 : span > 110 ? 1 : 0;
  const d = new Date((lo - 40587) * 86400000);
  const out = [];
  if (!step) { for (let t = Math.ceil(lo / 10) * 10; t <= hi; t += 10) out.push({ t, label: mjdToIso(t).slice(5) }); return out; }
  let y = d.getUTCFullYear(), m = Math.ceil((d.getUTCMonth() + (d.getUTCDate() > 1 ? 1 : 0)) / step) * step;
  for (let i = 0; i < 80; i += 1, m += step) {
    const yy = y + Math.floor(m / 12), mm = ((m % 12) + 12) % 12, t = mjdOf(yy, mm);
    if (t > hi) break;
    if (t >= lo) out.push({ t, label: step >= 12 || mm === 0 ? String(yy) : MONTHS[mm] });
  }
  return out;
}

function magTicks(lo, hi) {
  const span = hi - lo;
  const step = [0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5].find((x) => span / x <= 6) ?? 5;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(2));
  return out;
}

/** sky: {cutoff_mjd, series, window, t, mag, forecasts}; agents: scorecard agent names in column order. */
export function skyChart(sky, agents, target) {
  const [x0, x1] = sky.window;
  const drawn = sky.forecasts.filter((f) => f.series === sky.series && f.threshold != null && f.start >= sky.cutoff_mjd && f.start < x1);
  const undrawn = sky.forecasts.filter((f) => !drawn.includes(f));
  const ys = [...sky.mag, ...drawn.map((f) => f.threshold)].filter(Number.isFinite).sort((a, b) => a - b);
  // robust y-range: forecasts always fit; a lone wild point does not flatten the picture
  const q = (p) => ys[Math.min(ys.length - 1, Math.max(0, Math.round(p * (ys.length - 1))))];
  const thr = drawn.map((f) => f.threshold);
  let y0 = Math.min(q(0.003), ...thr), y1 = Math.max(q(0.997), ...thr);
  const pad = Math.max(0.02, (y1 - y0) * 0.1); y0 -= pad; y1 += pad;
  const X = (t) => M.l + ((t - x0) / (x1 - x0)) * (W - M.l - M.r);
  const Y = (m) => M.t + ((m - y0) / (y1 - y0)) * (H - M.t - M.b); // brighter is up
  const svg = s('svg', { class: 'tsky-svg', viewBox: `0 0 ${W} ${H}`, role: 'img',
    'aria-label': `${sky.series} light curve${target ? ` of ${target}` : ''}: shown to the agents until ${mjdToIso(sky.cutoff_mjd)}, held back after, with ${drawn.length} forecasts drawn` });
  const xc = X(sky.cutoff_mjd);
  svg.append(s('rect', { class: 'tsky-future', x: xc, y: M.t, width: W - M.r - xc, height: H - M.t - M.b }));
  for (const v of magTicks(y0, y1)) {
    svg.append(s('line', { class: 'tsky-grid', x1: M.l, x2: W - M.r, y1: Y(v), y2: Y(v) }),
      s('text', { class: 'tsky-tick', x: M.l - 6, y: Y(v) + 3, 'text-anchor': 'end' }, fmtNum(v, v % 1 ? (Math.abs(v * 10 % 1) > 1e-6 ? 2 : 1) : 0)));
  }
  for (const k of timeTicks(x0, x1)) {
    svg.append(s('line', { class: 'tsky-axis', x1: X(k.t), x2: X(k.t), y1: H - M.b, y2: H - M.b + 4 }),
      s('text', { class: 'tsky-tick', x: X(k.t), y: H - M.b + 15, 'text-anchor': 'middle' }, k.label));
  }
  svg.append(s('line', { class: 'tsky-axis', x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b }));
  svg.append(s('text', { class: 'tsky-ylab', x: M.l - 34, y: M.t - 8 }, `${sky.series.replace(/^.*:/, '').replace(/^(ATLAS|ZTF)_/, '')} mag`));

  const clampY = (m) => Math.max(M.t, Math.min(H - M.b, Y(m)));
  const pts = s('g', { class: 'tsky-pts' });
  sky.t.forEach((t, i) => {
    const m = sky.mag[i];
    if (!Number.isFinite(m) || t < x0 || t > x1) return;
    const off = m < y0 || m > y1;
    pts.append(s('circle', { class: `${t < sky.cutoff_mjd ? 'is-seen' : 'is-held'}${off ? ' is-off' : ''}`, cx: X(t), cy: clampY(m), r: t < sky.cutoff_mjd ? 1.7 : 2.1 }));
  });

  const marks = s('g', { class: 'tsky-marks' });
  const byKey = new Map();
  drawn.forEach((f) => {
    const xa = X(f.start), xb = Math.min(X(f.end), W - M.r), y = Y(f.threshold);
    // which side of the line the forecast said the sky would be on ("<" a magnitude = brighter = up)
    const up = f.op === '<';
    const depth = 16;
    const g = s('g', { class: `tsky-mark is-${f.outcome ?? 'pending'}`, 'data-key': `${f.agent}/${f.id}`, 'data-agent': f.agent },
      s('rect', { class: 'tsky-side', x: xa, y: up ? y - depth : y, width: Math.max(2, xb - xa), height: depth }),
      s('line', { class: 'tsky-line', x1: xa, x2: xb, y1: y, y2: y }),
      s('line', { class: 'tsky-line', x1: xa, x2: xa, y1: y, y2: y + (up ? -depth : depth) }),
      X(f.end) <= W - M.r ? s('line', { class: 'tsky-line', x1: xb, x2: xb, y1: y, y2: y + (up ? -depth : depth) }) : null,
      s('text', { class: 'tsky-mark-label', x: xa + 4, y: up ? y - depth - 3 : y + depth + 10 },
        `${agentShort(f.agent).split(' ')[0]} ${f.id} · ${pct(f.probability)} ${f.statistic} ${up ? 'brighter' : 'fainter'} than ${fmtNum(f.threshold, 2)}`));
    marks.append(g);
    byKey.set(`${f.agent}/${f.id}`, g);
  });
  svg.append(marks, pts,
    s('line', { class: 'tsky-cut', x1: xc, x2: xc, y1: M.t - 6, y2: H - M.b }),
    s('text', { class: 'tsky-cut-label', x: xc - 6, y: M.t - 9, 'text-anchor': 'end' }, `shown to the agents`),
    s('text', { class: 'tsky-cut-label is-held', x: xc + 6, y: M.t - 9 }, `held back from ${mjdToIso(sky.cutoff_mjd)}`));

  const wrap = h('figure', { class: 'tsky' });
  const setAgent = (a) => {
    wrap.dataset.agent = a ?? '';
    marks.querySelectorAll('.tsky-mark').forEach((g) => g.classList.toggle('is-muted', !!a && g.dataset.agent !== a));
    chips.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String((b.dataset.agent || '') === (a ?? ''))));
  };
  const withMarks = agents.filter((a) => drawn.some((f) => f.agent === a));
  const chips = h('div', { class: 'tsky-chips', role: 'group', 'aria-label': 'Whose forecasts to show' },
    [null, ...withMarks].map((a) => {
      const b = h('button', { type: 'button', class: 'tsky-chip', 'data-agent': a ?? '', 'aria-pressed': String(a == null) }, a ? agentShort(a) : 'All forecasts');
      b.addEventListener('click', () => setAgent(a));
      return b;
    }));
  wrap.append(
    h('div', { class: 'tsky-head' }, chips,
      h('p', { class: 'tsky-key' },
        h('span', { class: 'tsky-dot is-seen' }), 'shown ', h('span', { class: 'tsky-dot is-held' }), 'held back ',
        h('span', { class: 'tsky-swatch is-true' }), 'forecast came true ', h('span', { class: 'tsky-swatch is-false' }), 'did not')),
    h('div', { class: 'tsky-scroll' }, svg),
    h('figcaption', { class: 'tsky-cap muted small' },
      `Nightly medians of ${sky.series}, the data the grader read. Each bracket is one sealed forecast: its window, its magnitude line, and the side of the line the agent said the sky would be on.`,
      undrawn.length ? ` ${undrawn.length} forecast${undrawn.length > 1 ? 's' : ''} about other series or statistics ${undrawn.length > 1 ? 'are' : 'is'} listed below but not drawn.` : ''));
  /** Envelopes call this on hover/focus so the reader can find a forecast on the chart. */
  wrap.highlight = (key) => {
    marks.querySelectorAll('.tsky-mark').forEach((g) => g.classList.toggle('is-hot', g.dataset.key === key));
    wrap.classList.toggle('has-hot', !!key && byKey.has(key));
    if (key && byKey.has(key)) marks.append(byKey.get(key));
  };
  return wrap;
}
