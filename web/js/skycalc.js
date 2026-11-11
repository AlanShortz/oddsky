// Where a star is in the sky, for a place and a night. Pure functions (no DOM), so node can test them against
// astropy: tests/test_tonight.py. Low-precision formulae (Meeus, ch. 12, 13, 25): good to a few arcminutes, which is
// far finer than "is it up tonight".

const RAD = Math.PI / 180;
export const jdOf = (date) => date.getTime() / 86400000 + 2440587.5;

/** Greenwich mean sidereal time, degrees. */
export function gmst(jd) {
  const t = (jd - 2451545.0) / 36525;
  const g = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t;
  return ((g % 360) + 360) % 360;
}

/** The Sun's apparent right ascension and declination, degrees. */
export function sunRaDec(jd) {
  const n = jd - 2451545.0;
  const L = (280.460 + 0.9856474 * n) % 360;
  const g = ((357.528 + 0.9856003 * n) % 360) * RAD;
  const lam = (L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * RAD;
  const eps = (23.439 - 0.0000004 * n) * RAD;
  const ra = Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam)) / RAD;
  return { ra: (ra + 360) % 360, dec: Math.asin(Math.sin(eps) * Math.sin(lam)) / RAD };
}

/** Altitude in degrees of (ra, dec) seen from (lat, lon east-positive) at Julian date jd. No refraction. */
export function altitude(ra, dec, lat, lon, jd) {
  const ha = (gmst(jd) + lon - ra) * RAD;
  const s = Math.sin(lat * RAD) * Math.sin(dec * RAD) + Math.cos(lat * RAD) * Math.cos(dec * RAD) * Math.cos(ha);
  return Math.asin(Math.max(-1, Math.min(1, s))) / RAD;
}

/**
 * The coming night at (lat, lon): from the next local noon-to-noon span containing darkness, sampled every 10 minutes.
 * Dark means the Sun is more than `sunLimit` degrees below the horizon (12 = nautical: stars for photometry).
 * Returns { darkStart, darkEnd (Dates, or null where the Sun never gets that low), hoursDark, hoursUp (dark and the
 * star above `minAlt`), best: { date, alt } (highest in the dark), maxAlt (the star's highest that day, dark or not) }.
 */
export function night(ra, dec, lat, lon, from = new Date(), { sunLimit = 12, minAlt = 30 } = {}) {
  // start at the local solar noon before `from`
  const solarNoonOffsetMs = (12 - lon / 15) * 3600000;                 // UTC time of local mean noon
  let start = new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate()) + solarNoonOffsetMs);
  while (start.getTime() > from.getTime()) start = new Date(start.getTime() - 86400000);
  while (from.getTime() - start.getTime() >= 86400000) start = new Date(start.getTime() + 86400000);
  const span = scan(ra, dec, lat, lon, start, sunLimit, minAlt);
  // a visitor in the morning has last night behind them: show the night to come
  return span.darkEnd && span.darkEnd.getTime() < from.getTime() ? scan(ra, dec, lat, lon, new Date(start.getTime() + 86400000), sunLimit, minAlt) : span;
}

function scan(ra, dec, lat, lon, start, sunLimit, minAlt) {
  const step = 600000;
  let darkStart = null, darkEnd = null, dark = 0, up = 0, best = null, maxAlt = -90;
  for (let k = 0; k <= 144; k++) {
    const d = new Date(start.getTime() + k * step), jd = jdOf(d);
    const sun = sunRaDec(jd);
    const alt = altitude(ra, dec, lat, lon, jd);
    if (alt > maxAlt) maxAlt = alt;
    if (altitude(sun.ra, sun.dec, lat, lon, jd) < -sunLimit) {
      if (!darkStart) darkStart = d;
      darkEnd = d; dark += 1;
      if (alt >= minAlt) up += 1;
      if (!best || alt > best.alt) best = { date: d, alt };
    }
  }
  return { darkStart, darkEnd, hoursDark: dark / 6, hoursUp: up / 6, best, maxAlt };
}

/** Months (0-11) in which the star is at least `minAlt` up for an hour or more of darkness, on the 15th. */
export function season(ra, dec, lat, lon, year, opts = {}) {
  const out = [];
  for (let m = 0; m < 12; m++) if (night(ra, dec, lat, lon, new Date(Date.UTC(year, m, 15, 12)), opts).hoursUp >= 1) out.push(m);
  return out;
}

/** Can the star ever reach `minAlt` from this latitude? */
export const everUp = (dec, lat, minAlt = 30) => 90 - Math.abs(lat - dec) >= minAlt;

/** Runs of consecutive months as [[first, last], ...], joining December to January. */
export function monthRuns(months) {
  if (!months.length) return [];
  const runs = [];
  for (const m of months) {
    const last = runs[runs.length - 1];
    if (last && m === last[1] + 1) last[1] = m; else runs.push([m, m]);
  }
  if (runs.length > 1 && runs[0][0] === 0 && runs[runs.length - 1][1] === 11) { runs[0][0] = runs.pop()[0]; }
  return runs;
}

/** The next `count` times of minimum (Dates) after `from`, for T0 (MJD) and a period in days. */
export function nextMinima(t0Mjd, periodDays, from = new Date(), count = 40) {
  const mjd = from.getTime() / 86400000 + 40587;
  const e0 = Math.ceil((mjd - t0Mjd) / periodDays);
  return Array.from({ length: count }, (_, k) => new Date(((t0Mjd + (e0 + k) * periodDays) - 40587) * 86400000));
}

/** Is the Sun more than `sunLimit` below the horizon and the star at least `minAlt` up, at this moment? */
export function observable(ra, dec, lat, lon, date, { sunLimit = 12, minAlt = 30 } = {}) {
  const jd = jdOf(date), sun = sunRaDec(jd);
  return altitude(sun.ra, sun.dec, lat, lon, jd) < -sunLimit && altitude(ra, dec, lat, lon, jd) >= minAlt;
}
