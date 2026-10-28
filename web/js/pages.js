// #/cases, #/trials, #/about and the error states.

import { h, s, arr, fmtDate, fmtInt, fmtNum, pct, klassLabel, mjdToYear, mjdToIso, copyText, link } from './util.js';
import { loadCase } from './data.js';
import { ladder, emptyNote, MCP_CMD, REPO, stamp } from './components.js';

// ---- #/cases -----------------------------------------------------------------------------------
export function renderCases(index) {
  const cases = [...index.cases].sort((a, b) => (b.featured ? 1 : 0) - (a.featured ? 1 : 0));
  return h('article', { class: 'page' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'The casebook'),
      h('h1', null, 'Cases'),
      h('p', { class: 'page-lede' }, 'Each case is one strange star: its data from every archive that has seen it, and an open argument about what it is. A case is a directory in git; it climbs the ladder by surviving the Skeptic, being reproduced, and making a prediction that comes true.')),
    ladderKey(),
    cases.length ? h('ol', { class: 'case-cards' }, cases.map((c) => h('li', { class: c.featured ? 'is-featured' : '' }, caseCard(c))))
      : emptyNote('No cases yet.', h('p', null, 'Open the first one: ', h('code', null, 'oddsky open <star>'), '.')),
  );
}

export function caseCard(c) {
  const surveys = [...new Set(arr(c.series).map((k) => k.split(':')[0]))];
  const thumb = h('div', { class: 'card-thumb', 'aria-hidden': 'true' });
  lazyThumb(thumb, c.id, c.featured);
  return h('a', { class: 'case-card', href: link(`case/${encodeURIComponent(c.id)}`) },
    h('div', { class: 'card-top' }, h('span', { class: 'mono card-id' }, c.id), c.target ? h('span', { class: 'mono card-target' }, c.target) : null,
      c.featured ? h('span', { class: 'card-featured' }, 'featured') : null),
    h('h2', { class: 'card-title' }, c.title || c.target || c.id),
    c.hook ? h('p', { class: 'card-hook' }, c.hook) : null,
    thumb,
    h('div', { class: 'card-foot' },
      ladder(c.status, { compact: true }),
      h('dl', { class: 'card-counts' }, cnt('claims', c.n_claims), cnt('hypotheses', c.n_hypotheses), cnt('predictions', c.n_predictions))),
    surveys.length ? h('p', { class: 'card-series mono' }, surveys.join(' · ')) : null,
  );
}
const cnt = (k, n) => h('div', { class: n ? '' : 'is-zero' }, h('dt', null, k), h('dd', { class: 'mono' }, fmtInt(n ?? 0)));

// A tiny light curve per card, drawn when the card scrolls into view (each case file is ~200 kB).
const io = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
  for (const e of entries) if (e.isIntersecting) { io.unobserve(e.target); e.target._draw?.(); }
}, { rootMargin: '200px' }) : null;

function lazyThumb(el, id, big) {
  el._draw = async () => {
    try {
      const payload = await loadCase(id);
      drawThumb(el, payload, big);
    } catch { el.classList.add('is-failed'); }
  };
  if (io) io.observe(el); else el._draw();
}

function pickSeries(series) {
  const ok = (k) => arr(series[k]?.t).length > 20;
  const pref = ['AAVSO:V', 'ASAS-SN:V', 'ASAS-SN:g', 'ZTF:g', 'ZTF:r', 'AAVSO:Vis.', 'AAVSO:R', 'AAVSO:B', 'AAVSO:I'];
  const k = pref.find(ok) ?? Object.keys(series).filter((x) => !x.startsWith('TESS') && !x.startsWith('NEOWISE') && ok(x)).sort((a, b) => series[b].t.length - series[a].t.length)[0];
  return k ? [k, series[k]] : null;
}

function drawThumb(el, payload, big) {
  const pick = pickSeries(payload.series ?? {});
  if (!pick) { el.classList.add('is-failed'); return; }
  const [key, ser] = pick;
  const W = Math.max(200, el.clientWidth || 320), H = big ? 96 : 64, pad = 4;
  // same opening window as the case page: long records start in 2010
  let t = arr(ser.t), m = arr(ser.mag);
  if (mjdToYear(t[t.length - 1]) - mjdToYear(t[0]) > 25) {
    const keep = t.map((x, i) => i).filter((i) => mjdToYear(t[i]) >= 2009.7);
    if (keep.length > 20) { t = keep.map((i) => t[i]); m = keep.map((i) => m[i]); }
  }
  const sorted = [...m].sort((a, b) => a - b);
  const q = (p) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(p * (sorted.length - 1))))];
  const lo = q(0.002), hi = q(0.998);
  const t0 = Math.min(...t), t1 = Math.max(...t);
  const X = (x) => pad + ((x - t0) / (t1 - t0 || 1)) * (W - 2 * pad);
  const Y = (v) => pad + ((Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo || 1)) * (H - 2 * pad);
  let d = '';
  for (let i = 0; i < t.length; i++) d += `M${X(t[i]).toFixed(1)} ${Y(m[i]).toFixed(1)}h0`;
  const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, class: 'thumb-svg' },
    s('path', { d, class: 'thumb-dots', 'stroke-width': big ? 2.4 : 2, 'stroke-linecap': 'round' }));
  el.replaceChildren(svg, h('p', { class: 'thumb-cap mono' },
    h('span', null, `${key.replace(':', ' ').replace('Vis.', 'visual')} · brighter ↑`),
    h('span', null, `${Math.floor(mjdToYear(t0))}–${Math.floor(mjdToYear(t1))}`)));
}

function ladderKey() {
  return h('section', { class: 'ladder-key' },
    h('h2', { class: 'mini-h' }, 'The discovery ladder'),
    h('p', null, h('strong', null, 'observation'), ' data gathered → ', h('strong', null, 'anomaly'), ' something is odd → ',
      h('strong', null, 'reproduced'), ' seen independently → ', h('strong', null, 'interpreted'), ' an explanation leads → ',
      h('strong', null, 'validated'), ' a prediction came true. Most cases exit early, and that is a result too: ',
      h('strong', null, 'artifact'), ' (the instrument did it) or ', h('strong', null, 'closed'), ' (explained).'));
}

// ---- #/trials ----------------------------------------------------------------------------------
const recog = (v) => (v === true || /^(true|yes)$/i.test(String(v)) ? 'yes' : v == null || v === false || /^(false|no|)$/i.test(String(v)) ? null : String(v));
export const agentShort = (name) => {
  const m = /claude[- ]([a-z]+)[- ]([\d.]+)/i.exec(name ?? '');
  return m ? `${m[1][0].toUpperCase()}${m[1].slice(1)} ${m[2]}` : (name ?? 'agent').split(' ')[0];
};
function baseline(sc) {
  const m = /top1\s*([\d.]+).*brier\s*([\d.]+)/i.exec(sc?.summary?.baseline_note ?? '');
  return m ? { top1: +m[1], brier: +m[2] } : { top1: 1 / 11, brier: 10 / 11 };
}
const opensOn = (p) => { const m = /MJD\s*(\d+(?:\.\d+)?)/.exec(p.note ?? ''); return m ? mjdToIso(+m[1]) : null; };
const verdictText = { true: 'came true', false: 'did not happen', unresolvable: 'unresolvable', invalid: 'invalid', pending: 'sealed' };

/** Per-agent tallies used by the page and by the home teaser. */
export function tally(sc) {
  const cases = arr(sc.cases);
  const n = sc.summary?.n ?? cases.length;
  const top1 = cases.filter((c) => c.top1).length;
  const rec = cases.filter((c) => recog(c.recognised));
  const unrec = cases.filter((c) => !recog(c.recognised));
  const preds = arr(sc.predictions);
  const resolved = preds.filter((p) => p.outcome === 'true' || p.outcome === 'false');
  return {
    n, top1, rec, unrec, unrecTop1: unrec.filter((c) => c.top1).length, preds, resolved,
    trueN: resolved.filter((p) => p.outcome === 'true').length, pending: preds.filter((p) => p.outcome === 'pending').length,
  };
}

export function renderTrials(index) {
  const cards = [...index.scorecards].sort((a, b) => (b.summary?.top1 ?? 0) - (a.summary?.top1 ?? 0) || String(a.agent).localeCompare(String(b.agent)));
  const page = h('article', { class: 'page trials' });
  if (!cards.length) {
    page.append(h('header', { class: 'page-head' }, h('p', { class: 'kicker' }, 'Keeping ourselves honest'), h('h1', null, 'Trials'),
      h('p', { class: 'page-lede' }, 'An agent that sounds convincing is not the same as one that is right. So Oddsky tests the investigators on stars whose answers we already know, with the answers sealed before the run.')),
    h('section', { class: 'trials-empty' },
      h('div', { class: 'envelope is-sealed big' }, h('div', { class: 'env-flap', 'aria-hidden': 'true' }),
        h('div', { class: 'env-paper' },
          h('p', { class: 'env-statement' }, 'The first trial, ', h('span', { class: 'mono' }, 'strange-stars-001'), ', is being assembled: known odd stars, ordinary ones, and a few chosen to mislead.'),
          h('p', { class: 'env-check' }, 'No scorecards yet. When one is committed it appears here, failures included.')),
        h('div', { class: 'env-seal', 'aria-hidden': 'true' }, h('span', null, '001')))), howTrialsWork());
    return page;
  }
  const byTrial = new Map();
  for (const sc of cards) { const k = sc.trial ?? 'trial'; if (!byTrial.has(k)) byTrial.set(k, []); byTrial.get(k).push(sc); }
  for (const [trial, scs] of byTrial) page.append(trialSection(trial, scs, index));
  page.append(howTrialsWork());
  return page;
}

function trialSection(trial, scs, index) {
  const caseMap = new Map(index.cases.map((c) => [c.id, c]));
  const n = scs[0].summary?.n ?? arr(scs[0].cases).length;
  const modes = [...new Set(scs.flatMap((sc) => arr(sc.cases).map((c) => c.mode)).filter(Boolean))];
  const sha = scs.find((sc) => sc.answers_sha256)?.answers_sha256;
  const verify = `oddsky trial verify trials/${trial}`;
  const copy = h('button', { type: 'button', class: 'copy' }, 'Copy');
  copy.addEventListener('click', () => copyText(verify, copy));
  const sec = h('section', { class: 'trial', id: `trial-${trial}` },
    h('header', { class: 'trial-head' },
      h('p', { class: 'kicker' }, `Strange Stars · ${trial}${modes.length ? ` · ${modes.join(' + ')}` : ''}`),
      h('h1', { class: 'trial-title' }, 'Same tools, different minds.'),
      h('p', { class: 'page-lede' }, `${n === 10 ? 'Ten' : fmtInt(n)} packets of real data, names and dates removed. Answers sealed (sha256) before any agent ran; revealed after. Each agent got the same packets, the same tools and the same prompt.`)),
    sha ? h('div', { class: 'seal-row' },
      h('div', { class: 'seal-badge', 'aria-hidden': 'true' }, h('span', null, 'sealed')),
      h('div', { class: 'seal-text' },
        h('p', { class: 'sha' }, h('span', { class: 'sha-k' }, 'answer key sha256'), h('code', { class: 'sha-v' }, sha)),
        h('div', { class: 'copy-row verify' }, h('code', { class: 'cmd' }, h('span', { class: 'cmd-dollar', 'aria-hidden': 'true' }, '$ '), verify), copy),
        h('p', { class: 'muted small' }, 'Hash the revealed answer file and compare: if the key had been edited after the run to flatter an agent, the hash would not match.'))) : null,
    compareAgents(scs),
    contamination(scs, caseMap),
    matrix(scs, caseMap),
    hindsight(scs, caseMap),
    erratum(scs),
    processNotes(scs),
  );
  return sec;
}

// side-by-side metrics, each with the uniform-guess reference mark
function compareAgents(scs) {
  const base = baseline(scs[0]);
  const rows = [
    { k: 'Top-1 correct', note: 'the truth was its first choice', get: (sc, t) => ({ v: `${t.top1}/${t.n}`, f: t.n ? t.top1 / t.n : 0, ref: base.top1 }) },
    { k: 'Top-1, stars it did not recognise', note: 'the cleaner measure', get: (sc, t) => ({ v: t.unrec.length ? `${t.unrecTop1}/${t.unrec.length}` : '–', f: t.unrec.length ? t.unrecTop1 / t.unrec.length : 0, ref: base.top1 }) },
    { k: 'Mean p(truth)', note: 'probability it gave the right answer', get: (sc) => ({ v: pct(sc.summary?.mean_p_truth), f: sc.summary?.mean_p_truth ?? 0, ref: base.top1 }) },
    { k: 'Brier score', note: 'probability error over the 11 classes; lower is better', get: (sc) => ({ v: fmtNum(sc.summary?.brier, 2), f: (sc.summary?.brier ?? 0) / 2, ref: base.brier / 2, lowerBetter: true }) },
    { k: 'Hindsight forecasts', note: 'sealed predictions that came true', get: (sc, t) => ({ v: t.resolved.length ? `${t.trueN}/${t.resolved.length}` : '–', f: t.resolved.length ? t.trueN / t.resolved.length : 0, ref: null, extra: t.pending ? `${t.pending} still sealed` : null }) },
    { k: 'Forecast Brier', note: 'lower is better; always saying 50% scores 0.25', get: (sc) => ({ v: fmtNum(sc.summary?.prediction_brier, 3), f: Math.min(1, (sc.summary?.prediction_brier ?? 0) / 0.5), ref: 0.25 / 0.5, lowerBetter: true }) },
  ];
  const ts = scs.map((sc) => tally(sc));
  const bar = (x) => {
    const svg = s('svg', { class: 'cmp-bar', viewBox: '0 0 100 10', preserveAspectRatio: 'none', 'aria-hidden': 'true' },
      s('rect', { class: 'cmp-track', x: 0, y: 3, width: 100, height: 4, rx: 2 }),
      s('rect', { class: `cmp-fill ${x.lowerBetter ? 'is-lower' : ''}`, x: 0, y: 3, width: Math.max(0.8, Math.min(1, x.f) * 100), height: 4, rx: 2 }));
    if (x.ref != null) svg.append(s('line', { class: 'cmp-ref', x1: x.ref * 100, x2: x.ref * 100, y1: -3, y2: 13 }));
    return svg;
  };
  return h('section', { class: 'cmp' },
    h('div', { class: 'table-scroll' }, h('table', { class: 'cmp-table' },
      h('thead', null, h('tr', null, h('th', null, ''), scs.map((sc) => h('th', { class: 'cmp-agent' }, h('span', { class: 'cmp-name' }, agentShort(sc.agent)), h('span', { class: 'mono muted' }, sc.agent))))),
      h('tbody', null, rows.map((r) => h('tr', null,
        h('th', { scope: 'row' }, h('span', { class: 'cmp-k' }, r.k), h('span', { class: 'cmp-note' }, r.note)),
        scs.map((sc, i) => { const x = r.get(sc, ts[i]); return h('td', null, h('span', { class: 'cmp-v mono' }, x.v), x.extra ? h('span', { class: 'cmp-extra muted' }, ` ${x.extra}`) : null, bar(x)); })))))),
    h('p', { class: 'cmp-legend muted' }, h('span', { class: 'cmp-ref-key', 'aria-hidden': 'true' }), ` reference: uniform guessing over 11 classes (top-1 ${pct(base.top1)}, Brier ${fmtNum(base.brier, 2)}); for forecasts, always saying 50%.`));
}

function contamination(scs, caseMap) {
  const lines = scs.map((sc) => {
    const t = tally(sc);
    const who = agentShort(sc.agent);
    const named = t.rec.map((c) => `${caseMap.get(c.real_case)?.target ?? c.case}${recog(c.recognised) !== 'yes' ? ` (“${recog(c.recognised)}”)` : ''}`);
    return h('li', null, h('strong', null, who), ` said it recognised ${t.rec.length} of ${t.n} stars`,
      t.rec.length && t.rec.length <= 3 ? ` (${named.join(', ')})` : '', ` and named ${t.top1}/${t.n} correctly. `,
      t.unrec.length ? ['On the ', h('strong', null, `${t.unrec.length}`), ` it did not recognise: `, h('strong', null, `${t.unrecTop1}/${t.unrec.length}`), '.'] : 'It recognised every star.');
  });
  const note = scs.find((sc) => sc.summary?.contamination_note)?.summary.contamination_note;
  return h('aside', { class: 'callout contamination' },
    h('span', { class: 'stamp stamp-callout', style: { '--rot': '-2.5deg' } }, 'contamination'),
    h('div', null,
      h('h2', { class: 'callout-h' }, 'Famous stars leak through blinding.'),
      h('p', null, 'Removing names and dates does not stop a well-read model from recognising a light curve it has seen in papers. We asked each agent to say, honestly, whether it recognised the star. A perfect score on recognised stars is partly a memory test.'),
      h('ul', { class: 'callout-list' }, lines),
      note ? h('p', { class: 'muted small' }, note.charAt(0).toUpperCase() + note.slice(1)) : null));
}

function matrix(scs, caseMap) {
  const packets = [...new Set(scs.flatMap((sc) => arr(sc.cases).map((c) => c.case)))];
  const rows = [];
  for (const id of packets) {
    const per = scs.map((sc) => arr(sc.cases).find((c) => c.case === id));
    const any = per.find(Boolean);
    const real = caseMap.get(any?.real_case);
    const notes = [];
    per.forEach((c, i) => {
      if (!c) return;
      const who = agentShort(scs[i].agent);
      const r = arr(c.ranked);
      if (c.top1 && r[1] && r[0].p - r[1].p < 0.06) notes.push(`${who} was nearly fooled: ${klassLabel(r[0].klass)} ${fmtNum(r[0].p, 2)}, just ahead of ${klassLabel(r[1].klass)} ${fmtNum(r[1].p, 2)}.`);
      if (!c.top1 && per.some((o) => o?.top1)) notes.push(`${who} called it ${klassLabel(r[0]?.klass)} (${fmtNum(r[0]?.p, 2)}).`);
    });
    if (any?.mode === 'hindsight') {
      scs.forEach((sc) => {
        const ps = arr(sc.predictions).filter((p) => p.case === id);
        const res = ps.filter((p) => p.outcome === 'true' || p.outcome === 'false');
        if (ps.length) notes.push(`${agentShort(sc.agent)}'s forecasts: ${res.length ? `${res.filter((p) => p.outcome === 'true').length}/${res.length} came true` : 'none resolved yet'}${ps.length > res.length ? `, ${ps.length - res.length} still sealed` : ''}.`);
      });
    }
    const highlight = per.some((c) => c && !c.top1) && per.some((c) => c?.top1) && (any?.mode === 'hindsight' || notes.some((n) => n.includes('nearly')));
    rows.push(h('tr', { class: highlight ? 'is-highlight' : '' },
      h('th', { scope: 'row', class: 'mx-packet' }, h('span', { class: 'mono' }, id), any?.mode ? h('span', { class: `mode-chip mode-${any.mode}` }, any.mode) : null),
      h('td', { class: 'mx-truth' },
        h('span', { class: 'klass' }, klassLabel(any?.truth)),
        real ? h('a', { class: 'mx-real', href: link(`case/${real.id}`), title: real.hook ?? '' }, h('span', { class: 'mono' }, `→ ${real.id}`), ` ${real.target}`) : any?.real_case ? h('span', { class: 'mono muted' }, `→ ${any.real_case}`) : null,
        real?.title ? h('span', { class: 'mx-title' }, real.title) : null),
      per.map((c, i) => h('td', { class: `mx-cell ${c ? (c.top1 ? 'is-right' : 'is-wrong') : ''}`, 'data-agent': agentShort(scs[i].agent) }, c ? [
        h('div', { class: 'mx-top' }, h('span', { class: `mark ${c.top1 ? 'ok' : 'no'}`, title: c.top1 ? 'first choice was right' : 'first choice was wrong' }, c.top1 ? '✓' : '✗'),
          h('span', { class: 'mx-klass' }, klassLabel(arr(c.ranked)[0]?.klass))),
        h('div', { class: 'mx-p' }, h('span', { class: 'rk-bar' }, h('span', { style: { width: `${Math.max(0, Math.min(1, c.p_truth ?? 0)) * 100}%` } })), h('span', { class: 'mono' }, `p(truth) ${fmtNum(c.p_truth, 2)}`)),
        recog(c.recognised) ? h('span', { class: 'recog', title: 'the agent said it recognised this star (self-reported)' }, recog(c.recognised) === 'yes' ? 'recognised' : `recognised? ${recog(c.recognised)}`) : null,
      ] : '–')),
    ));
    if (highlight && notes.length) rows.push(h('tr', { class: 'mx-note-row' }, h('td', { colspan: 2 + scs.length }, h('p', { class: 'mx-note' }, real?.hook && /planted|control/i.test(`${real.title} ${real.hook}`) ? h('em', null, `${real.hook} `) : null, notes.join(' ')))));
  }
  return h('section', { class: 'sec mx' },
    h('header', { class: 'section-head' }, h('h2', null, 'Packet by packet'),
      h('p', { class: 'section-lede' }, 'Each row is a packet; its true class and the real case it came from were revealed after the run. Each column is an agent’s first choice, with the probability it gave the truth.')),
    h('div', { class: 'table-scroll' }, h('table', { class: 'mx-table' },
      h('thead', null, h('tr', null, h('th', null, 'Packet'), h('th', null, 'Truth (revealed)'), scs.map((sc) => h('th', null, agentShort(sc.agent))))),
      h('tbody', null, rows))));
}

function hindsight(scs, caseMap) {
  const packets = [...new Set(scs.flatMap((sc) => arr(sc.predictions).map((p) => p.case)))];
  if (!packets.length) return null;
  const sec = h('section', { class: 'sec hs' },
    h('header', { class: 'section-head' }, h('h2', null, 'Hindsight forecasts'),
      h('p', { class: 'section-lede' }, 'For hindsight packets the data stopped at a cut date. Each agent sealed predictions about what would happen next, as checks the archive could grade by itself. Then the sky answered.')));
  for (const id of packets) {
    const c0 = scs.map((sc) => arr(sc.cases).find((c) => c.case === id)).find(Boolean);
    const real = caseMap.get(c0?.real_case);
    sec.append(h('h3', { class: 'hs-packet' }, h('span', { class: 'mono' }, id), real ? [' → ', h('a', { href: link(`case/${real.id}`) }, real.target)] : null,
      c0?.truth ? h('span', { class: 'klass' }, klassLabel(c0.truth)) : null));
    sec.append(h('div', { class: 'hs-cols' }, scs.map((sc) => {
      const ps = arr(sc.predictions).filter((p) => p.case === id);
      const v1 = new Map(arr(sc.grader_v1?.predictions).map((p) => [`${p.case}/${p.id}`, p]));
      const c = arr(sc.cases).find((x) => x.case === id);
      return h('div', { class: 'hs-col' },
        h('p', { class: 'hs-agent' }, h('strong', null, agentShort(sc.agent)), c ? h('span', { class: 'muted' }, ` · called it ${klassLabel(arr(c.ranked)[0]?.klass)} ${c.top1 ? '✓' : '✗'}`) : null),
        ps.length ? ps.map((p) => miniEnvelope(p, v1.get(`${p.case}/${p.id}`))) : h('p', { class: 'muted' }, 'No forecasts.'));
    })));
  }
  return sec;
}

function miniEnvelope(p, old) {
  const sealed = p.outcome === 'pending';
  const changed = old && old.outcome !== p.outcome;
  return h('article', { class: `envelope is-mini ${sealed ? 'is-sealed' : `is-open outcome-${p.outcome}`}` },
    h('div', { class: 'env-flap', 'aria-hidden': 'true' }),
    h('div', { class: 'env-paper' },
      h('header', { class: 'env-head' }, h('span', { class: 'env-id mono' }, p.id),
        h('span', { class: 'env-prob' }, h('span', { class: 'mono' }, pct(p.probability)), h('span', { class: 'env-prob-k' }, 'likely'))),
      h('p', { class: 'env-statement' }, p.statement),
      h('div', { class: 'env-result' },
        sealed ? h('span', { class: 'verdict verdict-pending' }, 'sealed') : h('span', { class: `verdict verdict-${p.outcome}` }, verdictText[p.outcome] ?? p.outcome),
        h('p', null,
          sealed ? ['opens ', h('strong', { class: 'mono' }, opensOn(p) ?? 'later'), ' — the window has not closed yet.'] : [
            p.observed != null ? ['observed ', h('strong', { class: 'mono' }, fmtNum(p.observed, 3))] : null,
            p.n_points ? ` from ${fmtInt(p.n_points)} points` : '', '.'],
          changed ? h('span', { class: 'v1-note' }, ` Grader v1 said “${verdictText[old.outcome] ?? old.outcome}”${old.observed != null ? ` (${fmtNum(old.observed, 2)})` : ''}.`) : null))),
    sealed ? h('div', { class: 'env-seal', 'aria-hidden': 'true' }, h('span', null, p.id)) : null);
}

function erratum(scs) {
  const why = scs.map((sc) => sc.grader_v1?.why_changed).find(Boolean);
  if (!why) return null;
  const diffs = [];
  for (const sc of scs) {
    const now = new Map(arr(sc.predictions).map((p) => [`${p.case}/${p.id}`, p]));
    for (const o of arr(sc.grader_v1?.predictions)) {
      const p = now.get(`${o.case}/${o.id}`);
      if (p && p.outcome !== o.outcome) diffs.push({ sc, o, p });
    }
  }
  return h('section', { class: 'erratum' },
    h('span', { class: 'stamp stamp-erratum', style: { '--rot': '-3deg' } }, 'erratum'),
    h('h2', { class: 'erratum-h' }, 'We found a bug in our own grader.'),
    h('p', { class: 'erratum-why' }, why),
    diffs.length ? h('div', { class: 'table-scroll' }, h('table', { class: 'data-table erratum-table' },
      h('thead', null, h('tr', null, ['Agent', 'Forecast', 'Grader v1', 'Grader v2'].map((x) => h('th', null, x)))),
      h('tbody', null, diffs.map(({ sc, o, p }) => h('tr', null,
        h('td', null, agentShort(sc.agent)),
        h('td', { class: 'erratum-stmt' }, h('span', { class: 'mono' }, `${p.case} ${p.id}`), ' ', p.statement),
        h('td', null, h('span', { class: `verdict small verdict-${o.outcome}` }, verdictText[o.outcome] ?? o.outcome), o.observed != null ? h('span', { class: 'mono muted' }, ` ${fmtNum(o.observed, 2)}`) : null),
        h('td', null, h('span', { class: `verdict small verdict-${p.outcome}` }, verdictText[p.outcome] ?? p.outcome), p.observed != null ? h('span', { class: 'mono muted' }, ` ${fmtNum(p.observed, 2)}`) : null)))))) : null,
    h('ul', { class: 'erratum-sum' }, scs.filter((sc) => sc.grader_v1?.summary).map((sc) => {
      const a = sc.grader_v1.summary, b = sc.summary ?? {};
      return h('li', null, h('strong', null, agentShort(sc.agent)), ': ',
        h('span', { class: 'mono' }, `${a.predictions_true}/${a.predictions_resolved} true, Brier ${fmtNum(a.prediction_brier, 3)}`), ' → ',
        h('span', { class: 'mono' }, `${b.predictions_true}/${b.predictions_resolved} true, Brier ${fmtNum(b.prediction_brier, 3)}`));
    })),
    h('p', { class: 'muted small' }, `Both gradings are published. The fix was made after the answers were revealed, so you should weigh it accordingly. Scorecards now record their grader: ${scs[0].grader ?? 'v2'}.`));
}

function processNotes(scs) {
  return h('section', { class: 'sec process' },
    h('header', { class: 'section-head' }, h('h2', null, 'How each agent ran'),
      h('p', { class: 'section-lede' }, 'Self-reported deviations are part of the result.')),
    h('div', { class: 'process-cols' }, scs.map((sc) => h('div', { class: 'process-col' },
      h('p', { class: 'hs-agent' }, h('strong', null, agentShort(sc.agent)), h('span', { class: 'mono muted' }, ` ${sc.agent_meta?.model_id ?? sc.agent}`)),
      sc.agent_meta?.harness ? h('p', { class: 'small' }, sc.agent_meta.harness) : null,
      sc.process_notes ?? sc.agent_meta?.notes ? h('p', { class: 'process-text' }, (sc.process_notes ?? sc.agent_meta.notes).trim()) : null,
      h('p', { class: 'mono muted small' }, [sc.agent_meta?.prompt ? `prompt: ${sc.agent_meta.prompt}` : null, sc.scored_at ? `scored ${fmtDate(sc.scored_at)}` : null].filter(Boolean).join(' · '))))));
}

function howTrialsWork() {
  return h('section', { class: 'sec how' },
    h('header', { class: 'section-head' }, h('h2', null, 'How trials work')),
    h('div', { class: 'trial-modes' },
      h('section', { class: 'mode' }, h('h3', null, h('span', { class: 'mode-k' }, 'Blind'), ' Name the explanation'),
        h('p', null, 'The agent gets a star’s light curves, colours and neighbours with its identity scrubbed: no name, no coordinates, no dates. It ranks the possible explanations with probabilities. We score whether the truth was its first pick and how well calibrated its probabilities were.')),
      h('section', { class: 'mode' }, h('h3', null, h('span', { class: 'mode-k' }, 'Hindsight'), ' Predict the past'),
        h('p', null, 'The data is cut at a date. The agent commits to machine-checkable predictions about what happens next, with probabilities. Then we reveal what the sky actually did and grade every prediction automatically.')),
      h('section', { class: 'mode sealed-note' }, h('h3', null, h('span', { class: 'mode-k' }, 'Sealed'), ' Answers before results'),
        h('p', null, 'Before a trial runs, the answer key is hashed and the hash committed to git. Anyone can later check that the key wasn’t edited to flatter the agent: hash the revealed answers and compare.'))));
}

/** One-line strip for the home page. */
export function trialTeaser(index) {
  const scs = [...arr(index?.scorecards)].filter((sc) => arr(sc.cases).length).sort((a, b) => (b.summary?.top1 ?? 0) - (a.summary?.top1 ?? 0));
  if (!scs.length) return null;
  const caseMap = new Map(arr(index.cases).map((c) => [c.id, c]));
  const parts = scs.map((sc) => {
    const t = tally(sc);
    return h('span', { class: 'teaser-agent' }, h('strong', null, agentShort(sc.agent)), ` ${t.top1}/${t.n}`, t.rec.length > 1 ? h('span', { class: 'muted' }, ` (recognised ${t.rec.length})`) : null);
  });
  // the most striking forecast: an agent whose sealed forecasts for one packet all came true
  let star = null;
  for (const sc of scs) {
    const by = new Map();
    for (const p of arr(sc.predictions)) { if (!by.has(p.case)) by.set(p.case, []); by.get(p.case).push(p); }
    for (const [id, ps] of by) {
      const res = ps.filter((p) => p.outcome === 'true' || p.outcome === 'false');
      if (res.length >= 3 && res.every((p) => p.outcome === 'true') && (!star || res.length > star.n)) {
        const c = arr(sc.cases).find((x) => x.case === id);
        star = { who: agentShort(sc.agent), n: res.length, target: caseMap.get(c?.real_case)?.target ?? id, truth: c?.truth };
      }
    }
  }
  const modes = [...new Set(scs.flatMap((sc) => arr(sc.cases).map((c) => c.mode)).filter(Boolean))];
  return h('a', { class: 'teaser', href: link('trials') },
    h('span', { class: 'teaser-k' }, `Strange Stars ${String(scs[0].trial ?? '').replace(/^strange-stars-/, 'Trial ')}`),
    h('span', { class: 'teaser-mode mono' }, modes.join(' + ') || 'blind'),
    ...parts,
    star ? h('span', { class: 'teaser-star' }, `${star.who} forecast ${star.target}${star.truth === 'eclipse_companion' ? '’s next eclipse' : ''} blind: ${star.n}/${star.n} sealed predictions came true`) : null,
    h('span', { class: 'teaser-go', 'aria-hidden': 'true' }, '→'));
}

// ---- #/about -----------------------------------------------------------------------------------
export function renderAbout() {
  return h('article', { class: 'page about' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'About'),
      h('h1', null, 'The sky has been recorded. Almost none of it has been looked at.'),
      h('p', { class: 'page-lede' }, 'Gaia, NEOWISE, ZTF, ATLAS and TESS have measured billions of stars, and nearly all of it is public. What is scarce now is attention. Oddsky is an open-source observatory where curious people and their AI agents supply that attention carefully, and leave behind findings anyone can check. The aim: that a curious person anywhere can add something true to what we know about the universe.')),
    h('div', { class: 'manifesto' },
      h('section', null, h('h2', null, 'We ship the observatory, not the AI.'),
        h('p', null, 'Oddsky gives your agent the instruments: archive queries for Gaia, NEOWISE, AAVSO, ASAS-SN, ZTF and TESS, periodograms, dip finders, a skeptic. Bring whichever agent you like. Claude Code, Codex, Cursor, a model running on your own laptop: if it speaks MCP, it can observe.'),
        h('pre', { class: 'cmd-block' }, h('code', null, `$ ${MCP_CMD}`))),
      h('section', null, h('h2', null, 'Git is the database.'),
        h('p', null, 'A case is a directory: the data, the argument, the ledger of every tool call. To disagree, fork it. To contribute, open a pull request. Review is code review, and history is never lost.')),
      h('section', null, h('h2', null, 'Every claim wears a tag.'),
        h('p', null, h('span', { class: 'inline-stamps' }, stamp('observed', 'a1'), ' ', stamp('computed', 'a2'), ' ', stamp('inferred', 'a3'), ' ', stamp('speculated', 'a4'))),
        h('p', null, 'Observed, computed, inferred or speculated: you can always tell what was seen from what was guessed. Every number links to the tool call that produced it.')),
      h('section', null, h('h2', null, 'The Skeptic is code, not a vibe.'),
        h('p', null, 'Before anyone gets excited, a fixed battery of checks asks the boring questions: is a neighbour blended in? Is that period just the Moon? Did anyone else see it? It runs the same way for everyone.')),
      h('section', null, h('h2', null, 'Predictions are sealed and graded by the sky.'),
        h('p', null, 'A good explanation risks something. Predictions are registered in advance as checks the archive can run by itself, with probabilities attached, and they resolve when new data arrives. Not a committee; the sky.')),
      h('section', null, h('h2', null, 'Who'),
        h('p', null, 'Started by Alan Shortz and the advisor. Open source under the MIT licence. ', h('a', { href: REPO, rel: 'noopener', target: '_blank' }, 'github.com/oddsky-org/oddsky'), '.'))),
  );
}

export function renderNotFound(what) {
  return h('article', { class: 'page' }, h('header', { class: 'page-head' },
    h('p', { class: 'kicker' }, 'Not found'), h('h1', null, 'Nothing at these coordinates.'),
    h('p', { class: 'page-lede' }, what ? `${what} isn’t in this archive. ` : '', h('a', { href: link('cases') }, 'Browse the cases'), '.')));
}

export function renderError(err) {
  const fileProto = location.protocol === 'file:';
  return h('article', { class: 'page' }, h('header', { class: 'page-head' },
    h('p', { class: 'kicker' }, 'The data didn’t load'), h('h1', null, 'Clouds over the observatory.'),
    h('p', { class: 'page-lede' }, fileProto
      ? ['Browsers won’t load data from file:// pages. Serve this folder instead: ', h('code', null, 'python3 -m http.server'), ' in ', h('code', null, 'web/'), '.']
      : ['Could not read the case data. If you built this site yourself, run ', h('code', null, 'oddsky export-web'), ' first.']),
    h('pre', { class: 'error-detail' }, h('code', null, String(err?.message ?? err)))));
}
