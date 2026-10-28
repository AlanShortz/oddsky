// The live side of oddsky.ai, backed by the hosted service (/api, /mcp on Cloud Run):
// observers and passkeys (/observe), the Sky Ledger with in-browser verification (/ledger),
// published notebooks (/n/<id>) and observer pages (/o/<CODE>).

import { h, s, arr, fmtDate, pct, link, copyText } from './util.js';
import { stamp, statusPill, emptyNote } from './components.js';
import { renderMarkdown, inline } from './markdown.js';

const SESSION = 'oddsky-session';
const MCP_URL = `${location.origin.includes('localhost') ? 'https://oddsky.ai' : location.origin}/mcp`;

export const session = {
  get token() { try { return localStorage.getItem(SESSION); } catch { return null; } },
  set token(t) { try { if (t) localStorage.setItem(SESSION, t); else localStorage.removeItem(SESSION); } catch { /* private mode */ } },
  observer: null,
};

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'content-type': 'application/json' };
  if (auth && session.token) headers.authorization = `Bearer ${session.token}`;
  const r = await fetch(`/api/${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined, cache: 'no-store' });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(data.error || `HTTP ${r.status}`), { status: r.status });
  return data;
}

/** Who is signed in: the observer, or null. One /api/me per page load, shared by every caller. */
let pending = null;
export function whoami() {
  if (!session.token) return Promise.resolve(null);
  if (session.observer) return Promise.resolve(session.observer);
  return pending ??= api('me').then((d) => (session.observer = d.observer))
    .catch((e) => { if (e.status === 401) session.token = null; return null; })
    .finally(() => { pending = null; });
}

/** Tell the page someone signed in or out: main.js re-renders the route (or goes to `go`). */
function announce(go = null) { syncChip(); window.dispatchEvent(new CustomEvent('oddsky:session', { detail: { go } })); }

/** A session handed back by GitHub/Google sign-in travels in the URL fragment (#session=…), on
 *  whichever page the person started from. Keep it and tidy the URL. Called before every route. */
export function takeSession() {
  const frag = new URLSearchParams(location.hash.slice(1));
  if (!frag.get('session')) return;
  session.token = frag.get('session'); session.observer = null;
  frag.delete('session');
  history.replaceState(null, '', location.pathname + location.search + (String(frag) ? `#${frag}` : ''));
}

/** Keep the masthead chip in sync: "Sign in" (opens the sign-in sheet), or your code (your observatory). */
export async function syncChip() {
  const a = document.querySelector('[data-route="observe"]');
  if (!a) return;
  const out = () => { a.textContent = 'Sign in'; a.classList.remove('is-in'); a.title = 'Sign in or join: GitHub, Google or a passkey'; };
  if (!session.token) return out();
  const me = await whoami();
  if (!me) return out();
  a.textContent = me.code; a.classList.add('is-in'); a.title = `Signed in as observer ${me.code}: your observatory`;
}

// ---- the sign-in sheet: opens from the masthead on any page, no detour -----------------------------
let providersOnce = null;
const loadProviders = () => providersOnce ??= api('auth/providers', { auth: false }).then((d) => arr(d.providers)).catch(() => (providersOnce = null, []));

/** Where to land after signing in from here: the page you were on, except the front page, which
 *  sends you to your observatory. */
const landing = () => (/^\/?(index)?$/.test(location.pathname) && !/^#\//.test(location.hash) ? '/observe' : location.pathname + location.search);

export function setupSignInSheet() {
  const chip = document.querySelector('[data-route="observe"]');
  if (!chip || !('showPopover' in HTMLElement.prototype)) return; // no popover support: the link goes to /observe
  const sheet = h('div', { class: 'sheet', id: 'signin-sheet', popover: 'auto', role: 'dialog', 'aria-label': 'Sign in or join Oddsky' });
  document.body.append(sheet);
  const fill = async () => {
    const providers = await loadProviders();
    const close = h('button', { type: 'button', class: 'sheet-x', 'aria-label': 'Close' }, '×');
    close.addEventListener('click', () => sheet.hidePopover());
    sheet.replaceChildren(close, signInPanel(providers, landing(), () => { sheet.hidePopover(); announce(landing() === '/observe' ? '/observe' : null); }, {
      title: 'Sign in or join',
      foot: h('p', { class: 'door-note small' }, 'New here? Same buttons. You choose your observer code next; it takes a minute. ',
        h('a', { href: link('observe') }, 'What you get →')),
    }));
    sheet.querySelector('.pv-btn')?.focus();
  };
  chip.addEventListener('click', (e) => {
    if (session.token || e.metaKey || e.ctrlKey || e.shiftKey || /^\/?observe/.test(location.pathname)) return;
    e.preventDefault(); e.stopPropagation();
    // hang the sheet from the button, its pointer at the button's middle
    const r = chip.getBoundingClientRect(), right = Math.max(12, innerWidth - r.right - 8);
    sheet.style.setProperty('--sheet-top', `${r.bottom + 12}px`);
    sheet.style.setProperty('--sheet-right', `${right}px`);
    sheet.style.setProperty('--sheet-arrow', `${innerWidth - right - (r.left + r.width / 2) - 6}px`);
    sheet.replaceChildren(h('p', { class: 'loading' }, 'One moment…'));
    sheet.showPopover(); fill();
  }, true);
}

// ---- passkeys (WebAuthn JSON <-> ArrayBuffer) ------------------------------------------------------
const b64uToBuf = (s) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (s.length % 4)) % 4)), (c) => c.charCodeAt(0)).buffer;
const bufToB64u = (b) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

function creationOptions(json) {
  const o = JSON.parse(json);
  if (window.PublicKeyCredential?.parseCreationOptionsFromJSON) return PublicKeyCredential.parseCreationOptionsFromJSON(o);
  return { ...o, challenge: b64uToBuf(o.challenge), user: { ...o.user, id: b64uToBuf(o.user.id) },
    excludeCredentials: arr(o.excludeCredentials).map((c) => ({ ...c, id: b64uToBuf(c.id) })) };
}
function requestOptions(json) {
  const o = JSON.parse(json);
  if (window.PublicKeyCredential?.parseRequestOptionsFromJSON) return PublicKeyCredential.parseRequestOptionsFromJSON(o);
  return { ...o, challenge: b64uToBuf(o.challenge), allowCredentials: arr(o.allowCredentials).map((c) => ({ ...c, id: b64uToBuf(c.id) })) };
}
function credJSON(c) {
  if (typeof c.toJSON === 'function') { try { return c.toJSON(); } catch { /* fall through */ } }
  const r = c.response, out = { id: c.id, rawId: bufToB64u(c.rawId), type: c.type, clientExtensionResults: c.getClientExtensionResults?.() ?? {}, response: { clientDataJSON: bufToB64u(r.clientDataJSON) } };
  if (r.attestationObject) Object.assign(out.response, { attestationObject: bufToB64u(r.attestationObject), transports: r.getTransports?.() ?? [] });
  if (r.authenticatorData) Object.assign(out.response, { authenticatorData: bufToB64u(r.authenticatorData), signature: bufToB64u(r.signature), userHandle: r.userHandle ? bufToB64u(r.userHandle) : null });
  return out;
}

async function register(code, name) {
  const begin = await api('register/begin', { method: 'POST', body: { code, name }, auth: false });
  const cred = await navigator.credentials.create({ publicKey: creationOptions(begin.options) });
  const fin = await api('register/finish', { method: 'POST', body: { challenge_id: begin.challenge_id, credential: credJSON(cred) }, auth: false });
  session.token = fin.token; session.observer = fin.observer;
}

async function login() {
  const begin = await api('login/begin', { method: 'POST', auth: false });
  const cred = await navigator.credentials.get({ publicKey: requestOptions(begin.options) });
  const fin = await api('login/finish', { method: 'POST', body: { challenge_id: begin.challenge_id, credential: credJSON(cred) }, auth: false });
  session.token = fin.token; session.observer = fin.observer;
}

// ---- /observe ------------------------------------------------------------------------------------------
async function addPasskey() {
  const begin = await api('passkeys/begin', { method: 'POST' });
  const cred = await navigator.credentials.create({ publicKey: creationOptions(begin.options) });
  await api('passkeys/finish', { method: 'POST', body: { challenge_id: begin.challenge_id, credential: credJSON(cred) } });
}

const GH_ICON = 'M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.7 1.6.3 2.8.1 3.1.8.8 1.2 1.9 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 23.5 12C23.5 5.7 18.3.5 12 .5Z';
const G_ICON = [['#4285F4', 'M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.7Z'], ['#34A853', 'M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24Z'], ['#FBBC05', 'M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1Z'], ['#EA4335', 'M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9Z']];
const providerIcon = (id) => s('svg', { viewBox: '0 0 24 24', class: 'pv-icon', 'aria-hidden': 'true' },
  id === 'github' ? s('path', { d: GH_ICON, fill: 'currentColor' }) : G_ICON.map(([f, d]) => s('path', { d, fill: f })));

/** The sign-in panel: GitHub, Google, passkey. `next` is where to land afterwards. */
function signInPanel(providers, next, rerender, { title = 'Sign in or join', lede, foot } = {}) {
  const status = h('p', { class: 'obs-status', role: 'status' });
  const pk = h('button', { type: 'button', class: 'pv-btn' }, s('svg', { viewBox: '0 0 24 24', class: 'pv-icon', 'aria-hidden': 'true' },
    s('path', { d: 'M8 11a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm0 2c3 0 7 1.5 7 4.5V20H1v-2.5C1 14.5 5 13 8 13Zm10-4.2a3 3 0 1 1 1.8.1V12l1.2 1.2-1.2 1.2 1.2 1.2-1.8 1.8L17.6 16V8.8h.4Z', fill: 'currentColor' })), 'Sign in with a passkey');
  pk.addEventListener('click', async () => {
    try { await login(); await syncChip(); rerender(); } catch (e) { status.textContent = e.name === 'NotAllowedError' ? 'No passkey chosen. New here? Continue with GitHub or Google.' : e.message; status.className = 'obs-status is-bad'; }
  });
  return h('section', { class: 'door signin' },
    h('p', { class: 'door-k mono' }, title),
    lede ? h('p', { class: 'door-note' }, lede) : null,
    h('div', { class: 'pv-list' },
      providers.map((p) => h('a', { class: 'pv-btn', href: `/api/oauth/${p.id}/start?next=${encodeURIComponent(next)}` }, providerIcon(p.id), `Continue with ${p.label}`)),
      pk),
    status,
    foot ?? (providers.length ? h('p', { class: 'door-note small' }, `New with ${providers.map((p) => p.label).join(' or ')}? You choose your observer code next. Your email is never shown or shared.`) : null));
}

function passkeyJoin(rerender) {
  const status = h('p', { class: 'obs-status', role: 'status' });
  const code = codeInput(status);
  const name = h('input', { class: 'obs-name', maxlength: 80, placeholder: 'Your name (optional, shown on your notebooks)', 'aria-label': 'Name' });
  const go = h('button', { type: 'button', class: 'btn' }, 'Create my passkey');
  go.addEventListener('click', async () => {
    go.disabled = true; status.textContent = 'Waiting for your passkey…'; status.className = 'obs-status';
    try { await register(code.value, name.value); welcome.set(); await syncChip(); rerender(); }
    catch (e) { status.textContent = e.name === 'NotAllowedError' ? 'Passkey cancelled.' : e.message; status.className = 'obs-status is-bad'; go.disabled = false; }
  });
  return h('details', { class: 'door pk-join' }, h('summary', null, h('span', { class: 'door-k mono' }, 'Or join with only a passkey')),
    h('label', { class: 'obs-label' }, 'Observer code ', h('span', { class: 'muted' }, '(2–5 letters or digits)')), code, name, go, status);
}

function codeInput(status, value = '') {
  const code = h('input', { class: 'obs-code mono', maxlength: 5, placeholder: 'ASH', autocomplete: 'off', spellcheck: 'false', 'aria-label': 'Observer code', value });
  let t;
  const check = () => {
    code.value = code.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    clearTimeout(t);
    if (!code.value) { status.textContent = ''; return; }
    t = setTimeout(async () => {
      try { const r = await api('observers/check', { method: 'POST', body: { code: code.value }, auth: false }); status.textContent = r.problem ? `${r.code}: ${r.problem}` : `${r.code} is yours if you want it.`; status.className = `obs-status ${r.problem ? 'is-bad' : 'is-ok'}`; } catch { /* offline */ }
    }, 250);
  };
  code.addEventListener('input', check);
  if (value) setTimeout(check, 0);
  return code;
}

const NEXT_STEPS = () => h('section', { class: 'next-steps', 'aria-label': 'What happens next' },
  h('p', { class: 'door-k mono' }, 'What happens next'),
  h('ol', null,
    h('li', null, h('strong', null, 'Sign in.'), ' GitHub, Google or a passkey. No password, no mailing list.'),
    h('li', null, h('strong', null, 'Choose your code.'), ' Two to five letters, yours for good. It is how your work is credited.'),
    h('li', null, h('strong', null, 'Connect your agent.'), ' One line in Claude Code; any agent that speaks MCP works.'),
    h('li', null, h('strong', null, 'First light.'), ' Your agent opens a real case, and its first prediction goes on the Sky Ledger for the sky to grade.')),
  h('p', { class: 'door-note small' }, 'About a minute to the first tool call. Free, and open source.'));

const WHAT_YOU_GET = () => h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'What you get'),
  h('div', { class: 'agent-grid' },
    h('div', null, h('h3', null, 'The observatory, hosted'), h('p', null, 'Every Oddsky tool from any agent, nothing to install. In Claude Code it is one line, and you sign in with the same button.')),
    h('div', null, h('h3', null, 'A notebook that keeps'), h('p', null, 'Your agent’s claims, hypotheses and ledger of tool calls persist between sessions. Publish a notebook when it is worth checking.')),
    h('div', null, h('h3', null, 'A record graded by the universe'), h('p', null, 'Predictions are sealed on the public Sky Ledger and graded by the archives. Your calibration, and your model’s, is on the scoreboard.')),
    h('div', null, h('h3', null, 'No private predictions'), h('p', null, 'Sealing is publishing, so nobody can seal fifty and show the three that came true. That is what makes the record worth anything.'))));

export function renderObserve(rerender) {
  const page = h('article', { class: 'page front observe' });
  const q = new URLSearchParams(location.search), frag = new URLSearchParams(location.hash.slice(1));
  const linkedNow = frag.get('linked'); if (linkedNow) history.replaceState(null, '', location.pathname + location.search);
  const err = q.get('signin_error');
  page.append(h('p', { class: 'loading' }, 'One moment…'));
  (async () => {
    const providers = arr((await api('auth/providers', { auth: false }).catch(() => ({}))).providers);
    const parts = [];
    if (err) parts.push(h('p', { class: 'obs-alert' }, `Sign-in didn’t finish: ${err}`));
    if (q.get('authorize')) parts.push(...await authorizeView(q.get('authorize'), providers, rerender));
    else if (q.get('claim') && !session.token) parts.push(...await claimView(q.get('claim'), q.get('then'), rerender));
    else if (session.token) { await profile(page, rerender, providers, linkedNow); if (err) page.prepend(parts[0]); return; }
    else {
      parts.push(
        h('header', { class: 'page-head' },
          h('p', { class: 'kicker' }, 'Sign in or join'),
          h('h1', null, 'Get your observer code.'),
          h('p', { class: 'page-lede' }, 'AAVSO has given its observers codes for a century; the light curve in our first case is 7,115 measurements by HMB. Oddsky does the same for you and your agents: everything your agent finds is credited to your code.')),
        h('div', { class: 'obs-grid' }, h('div', { class: 'door-col' }, signInPanel(providers, '/observe', rerender), passkeyJoin(rerender)), NEXT_STEPS()),
        WHAT_YOU_GET());
    }
    page.replaceChildren(...parts);
  })().catch((e) => page.replaceChildren(emptyNote('The observatory didn’t answer.', e.message)));
  return page;
}

async function claimView(token, then, rerender) {
  let info;
  try { info = await api(`claim/${encodeURIComponent(token)}`, { auth: false }); } catch (e) { return [emptyNote('That sign-up link expired.', h('a', { href: link('observe') }, 'Start again'))]; }
  const status = h('p', { class: 'obs-status', role: 'status' });
  const code = codeInput(status, info.suggestions[0] ?? '');
  const name = h('input', { class: 'obs-name', maxlength: 80, value: info.name ?? '', placeholder: 'Your name (shown on your notebooks)', 'aria-label': 'Name' });
  const go = h('button', { type: 'button', class: 'btn btn-odd' }, 'Claim this code');
  go.addEventListener('click', async () => {
    go.disabled = true;
    try {
      const r = await api('claim', { method: 'POST', body: { token, code: code.value, name: name.value }, auth: false });
      session.token = r.token; session.observer = r.observer; welcome.set(); await syncChip();
      // approving an agent? finish that. Otherwise first light, starting from the case you came from.
      const fromCase = /^\/case\/(OS-\d+)/.exec(then ?? '');
      if (fromCase) firstCase.set(fromCase[1]);
      history.replaceState(null, '', then?.startsWith('/observe?authorize=') ? then : '/observe'); rerender();
    } catch (e) { status.textContent = e.message; status.className = 'obs-status is-bad'; go.disabled = false; }
  });
  return [
    h('header', { class: 'page-head' }, h('p', { class: 'kicker' }, `Signed in with ${info.label}${info.handle ? ` as ${info.handle}` : ''}`),
      h('h1', null, `${info.name ? `Welcome, ${info.name.split(' ')[0]}.` : 'Welcome.'} Choose your observer code.`),
      h('p', { class: 'page-lede' }, 'It is how Oddsky credits your work: on notebooks, on the Sky Ledger, on the scoreboard. Two to five letters or digits, and it is yours for good.')),
    h('section', { class: 'door claim' },
      h('label', { class: 'obs-label' }, 'Observer code'), code,
      info.suggestions.length > 1 ? h('p', { class: 'claim-sugg' }, 'Free: ', info.suggestions.map((c) => {
        const b = h('button', { type: 'button', class: 'st-chip chip-day' }, c); b.addEventListener('click', () => { code.value = c; code.dispatchEvent(new Event('input')); }); return b;
      })) : null,
      h('label', { class: 'obs-label' }, 'Name'), name, go, status)];
}

async function authorizeView(rid, providers, rerender) {
  let req;
  try { req = await api(`authorize/${encodeURIComponent(rid)}`, { auth: false }); } catch (e) { return [emptyNote('This connection request expired.', 'Start again from your agent: it will open a fresh one.')]; }
  const here = `/observe?authorize=${encodeURIComponent(rid)}`;
  const head = h('header', { class: 'page-head' }, h('p', { class: 'kicker' }, 'Connect an agent'),
    h('h1', null, `${req.client_name} wants to use the observatory.`));
  if (!session.token) {
    return [head, h('div', { class: 'obs-grid' }, signInPanel(providers, here, rerender, { title: 'First, sign in', lede: 'Sign in, or join, and you’ll come straight back here to approve it.' }), passkeyJoin(rerender))];
  }
  let me;
  try { me = await api('me'); } catch { session.token = null; return authorizeView(rid, providers, rerender); }
  const decide = async (allow) => { const r = await api(`authorize/${encodeURIComponent(rid)}`, { method: 'POST', body: { allow } }); location.href = r.redirect; };
  const allow = h('button', { type: 'button', class: 'btn btn-odd' }, `Allow, as ${me.observer.code}`);
  const deny = h('button', { type: 'button', class: 'btn btn-ghost' }, 'Deny');
  allow.addEventListener('click', () => { allow.disabled = true; decide(true).catch((e) => { allow.disabled = false; alert(e.message); }); });
  deny.addEventListener('click', () => decide(false));
  return [head, h('section', { class: 'door consent' },
    h('div', { class: 'consent-who' }, h('div', { class: 'obs-badge mono', 'aria-hidden': 'true' }, me.observer.code),
      h('div', null, h('p', { class: 'door-k mono' }, 'It will work as'), h('h2', null, me.observer.name || me.observer.code), h('p', { class: 'muted small' }, `returns to ${req.redirect_host}`))),
    h('ul', { class: 'consent-list' },
      h('li', null, 'Run every Oddsky tool: archive queries, analysis, the Skeptic.'),
      h('li', null, 'Write claims and hypotheses into your notebook, and publish it when you ask.'),
      h('li', null, h('strong', null, 'Seal predictions on the public Sky Ledger under your code. '), 'Those can never be edited or withdrawn.')),
    h('p', { class: 'door-note' }, 'It gets an instrument key you can revoke from this page at any time.'),
    h('div', { class: 'hero-actions' }, allow, deny))];
}

async function profile(page, rerender, providers = [], linkedNow = null) {
  page.replaceChildren(h('p', { class: 'loading' }, 'Opening your notebook…'));
  let me;
  try { me = await api('me'); } catch (e) {
    if (e.status === 401) { session.token = null; await syncChip(); rerender(); return; }
    page.replaceChildren(emptyNote('The observatory didn’t answer.', e.message)); return;
  }
  const o = me.observer;
  const keyOut = h('div', { class: 'key-out' });
  const label = h('input', { class: 'obs-name', placeholder: 'What will use this key? e.g. Cursor on my laptop', maxlength: 60 });
  const mint = h('button', { type: 'button', class: 'btn btn-ghost' }, 'Mint a key');
  mint.addEventListener('click', async () => {
    mint.disabled = true;
    try { const k = await api('keys', { method: 'POST', body: { label: label.value } }); keyOut.replaceChildren(keyBlock(k.key)); } catch (e) { keyOut.textContent = e.message; }
    mint.disabled = false;
  });
  const out = h('button', { type: 'button', class: 'linkish' }, 'Sign out');
  out.addEventListener('click', async () => { try { await api('logout', { method: 'POST' }); } catch { /* ignore */ } session.token = null; session.observer = null; await syncChip(); rerender(); });

  // sign-in methods: linked providers, link more, passkeys
  const ids = new Map(arr(me.identities).map((x) => [x.provider, x]));
  const pkStatus = h('span', { class: 'muted small' });
  const addPk = h('button', { type: 'button', class: 'linkish' }, me.passkeys ? 'add another' : 'add one');
  addPk.addEventListener('click', async () => { try { await addPasskey(); rerender(); } catch (e) { pkStatus.textContent = e.name === 'NotAllowedError' ? ' cancelled' : ` ${e.message}`; } });
  const methods = h('ul', { class: 'methods' },
    arr(me.providers).map((p) => {
      const have = ids.get(p.id);
      const btn = h('button', { type: 'button', class: 'linkish' }, `link ${p.label}`);
      btn.addEventListener('click', async () => { const r = await api(`oauth/${p.id}/link`, { method: 'POST', body: { next: '/observe' } }); location.href = r.url; });
      return h('li', null, providerIcon(p.id), h('strong', null, p.label), have ? h('span', { class: 'mono small' }, ` ${have.handle ?? ''} ✓`) : btn);
    }),
    h('li', null, s('svg', { viewBox: '0 0 24 24', class: 'pv-icon', 'aria-hidden': 'true' }, s('circle', { cx: 12, cy: 12, r: 5, fill: 'currentColor' })),
      h('strong', null, 'Passkeys'), h('span', { class: 'mono small' }, ` ${me.passkeys} `), addPk, pkStatus));

  const fl = firstLight(me);
  const fresh = welcome.take();
  page.replaceChildren(...[
    linkedNow ? h('p', { class: 'obs-alert is-ok' }, `Linked ${linkedNow}. You can sign in with it from now on.`) : null,
    h('header', { class: 'page-head obs-head' },
      h('div', { class: `obs-badge mono ${fresh ? 'is-new' : ''}`, 'aria-hidden': 'true' }, o.code),
      h('div', null, h('p', { class: 'kicker' }, fresh ? `Welcome, observer ${o.code}` : 'Your observatory'), h('h1', null, o.name || o.code),
        h('p', { class: 'muted' }, `Observer since ${fmtDate(o.since)} · `, h('a', { href: link(`o/${o.code}`) }, 'your public page'), ' · ', out))),
    fl?.el,
    h('div', { class: 'obs-grid' },
      h('section', { class: 'door', id: 'agents' },
        h('p', { class: 'door-k mono' }, 'Connect your agent'),
        // until an agent is connected, First light above carries the one-liner
        arr(me.keys).length ? [h('h2', null, 'One line, then sign in'), copyLine(CONNECT_CMD),
          h('p', { class: 'door-note' }, 'Claude Code opens this page to sign you in the first time you use it (or type /mcp). Any client that speaks MCP sign-in works the same way: point it at ', h('code', null, MCP_URL), '.')]
          : [h('h2', null, 'Another agent?'),
            h('p', { class: 'door-note' }, 'Any client that speaks MCP sign-in works the same way: point it at ', h('code', null, MCP_URL), ' and approve it here.')],
        h('details', { class: 'more-keys' }, h('summary', null, 'A client that can’t sign in? Use a key'),
          h('div', { class: 'mint-row' }, label, mint), keyOut)),
      h('section', { class: 'door' },
        h('p', { class: 'door-k mono' }, 'Sign-in methods'),
        h('h2', null, 'Ways to prove you’re ', o.code),
        methods,
        h('p', { class: 'door-note small' }, 'Link more than one and you can always get back in.'))),
    arr(me.keys).length ? h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Connected agents and keys'),
      h('ul', { class: 'key-list' }, me.keys.map((k) => {
        const rv = h('button', { type: 'button', class: 'linkish' }, 'revoke');
        rv.addEventListener('click', async () => { await api('keys/revoke', { method: 'POST', body: { prefix: k.prefix } }); rerender(); });
        return h('li', null, h('span', { class: 'mono' }, `${k.prefix}…`), ' ', k.label, h('span', { class: 'muted' }, ` · ${fmtDate(k.created_at)} · `), rv);
      }))) : null,
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Your sealed predictions'),
      arr(me.seals).length ? sealList(me.seals) : emptyNote('Nothing sealed yet.', 'When your agent calls register_prediction, it lands on the Sky Ledger and here.')),
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Your notebooks'),
      arr(me.notebook_cases).length ? h('p', null, 'Cases in your notebook: ', me.notebook_cases.map((c, i) => [i ? ', ' : '', h('span', { class: 'mono' }, c)])) : null,
      arr(me.notebooks).length ? h('ul', { class: 'nb-list' }, me.notebooks.map((n) => h('li', null, h('a', { href: link(`n/${n.id}`) }, n.title), h('span', { class: 'muted mono small' }, ` ${n.case} · ${fmtDate(n.published_at)}`))))
        : h('p', { class: 'muted' }, 'Nothing published yet. Ask your agent to publish_notebook when it has something worth checking.'))].filter(Boolean));
  if (fl && !fl.done) watch(page, fl);
}

// ---- first light: a new telescope's first image. A new observer's path to theirs ----------------------
// Each step is read off /api/me, so it lights up when your agent actually does the thing. While a step
// is open the page checks every few seconds (only while visible), so running the one-liner in a
// terminal lights up the tab you left open.
const CONNECT_CMD = `claude mcp add --transport http oddsky ${MCP_URL}`;
const FIRST_CASE_DEFAULT = 'OS-0014';
const stash = (key, store) => ({
  set(v = '1') { try { window[store].setItem(key, v); } catch { /* private mode */ } },
  get() { try { return window[store].getItem(key); } catch { return null; } },
  take() { const v = this.get(); try { window[store].removeItem(key); } catch { /* private mode */ } return v; },
});
const welcome = stash('oddsky-welcome', 'sessionStorage');
const firstCase = stash('oddsky-first-case', 'localStorage');

function copyLine(text, { prompt = false } = {}) {
  const b = h('button', { type: 'button', class: 'copy' }, 'Copy'); b.addEventListener('click', () => copyText(text, b));
  return h('div', { class: `copy-row ${prompt ? 'is-prompt' : ''}` },
    prompt ? h('p', { class: 'prompt-text' }, text) : h('code', { class: 'cmd' }, h('span', { class: 'cmd-dollar', 'aria-hidden': 'true' }, '$ '), text), b);
}

function progress(me) {
  const keys = arr(me.keys), seals = arr(me.seals), nbs = arr(me.notebooks), cases = arr(me.notebook_cases);
  return [
    { k: 'code', t: 'Claim your code', did: `${me.observer.code} is yours` },
    { k: 'agent', t: 'Connect your agent', did: keys.length ? `${keys.at(-1).label || 'An agent'} connected` : null },
    { k: 'case', t: 'Open a case', did: cases.length ? `${cases[0]} in your notebook` : null },
    { k: 'seal', t: 'Seal a prediction', did: seals.length ? `#${seals.at(-1).seq} on the Sky Ledger` : null },
    { k: 'publish', t: 'Publish a notebook', did: nbs.length ? 'Published' : null },
  ];
}

function stepBody(k, me) {
  const id = arr(me.notebook_cases)[0] ?? firstCase.get() ?? FIRST_CASE_DEFAULT;
  const watching = (what) => h('p', { class: 'fl-watch mono', role: 'status' }, h('i', { 'aria-hidden': 'true' }), what);
  if (k === 'agent') return [
    h('h3', null, 'Give your agent the instruments.'),
    copyLine(CONNECT_CMD),
    h('p', { class: 'door-note' }, 'Run it in a terminal, then start Claude Code. The first time it uses Oddsky it opens this site so you can approve it (or type ', h('code', null, '/mcp'), '). ',
      h('a', { href: '#agents', onclick: (e) => { e.preventDefault(); document.getElementById('agents')?.scrollIntoView({ behavior: 'smooth' }); } }, 'Another agent?')),
    watching('Watching for your agent…')];
  if (k === 'case') return [
    h('h3', null, 'Give it a real star.'),
    copyLine(`Open Oddsky case ${id}. Run the Skeptic first, then try to break the leading explanation. Tag every claim honestly: observed, computed, inferred or speculated.`, { prompt: true }),
    h('p', { class: 'door-note' }, 'Paste this into your agent. ', h('a', { href: link(`case/${id}`) }, `Read ${id} yourself`), ' or ', h('a', { href: link('cases') }, 'pick another case'), '.'),
    watching('Watching for your first case…')];
  if (k === 'seal') return [
    h('h3', null, 'Let the sky grade it.'),
    copyLine(`What would you bet on about ${id}? Seal one machine-checkable prediction on the Sky Ledger, with a probability you actually believe.`, { prompt: true }),
    h('p', { class: 'door-note' }, 'Sealing is publishing: it goes on the public ', h('a', { href: link('ledger') }, 'Sky Ledger'), ' for good, and the archives grade it when its window closes. A 60% you believe beats a 95% you don’t.'),
    watching('Watching the Sky Ledger…')];
  if (k === 'publish') return [
    h('h3', null, 'Show your work.'),
    copyLine(`Publish your Oddsky notebook on ${id}, with a short summary that cites your claims and receipts.`, { prompt: true }),
    h('p', { class: 'door-note' }, 'Publish when it is worth someone checking. “This turned out to be nothing” is a result too.'),
    watching('Watching for your notebook…')];
  return [];
}

function firstLight(me) {
  const el = h('section', { class: 'first-light', 'aria-labelledby': 'fl-h' });
  let sig = null;
  const api_ = {
    el, done: false,
    /** Re-read progress; redraw only if something changed. */
    update(next) {
      const steps = progress(next);
      const s2 = steps.map((x) => (x.did ? 1 : 0)).join('');
      if (s2 === sig) return;
      const lit = sig ? steps.findIndex((x, i) => x.did && sig[i] === '0') : -1;
      sig = s2;
      const now = steps.findIndex((x) => !x.did);
      api_.done = now < 0;
      const n = steps.filter((x) => x.did).length;
      el.classList.toggle('is-done', api_.done);
      el.replaceChildren(
        h('header', { class: 'fl-head' },
          h('div', null, h('p', { class: 'kicker' }, 'First light'),
            h('h2', { id: 'fl-h' }, api_.done ? 'First light. The rest is observing.' : 'From sign-in to your first prediction.')),
          h('p', { class: 'fl-count mono' }, `${n} of ${steps.length}`)),
        h('ol', { class: 'fl-steps' }, steps.map((x, i) => h('li', { class: `${x.did ? 'is-did' : ''} ${i === now ? 'is-now' : ''} ${i === lit ? 'is-lit' : ''}`, 'aria-current': i === now ? 'step' : null },
          h('span', { class: 'fl-star', 'aria-hidden': 'true' }),
          h('span', { class: 'fl-t' }, x.t),
          h('span', { class: 'fl-did mono' }, x.did ?? (i === now ? 'now' : ''))))),
        api_.done ? h('p', { class: 'fl-end' }, 'Your agent is connected, your first prediction is with the sky, and your notebook is public. From here, every finding is credited to ', h('strong', { class: 'mono' }, me.observer.code), '.')
          : h('div', { class: 'fl-body' }, stepBody(steps[now].k, next)));
    },
  };
  api_.update(me);
  return api_.done ? null : api_;
}

/** While First light is open, re-read /api/me every few seconds the page is visible, for 30 minutes. */
function watch(page, fl) {
  const until = Date.now() + 30 * 60e3;
  let busy = false;
  const tick = async () => {
    if (!page.isConnected || fl.done || Date.now() > until) { stop(); return; }
    if (document.visibilityState !== 'visible' || busy) return;
    busy = true;
    try { fl.update(await api('me')); } catch { /* next tick */ } finally { busy = false; }
  };
  const timer = setInterval(tick, 5000);
  document.addEventListener('visibilitychange', tick);
  function stop() { clearInterval(timer); document.removeEventListener('visibilitychange', tick); }
}

function keyBlock(key) {
  const claude = `claude mcp add --transport http oddsky ${MCP_URL} --header "Authorization: Bearer ${key}"`;
  const json = JSON.stringify({ mcpServers: { oddsky: { url: MCP_URL, headers: { Authorization: `Bearer ${key}` } } } }, null, 2);
  const codex = `codex mcp add oddsky --url ${MCP_URL} --bearer-token-env-var ODDSKY_KEY   # with ODDSKY_KEY=${key}`;
  const row = (title, text) => {
    const b = h('button', { type: 'button', class: 'copy' }, 'Copy'); b.addEventListener('click', () => copyText(text, b));
    return h('div', null, h('p', { class: 'step-label' }, title), h('div', { class: 'copy-row' }, h('code', { class: 'cmd' }, text), b));
  };
  return h('div', { class: 'key-block' },
    h('p', { class: 'key-warn' }, 'Copy it now: this is the only time Oddsky shows this key.'),
    row('Claude Code', claude), row('Codex', codex), row('Cursor, Claude Desktop, anything else (mcp.json)', json),
    h('p', { class: 'door-note' }, 'Then ask: ', h('em', null, '“Open Oddsky case OS-0014. Run the skeptic first, then try to break the leading hypothesis. Tag every claim honestly.”')));
}

function sealList(seals) {
  return h('ol', { class: 'dk-next' }, [...seals].reverse().map((s) => h('li', { class: 'dk-row' },
    h('a', { href: link(`ledger#seq-${s.seq}`) },
      h('div', { class: 'dk-when' }, h('span', { class: 'dk-days mono' }, `#${s.seq}`), h('span', { class: 'dk-days-k' }, s.outcome), h('span', { class: 'mono dk-date' }, fmtDate(s.resolve_by))),
      h('div', { class: 'dk-what' }, h('p', { class: 'dk-where mono' }, `${s.case}${s.target ? ` · ${s.target}` : ''} · ${s.prediction ?? ''}`), h('p', { class: 'dk-st' }, s.statement),
        h('p', { class: 'dk-by mono' }, `${s.observer}${s.model ? ` · ${s.model}` : ''} · sealed ${fmtDate(s.at)}`)),
      h('div', { class: 'dk-prob' }, h('span', { class: 'mono' }, pct(s.probability)))))));
}

// ---- /ledger ---------------------------------------------------------------------------------------------
export async function renderLedger() {
  let data;
  try { data = await api('ledger?limit=5000', { auth: false }); } catch (e) { return emptyNote('The Sky Ledger didn’t load.', e.message); }
  const entries = arr(data.entries);
  const seals = new Map();
  const result = h('div', { class: 'verify-out', role: 'status' });
  const bar = h('div', { class: 'verify-bar' }, h('span'));
  const btn = h('button', { type: 'button', class: 'btn' }, 'Verify the chain in your browser');
  btn.addEventListener('click', async () => {
    btn.disabled = true; result.textContent = '';
    let prev = '0'.repeat(64), ok = true, i = 0;
    for (const e of entries) {
      const hex = [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${e.prev}\n${e.body}`)))].map((b) => b.toString(16).padStart(2, '0')).join('');
      const row = document.getElementById(`seq-${e.seq}`);
      const good = hex === e.hash && e.prev === prev;
      row?.classList.add(good ? 'is-verified' : 'is-broken');
      if (!good) { ok = false; result.replaceChildren(h('strong', { class: 'verify-bad' }, `✗ Entry #${e.seq} does not match. The chain is broken here.`)); break; }
      prev = e.hash; i++;
      bar.firstChild.style.width = `${(i / entries.length) * 100}%`;
      if (i % 4 === 0) await new Promise((r) => setTimeout(r, 12));
    }
    if (ok) result.replaceChildren(h('strong', { class: 'verify-ok' }, `✓ ${i} entries re-hashed with SHA-256 on your machine. The chain is intact.`), h('br'),
      h('span', { class: 'muted small mono' }, `head #${data.head.seq} ${data.head.hash}`));
    btn.disabled = false;
  });
  const rows = entries.map((e) => {
    const b = JSON.parse(e.body);
    if (b.kind === 'seal') seals.set(e.seq, b);
    const ref = b.kind === 'grade' ? seals.get(b.ref) : null;
    return h('li', { class: `lg-row lg-${b.kind}`, id: `seq-${e.seq}` },
      h('div', { class: 'lg-seq mono' }, `#${e.seq}`, h('span', { class: 'lg-kind' }, b.kind)),
      h('div', { class: 'lg-main' },
        b.kind === 'seal' ? [
          h('p', { class: 'dk-where mono' }, `${b.case}${b.target ? ` · ${b.target}` : ''}${b.trial ? ` · ${b.trial} ${b.packet}` : ''} · `, h('a', { href: link(`o/${b.observer}`) }, b.observer), b.model ? ` · ${b.model}` : '', ` · ${pct(b.probability)}`),
          h('p', { class: 'lg-st' }, b.statement),
          h('p', { class: 'dk-by mono' }, `sealed ${fmtDate(b.at)}${b.resolve_by ? ` · resolves by ${fmtDate(b.resolve_by)}` : ''}${b.source !== 'mcp' ? ` · ${b.provenance ?? b.source}` : ''}`)]
          : b.kind === 'grade' ? [
            h('p', { class: 'lg-st' }, h('span', { class: `verdict verdict-${b.outcome}` }, b.outcome === 'true' ? 'came true' : b.outcome === 'false' ? 'did not happen' : b.outcome), ' ',
              h('a', { href: `#seq-${b.ref}` }, `#${b.ref}`), ref ? ` ${ref.statement.slice(0, 120)}${ref.statement.length > 120 ? '…' : ''}` : ''),
            h('p', { class: 'dk-by mono' }, `${fmtDate(b.at)} · ${b.source}${b.note ? ` · ${b.note}` : ''}`)]
            : h('p', { class: 'lg-st' }, b.text ?? '')),
      h('div', { class: 'lg-hash mono', title: `hash ${e.hash}\nprev ${e.prev}` }, e.hash.slice(0, 12), h('span', { class: 'lg-prev' }, `← ${e.prev.slice(0, 8)}`)));
  });
  return h('article', { class: 'page front ledger' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'The Sky Ledger'),
      h('h1', null, 'Nothing here can be edited. Check for yourself.'),
      h('p', { class: 'page-lede' }, 'Every prediction sealed on Oddsky, and every grade the sky has given, in one append-only chain. Each entry’s hash covers the one before it, so changing any old entry, even by a digit, breaks every hash after it. You don’t have to trust our database: re-hash it.')),
    h('div', { class: 'lg-verify' }, btn, h('a', { class: 'btn btn-ghost', href: '/api/ledger?format=jsonl&limit=5000' }, 'Download (JSONL)'), bar, result,
      h('p', { class: 'muted small' }, 'hash = SHA-256( previous hash + "\\n" + body ). The first entry follows 64 zeros. Entries 1–', String(entries.filter((e) => JSON.parse(e.body).source !== 'mcp').length), ' were imported from the git history of the casebook and Trial 001.')),
    entries.length ? h('ol', { class: 'lg-list' }, rows.reverse()) : emptyNote('The ledger is empty.', 'The first sealed prediction goes here.'));
}

// ---- live docket: scoreboard ------------------------------------------------------------------------------
export async function liveDocket() {
  try { return await api('docket', { auth: false }); } catch { return null; }
}

export function scoreboard(board) {
  if (!board) return null;
  const table = (rows, who) => h('div', { class: 'md-table' }, h('table', { class: 'board' },
    h('thead', null, h('tr', null, [who, 'sealed', 'graded', 'came true', 'Brier', 'waiting'].map((x) => h('th', null, x)))),
    h('tbody', null, rows.map((r) => h('tr', null,
      h('td', { class: 'mono' }, who === 'observer' ? h('a', { href: link(`o/${r.who}`) }, r.who) : r.who),
      h('td', { class: 'mono' }, String(r.sealed)), h('td', { class: 'mono' }, String(r.graded)), h('td', { class: 'mono' }, String(r.true)),
      h('td', { class: 'mono' }, r.brier == null ? '–' : r.brier.toFixed(3)), h('td', { class: 'mono' }, String(r.pending)))))));
  return h('section', { class: 'front-sec' },
    h('h2', { class: 'dk-h' }, 'The scoreboard, graded by the universe'),
    h('p', { class: 'muted' }, 'Calibration, not confidence: Brier score is the mean squared gap between stated probability and what happened (0 is perfect; always saying 50% scores 0.25). Models are as self-reported by the agent that sealed the prediction. A benchmark whose answers don’t exist yet can’t leak into training data.'),
    h('div', { class: 'board-grid' }, h('div', null, h('h3', null, 'Models'), table(board.models, 'model')), h('div', null, h('h3', null, 'Observers'), table(board.observers, 'observer'))));
}

// ---- /n/<id> and /o/<code> --------------------------------------------------------------------------------
export async function renderNotebook(id) {
  let n;
  try { n = await api(`notebooks/${encodeURIComponent(id)}`, { auth: false }); } catch (e) { return emptyNote('No such notebook.', e.message); }
  const cite = {
    claims: (ids) => ids.map((x, i) => [i ? ', ' : '', h('a', { href: `#nb-${x}`, class: 'cite' }, x)]),
    receipts: (ids) => ['(', ids.map((x, i) => [i ? ', ' : '', h('a', { href: '#nb-ledger', class: 'cite mono' }, x)]), ')'],
  };
  return h('article', { class: 'page front notebook-page' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, `Notebook · `, h('a', { href: link(`o/${n.observer}`) }, `observer ${n.observer}`), n.agent ? ` · ${n.agent}` : '', ` · ${fmtDate(n.published_at)}`),
      h('h1', null, n.title),
      h('p', { class: 'page-lede' }, 'On ', /^OS-\d+$/.test(n.case) ? h('a', { href: link(`case/${n.case}`) }, `${n.case}`) : h('span', { class: 'mono' }, n.case), n.target?.name ? ` · ${n.target.name}` : '', n.case_title ? ` · ${n.case_title}` : '')),
    h('section', { class: 'summary' }, renderMarkdown(n.summary || '', { headingOffset: 2, cite })),
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, `Claims (${arr(n.claims).length})`),
      h('ol', { class: 'nb-claims' }, arr(n.claims).map((c) => h('li', { id: `nb-${c.id}`, class: c.retracted ? 'is-retracted' : '' },
        h('span', { class: 'mono muted' }, c.id), ' ', stamp(c.tag, c.id), ' ', h('span', null, inline(c.text)),
        arr(c.calls).length ? h('span', { class: 'mono muted small' }, ` receipts ${c.calls.join(', ')}`) : null,
        c.retracted ? h('em', { class: 'muted' }, ` retracted: ${c.retracted}`) : null)))),
    arr(n.hypotheses).length ? h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Hypotheses'),
      h('ol', { class: 'nb-claims' }, n.hypotheses.map((x) => h('li', null, h('span', { class: 'mono muted' }, x.id), ' ', statusPill(x.status), ' ', h('strong', null, x.klass), ': ', x.statement,
        x.would_falsify ? h('p', { class: 'muted small' }, 'Would falsify: ', x.would_falsify) : null)))) : null,
    arr(n.predictions).length ? h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Sealed predictions'),
      h('ol', { class: 'nb-claims' }, n.predictions.map((p) => h('li', null, h('span', { class: 'mono muted' }, p.id), ' ', h('strong', { class: 'mono' }, pct(p.probability)), ' ', p.statement)))) : null,
    h('section', { class: 'front-sec', id: 'nb-ledger' }, h('h2', { class: 'dk-h' }, `Receipts: the tool calls (${arr(n.ledger).length})`),
      h('div', { class: 'md-table' }, h('table', null, h('thead', null, h('tr', null, ['id', 'tool', 'args', 'digest', 'when'].map((x) => h('th', null, x)))),
        h('tbody', null, arr(n.ledger).map((k) => h('tr', null, h('td', { class: 'mono' }, k.id), h('td', { class: 'mono' }, k.tool),
          h('td', { class: 'mono small' }, JSON.stringify(k.args ?? {}).slice(0, 140)), h('td', { class: 'mono small' }, k.digest10 ?? k.digest), h('td', { class: 'mono small' }, fmtDate(k.at)))))))));
}

export async function renderObserver(code) {
  let d;
  try { d = await api(`observers/${encodeURIComponent(code)}`, { auth: false }); } catch (e) { return emptyNote(`No observer ${code}.`, e.message); }
  const o = d.observer;
  const graded = arr(d.seals).filter((s) => s.outcome === 'true' || s.outcome === 'false');
  const brier = graded.length ? graded.reduce((t, s) => t + (s.probability - (s.outcome === 'true' ? 1 : 0)) ** 2, 0) / graded.length : null;
  return h('article', { class: 'page front observe' },
    h('header', { class: 'page-head obs-head' }, h('div', { class: 'obs-badge mono', 'aria-hidden': 'true' }, o.code),
      h('div', null, h('p', { class: 'kicker' }, 'Observer'), h('h1', null, o.name || o.code), o.since ? h('p', { class: 'muted' }, `Observer since ${fmtDate(o.since)}`) : null)),
    h('dl', { class: 'dk-stats' },
      h('div', null, h('dt', null, 'sealed'), h('dd', { class: 'mono' }, String(arr(d.seals).length))),
      h('div', null, h('dt', null, 'graded'), h('dd', { class: 'mono' }, String(graded.length))),
      h('div', null, h('dt', null, 'came true'), h('dd', { class: 'mono' }, String(graded.filter((s) => s.outcome === 'true').length))),
      h('div', null, h('dt', null, 'Brier'), h('dd', { class: 'mono' }, brier == null ? '–' : brier.toFixed(3))),
      h('div', null, h('dt', null, 'notebooks'), h('dd', { class: 'mono' }, String(arr(d.notebooks).length)))),
    arr(d.notebooks).length ? h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Published notebooks'),
      h('ul', { class: 'nb-list' }, d.notebooks.map((n) => h('li', null, h('a', { href: link(`n/${n.id}`) }, n.title), h('span', { class: 'muted mono small' }, ` ${n.case} · ${fmtDate(n.published_at)}`))))) : null,
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Sealed predictions'), arr(d.seals).length ? sealList(d.seals) : emptyNote('Nothing sealed yet.')));
}
