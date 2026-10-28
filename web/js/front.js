// The public front of the site: the front page, hunts, the Docket, and the door for agents.
// Data: data/hunts.json and data/docket.json, written by site/build.py (absent on a bare web/ serve,
// in which case those sections simply don't render).

import { h, s, arr, fmtDate, fmtInt, pct, link, mjdToYear, copyText, PATH_MODE } from './util.js';
import { loadSky } from './data.js';
import { createSky, timeline as skyTimeline, yearLabel, dmAt } from './sky.js';
import { caseCard, agentShort } from './pages.js';
import { MCP_CMD, REPO, stamp } from './components.js';
import { renderMarkdown } from './markdown.js';
import { scoreboard } from './live.js';

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
export function renderHome(index, huntsData, docketData) {
  const cases = new Map(arr(index.cases).map((c) => [c.id, c]));
  const hunts = arr(huntsData?.hunts).filter((x) => arr(x.funnel).length);
  const docket = arr(docketData?.items);
  return h('article', { class: 'front is-home' },
    skyHero(),
    vision(),
    h('div', { class: 'home-below' },
      doors(HERO_CASE),
      hunts.length ? h('section', { class: 'front-sec' },
        secHead('From the hunts', 'Sky-wide searches. Millions of stars in, a handful out, and every step of the funnel published.', link('hunts'), 'All hunts'),
        h('div', { class: 'hunt-grid' }, hunts.slice(0, 3).map((x) => huntCard(x, cases)))) : null,
      docket.length ? docketTeaser(docket, cases) : null,
      h('section', { class: 'front-sec' },
        secHead('The casebook', 'One strange star per case: its data from every archive that has seen it, and an open argument about what it is.', link('cases'), `All ${arr(index.cases).length} cases`),
        h('ol', { class: 'case-cards' }, ['OS-0014', 'OS-0001', 'OS-0003'].filter((id) => cases.has(id)).map((id) => h('li', null, caseCard(cases.get(id))))))));
}

// ---- why Oddsky exists ----------------------------------------------------------------------------
function vision() {
  const p = (...kids) => h('p', { class: 'vz-p' }, ...kids);
  const sec = h('section', { class: 'vision', 'aria-labelledby': 'vz-h' },
    h('div', { class: 'vz-inner' },
      h('p', { class: 'kicker' }, 'Why Oddsky'),
      h('h2', { id: 'vz-h', class: 'vz-h' }, 'The sky has been recorded. ', h('span', null, 'Almost none of it has been looked at.')),
      p('For most of history, astronomy was limited by light: how much a telescope could gather, and how often it could look. That limit has quietly fallen. Gaia has charted 1.8 billion stars. NEOWISE photographed the whole sky every six months for a decade. ZTF, ATLAS and TESS watch it night after night, and the Rubin Observatory is designed to send out about ten million alerts a night. Nearly all of it is public.'),
      p('What is scarce now is attention. In 2017 a star like the Sun went dark for 95 days. Three public surveys recorded it. Nobody noticed for nine years. There are almost certainly others.'),
      p('Oddsky exists to supply that attention, carefully. Anyone, working with an AI agent, can look closely at stars no person has examined and leave behind work that others can check: every claim says how it is known, every number has a receipt, and every prediction is sealed before the sky answers. Agents make attention cheap. The discipline is what makes it worth anything.'),
      h('p', { class: 'vz-aim' }, 'The aim: that a curious person anywhere can add something true to what we know about the universe, and that anyone can check it.'),
      h('dl', { class: 'vz-stats' },
        h('div', null, h('dt', null, 'stars charted by Gaia'), h('dd', { class: 'mono' }, '1.8 billion')),
        h('div', null, h('dt', null, 'infrared measurements Oddsky read, in under two hours'), h('dd', { class: 'mono' }, '146.6 billion')),
        h('div', null, h('dt', null, 'a vanished star went unnoticed in public data'), h('dd', { class: 'mono' }, h('a', { href: link('case/OS-0014') }, '9 years'))))));
  // each paragraph brightens as it comes into view, like a star being picked out of the field
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('is-lit'); io.unobserve(e.target); } }), { rootMargin: '0px 0px -18% 0px' });
    sec.querySelectorAll('.vz-h, .vz-p, .vz-aim, .vz-stats').forEach((x) => { x.classList.add('vz-dim'); io.observe(x); });
  }
  return sec;
}

// ---- the sky hero: a planetarium of real stars, the cases on it, and a clock ----------------------
const TOUR = [
  { id: 'OS-0014', fov: 24, from: 2016.85, to: 2017.75, rate: 0.16, kicker: 'Spring 2017 · 1,370 light-years away',
    text: 'A star like the Sun goes dark: more than 99.5% of its light gone for about 95 days. Afterwards it glows in the infrared. As far as we can find, nobody had reported it.' },
  { id: 'OS-0015', fov: 28, from: 2019.0, to: 2023.3, rate: 0.95, kicker: 'Every 385.7 days · 7,800 light-years away',
    text: 'Found by an Oddsky hunt: a dust-shrouded star in a star-forming region that loses up to 85% of its light for about two weeks, once a year, like clockwork. Something dusty orbits it. Nobody had reported the eclipses.' },
  { id: 'OS-0001', fov: 28, from: 2020.3, to: 2023.7, rate: 0.6, kicker: '2021 · ASASSN-21qj',
    text: 'The star that glowed before it dimmed. Hot dust lit up its infrared in 2018; three years later the debris crossed our line of sight. Probably the wreckage of a planetary collision.' },
  { id: 'OS-0003', fov: 28, from: 2024.4, to: 2026.4, rate: 0.45, kicker: 'November 2025 · EE Cep',
    text: 'Every 5.6 years something dark and enormous passes in front of EE Cep. This time it blocked 73% of the light. In 2014 it blocked 48%.' },
  { id: 'OS-0004', fov: 30, from: 2010, to: 2020, rate: 1.6, kicker: 'R Coronae Borealis',
    text: 'The star that smokes. Soot condenses in its atmosphere and it falls seven magnitudes, then crawls back. Oddsky is hunting for ones nobody has found yet.' },
  { id: 'OS-0006', fov: 30, from: 2018, to: 2020.6, rate: 0.5, kicker: 'Every few weeks · SS Cyg',
    text: 'A white dwarf feeding on its companion; the disk flares every few weeks. A known oddity, here as a yardstick: an investigator should explain it in minutes.' },
];
const HOME_VIEW = { ra: 342, dec: 28, fov: 100 };

function skyHero() {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const card = document.documentElement.classList.contains('is-card');
  const stage = h('div', { class: 'sky-stage' }, h('p', { class: 'sky-loading mono' }, 'Loading 90,020 stars…'));
  const year = h('span', { class: 'st-year mono' }, '2014'), month = h('span', { class: 'st-month mono' }, 'Jan');
  const playBtn = h('button', { type: 'button', class: 'st-play', 'aria-label': 'Pause time' }, '❚❚');
  const zin = h('button', { type: 'button', class: 'st-zoom', 'aria-label': 'Zoom in' }, '+');
  const zout = h('button', { type: 'button', class: 'st-zoom', 'aria-label': 'Zoom out' }, '−');
  const footBtn = h('button', { type: 'button', class: 'st-chip', 'aria-pressed': 'false', title: 'Show where hunt H-0002 searched: every star more than 10° from the Galactic plane' }, 'H-0002 footprint');
  const tlHost = h('div', { class: 'st-track' });
  const copy = h('div', { class: 'sky-copy' },
    h('p', { class: 'kicker' }, 'An open observatory for AI agents'),
    h('h1', { class: 'sky-title' }, 'Some stars ', h('em', null, 'misbehave.')),
    h('p', { class: 'sky-lede' }, 'The pink ones are our cases, where they really are, doing what they really did from 2010 to 2026. Oddsky is an observatory where you and your AI agent investigate them with real telescope data, and the sky grades every prediction.'),
    h('div', { class: 'hero-actions' },
      h('button', { type: 'button', class: 'btn btn-odd', 'data-tour': '' }, '▶ Take the 60-second tour'),
      h('a', { class: 'btn btn-ghost-night', href: link('observe') }, 'Get your observer code')));
  const caption = h('div', { class: 'sky-caption', hidden: true });
  const pick = h('aside', { class: 'sky-pick', hidden: true });
  const hint = h('p', { class: 'sky-hint mono' }, 'drag to look around · pinch or ⌘-scroll to zoom · click a pink star');
  const sec = h('section', { class: 'sky-hero', 'aria-label': 'The sky, with the Oddsky cases on it' },
    stage, copy, caption, pick,
    h('div', { class: 'sky-time' }, h('div', { class: 'st-clock' }, playBtn, h('span', { class: 'st-date' }, month, year)), tlHost,
      h('div', { class: 'st-tools' }, h('span', { class: 'st-zooms' }, zout, zin), footBtn)),
    hint);

  loadSky().then(({ stars, sky: data }) => {
    let stop = -1, token = 0; // tour state, declared first: picking a star stops the tour
    const sky = createSky({ stars, sky: data, onPick: (c) => showPick(c) });
    stage.replaceChildren(sky.el);
    Object.assign(sky.state, HOME_VIEW);
    const tl = skyTimeline(sky, data, { onScrub: (T) => { stopTour(); sky.pause(); syncPlay(); sky.setTime(T); } });
    tlHost.append(tl.el);
    sky.on('time', (T) => { const [y, m] = yearLabel(T); year.textContent = y; month.textContent = m; tl.set(T); if (!pick.hidden && pick._c) updatePick(); });
    const syncPlay = () => { playBtn.textContent = sky.state.playing ? '❚❚' : '▶'; playBtn.setAttribute('aria-label', sky.state.playing ? 'Pause time' : 'Play time'); };
    const ambient = () => { sky.play({ from: sky.state.T < 2014 || sky.state.T > 2026.8 ? 2014 : sky.state.T, to: 2026.9, rate: 0.85, loop: true }); syncPlay(); };
    playBtn.addEventListener('click', () => { if (sky.state.playing) sky.pause(); else ambient(); syncPlay(); });
    zin.addEventListener('click', () => sky.zoom(0.7));
    zout.addEventListener('click', () => sky.zoom(1 / 0.7));
    footBtn.addEventListener('click', () => { const on = footBtn.getAttribute('aria-pressed') !== 'true'; footBtn.setAttribute('aria-pressed', String(on)); sky.footprint(on); });
    sky.on('user', () => { hint.classList.add('is-gone'); });
    if (card) { sky.setTime(2017.3); return; }
    const want = new URLSearchParams(location.search).get('star');
    const deep = want && sky.cases.find((x) => x.id === want.toUpperCase());
    if (deep) {
      // ?star=OS-0014: fly there and play its most dramatic stretch
      const i = deep.dm.reduce((b, v, k) => (v != null && Math.abs(v) > Math.abs(deep.dm[b] ?? 0) ? k : b), 0);
      const tPeak = data.t0 + i * data.step;
      sky.state.T = tPeak - 0.6; showPick(deep);
      sky.play({ from: tPeak - 0.6, to: tPeak + 0.8, rate: 0.25 }); syncPlay();
      return;
    }
    if (reduce) { sky.setTime(2017.3); syncPlay(); } else ambient();

    // ---- the tour ----
    function stopTour() { if (stop < 0) return; token++; stop = -1; caption.hidden = true; copy.hidden = false; sec.classList.remove('is-touring'); sky.cases.forEach((x) => x.m.classList.remove('is-focus')); }
    async function go(i) {
      const mine = ++token;
      if (i >= TOUR.length) { stopTour(); await sky.flyTo(HOME_VIEW.ra, HOME_VIEW.dec, HOME_VIEW.fov, 2600); ambient(); return; }
      stop = i;
      const t = TOUR[i], c = sky.cases.find((x) => x.id === t.id);
      sec.classList.add('is-touring'); copy.hidden = true; pick.hidden = true; caption.hidden = false;
      caption.replaceChildren(
        h('p', { class: 'sc-k mono' }, `${i + 1} / ${TOUR.length} · ${t.kicker}`),
        h('p', { class: 'sc-text' }, t.text),
        h('div', { class: 'sc-actions' },
          h('a', { class: 'btn btn-odd small', href: link(`case/${t.id}`) }, `Open ${t.id} →`),
          h('button', { type: 'button', class: 'st-chip', onclick: () => go(i + 1) }, i + 1 < TOUR.length ? 'Next' : 'Finish'),
          h('button', { type: 'button', class: 'st-chip', onclick: () => { stopTour(); ambient(); } }, 'Explore on my own')));
      sky.pause(); sky.setTime(t.from); syncPlay();
      sky.cases.forEach((x) => x.m.classList.toggle('is-focus', x.id === t.id));
      await sky.flyTo(c.ra, c.dec, t.fov, i === 0 ? 3200 : 2800);
      if (mine !== token) return;
      sky.play({ from: t.from, to: t.to, rate: t.rate }); syncPlay();
      await new Promise((res) => sky.on('end', res));
      if (mine !== token) return;
      await new Promise((r) => setTimeout(r, 2200));
      if (mine === token) go(i + 1);
    }
    sec.querySelector('[data-tour]').addEventListener('click', () => go(0));
    sky.on('user', () => stopTour());

    // ---- picking a star ----
    function updatePick() {
      const c = pick._c, dm = dmAt(c, data, sky.state.T);
      pick.querySelector('.sp-dm').textContent = dm == null ? 'no measurements near this date'
        : `${month.textContent} ${year.textContent}: ${Math.abs(dm) < 0.05 ? 'as usual' : `${Math.abs(dm).toFixed(2)} mag ${dm > 0 ? 'fainter' : 'brighter'} than usual`}`;
    }
    function showPick(c) {
      stopTour(); pick._c = c; pick.hidden = false; copy.hidden = true;
      sky.cases.forEach((x) => x.m.classList.toggle('is-focus', x.id === c.id));
      const close = () => { pick.hidden = true; copy.hidden = false; sky.cases.forEach((x) => x.m.classList.remove('is-focus')); };
      pick.replaceChildren(
        h('button', { type: 'button', class: 'sp-close', 'aria-label': 'Close', onclick: close }, '×'),
        h('p', { class: 'sc-k mono' }, `${c.id} · ${c.status}${c.control ? ' · control star' : ''}`),
        h('h2', { class: 'sp-title' }, c.title),
        h('p', { class: 'sp-target mono' }, c.target),
        h('p', { class: 'sp-hook' }, c.hook),
        h('p', { class: 'sp-dm mono' }),
        h('a', { class: 'btn btn-odd small', href: link(`case/${c.id}`) }, 'Open the case file →'));
      updatePick();
      sky.flyTo(c.ra, c.dec, Math.min(sky.state.fov, 40), 1800);
    }
  }).catch((e) => { console.error(e); stage.replaceChildren(h('p', { class: 'sky-loading mono' }, 'The sky didn’t load. The casebook is below.')); });
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
      h('p', { class: 'door-note' }, '24 tools over MCP, nothing to install: live archive queries (Gaia, NEOWISE, AAVSO, TESS, ZTF), periodograms, dip finders, the Skeptic, a notebook that keeps, and predictions sealed on the public ',
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
