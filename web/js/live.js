// The live side of oddsky.ai, backed by the hosted service (/api, /mcp on Cloud Run):
// observers and passkeys (/observe), the Sky Ledger with in-browser verification (/ledger),
// published notebooks (/n/<id>) and observer pages (/o/<CODE>).

import { h, arr, fmtDate, pct, link, copyText } from './util.js';
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

/** Keep the masthead chip in sync with who is signed in. */
export async function syncChip() {
  const a = document.querySelector('[data-route="observe"]');
  if (!a) return;
  if (!session.token) { a.textContent = 'Observe'; a.classList.remove('is-in'); return; }
  try {
    const me = session.observer ?? (session.observer = (await api('me')).observer);
    a.textContent = me.code; a.classList.add('is-in'); a.title = `Signed in as observer ${me.code}`;
  } catch (e) { if (e.status === 401) { session.token = null; a.textContent = 'Observe'; } }
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
export function renderObserve(rerender) {
  const page = h('article', { class: 'page front observe' });
  if (session.token) { profile(page, rerender); return page; }
  const status = h('p', { class: 'obs-status', role: 'status' });
  const code = h('input', { class: 'obs-code mono', maxlength: 5, placeholder: 'ASH', autocomplete: 'off', spellcheck: 'false', 'aria-label': 'Observer code' });
  const name = h('input', { class: 'obs-name', maxlength: 80, placeholder: 'Your name (optional, shown on your notebooks)', 'aria-label': 'Name' });
  const go = h('button', { type: 'button', class: 'btn' }, 'Create my passkey');
  let t;
  code.addEventListener('input', () => {
    code.value = code.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    clearTimeout(t);
    if (!code.value) { status.textContent = ''; return; }
    t = setTimeout(async () => {
      try { const r = await api('observers/check', { method: 'POST', body: { code: code.value }, auth: false }); status.textContent = r.problem ? `${r.code}: ${r.problem}` : `${r.code} is yours if you want it.`; status.className = `obs-status ${r.problem ? 'is-bad' : 'is-ok'}`; } catch { /* offline */ }
    }, 250);
  });
  go.addEventListener('click', async () => {
    go.disabled = true; status.textContent = 'Waiting for your passkey…'; status.className = 'obs-status';
    try { await register(code.value, name.value); await syncChip(); rerender(); }
    catch (e) { status.textContent = e.name === 'NotAllowedError' ? 'Passkey cancelled.' : e.message; status.className = 'obs-status is-bad'; go.disabled = false; }
  });
  const signin = h('button', { type: 'button', class: 'btn btn-ghost' }, 'Sign in with my passkey');
  const sstatus = h('p', { class: 'obs-status', role: 'status' });
  signin.addEventListener('click', async () => {
    try { await login(); await syncChip(); rerender(); } catch (e) { sstatus.textContent = e.name === 'NotAllowedError' ? 'Passkey cancelled.' : e.message; sstatus.className = 'obs-status is-bad'; }
  });
  page.append(
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'Become an observer'),
      h('h1', null, 'Get your observer code.'),
      h('p', { class: 'page-lede' }, 'AAVSO has given its observers three-letter codes for a century; the light curve in our first case is 7,115 measurements by HMB. Oddsky does the same for you and your agents. No email, no password: a passkey on your device. Then your agent gets the whole observatory in one line, and everything it finds is credited to your code.')),
    h('div', { class: 'obs-grid' },
      h('section', { class: 'door obs-new' },
        h('p', { class: 'door-k mono' }, 'New observer'),
        h('label', { class: 'obs-label' }, 'Observer code ', h('span', { class: 'muted' }, '(2–5 letters or digits)')), code, name, go, status),
      h('section', { class: 'door' },
        h('p', { class: 'door-k mono' }, 'Already an observer'),
        h('h2', null, 'Welcome back'), h('p', { class: 'door-note' }, 'Your passkey lives on your device (and syncs through iCloud Keychain or Google Password Manager).'), signin, sstatus)),
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'What you get'),
      h('div', { class: 'agent-grid' },
        h('div', null, h('h3', null, 'The observatory, hosted'), h('p', null, 'Every Oddsky tool over MCP from any agent, no Python install: Gaia, NEOWISE, AAVSO, TESS, ZTF, the Skeptic.')),
        h('div', null, h('h3', null, 'A notebook that keeps'), h('p', null, 'Your agent’s claims, hypotheses and ledger of tool calls persist between sessions. Publish a notebook when it is worth checking.')),
        h('div', null, h('h3', null, 'A record graded by the universe'), h('p', null, 'Predictions are sealed on the public Sky Ledger and graded by the archives. Your calibration, and your model’s, is on the scoreboard.')),
        h('div', null, h('h3', null, 'No private predictions'), h('p', null, 'Sealing is publishing, so nobody can seal fifty and show the three that came true. That is what makes the record worth anything.')))));
  return page;
}

async function profile(page, rerender) {
  page.append(h('p', { class: 'loading' }, 'Opening your notebook…'));
  let me;
  try { me = await api('me'); } catch (e) {
    if (e.status === 401) { session.token = null; await syncChip(); rerender(); return; }
    page.replaceChildren(emptyNote('The observatory didn’t answer.', e.message)); return;
  }
  const o = me.observer;
  const keyOut = h('div', { class: 'key-out' });
  const label = h('input', { class: 'obs-name', placeholder: 'What will use this key? e.g. Claude Code on my laptop', maxlength: 60 });
  const mint = h('button', { type: 'button', class: 'btn' }, 'Mint an instrument key');
  mint.addEventListener('click', async () => {
    mint.disabled = true;
    try { const k = await api('keys', { method: 'POST', body: { label: label.value } }); keyOut.replaceChildren(keyBlock(k.key)); } catch (e) { keyOut.textContent = e.message; }
    mint.disabled = false;
  });
  const out = h('button', { type: 'button', class: 'linkish' }, 'Sign out');
  out.addEventListener('click', async () => { try { await api('logout', { method: 'POST' }); } catch { /* ignore */ } session.token = null; session.observer = null; await syncChip(); rerender(); });
  page.replaceChildren(
    h('header', { class: 'page-head obs-head' },
      h('div', { class: 'obs-badge mono', 'aria-hidden': 'true' }, o.code),
      h('div', null, h('p', { class: 'kicker' }, 'Observer'), h('h1', null, o.name || o.code),
        h('p', { class: 'muted' }, `Observer since ${fmtDate(o.since)} · `, h('a', { href: link(`o/${o.code}`) }, 'your public page'), ' · ', out))),
    h('section', { class: 'door' },
      h('p', { class: 'door-k mono' }, 'Connect an agent'),
      h('h2', null, 'One key per agent'),
      h('p', { class: 'door-note' }, 'Keys let an agent work as you. You see a key once; mint another any time, and revoke any you lose.'),
      h('div', { class: 'mint-row' }, label, mint), keyOut,
      arr(me.keys).length ? h('ul', { class: 'key-list' }, me.keys.map((k) => {
        const rv = h('button', { type: 'button', class: 'linkish' }, 'revoke');
        rv.addEventListener('click', async () => { await api('keys/revoke', { method: 'POST', body: { prefix: k.prefix } }); rerender(); });
        return h('li', null, h('span', { class: 'mono' }, `${k.prefix}…`), ' ', k.label, h('span', { class: 'muted' }, ` · ${fmtDate(k.created_at)} · `), rv);
      })) : null),
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Your sealed predictions'),
      arr(me.seals).length ? sealList(me.seals) : emptyNote('Nothing sealed yet.', 'When your agent calls register_prediction, it lands on the Sky Ledger and here.')),
    h('section', { class: 'front-sec' }, h('h2', { class: 'dk-h' }, 'Your notebooks'),
      arr(me.notebook_cases).length ? h('p', null, 'Cases in your notebook: ', me.notebook_cases.map((c, i) => [i ? ', ' : '', h('span', { class: 'mono' }, c)])) : null,
      arr(me.notebooks).length ? h('ul', { class: 'nb-list' }, me.notebooks.map((n) => h('li', null, h('a', { href: link(`n/${n.id}`) }, n.title), h('span', { class: 'muted mono small' }, ` ${n.case} · ${fmtDate(n.published_at)}`))))
        : h('p', { class: 'muted' }, 'Nothing published yet. Ask your agent to publish_notebook when it has something worth checking.')));
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
