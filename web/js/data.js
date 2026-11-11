// Data loading. The site is files: data/index.json and data/cases/<ID>.json, written by
// `oddsky export-web`. All URLs are relative so the site works from any sub-path.
//
// Dev switch: ?fixture=1 (before or after the #) loads dev/fixture-index.json and
// dev/fixture-<ID>.json instead, falling back to the real files when a fixture is missing.

const qs = new URLSearchParams(location.search);
const inHash = (k) => new RegExp(`[?&]${k}=([^&]*)`).exec(location.hash)?.[1];
export const FIXTURE = qs.get('fixture') === '1' || inHash('fixture') === '1';

const cache = new Map();
// Resolve data files against the site root (this module lives in js/), so pages at /case/OS-0001 work too.
const at = (path) => new URL(`../${path}`, import.meta.url).href;

// Gaia source ids exceed 2^53; quote them before JSON.parse so they survive intact.
const BIGINT_KEYS = /("(?:[a-z_]*source_id)"\s*:\s*)(-?\d{16,})/g;
// Python's json.dumps writes NaN/Infinity, which is not JSON; read them as null.
const NON_FINITE = /([:\[,]\s*)-?(?:NaN|Infinity)(?=\s*[,\]}])/g;

async function getJSON(url) {
  if (cache.has(url)) return cache.get(url);
  const p = fetch(at(url), { cache: 'no-cache' }).then(async (r) => {
    if (!r.ok) throw Object.assign(new Error(`${url}: HTTP ${r.status}`), { status: r.status });
    const text = await r.text();
    const fixed = text.replace(BIGINT_KEYS, '$1"$2"');
    try { return JSON.parse(fixed); } catch { return JSON.parse(fixed.replace(NON_FINITE, '$1null')); }
  });
  cache.set(url, p);
  p.catch(() => cache.delete(url));
  return p;
}

async function firstOf(urls) {
  let last;
  for (const u of urls) {
    try { return await getJSON(u); } catch (e) { last = e; }
  }
  throw last;
}

export async function loadIndex() {
  const idx = await firstOf(FIXTURE ? ['dev/fixture-index.json', 'data/index.json'] : ['data/index.json']);
  return { cases: Array.isArray(idx?.cases) ? idx.cases : [], scorecards: Array.isArray(idx?.scorecards) ? idx.scorecards : [] };
}

export async function loadCase(id) {
  if (!/^[\w.-]+$/.test(id)) throw new Error(`bad case id ${id}`);
  return firstOf(FIXTURE ? [`dev/fixture-${id}.json`, `data/cases/${id}.json`] : [`data/cases/${id}.json`]);
}

/** data/hunts.json and data/docket.json are written by site/build.py; plain web/ has neither. */
export const loadHunts = () => getJSON('data/hunts.json').catch(() => ({ hunts: [], wrong: [] }));
export const loadDocket = () => getJSON('data/docket.json').catch(() => ({ items: [] }));
/** data/trials.json (oddsky export-web): each trial's premise, revealed key and the held-back light curves. */
export const loadTrials = () => getJSON('data/trials.json').catch(() => ({ trials: [] }));

/** The home page sky: packed Hipparcos stars and each case's binned light curve. */
export async function loadSky() {
  const [stars, sky] = await Promise.all([fetch(at('data/sky/stars.bin')).then((r) => { if (!r.ok) throw new Error('stars'); return r.arrayBuffer(); }), getJSON('data/sky/cases.json')]);
  return { stars, sky };
}

export const featuredCase = (index) => index.cases.find((c) => c.featured) ?? index.cases[0] ?? null;
