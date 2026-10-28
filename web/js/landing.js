// The landing page below the sky: what Oddsky is for, what the platform does, and how to start.
// Each pillar carries a small live vignette (a terminal, a coverage chart, a claim, a funnel, the
// ledger) instead of a screenshot, so the page shows the product working rather than describing it.

import { h, s, arr, link, copyText } from './util.js';
import { stamp } from './components.js';
import { whoami } from './live.js';

const SITE = location.origin.includes('localhost') ? 'https://oddsky.ai' : location.origin;
export const CONNECT = `claude mcp add --transport http oddsky ${SITE}/mcp`;
const reduce = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Run fn once when el scrolls into view. */
function onView(el, fn, margin = '0px 0px -15% 0px') {
  if (!('IntersectionObserver' in window)) { fn(); return; }
  const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { io.disconnect(); fn(); } }, { rootMargin: margin });
  io.observe(el);
}

export function copyCmd(text, cls = '') {
  const b = h('button', { type: 'button', class: 'cc-btn', 'aria-label': 'Copy command' }, 'Copy');
  b.addEventListener('click', () => copyText(text, b));
  return h('div', { class: `cc ${cls}` }, h('code', null, h('span', { class: 'cc-dollar', 'aria-hidden': 'true' }, '$ '), text), b);
}

/** "Get your observer code", or, once signed in, the way back to your own observatory. */
export function observerCta() {
  const a = h('a', { class: 'btn btn-odd', href: link('observe') }, 'Get your observer code');
  whoami().then((o) => {
    if (!o) return;
    a.replaceChildren(h('span', { class: 'cta-code mono', 'aria-hidden': 'true' }, o.code), 'Your observatory');
    a.setAttribute('aria-label', `Your observatory, observer ${o.code}`);
  });
  return a;
}

// ---- why ------------------------------------------------------------------------------------------
function why() {
  const p = (...k) => h('p', { class: 'vz-p' }, ...k);
  const sec = h('section', { class: 'vision', 'aria-labelledby': 'vz-h' },
    h('div', { class: 'vz-inner' },
      h('p', { class: 'kicker' }, 'Why Oddsky'),
      h('h2', { id: 'vz-h', class: 'vz-h' }, 'The sky has been recorded. ', h('span', null, 'Almost none of it has been looked at.')),
      p('For most of history astronomy was limited by light: how much a telescope could gather, and how often it could look. That limit has quietly fallen. Gaia has charted 1.8 billion stars. NEOWISE photographed the whole sky every six months for a decade. ZTF, ATLAS and TESS watch it night after night, and nearly all of it is public.'),
      p('What is scarce now is attention. Most of that record has never been looked at closely by anyone, and whatever is in it stays unknown until someone does.'),
      p('Oddsky is an open-source observatory built to supply that attention. A curious person, using an AI agent as the instrument, can look closely at stars no one has examined and leave behind work that others can check. The tools make attention cheap, so what matters now is where it is directed, and how honestly.'),
      h('p', { class: 'vz-aim' }, 'The question Oddsky exists to ask: can an interested amateur, armed with increasingly capable AI, add something true to what is known?'),
      h('figure', { class: 'vz-quote' }, h('blockquote', null, '“The prize is the pleasure of finding the thing out, the kick in the discovery, the observation that other people use it. Those are the real things.”'), h('figcaption', null, 'Richard P. Feynman')),
      h('dl', { class: 'vz-stats' },
        h('div', null, h('dt', null, 'stars charted by Gaia'), h('dd', { class: 'mono' }, '1.8 billion')),
        h('div', null, h('dt', null, 'years NEOWISE mapped the whole sky in the infrared, twice a year'), h('dd', { class: 'mono' }, '10')),
        h('div', null, h('dt', null, 'alerts a night the Rubin Observatory is designed to send'), h('dd', { class: 'mono' }, '~10 million')))));
  if ('IntersectionObserver' in window && !reduce()) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('is-lit'); io.unobserve(e.target); } }), { rootMargin: '0px 0px -18% 0px' });
    sec.querySelectorAll('.vz-h, .vz-p, .vz-aim, .vz-quote, .vz-stats').forEach((x) => { x.classList.add('vz-dim'); io.observe(x); });
  }
  return sec;
}

// ---- vignette: an agent at work ------------------------------------------------------------------------
const SESSION = [
  ['cmd', CONNECT],
  ['ok', '✓ oddsky connected · signed in as observer ASH'],
  ['you', 'Something odd about this star? Open a case, run the Skeptic first, then try to break your best explanation.'],
  ['tool', 'open_case', 'fetched Gaia, NEOWISE, AAVSO, ZTF, ATLAS, TESS', 'K1'],
  ['tool', 'skeptic_report', '11 checks · 9 pass · 2 warn (blend, single observer)', 'K2'],
  ['tool', 'find_excursions', 'ZTF:g · 1 dip, 1.8 mag, 14 days', 'K3'],
  ['tool', 'cross_band', 'deeper in g than r: small grains', 'K4'],
  ['claim', 'computed', 'The dip is chromatic, as dust is, not grey as an eclipsing star would be.', 'K3, K4'],
  ['tool', 'register_prediction', 'p = 0.7 · sealed on the Sky Ledger', 'K5'],
];

function terminal() {
  const body = h('div', { class: 'term-body', role: 'log', 'aria-label': 'An illustrative agent session' });
  const el = h('figure', { class: 'term' },
    h('div', { class: 'term-bar' }, h('i'), h('i'), h('i'), h('span', { class: 'mono' }, 'claude — an illustrative session')), body);
  const line = (x) => {
    if (x[0] === 'cmd') return h('p', { class: 'tl tl-cmd' }, h('span', { class: 'tl-p' }, '$ '), x[1]);
    if (x[0] === 'ok') return h('p', { class: 'tl tl-ok' }, x[1]);
    if (x[0] === 'you') return h('p', { class: 'tl tl-you' }, h('span', { class: 'tl-p' }, '> '), x[1]);
    if (x[0] === 'claim') return h('p', { class: 'tl tl-claim' }, h('span', { class: 'tl-k' }, '⏺ add_claim '), stamp(x[1], 'term'), ' ', x[2], h('span', { class: 'tl-r' }, ` ← ${x[3]}`));
    return h('p', { class: 'tl tl-tool' }, h('span', { class: 'tl-k' }, `⏺ oddsky · ${x[1]}`), h('span', { class: 'tl-out' }, ` ${x[2]}`), h('span', { class: 'tl-r' }, ` ${x[3]}`));
  };
  const all = () => body.replaceChildren(...SESSION.map(line));
  if (reduce()) all();
  else onView(el, async () => {
    for (const x of SESSION) {
      const n = line(x); n.classList.add('tl-in'); body.append(n);
      await new Promise((r) => setTimeout(r, x[0] === 'cmd' ? 900 : x[0] === 'you' ? 1100 : 520));
    }
  });
  return el;
}

// ---- vignette: a century of sky, on one time axis -------------------------------------------------------
const ARCHIVES = [
  ['AAVSO', 1911, 2026.8, 'amateur observers, a century of light curves'],
  ['ASAS-SN', 2013, 2026.8, 'the whole sky, every night'],
  ['NEOWISE', 2013.9, 2024.6, 'infrared, whole sky twice a year'],
  ['Gaia', 2014.6, 2017.4, 'epoch photometry for millions of variables'],
  ['ATLAS', 2015.5, 2026.8, 'whole sky, several times a night'],
  ['ZTF', 2018.2, 2025.7, 'the northern sky, deep (public releases)'],
  ['TESS', 2018.6, 2026.8, '27-day stares at minute cadence'],
];
function coverage() {
  const T0 = 1905, T1 = 2027, W = 560, rowH = 30, top = 8;
  const X = (t) => 92 + ((t - T0) / (T1 - T0)) * (W - 100);
  const svg = s('svg', { class: 'cov', viewBox: `0 0 ${W} ${top + ARCHIVES.length * rowH + 30}`, role: 'img', 'aria-label': 'When each archive Oddsky reads was recording' });
  [1920, 1960, 2000, 2020].forEach((y) => svg.append(s('line', { x1: X(y), x2: X(y), y1: top - 4, y2: top + ARCHIVES.length * rowH, class: 'cov-grid' }),
    s('text', { x: X(y), y: top + ARCHIVES.length * rowH + 18, class: 'cov-yr', 'text-anchor': 'middle' }, String(y))));
  ARCHIVES.forEach(([name, a, b, note], i) => {
    const y = top + i * rowH;
    svg.append(s('text', { x: 84, y: y + 17, class: 'cov-name', 'text-anchor': 'end' }, name),
      s('rect', { x: X(a), y: y + 7, width: Math.max(4, X(b) - X(a)), height: 14, rx: 3, class: 'cov-bar', style: `--d:${i * 90}ms` }, s('title', null, `${name}: ${note}`)));
  });
  const el = h('figure', { class: 'vig cov-wrap' }, svg,
    h('figcaption', { class: 'vig-cap' }, 'Every archive a star has been seen in, on one time axis. Your agent asks; Oddsky fetches, cleans and records exactly which rows it used.'));
  onView(el, () => el.classList.add('is-on'));
  return el;
}

// ---- vignette: a claim with its receipts ------------------------------------------------------------------
function claimCard() {
  const r = (k) => h('span', { class: 'rcpt mono' }, k);
  return h('figure', { class: 'vig claim-vig' },
    h('div', { class: 'cv-row' }, h('span', { class: 'mono cv-id' }, 'C7'), stamp('computed', 'cv1'),
      h('p', null, 'Between the two visits W1 brightened by 0.31 mag while the optical stayed flat to 0.01 mag. ', r('K12'), ' ', r('K14'))),
    h('div', { class: 'cv-row' }, h('span', { class: 'mono cv-id' }, 'C8'), stamp('inferred', 'cv2'),
      h('p', null, 'Warm dust appeared that is not in our line of sight. ', r('C7'))),
    h('div', { class: 'cv-row' }, h('span', { class: 'mono cv-id' }, 'C9'), stamp('speculated', 'cv3'),
      h('p', null, 'A collision between planetary bodies. What would rule it out: no dimming within five years.')),
    h('div', { class: 'cv-skeptic' },
      h('p', { class: 'mono' }, h('b', { class: 'ok' }, '✓'), ' no brighter neighbour inside the beam'),
      h('p', { class: 'mono' }, h('b', { class: 'warn' }, '!'), ' one observer supplies 94% of the optical points'),
      h('p', { class: 'mono' }, h('b', { class: 'ok' }, '✓'), ' period is not a survey-cadence alias')),
    h('figcaption', { class: 'vig-cap' }, 'An example. Every claim says how it is known. Every number links to the tool call that produced it, and anyone can replay the ledger. The Skeptic is code, so it can’t be talked out of a warning.'));
}

// ---- vignette: a hunt funnel ---------------------------------------------------------------------------------
const FUNNEL = [[176900000, 'stars read'], [18100000, 'steady enough to test'], [224, 'flagged'], [43, 'not a blend or a pair'], [6, 'pass vetting'], [2, 'in no catalogue']];
function funnelVig() {
  const max = Math.log10(FUNNEL[0][0]);
  const el = h('figure', { class: 'vig fun-vig' },
    h('ol', { class: 'funnel' }, FUNNEL.map(([n, l], i) => h('li', { class: i === FUNNEL.length - 1 ? 'is-last' : '', style: { '--d': `${i * 120}ms` } },
      h('span', { class: 'fn-bar', style: { width: `${Math.max(2, (Math.log10(n + 1) / max) * 100)}%` } }),
      h('span', { class: 'fn-n mono' }, n >= 1e6 ? `${(n / 1e6).toFixed(1)} M` : n.toLocaleString('en-US')), h('span', { class: 'fn-label' }, l)))),
    h('figcaption', { class: 'vig-cap' }, 'One hunt: 146.6 billion infrared measurements, read in under two hours for a few dollars. Every cut is published, including the stars that fooled us for a while. ', h('a', { href: link('hunts') }, 'See the hunts →')));
  onView(el, () => el.classList.add('is-on'));
  return el;
}

// ---- vignette: the Sky Ledger ---------------------------------------------------------------------------------
function ledgerVig() {
  // the real last three entries of the Sky Ledger, then an empty slot for yours
  const chain = h('ol', { class: 'chain' });
  const el = h('figure', { class: 'vig led-vig' }, chain,
    h('figcaption', { class: 'vig-cap' }, 'Live: the latest entries on the Sky Ledger. Predictions are sealed before the data exists, on a public hash chain anyone can re-verify in their browser, and the archives grade them when their window closes. Nobody grades their own homework. ', h('a', { href: link('ledger') }, 'Open the Sky Ledger →')));
  const blk = (n, kind, text, p, hash, i, next = false) => h('li', { class: `blk ${next ? 'is-next' : ''}`, style: { '--d': `${i * 220}ms` } },
    h('p', { class: 'blk-h mono' }, h('b', null, n), ` ${kind}`), h('p', { class: 'blk-t' }, text), h('p', { class: 'blk-f mono' }, h('span', null, p), h('span', null, hash)));
  fetch('/api/ledger?limit=5000').then((r) => r.json()).then((d) => {
    const es = arr(d.entries).slice(-3);
    const short = (t) => (t.length > 70 ? `${t.slice(0, 68)}…` : t);
    chain.replaceChildren(...es.map((e, i) => {
      const b = JSON.parse(e.body);
      return blk(`#${e.seq}`, b.kind, short(b.kind === 'seal' ? `${b.target && b.target.length < 18 ? b.target : b.case}: ${b.statement}` : `${b.outcome} · ${b.note ?? ''}`), b.kind === 'seal' ? `${Math.round(b.probability * 100)}%` : '', e.hash.slice(0, 8), i);
    }), blk(`#${(d.head?.seq ?? 0) + 1}`, 'yours', 'your next prediction', '?', '········', es.length, true));
    onView(el, () => el.classList.add('is-on'));
  }).catch(() => el.remove());
  return el;
}

// ---- vignette: open by default --------------------------------------------------------------------------------
function openVig() {
  const tree = [
    ['cases/OS-0042/', ''],
    ['  case.yaml', 'the argument: claims, hypotheses, predictions'],
    ['  data/*.parquet', 'the evidence, one file per survey'],
    ['  ledger.jsonl', 'every tool call, with a digest of its result'],
    ['  investigations/', 'write-ups, one per investigator'],
    ['  reviews/', 'referees, human or AI, trying to break it'],
  ];
  return h('figure', { class: 'vig open-vig' },
    h('div', { class: 'tree mono' }, tree.map(([a, b]) => h('p', null, h('span', null, a), b ? h('span', { class: 'tree-c' }, `# ${b}`) : null))),
    h('div', { class: 'agents-row' }, ['Claude Code', 'Codex', 'Cursor', 'Claude Desktop', 'any MCP client', 'a local model'].map((x) => h('span', { class: 'agent-chip' }, x))),
    h('figcaption', { class: 'vig-cap' }, 'A case is a directory in git. Disagree? Fork it. Contribute? Open a pull request. MIT licensed, and Oddsky ships the instruments, never the AI: bring whichever agent you trust.'));
}

// ---- the pillars ------------------------------------------------------------------------------------------------
const PILLARS = [
  { k: 'Instruments', h: 'Your agent is the instrument.', p: 'Connect any AI agent to a working observatory in one line: live archive queries, periodograms, dip finders, colour and infrared analysis, a notebook that keeps. No install, no account wrangling, no API keys.', v: terminal },
  { k: 'Archives', h: 'A century of sky, on one time axis.', p: 'Every major public survey that has watched a star, fetched, quality-cut and lined up together, from photographic-era amateur estimates to last night’s survey frames.', v: coverage },
  { k: 'Receipts', h: 'Show your work. Then try to break it.', p: 'Claims are tagged observed, computed, inferred or speculated. Numbers carry receipts. A deterministic Skeptic asks the boring questions before anyone gets excited, and referees, human or AI, are invited to tear it down.', v: claimCard },
  { k: 'Hunts', h: 'Ask the whole sky a question.', p: 'Go beyond one star: sweep hundreds of millions of them for a signature, publish every cut of the funnel, and hand the few survivors to careful investigation.', v: funnelVig },
  { k: 'The Sky Ledger', h: 'Let the universe grade you.', p: 'A good explanation risks something. Seal a machine-checkable prediction with a probability, and the sky answers when new data arrives. Calibration, for people and for models, accumulates on a public scoreboard.', v: ledgerVig },
  { k: 'Open', h: 'Open all the way down.', p: 'Cases are directories, review is a pull request, and the code is MIT licensed. Your observer code credits your work, the way AAVSO has credited its observers for a century.', v: openVig },
];

function pillars() {
  return h('section', { class: 'pillars', 'aria-label': 'What Oddsky does' },
    h('header', { class: 'pl-head' }, h('p', { class: 'kicker' }, 'The platform'),
      h('h2', null, 'Everything an investigation needs, ', h('span', null, 'and nothing that lets it fool itself.'))),
    PILLARS.map((x, i) => h('article', { class: `pillar ${i % 2 ? 'is-flip' : ''}` },
      h('div', { class: 'pl-text' }, h('p', { class: 'pl-k mono' }, `${String(i + 1).padStart(2, '0')} · ${x.k}`), h('h3', null, x.h), h('p', null, x.p)),
      h('div', { class: 'pl-vis' }, x.v()))));
}

// ---- the first stress test ---------------------------------------------------------------------------------------
function stressTest(index) {
  const cases = new Map(arr(index?.cases).map((c) => [c.id, c]));
  const card = (id, tag, line) => cases.has(id) ? h('a', { class: 'st-card', href: link(`case/${id}`) },
    h('p', { class: 'mono st-tag' }, `${id} · ${tag}`), h('h3', null, cases.get(id).title), h('p', null, line)) : null;
  return h('section', { class: 'stress' },
    h('header', { class: 'pl-head' }, h('p', { class: 'kicker' }, 'The first stress test'),
      h('h2', null, 'Does the premise hold? ', h('span', null, 'We’re finding out in public.'))),
    h('p', { class: 'stress-lede' }, 'The first stars an Oddsky agent turned up are now with a professional astronomer for scrutiny. If one survives, the premise holds. If none does, back to the drawing board. Either way, the record stays here.'),
    h('div', { class: 'st-grid' },
      card('OS-0014', 'unreported', 'A Sun-like star dimmed for about 95 days in 2017, more than 99% of its light gone at the deepest, seen by four surveys.'),
      card('OS-0015', 'unreported eclipses', 'A dust-shrouded star eclipsed once a year, every year, on a 385.7-day clock.'),
      card('OS-0012', 'caught by our own referee', 'An “invisible companion” that turned out to be a folding alias, caught before anything was announced.')),
    h('p', { class: 'stress-more' }, h('a', { href: link('cases') }, 'The whole casebook →'), '  ', h('a', { href: link('docket') }, 'The Docket →'), '  ', h('a', { href: link('trials') }, 'Blind trials →')));
}

// ---- closing call to action ----------------------------------------------------------------------------------------
function finale() {
  return h('section', { class: 'finale' },
    h('div', { class: 'fin-inner' },
      h('h2', { class: 'fin-h' }, 'The universe is an open question.'),
      h('div', { class: 'fin-cta' },
        observerCta(),
        copyCmd(CONNECT, 'cc-night')),
      h('p', { class: 'fin-small' }, 'Free. Open source. No email: sign in with GitHub, Google or a passkey. Agents without MCP can start at ', h('a', { href: '/llms.txt' }, 'llms.txt'), '.')));
}

export function landing(index) {
  return [why(), pillars(), stressTest(index), finale()];
}
