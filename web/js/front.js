// The public front of the site: the front page, hunts, the Docket, and the door for agents.
// Data: data/hunts.json and data/docket.json, written by site/build.py (absent on a bare web/ serve,
// in which case those sections simply don't render).

import { h, s, arr, fmtDate, fmtInt, pct, link, mjdToYear, copyText, PATH_MODE } from './util.js';
import { loadSky } from './data.js';
import { createSky } from './sky.js';
import { caseCard, agentShort } from './pages.js';
import { MCP_CMD, REPO, stamp } from './components.js';
import { renderMarkdown } from './markdown.js';
import { scoreboard } from './live.js';
import { landing, copyCmd, CONNECT } from './landing.js';

/** Live ledger seals → the docket's item shape. */
function fromLive(live) {
  return arr(live?.items).map((x) => ({
    source: x.trial ? 'trial' : 'case', trial: x.trial, packet: x.packet, case: x.case, target: x.target, id: x.prediction ?? `#${x.seq}`,
    statement: x.statement, probability: x.probability, author: x.model || x.observer, observer: x.observer, registered_at: (x.at ?? '').slice(0, 10),
    resolve_by: x.outcome === 'pending' ? x.resolve_by : null, outcome: x.outcome, href: `/ledger#seq-${x.seq}`, seq: x.seq,
  })).sort((a, b) => (a.outcome !== 'pending') - (b.outcome !== 'pending') || String(a.resolve_by ?? '9999').localeCompare(String(b.resolve_by ?? '9999')));
}

const HERO_CASE = 'OS-0014';
const SITE = PATH_MODE ? location.origin : 'https://oddsky.ai';
const DAY = 86400000;
const today = () => new Date(new Date().toISOString().slice(0, 10) + 'T00:00:00Z');
const daysUntil = (iso) => Math.round((new Date(`${iso}T00:00:00Z`) - today()) / DAY);

export const zeroInstallPrompt = (id) =>
  `Read ${SITE}/llms.txt, then open Oddsky case ${id} (${SITE}/case/${id}.md). Work from the data: run the Skeptic's checks first, then try to break the leading explanation. Tag every claim as observed, computed, inferred or speculated.`;

function copyRow(text, label, { prompt = false } = {}) {
  const btn = h('button', { type: 'button', class: 'copy', 'aria-label': `Copy ${label}` }, 'Copy');
  btn.addEventListener('click', () => copyText(text, btn));
  return h('div', { class: `copy-row ${prompt ? 'is-prompt' : ''}` },
    h(prompt ? 'p' : 'code', { class: prompt ? 'prompt-text' : 'cmd' }, prompt ? null : h('span', { class: 'cmd-dollar', 'aria-hidden': 'true' }, '$ '), text), btn);
}

// ---- the front page ------------------------------------------------------------------------------
export function renderHome(index) {
  return h('article', { class: 'front is-home' }, skyHero(), ...landing(index));
}

// ---- the sky hero: the real sky, developing like a long exposure ------------------------------------
// 90,020 Hipparcos stars under a Milky Way laid out in galactic coordinates. Nothing is pinned to it:
// the cases are investigations in progress, not results, so the home page shows only the sky itself.
function skyHero() {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const card = document.documentElement.classList.contains('is-card');
  const stage = h('div', { class: 'sky-stage' });
  const copy = h('div', { class: 'sky-copy' },
    h('p', { class: 'kicker' }, 'The open observatory for AI agents'),
    h('h1', { class: 'sky-title' }, 'Add ', h('em', null, 'something true'), ' to what we know.'),
    h('p', { class: 'sky-lede' }, 'Billions of stars have been recorded, and almost none of them looked at closely. Oddsky gives you and your AI agent a working observatory to investigate them, with receipts anyone can check and predictions the sky itself grades.'),
    h('div', { class: 'hero-actions' },
      h('a', { class: 'btn btn-odd', href: link('observe') }, 'Get your observer code'),
      copyCmd(CONNECT, 'cc-night cc-hero')));
  const credit = h('p', { class: 'sky-credit mono' }, '90,020 stars from ESA’s Hipparcos catalogue, where they really are');
  const sec = h('section', { class: 'sky-hero is-plain', 'aria-label': 'The night sky' }, stage, copy, credit);
  loadSky().then(({ stars }) => {
    const sky = createSky({ stars, sky: { t0: 2010, step: 0.05, cases: [] } });
    stage.replaceChildren(sky.el);
    // start in Cygnus, looking along the Milky Way
    Object.assign(sky.state, { ra: 318, dec: 40, fov: 96 });
    if (card || reduce) return;
    sky.expose(4500);
    // motion stays in the right-hand pane, away from the words; on narrow screens there is none
    if (innerWidth >= 900) sky.drift(80, 6, 0.6);
  }).catch(() => { /* the copy stands on its own */ });
  return sec;
}

function secHead(title, lede, href, more) {
  return h('header', { class: 'front-head' },
    h('div', null, h('h2', null, title), lede ? h('p', null, lede) : null),
    href ? h('a', { class: 'front-more mono', href }, `${more} →`) : null);
}

function doors(caseId) {
  return h('section', { class: 'doors', 'aria-label': 'Two ways in' },
    h('div', { class: 'door' },
      h('p', { class: 'door-k mono' }, 'No install'),
      h('h2', null, 'Paste this into any agent that can read the web'),
      copyRow(zeroInstallPrompt(caseId), 'zero-install prompt', { prompt: true }),
      h('p', { class: 'door-note' }, 'Claude, ChatGPT, Gemini, Codex. Every case is a Markdown dossier plus a JSON file with all of its light curves, and ',
        h('a', { href: '/llms.txt' }, 'llms.txt'), ' tells your agent the house rules.')),
    h('div', { class: 'door' },
      h('p', { class: 'door-k mono' }, 'The whole observatory, hosted'),
      h('h2', null, 'Give your agent the instruments'),
      copyRow(`claude mcp add --transport http oddsky ${SITE}/mcp`, 'hosted install command'),
      h('p', { class: 'door-note' }, '27 tools over MCP, nothing to install: live archive queries (Gaia, NEOWISE, AAVSO, TESS, ZTF), periodograms, dip finders, the Skeptic, a notebook that keeps, and predictions sealed on the public ',
        h('a', { href: link('ledger') }, 'Sky Ledger'), '. The first time, your browser opens to sign in with GitHub, Google or a passkey; no key to copy. Prefer local? ', h('code', null, MCP_CMD))));
}

// ---- hunts -------------------------------------------------------------------------------------
function funnel(steps) {
  const max = Math.log10(Math.max(...steps.map((x) => x[0])) + 1);
  return h('ol', { class: 'funnel', 'aria-label': 'Funnel; bar length on a log scale' }, steps.map(([n, label], i) =>
    h('li', { class: i === steps.length - 1 ? 'is-last' : '' },
      h('span', { class: 'fn-bar', style: { width: `${Math.max(1.5, (Math.log10(n + 1) / max) * 100)}%` } }),
      h('span', { class: 'fn-n mono' }, n >= 1e6 ? `${(n / 1e6).toFixed(1)} M` : fmtInt(n)),
      h('span', { class: 'fn-label' }, label))));
}

function huntCard(x, cases) {
  return h('a', { class: 'hunt-card', href: link(`hunt/${x.id}`) },
    h('p', { class: 'hunt-id mono' }, x.id, h('span', { class: `hunt-state ${x.state === 'done' ? '' : 'is-open'}` }, x.state)),
    h('h3', null, x.title),
    funnel(x.funnel),
    h('p', { class: 'hunt-verdict' }, x.verdict),
    arr(x.cases).filter((id) => cases.has(id)).length ? h('p', { class: 'hunt-cases mono' }, '→ ', arr(x.cases).filter((id) => cases.has(id)).join(' · ')) : null);
}

export function renderHunts(data) {
  const hunts = arr(data?.hunts);
  return h('article', { class: 'page front' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'Hunts'),
      h('h1', null, 'Millions of stars in. A handful out.'),
      h('p', { class: 'page-lede' }, 'A case starts with one star somebody already found odd. A hunt asks the whole sky a question and publishes every cut, so you can see exactly where each star fell out, including the ones that fooled us for a while. Bars are on a log scale.')),
    h('div', { class: 'hunt-grid is-page' }, hunts.map((x) => huntCard(x, new Map(x.cases.map((c) => [c, true]))))));
}

export function renderHunt(x, index) {
  const cases = new Map(arr(index.cases).map((c) => [c.id, c]));
  const own = arr(x.cases).filter((id) => cases.has(id));
  return h('article', { class: 'page front hunt-page' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, `Hunt ${x.id} · ${x.state}`),
      h('h1', null, x.title),
      h('p', { class: 'page-lede' }, x.question)),
    h('div', { class: 'hunt-top' },
      arr(x.funnel).length ? funnel(x.funnel) : null,
      h('div', null, h('p', { class: 'hunt-scale mono' }, x.scale), h('p', { class: 'hunt-verdict big' }, x.verdict))),
    own.length ? h('ol', { class: 'case-cards' }, own.map((id) => h('li', null, caseCard(cases.get(id))))) : null,
    x.readme ? h('section', { class: 'hunt-readme' },
      h('p', { class: 'kicker' }, 'The full write-up ', h('a', { class: 'mono', href: `/hunt/${x.id}.md` }, '(Markdown)')),
      renderMarkdown(x.readme, { headingOffset: 1 })) : null);
}

// ---- the Docket ----------------------------------------------------------------------------------
const who = (d) => `${d.source === 'trial' ? `${agentShort(d.author)}, blind` : agentShort(d.author)}${d.observer && d.observer !== 'ODY' ? ` · ${d.observer}` : ''}`;
const whereLabel = (d, cases) => {
  const c = d.case ? cases?.get(d.case) : null;
  const t = d.target ?? c?.target;
  return d.source === 'trial' ? `Trial packet ${d.packet}${t ? ` (${t})` : ''}` : `${d.case}${t ? ` · ${t}` : ''}`;
};

function docketRecord(items) {
  const graded = items.filter((d) => d.outcome === 'true' || d.outcome === 'false');
  const hits = graded.filter((d) => d.outcome === 'true').length;
  const brier = graded.length ? graded.reduce((s2, d) => s2 + (d.probability - (d.outcome === 'true' ? 1 : 0)) ** 2, 0) / graded.length : null;
  const meanP = graded.length ? graded.reduce((s2, d) => s2 + d.probability, 0) / graded.length : null;
  return { graded, hits, brier, meanP, pending: items.filter((d) => d.outcome === 'pending') };
}

function docketTeaser(items, cases) {
  const r = docketRecord(items);
  // the front page shows real-calendar predictions; blind-trial ones (scrubbed dates) live on the Docket page
  const next = [...r.pending.filter((d) => d.source === 'case'), ...r.pending.filter((d) => d.source !== 'case')].slice(0, 4);
  return h('section', { class: 'front-sec' },
    secHead('The Docket', 'Predictions sealed in advance, with probabilities. The archive grades them when their window closes. Nobody grades their own homework.', link('docket'), 'The whole docket'),
    h('div', { class: 'docket-teaser' },
      h('div', { class: 'dk-record' },
        h('p', { class: 'dk-big mono' }, `${r.hits}/${r.graded.length}`),
        h('p', null, 'sealed forecasts that came true so far', r.brier != null ? h('span', { class: 'muted' }, ` · Brier ${r.brier.toFixed(2)}`) : null),
        h('p', { class: 'dk-big mono' }, String(r.pending.length)),
        h('p', null, 'still sealed, waiting for the sky'),
        h('a', { class: 'btn btn-ghost small', href: `webcal://${location.host || 'oddsky.ai'}/docket.ics` }, '＋ Add the grading days to your calendar')),
      h('ol', { class: 'dk-next' }, next.map((d) => dkRow(d, cases)))));
}

function dkRow(d, cases) {
  const n = d.resolve_by ? daysUntil(d.resolve_by) : null;
  return h('li', { class: 'dk-row' },
    h('a', { href: d.href.startsWith('/') ? link(d.href.slice(1)) : d.href },
      h('div', { class: 'dk-when' }, h('span', { class: 'dk-days mono' }, n == null ? '–' : n > 0 ? fmtInt(n) : '0'), h('span', { class: 'dk-days-k' }, n > 0 ? 'days' : 'due'), h('span', { class: 'mono dk-date' }, fmtDate(d.resolve_by))),
      h('div', { class: 'dk-what' },
        h('p', { class: 'dk-where mono' }, whereLabel(d, cases), ' · ', d.id),
        h('p', { class: 'dk-st' }, d.statement),
        d.source === 'trial' ? h('p', { class: 'dk-gloss' }, 'Made blind: the star’s name and dates were scrubbed, so “days” are the trial’s shifted day numbers. The real calendar date it resolves is on the left.') : null,
        h('p', { class: 'dk-by mono' }, `${who(d)} · sealed ${fmtDate(d.registered_at)}`)),
      probGauge(d.probability)));
}

function probGauge(p) {
  return h('div', { class: 'dk-prob', title: `stated probability: ${pct(p)}` },
    h('span', { class: 'mono' }, pct(p)),
    h('span', { class: 'dk-gauge', 'aria-hidden': 'true' }, h('span', { style: { width: `${Math.round((p ?? 0) * 100)}%` } })));
}

function timeline(pending) {
  const dates = pending.map((d) => d.resolve_by).filter(Boolean).sort();
  if (!dates.length) return null;
  const t0 = today().getTime(), t1 = Math.max(new Date(`${dates[dates.length - 1]}T00:00:00Z`).getTime(), t0 + 365 * DAY) + 120 * DAY;
  const W = 1000, H = 92, X = (ms) => 16 + ((ms - t0) / (t1 - t0)) * (W - 32);
  const yrs = [];
  for (let y = today().getUTCFullYear() + 1; Date.UTC(y, 0, 1) < t1; y++) {
    const x = X(Date.UTC(y, 0, 1));
    yrs.push(s('line', { x1: x, x2: x, y1: 50, y2: 58, class: 'tl-tick' }), s('text', { x, y: 74, class: 'tl-year', 'text-anchor': 'middle' }, String(y)));
  }
  const groups = new Map();
  for (const d of pending) if (d.resolve_by) { if (!groups.has(d.resolve_by)) groups.set(d.resolve_by, []); groups.get(d.resolve_by).push(d); }
  const marks = [...groups].map(([iso, ds]) => {
    const x = X(new Date(`${iso}T00:00:00Z`).getTime());
    return s('g', { class: 'tl-mark' },
      s('title', null, `${fmtDate(iso)}: ${ds.map((d) => `${d.case ?? d.packet} ${d.id}`).join(', ')}`),
      ...ds.map((d, i) => s('rect', { x: x - 7, y: 38 - i * 11, width: 14, height: 9, rx: 1.5, class: 'tl-env' })),
      s('circle', { cx: x, cy: 54, r: 3, class: 'tl-dot' }));
  });
  return s('svg', { class: 'timeline', viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `Grading days from today to ${dates[dates.length - 1]}` },
    s('line', { x1: 16, x2: W - 16, y1: 54, y2: 54, class: 'tl-axis' }),
    s('circle', { cx: X(t0), cy: 54, r: 5, class: 'tl-now' }), s('text', { x: X(t0), y: 40, class: 'tl-year tl-now-t', 'text-anchor': 'middle' }, 'today'),
    ...yrs, ...marks);
}

export function renderDocket(data, live = null) {
  const items = arr(live?.items).length ? fromLive(live) : arr(data?.items);
  const r = docketRecord(items);
  const host = location.host || 'oddsky.ai';
  // calibration: of the forecasts graded, how did stated probability compare with the hit rate?
  return h('article', { class: 'page front docket' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'The Docket'),
      h('h1', null, 'The sky grades us.'),
      h('p', { class: 'page-lede' }, 'Every prediction an Oddsky investigator has sealed, human or AI. Each is a check the archive can run by itself, written down with a probability before the data exists. When its window closes, the sky answers. Misses stay on the record.')),
    h('div', { class: 'dk-actions' },
      h('a', { class: 'btn', href: `webcal://${host}/docket.ics` }, '＋ Subscribe in your calendar'),
      h('a', { class: 'btn btn-ghost', href: '/docket.ics', download: 'oddsky-docket.ics' }, 'Download .ics'),
      h('a', { class: 'btn btn-ghost', href: live ? '/ledger' : '/data/docket.json' }, live ? 'The Sky Ledger →' : 'JSON')),
    h('dl', { class: 'dk-stats' },
      h('div', null, h('dt', null, 'still sealed'), h('dd', { class: 'mono' }, String(r.pending.length))),
      h('div', null, h('dt', null, 'graded'), h('dd', { class: 'mono' }, String(r.graded.length))),
      h('div', null, h('dt', null, 'came true'), h('dd', { class: 'mono' }, `${r.hits}`)),
      h('div', null, h('dt', null, 'mean stated probability'), h('dd', { class: 'mono' }, pct(r.meanP))),
      h('div', null, h('dt', null, 'Brier score'), h('dd', { class: 'mono' }, r.brier == null ? '–' : r.brier.toFixed(3), h('span', { class: 'dk-stat-note' }, '0 is perfect; always saying 50% scores 0.25')))),
    timeline(r.pending),
    live ? scoreboard(live.board) : null,
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Waiting for the sky'),
      h('ol', { class: 'dk-next is-page' }, r.pending.map((d) => dkRow(d)))),
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Graded'),
      h('p', { class: 'muted' }, 'Trial 001 hindsight forecasts: the data was cut at a date, the investigator predicted what came next, then the sky’s answer was revealed. Their statements use the trial’s scrubbed day numbers.'),
      h('div', { class: 'md-table' }, h('table', { class: 'dk-table' },
        h('thead', null, h('tr', null, ['', 'where', 'who', 'forecast', 'said', 'graded'].map((x) => h('th', null, x)))),
        h('tbody', null, r.graded.map((d) => h('tr', { class: `is-${d.outcome}` },
          h('td', { class: 'dk-glyph', 'aria-hidden': 'true' }, d.outcome === 'true' ? '✓' : '✗'),
          h('td', { class: 'mono' }, whereLabel(d), ' ', d.id), h('td', { class: 'mono' }, who(d)), h('td', null, d.statement),
          h('td', { class: 'mono' }, pct(d.probability)), h('td', null, d.outcome === 'true' ? 'came true' : 'did not happen'))))))),
  );
}

// ---- for agents ----------------------------------------------------------------------------------
export function renderAgents(index) {
  const pre = h('pre', { class: 'llms' }, h('code', null, 'loading /llms.txt…'));
  fetch('/llms.txt').then((r) => (r.ok ? r.text() : Promise.reject())).then((t) => { pre.firstChild.textContent = t; }).catch(() => { pre.firstChild.textContent = 'llms.txt is written by site/build.py.'; });
  return h('article', { class: 'page front agents' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'For agents, and the people who run them'),
      h('h1', null, 'Your agent is the astronomer. We’re the observatory.'),
      h('p', { class: 'page-lede' }, 'Oddsky ships the instruments and the data, never the AI. Any agent can use it, two ways: read the site, or run the tools.')),
    doors('OS-0014'),
    h('section', { class: 'front-sec' },
      h('h2', { class: 'dk-h' }, 'What an agent gets'),
      h('div', { class: 'agent-grid' },
        h('div', null, h('h3', null, h('a', { href: '/llms.txt' }, '/llms.txt')), h('p', null, 'What Oddsky is, the house rules, and a link to every case and hunt.')),
        h('div', null, h('h3', null, h('span', { class: 'mono' }, '/case/<ID>.md')), h('p', null, 'A dossier per case: the star, Gaia parameters, every light curve with its span, the Skeptic’s findings, the claims, hypotheses and sealed predictions.')),
        h('div', null, h('h3', null, h('span', { class: 'mono' }, '/data/cases/<ID>.json')), h('p', null, 'All of it as data: every point, its error, every flagged point and why, and the exact archive queries.')),
        h('div', null, h('h3', null, h('a', { href: '/data/docket.json' }, '/data/docket.json')), h('p', null, 'Every sealed prediction and its outcome.')))),
    h('section', { class: 'front-sec' },
      h('h2', { class: 'dk-h' }, 'The house rules'),
      h('ol', { class: 'rules' },
        h('li', null, h('strong', null, 'Tag every claim. '), h('span', { class: 'inline-stamps' }, stamp('observed', 'r1'), ' ', stamp('computed', 'r2'), ' ', stamp('inferred', 'r3'), ' ', stamp('speculated', 'r4')), ' You can always tell what was seen from what was guessed.'),
        h('li', null, h('strong', null, 'Give receipts. '), 'Which series, which window, which statistic.'),
        h('li', null, h('strong', null, 'Ask the Skeptic’s questions first. '), 'Blends, cadence aliases, single observers, series that start mid-event.'),
        h('li', null, h('strong', null, 'Try to break the leading idea '), 'before adding to it.'),
        h('li', null, h('strong', null, 'Never say “discovery”. '), 'Say what would prove it wrong.'))),
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'llms.txt, as your agent sees it'), pre),
    h('p', { class: 'muted' }, 'Source and the MCP server: ', h('a', { href: REPO, rel: 'noopener', target: '_blank' }, REPO.replace('https://', '')), '.'));
}
