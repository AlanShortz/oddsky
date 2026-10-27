// Router. Hash routes so the site works on any static host, at any sub-path:
//   #/                 featured case        #/case/OS-0001   one case
//   #/cases            the casebook         #/trials         scorecards        #/about
// Dev: ?fixture=1 loads web/dev fixtures; ?theme=dark|light forces a theme.

import { h } from './util.js';
import { loadIndex, loadCase, featuredCase, FIXTURE } from './data.js';
import { renderCase } from './case.js';
import { renderCases, renderTrials, renderAbout, renderNotFound, renderError } from './pages.js';

const app = document.getElementById('app');
const SITE = 'Oddsky';

function parse() {
  const raw = location.hash.replace(/^#\/?/, '').split('?')[0];
  const parts = raw.split('/').filter(Boolean).map(decodeURIComponent);
  if (!parts.length) return { name: 'home' };
  if (parts[0] === 'case' && parts[1]) return { name: 'case', id: parts[1] };
  if (['cases', 'trials', 'about'].includes(parts[0])) return { name: parts[0] };
  return { name: 'notfound', what: raw };
}

let token = 0;
async function route() {
  const r = parse();
  const mine = ++token;
  document.querySelectorAll('.nav a').forEach((a) => {
    const on = a.dataset.route === r.name || (r.name === 'case' && a.dataset.route === 'cases');
    if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  app.setAttribute('aria-busy', 'true');
  try {
    let view, title;
    if (r.name === 'home' || r.name === 'case') {
      const index = await loadIndex();
      const entry = r.name === 'home' ? featuredCase(index) : index.cases.find((c) => c.id === r.id) ?? { id: r.id };
      if (!entry) { view = renderCases(index); title = 'Cases'; }
      else {
        let payload;
        try { payload = await loadCase(entry.id); } catch (e) {
          if (e.status === 404) { view = renderNotFound(`Case ${entry.id}`); title = 'Not found'; }
          else throw e;
        }
        if (payload) {
          view = renderCase(payload, { home: r.name === 'home' });
          const c = payload.case ?? {};
          title = r.name === 'home' ? null : `${c.id} · ${c.title ?? c.target?.name ?? ''}`;
        }
      }
    } else if (r.name === 'cases') { view = renderCases(await loadIndex()); title = 'Cases'; }
    else if (r.name === 'trials') { view = renderTrials(await loadIndex()); title = 'Trials'; }
    else if (r.name === 'about') { view = renderAbout(); title = 'About'; }
    else { view = renderNotFound(r.what); title = 'Not found'; }
    if (mine !== token) return;
    app.replaceChildren(view);
    document.title = title ? `${title} — ${SITE}` : `${SITE} — investigate strange stars with your AI agent`;
  } catch (err) {
    if (mine !== token) return;
    console.error(err);
    app.replaceChildren(renderError(err));
  } finally {
    if (mine === token) app.removeAttribute('aria-busy');
  }
  window.scrollTo(0, 0);
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
window.addEventListener('hashchange', route);
route();
