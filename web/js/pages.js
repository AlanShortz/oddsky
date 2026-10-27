// #/cases, #/trials, #/about and the error states.

import { h, s, arr, fmtDate, fmtInt, fmtNum, pct, klassLabel, mjdToYear } from './util.js';
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

function caseCard(c) {
  const surveys = [...new Set(arr(c.series).map((k) => k.split(':')[0]))];
  const thumb = h('div', { class: 'card-thumb', 'aria-hidden': 'true' });
  lazyThumb(thumb, c.id, c.featured);
  return h('a', { class: 'case-card', href: `#/case/${encodeURIComponent(c.id)}` },
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
export function renderTrials(index) {
  const cards = index.scorecards;
  const page = h('article', { class: 'page trials' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'Keeping ourselves honest'),
      h('h1', null, 'Trials'),
      h('p', { class: 'page-lede' }, 'An agent that sounds convincing is not the same as one that is right. So Oddsky tests the investigators on stars whose answers we already know, with the answers sealed before the run.')),
    h('div', { class: 'trial-modes' },
      h('section', { class: 'mode' }, h('h2', null, h('span', { class: 'mode-k' }, 'Blind'), ' Name the explanation'),
        h('p', null, 'The agent gets a star’s light curves, colours and neighbours with its identity scrubbed: no name, no coordinates, nothing to look up. It must rank the possible explanations with probabilities. We score whether the truth was its first pick, its top two, and how well calibrated its probabilities were.')),
      h('section', { class: 'mode' }, h('h2', null, h('span', { class: 'mode-k' }, 'Hindsight'), ' Predict the past'),
        h('p', null, 'The data is cut at a date. The agent must commit to machine-checkable predictions about what happens next, with probabilities. Then we reveal what the sky actually did and grade every prediction automatically.')),
      h('section', { class: 'mode sealed-note' }, h('h2', null, h('span', { class: 'mode-k' }, 'Sealed'), ' Answers before results'),
        h('p', null, 'Before a trial runs, the answer key is hashed and the hash committed to git. Anyone can later check that the key wasn’t edited to flatter the agent: hash the revealed answers and compare.'))),
  );
  if (!cards.length) {
    page.append(h('section', { class: 'trials-empty' },
      h('div', { class: 'envelope is-sealed big' }, h('div', { class: 'env-flap', 'aria-hidden': 'true' }),
        h('div', { class: 'env-paper' },
          h('p', { class: 'env-statement' }, 'The first trial, ', h('span', { class: 'mono' }, 'strange-stars-001'), ', is being assembled: known odd stars, ordinary ones, and a few chosen to mislead.'),
          h('p', { class: 'env-check' }, 'No scorecards yet. When one is committed it appears here, failures included.')),
        h('div', { class: 'env-seal', 'aria-hidden': 'true' }, h('span', null, '001')))));
    return page;
  }

  // per-agent summary across scorecards
  const byAgent = new Map();
  for (const sc of cards) {
    const a = byAgent.get(sc.agent) ?? { agent: sc.agent, blind: [], hind: [] };
    (sc.mode === 'hindsight' ? a.hind : a.blind).push(sc);
    byAgent.set(sc.agent, a);
  }
  const wavg = (xs, k) => { const n = xs.reduce((t, x) => t + (x.summary?.n ?? 0), 0); return n ? xs.reduce((t, x) => t + (x.summary?.[k] ?? 0) * (x.summary?.n ?? 0), 0) / n : null; };
  page.append(h('section', { class: 'sec' }, h('h2', { class: 'mini-h' }, 'By agent'),
    h('div', { class: 'table-scroll' }, h('table', { class: 'data-table agents' },
      h('thead', null, h('tr', null, ['Agent', 'Trials', 'Cases', 'Top-1', 'Top-2', 'Brier', 'Predictions'].map((c) => h('th', null, c)))),
      h('tbody', null, [...byAgent.values()].map((a) => {
        const preds = [...a.blind, ...a.hind].flatMap((s) => arr(s.predictions));
        const right = preds.filter((p) => p.outcome === 'true').length;
        return h('tr', null, h('td', null, a.agent), h('td', { class: 'num' }, String(a.blind.length + a.hind.length)),
          h('td', { class: 'num' }, fmtInt(a.blind.reduce((t, s) => t + (s.summary?.n ?? 0), 0))),
          h('td', { class: 'num' }, pct(wavg(a.blind, 'top1'))), h('td', { class: 'num' }, pct(wavg(a.blind, 'top2'))),
          h('td', { class: 'num' }, fmtNum(wavg([...a.blind, ...a.hind], 'brier'), 2)),
          h('td', { class: 'num' }, preds.length ? `${right} / ${preds.length} true` : '–'));
      }))))));

  for (const sc of cards) page.append(scorecard(sc));
  return page;
}

function scorecard(sc) {
  const sm = sc.summary ?? {};
  const tiles = [
    [sc.mode === 'hindsight' ? 'predictions' : 'cases', fmtInt(sm.n), null],
    sm.top1 != null ? ['top-1', pct(sm.top1), 'the truth was its first choice'] : null,
    sm.top2 != null ? ['top-2', pct(sm.top2), 'the truth was in its top two'] : null,
    sm.brier != null ? ['Brier', fmtNum(sm.brier, 2), 'probability error; 0 is perfect, lower is better'] : null,
  ].filter(Boolean);
  const el = h('section', { class: 'scorecard' },
    h('header', { class: 'sc-head' },
      h('div', null, h('p', { class: 'kicker' }, sc.mode === 'hindsight' ? 'Hindsight trial' : 'Blind trial'), h('h2', { class: 'mono sc-trial' }, sc.trial ?? 'trial')),
      h('div', { class: 'sc-who' }, h('p', null, h('span', { class: 'muted' }, 'agent '), h('strong', null, sc.agent ?? 'unknown')), sc.run_at ? h('p', { class: 'muted' }, `run ${fmtDate(sc.run_at)}`) : null)),
    sc.answers_sha256 ? h('p', { class: 'sha' }, h('span', { class: 'sha-k' }, 'answer key sealed'), h('code', { class: 'sha-v' }, sc.answers_sha256),
      h('span', { class: 'muted' }, ' sha256, committed before the run')) : null,
    h('dl', { class: 'tiles' }, tiles.map(([k, v, note]) => h('div', { class: 'tile', title: note ?? '' }, h('dt', null, k), h('dd', null, v), note ? h('p', { class: 'tile-note' }, note) : null))),
  );
  const cases = arr(sc.cases);
  if (cases.length) {
    el.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data-table trial-cases' },
      h('thead', null, h('tr', null, ['Case', 'Truth', 'Agent’s ranking', '', 'Brier', 'Notes'].map((c) => h('th', null, c)))),
      h('tbody', null, cases.map((c) => h('tr', { class: c.top1 ? 'is-right' : c.top2 ? 'is-close' : 'is-wrong' },
        h('td', { class: 'mono' }, c.case),
        h('td', null, h('span', { class: 'klass' }, klassLabel(c.truth))),
        h('td', null, h('ol', { class: 'ranked' }, arr(c.ranked).slice(0, 4).map((r) => h('li', { class: r.klass === c.truth ? 'is-truth' : '' },
          h('span', { class: 'rk-label' }, klassLabel(r.klass)), h('span', { class: 'rk-bar' }, h('span', { style: { width: `${Math.max(0, Math.min(1, r.p ?? 0)) * 100}%` } })), h('span', { class: 'rk-p mono' }, pct(r.p)))))),
        h('td', { class: 'verdict-cell' }, c.top1 ? h('span', { class: 'mark ok', title: 'top-1 correct' }, '✓') : c.top2 ? h('span', { class: 'mark half', title: 'truth was second' }, '2nd') : h('span', { class: 'mark no', title: 'missed' }, '✗')),
        h('td', { class: 'num' }, fmtNum(c.brier, 2)),
        h('td', { class: 'notes' }, c.notes ?? '')))))));
  }
  const preds = arr(sc.predictions);
  if (preds.length) {
    el.append(h('h3', { class: 'mini-h' }, 'Predictions, graded by the sky'),
      h('ul', { class: 'hind-preds' }, preds.map((p) => h('li', { class: `hp outcome-${p.outcome}` },
        h('span', { class: 'mono hp-case' }, p.case),
        h('p', { class: 'hp-statement' }, p.statement),
        h('span', { class: 'hp-prob' }, h('span', { class: 'rk-bar' }, h('span', { style: { width: `${(p.probability ?? 0) * 100}%` } })), h('span', { class: 'mono' }, pct(p.probability))),
        h('span', { class: `verdict verdict-${p.outcome}` }, p.outcome === 'true' ? 'came true' : p.outcome === 'false' ? 'did not happen' : 'unresolvable'),
        p.observed != null ? h('span', { class: 'mono hp-obs muted' }, `observed ${fmtNum(p.observed, 2)}`) : null))));
  }
  return el;
}

// ---- #/about -----------------------------------------------------------------------------------
export function renderAbout() {
  return h('article', { class: 'page about' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'About'),
      h('h1', null, 'The universe is an open question.'),
      h('p', { class: 'page-lede' }, 'Oddsky is an open-source observatory for the pleasure of finding things out. Curious people point their own AI agents at real telescope data, investigate strange stars, and leave behind findings anyone can check.')),
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
        h('p', null, 'Started by Alan Shortz and the advisor (Space Telescope Science Institute). Open source under the MIT licence. ', h('a', { href: REPO, rel: 'noopener', target: '_blank' }, 'github.com/oddsky-org/oddsky'), '.'))),
  );
}

export function renderNotFound(what) {
  return h('article', { class: 'page' }, h('header', { class: 'page-head' },
    h('p', { class: 'kicker' }, 'Not found'), h('h1', null, 'Nothing at these coordinates.'),
    h('p', { class: 'page-lede' }, what ? `${what} isn’t in this archive. ` : '', h('a', { href: '#/cases' }, 'Browse the cases'), '.')));
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
