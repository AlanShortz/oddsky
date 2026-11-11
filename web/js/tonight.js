// Tonight: stars a small telescope can reach, and what watching them would help settle.
// Data: data/tonight.json (site/build.py, from the case files). The visitor's place is only ever used in the browser.

import { h, arr, link, pct, fmtRA, fmtDec, isoDay } from './util.js';
import { night, season, everUp, monthRuns, nextMinima, observable } from './skycalc.js';

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const KEY = 'oddsky.place';
const PRESETS = [['50°N', 50], ['40°N', 40], ['30°N', 30], ['Equator', 0], ['35°S', -35]];
const wrapLon = (lon) => ((((lon + 180) % 360) + 360) % 360) - 180;

function loadPlace() {
  try { const p = JSON.parse(localStorage.getItem(KEY)); if (p && isFinite(p.lat) && isFinite(p.lon)) return p; } catch { /* none */ }
  return { lat: 40, lon: wrapLon(-new Date().getTimezoneOffset() / 4), assumed: true };
}
const savePlace = (p) => { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* private mode */ } };
const hhmm = (d) => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const dayTime = (d) => `${d.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' })}, ${hhmm(d)}`;
const untilText = (iso, now) => {
  const n = (new Date(iso + 'T00:00:00Z') - now) / 86400000;
  return n <= 0 ? null : n < 60 ? `in ${Math.round(n)} days` : n < 730 ? `in ${Math.round(n / 30.44)} months` : `in ${(n / 365.25).toFixed(1)} years`;
};
const seasonText = (months) => (months.length === 12 ? 'all year' : monthRuns(months).map(([a, b]) => (a === b ? MON[a] : `${MON[a]}–${MON[b]}`)).join(', '));

function skyLine(x, place, now) {
  if (!everUp(x.dec, place.lat)) return h('p', { class: 'tn-sky is-down' }, 'Never gets 30° above your horizon.');
  const n = night(x.ra, x.dec, place.lat, place.lon, now);
  const months = season(x.ra, x.dec, place.lat, place.lon, now.getUTCFullYear());
  const when = months.length ? seasonText(months) : null;
  if (n.hoursUp >= 0.5 && n.best) {
    return h('p', { class: 'tn-sky is-up' }, h('strong', null, 'Up tonight'), ` for ${n.hoursUp.toFixed(1)} h of darkness, highest (${Math.round(n.best.alt)}°) at ${hhmm(n.best.date)}.`,
      when ? h('span', { class: 'muted' }, ` Above 30° in the dark: ${when}.`) : null);
  }
  if (!n.darkStart) return h('p', { class: 'tn-sky is-down' }, 'No darkness at your latitude tonight.', when ? ` Above 30° in the dark: ${when}.` : '');
  return h('p', { class: 'tn-sky is-down' }, 'Not 30° up in the dark tonight.', when ? ` In season ${when}.` : ' From here it never is for a full hour.');
}

function eclipseLine(x, place, now) {
  const e = x.ephemeris;
  if (!e) return null;
  const half = (e.half_width_h ?? 3) * 3600000;
  const long = (e.half_width_h ?? 3) > 12;                 // an eclipse lasting days: ask about nights, not instants
  const mins = nextMinima(e.t0_mjd, e.period_d, now, long ? 6 : Math.ceil(400 / e.period_d));
  const up = (t) => observable(x.ra, x.dec, place.lat, place.lon, t);
  const nightsUp = (d) => {
    let n = 0;
    const w = Math.round((e.half_width_h ?? 3) / 24);
    for (let k = -w; k <= w; k++) if (night(x.ra, x.dec, place.lat, place.lon, new Date(+d + k * 86400000)).hoursUp >= 1) n += 1;
    return n;
  };
  // a short eclipse counts when the minimum and at least one branch are in the dark sky
  const ok = long ? mins.filter((d) => nightsUp(d) >= 3) : mins.filter((d) => up(d) && (up(new Date(+d - half)) || up(new Date(+d + half))));
  const part = (d) => (up(new Date(+d - half)) && up(new Date(+d + half)) ? 'whole eclipse' : up(new Date(+d - half)) ? 'ingress and minimum' : 'minimum and egress');
  return h('div', { class: 'tn-eph' },
    h('p', { class: 'tn-label' }, `Next ${e.what} within reach from here`),
    ok.length ? h('ul', { class: 'tn-ephlist mono' }, ok.slice(0, 3).map((d) => h('li', null,
      long ? `around ${isoDay(d)}: ${nightsUp(d)} nights within a week of it` : `${dayTime(d)} (mid-eclipse, your clock; ${part(d)} in your dark sky)`)))
      : h('p', { class: 'muted tn-note' }, `None from here in the next ${long ? `${mins.length} eclipses` : '400 days'}.`),
    h('p', { class: 'muted tn-note' }, `Predicted from MJD ${e.t0_mjd} + ${e.period_d} × E (`, h('a', { href: link(`case/${x.case}`) }, `claim ${e.claim}`),
      '), from survey photometry: times are UTC with no heliocentric correction (up to 8 minutes) and have not been checked against a timed eclipse. Report your own times in HJD or BJD as usual.'));
}

function judgedRow(x, j, now) {
  const opens = untilText(j.window[0], now), closes = untilText(j.window[1], now);
  const baseOpen = j.baseline && !untilText(j.baseline[0], now) && untilText(j.baseline[1], now);
  const state = opens ? `window opens ${opens}` : closes ? `window open, closes ${closes}` : 'window closed';
  return h('li', { class: 'tn-judged' },
    h('p', { class: 'tn-j-head mono' }, h('a', { href: j.href }, `${x.case} ${j.id}`), ` · sealed at ${pct(j.probability)} · ${state}`),
    h('p', { class: 'tn-j-say' }, j.statement),
    h('p', { class: 'tn-j-judge' },
      j.amateur ? h('span', null, h('strong', null, `Checked on AAVSO ${j.band} photometry`), `, ${j.window[0]} to ${j.window[1]}. `,
        j.in_window ? `${j.in_window} points in the window in our copy.` : 'Without observations in that window it cannot be graded.')
        : h('span', null, `Checked on the ${j.survey} survey’s ${j.band} photometry, ${j.window[0]} to ${j.window[1]}. `,
          j.copy_ends ? `Our copy of the public archive ends ${j.copy_ends}; public releases lag, and if none reaches the window the check is recorded as unresolvable. Photometry filed with the AAVSO would be reported beside the verdict, not as the verdict.` : null),
      j.baseline ? h('span', { class: baseOpen ? 'tn-now' : null }, ` It is compared with ${j.baseline[0]} to ${j.baseline[1]}`,
        baseOpen ? h('strong', null, `, which is open now (${j.in_baseline} points in our copy)`) : `${j.in_baseline ? ` (${j.in_baseline} points in our copy)` : ''}`, '.') : null));
}

function card(x, place, now) {
  const ob = x.observers;
  const aladin = `https://aladin.cds.unistra.fr/AladinLite/?target=${encodeURIComponent(`${x.ra.toFixed(5)} ${x.dec >= 0 ? '+' : ''}${x.dec.toFixed(5)}`)}&fov=0.25&survey=P%2FDSS2%2Fcolor`;
  const read = x.latest.archive_read ? `; archive read ${x.latest.archive_read}` : '';
  return h('li', { class: 'tn-card' },
    h('header', { class: 'tn-head' },
      h('h3', null, h('a', { href: link(`case/${x.case}`) }, x.name)),
      h('p', { class: 'tn-sub' }, x.title)),
    h('dl', { class: 'tn-facts mono' },
      h('div', null, h('dt', null, 'where (J2000)'), h('dd', null, `${fmtRA(x.ra)}  ${fmtDec(x.dec)}`)),
      h('div', null, h('dt', null, 'brightness'), h('dd', null, `about ${x.typical_mag.toFixed(1)} in ${x.typical_band.replace('_', ' ')}`)),
      h('div', null, h('dt', null, 'last in our copy'), h('dd', null, `${x.latest.mag.toFixed(2)} (${x.latest.series.replace(':', ' ').replace('_', ' ')}) on ${x.latest.date}${read}`)),
      h('div', null, h('dt', null, 'AAVSO record'), h('dd', null,
        ob ? (ob.top_share >= 0.999 ? `one observer, ${ob.top}, supplied all ${ob.points.toLocaleString('en-US')} points`
          : `${ob.points.toLocaleString('en-US')} points from ${ob.more ? '12 or more' : ob.listed} observers; ${ob.top} supplied ${pct(ob.top_share)}`)
          : x.has_aavso_record ? 'AAVSO observers' : 'none in our copy: surveys only'))),
    skyLine(x, place, now),
    x.ask ? h('div', { class: 'tn-ask' },
      h('p', { class: 'tn-settles' }, h('span', { class: 'tn-label' }, 'Watching it would help settle'), x.ask.settles),
      h('p', { class: 'tn-want mono' }, `wanted: ${x.ask.bands}; ${x.ask.cadence}`),
      x.ask.note ? h('p', { class: 'muted tn-note' }, x.ask.note) : null) : null,
    eclipseLine(x, place, now),
    arr(x.judged).length ? h('ul', { class: 'tn-judgedlist' }, x.judged.map((j) => judgedRow(x, j, now))) : null,
    h('p', { class: 'tn-links' },
      h('a', { href: aladin, rel: 'noopener', target: '_blank' }, 'Find it (Aladin)'),
      x.aavso ? h('a', { href: `https://www.aavso.org/vsx/index.php?view=results.get&ident=${encodeURIComponent(x.aavso)}`, rel: 'noopener', target: '_blank' }, 'AAVSO index entry') : null,
      x.aavso ? h('a', { href: 'https://www.aavso.org/webobs', rel: 'noopener', target: '_blank' }, `Report to the AAVSO as “${x.aavso}”`)
        : h('span', { class: 'muted' }, 'Not in the AAVSO index, so it cannot be submitted there yet.'),
      h('a', { href: link(`case/${x.case}`) }, 'The case →')));
}

export function renderTonight(data) {
  const targets = arr(data?.targets);
  const now = new Date();
  let place = loadPlace();
  const list = h('ol', { class: 'tn-list' });
  const placeNote = h('span', { class: 'tn-place-now mono' });
  const amateur = (x) => arr(x.judged).some((j) => j.amateur);
  const draw = () => {
    placeNote.textContent = `${Math.abs(place.lat).toFixed(0)}°${place.lat >= 0 ? 'N' : 'S'}, ${Math.abs(place.lon).toFixed(0)}°${place.lon >= 0 ? 'E' : 'W'}${place.assumed ? ' (40°N assumed; longitude from your clock)' : ''}`;
    const groups = [
      ['Predictions checked on AAVSO photometry', 'Sealed in advance, with a probability. Each check runs on what observers have filed with the AAVSO when its window closes.', targets.filter(amateur)],
      ['Watching would help settle something', 'Open questions in the casebook that a small telescope can move.', targets.filter((x) => !amateur(x) && x.ask)],
      ['Already well watched', 'In the casebook, with long AAVSO records and nothing specific asked.', targets.filter((x) => !amateur(x) && !x.ask)],
    ];
    list.replaceChildren(...groups.filter(([, , xs]) => xs.length).map(([title, lede, xs]) => h('li', { class: 'tn-group' },
      h('h2', { class: 'dk-h' }, title), h('p', { class: 'muted tn-group-lede' }, lede),
      h('ol', { class: 'tn-cards' }, xs.map((x) => card(x, place, now))))));
  };
  const setPlace = (p) => { place = p; savePlace(p); draw(); };
  const judged = targets.reduce((n, x) => n + arr(x.judged).filter((j) => j.amateur).length, 0);
  const timed = targets.filter((x) => x.ephemeris).length;
  const geo = h('button', { class: 'btn btn-ghost small', type: 'button' }, 'Use my location');
  geo.addEventListener('click', () => {
    if (!navigator.geolocation) { geo.textContent = 'Location unavailable'; return; }
    geo.textContent = 'Asking…';
    navigator.geolocation.getCurrentPosition(
      (pos) => { geo.textContent = 'Use my location'; setPlace({ lat: pos.coords.latitude, lon: pos.coords.longitude }); },
      () => { geo.textContent = 'Location unavailable'; });
  });
  draw();
  return h('article', { class: 'page front tonight' },
    h('header', { class: 'page-head' },
      h('p', { class: 'kicker' }, 'Tonight'),
      h('h1', null, 'The sky grades us. Here is where to look.'),
      h('p', { class: 'page-lede' }, 'Oddsky seals predictions about real stars, and several are checked on photometry that amateur observers file with the AAVSO. These are the stars in the casebook a small telescope can reach, what watching each would help settle, and when each is up from where you are. Observations go to the AAVSO, as for any variable star, not to us; we read them from there.')),
    h('dl', { class: 'dk-stats' },
      h('div', null, h('dt', null, 'stars within reach'), h('dd', { class: 'mono' }, String(targets.length))),
      h('div', null, h('dt', null, 'sealed predictions checked on AAVSO data'), h('dd', { class: 'mono' }, String(judged))),
      h('div', null, h('dt', null, 'with an ephemeris'), h('dd', { class: 'mono' }, String(timed)))),
    h('div', { class: 'tn-place' },
      h('span', { class: 'tn-place-label' }, 'Observing from '), placeNote,
      h('span', { class: 'tn-presets' }, PRESETS.map(([label, lat]) => {
        const b = h('button', { class: 'btn btn-ghost small', type: 'button' }, label);
        b.addEventListener('click', () => setPlace({ lat, lon: place.lon }));
        return b;
      }), geo),
      h('span', { class: 'muted tn-privacy' }, 'Your place stays in your browser.')),
    list,
    h('section', { class: 'front-sec tn-how' },
      h('h2', { class: 'dk-h' }, 'How a measurement counts'),
      h('p', null, 'Submit photometry to the AAVSO under the name shown, with its comparison sequence, as you would for any variable star. Oddsky reads the AAVSO International Database and credits observers by code. When a prediction’s window closes, its check runs on whatever the archive then holds, and the result goes on ', h('a', { href: link('docket') }, 'the Docket'), '.'),
      h('p', { class: 'muted' }, '“Last in our copy” is the newest point in the archive copy each case holds, with the day that copy was read; the star may have been observed since. Rise and set are computed in your browser for a Sun 12° below the horizon and a star at least 30° up. ',
        h('a', { href: '/tonight.md' }, 'This page as plain text'), ' · ', h('a', { href: '/data/tonight.json' }, 'JSON'))));
}
