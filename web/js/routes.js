// The routes the app renders, as a pure function of the path (no DOM, so node can test it:
// tests/test_web_routes.py). Anything that isn't one of these belongs to the server
// (/api/oauth/github/start, /api/ledger?format=jsonl, /mcp, /authorize …) and gets a real page load.

const PAGES = ['cases', 'trials', 'about', 'hunts', 'docket', 'agents', 'observe', 'ledger', 'privacy', 'terms'];

/** '/case/OS-0001' or 'case/OS-0001' → { name: 'case', id: 'OS-0001' }; unknown → { name: 'notfound' }. */
export function parseRoute(path) {
  const raw = String(path).replace(/^\/+/, '').split('?')[0].replace(/\.html$/, '');
  const parts = raw.split('/').filter(Boolean).map(decodeURIComponent);
  if (!parts.length || parts[0] === 'index') return { name: 'home' };
  if (parts[0] === 'case' && parts[1]) return { name: 'case', id: parts[1] };
  if (parts[0] === 'hunt' && parts[1]) return { name: 'hunt', id: parts[1] };
  if (parts[0] === 'n' && parts[1]) return { name: 'notebook', id: parts[1] };
  if (parts[0] === 'o' && parts[1]) return { name: 'observer', id: parts[1].toUpperCase() };
  if (PAGES.includes(parts[0])) return { name: parts[0] };
  return { name: 'notfound', what: raw };
}
