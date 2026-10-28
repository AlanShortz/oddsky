// Router. Two modes, same routes:
//   path (the built site, <html data-router="path">):  /case/OS-0001, /hunts, /docket …
//   hash (web/ served as-is, any host, any sub-path):    #/case/OS-0001, #/hunts …
// Routes: /  the front page   /case/<ID>  /cases  /hunts  /hunt/<ID>  /docket  /trials  /agents  /about
// Dev: ?fixture=1 loads web/dev fixtures; ?theme=dark|light forces a theme.

import { h, PATH_MODE, link } from './util.js';
import { loadIndex, loadCase, loadHunts, loadDocket, FIXTURE } from './data.js';
import { renderCase } from './case.js';
import { renderCases, renderTrials, renderAbout, renderNotFound, renderError, renderPrivacy, renderTerms } from './pages.js';
import { renderHome, renderHunts, renderHunt, renderDocket, renderAgents } from './front.js';
import { renderObserve, renderLedger, renderNotebook, renderObserver, liveDocket, syncChip } from './live.js';

const app = document.getElementById('app');
const SITE = 'Oddsky';

function parse() {
  const hashRoute = /^#\//.test(location.hash);
  const raw = (PATH_MODE && !hashRoute ? location.pathname : location.hash.replace(/^#/, '')).replace(/^\/+/, '').split('?')[0].replace(/\.html$/, '');
  const parts = raw.split('/').filter(Boolean).map(decodeURIComponent);
  if (!parts.length || parts[0] === 'index') return { name: 'home' };
  if (parts[0] === 'case' && parts[1]) return { name: 'case', id: parts[1] };
  if (parts[0] === 'hunt' && parts[1]) return { name: 'hunt', id: parts[1] };
  if (parts[0] === 'n' && parts[1]) return { name: 'notebook', id: parts[1] };
  if (parts[0] === 'o' && parts[1]) return { name: 'observer', id: parts[1].toUpperCase() };
  if (['cases', 'trials', 'about', 'hunts', 'docket', 'agents', 'observe', 'ledger', 'privacy', 'terms'].includes(parts[0])) return { name: parts[0] };
  return { name: 'notfound', what: raw };
}

// Old #/ links keep working on the built site: swap them for the clean URL.
if (PATH_MODE && /^#\//.test(location.hash)) history.replaceState(null, '', link(location.hash.slice(2)) + location.search);

let token = 0;
async function route() {
  const r = parse();
  const mine = ++token;
  document.querySelectorAll('.nav a').forEach((a) => {
    const on = a.dataset.route === r.name || (r.name === 'observer' && a.dataset.route === 'observe') || (r.name === 'case' && a.dataset.route === 'cases') || (r.name === 'hunt' && a.dataset.route === 'hunts');
    if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  document.documentElement.classList.toggle('at-home', r.name === 'home');
  app.setAttribute('aria-busy', 'true');
  try {
    let view, title;
    if (r.name === 'home') {
      view = renderHome(await loadIndex()); title = null;
    } else if (r.name === 'case') {
      const index = await loadIndex();
      let payload;
      try { payload = await loadCase(r.id); } catch (e) {
        if (e.status === 404) { view = renderNotFound(`Case ${r.id}`); title = 'Not found'; }
        else throw e;
      }
      if (payload) {
        view = renderCase(payload, { index });
        const c = payload.case ?? {};
        title = `${c.title ?? c.target?.name ?? ''} — ${c.id}`;
      }
    } else if (r.name === 'hunts') { view = renderHunts(await loadHunts()); title = 'Hunts'; }
    else if (r.name === 'hunt') {
      const [hunts, index] = await Promise.all([loadHunts(), loadIndex()]);
      const hu = hunts.hunts.find((x) => x.id === r.id);
      view = hu ? renderHunt(hu, index) : renderNotFound(`Hunt ${r.id}`); title = hu ? `${hu.title} — ${hu.id}` : 'Not found';
    } else if (r.name === 'docket') { const [d, live] = await Promise.all([loadDocket(), liveDocket()]); view = renderDocket(d, live); title = 'The Docket'; }
    else if (r.name === 'observe') { view = renderObserve(route); title = 'Observe'; }
    else if (r.name === 'ledger') { view = await renderLedger(); title = 'The Sky Ledger'; }
    else if (r.name === 'notebook') { view = await renderNotebook(r.id); title = 'Notebook'; }
    else if (r.name === 'observer') { view = await renderObserver(r.id); title = `Observer ${r.id}`; }
    else if (r.name === 'agents') { view = renderAgents(await loadIndex()); title = 'For agents'; }
    else if (r.name === 'cases') { view = renderCases(await loadIndex()); title = 'Cases'; }
    else if (r.name === 'trials') { view = renderTrials(await loadIndex()); title = 'Trials'; }
    else if (r.name === 'privacy') { view = renderPrivacy(); title = 'Privacy'; }
    else if (r.name === 'terms') { view = renderTerms(); title = 'Terms'; }
    else if (r.name === 'about') { view = renderAbout(); title = 'About'; }
    else { view = renderNotFound(r.what); title = 'Not found'; }
    if (mine !== token) return;
    app.replaceChildren(view);
    document.title = title ? `${title} — ${SITE}` : `${SITE} — an open observatory your AI agent can use`;
  } catch (err) {
    if (mine !== token) return;
    console.error(err);
    app.replaceChildren(renderError(err));
  } finally {
    if (mine === token) app.removeAttribute('aria-busy');
  }
  const target = location.hash && !/^#\//.test(location.hash) && document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (target) target.scrollIntoView(); else window.scrollTo(0, 0);
}

// Path mode: in-site links navigate without a page load.
function setupLinks() {
  if (!PATH_MODE) { window.addEventListener('hashchange', route); return; }
  document.addEventListener('click', (e) => {
    const a = e.target.closest?.('a[href]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target === '_blank' || a.hasAttribute('download')) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || /\.[a-z0-9]+$/i.test(url.pathname)) return; // files (.md, .json, .ics, .txt) load normally
    if (url.pathname === location.pathname && url.hash && !/^#\//.test(url.hash)) return; // in-page anchor
    e.preventDefault();
    history.pushState(null, '', url.pathname + url.search + url.hash);
    route();
  });
  window.addEventListener('popstate', route);
}

// ---- theme: light paper, or red-light mode for the night -----------------------------------
function setupTheme() {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;
  const sync = () => {
    const dark = document.documentElement.dataset.theme === 'dark';
    btn.setAttribute('aria-pressed', String(dark));
    btn.querySelector('.theme-label').textContent = dark ? 'daylight' : 'red-light';
    btn.title = dark ? 'Switch to daylight (paper) mode' : 'Switch to red-light mode, as in an observatory control room at night';
  };
  btn.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('oddsky-theme', next); } catch { /* private mode */ }
    sync();
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    let stored = null;
    try { stored = localStorage.getItem('oddsky-theme'); } catch { /* ignore */ }
    if (!stored && !/[?&]theme=/.test(location.search)) { document.documentElement.dataset.theme = e.matches ? 'dark' : 'light'; sync(); }
  });
  sync();
}

// ?card=1 renders a bare 1200x630 composition used to make og.png (see README).
if (/[?&]card=1/.test(location.search)) document.documentElement.classList.add('is-card');
else if (FIXTURE) document.body.append(h('div', { class: 'dev-badge', title: 'Loaded from web/dev fixtures, not real exported data' }, 'fixture data'));
setupTheme();
setupLinks();
syncChip();
document.querySelectorAll('[data-route]').forEach((a) => { a.href = link(a.dataset.route === 'home' ? '' : a.dataset.route); });
route();
