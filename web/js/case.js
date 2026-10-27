// The case page: one star, its data on a shared time axis, and the argument about what it is.

import {
  h, arr, isEmpty, fmtDate, fmtInt, fmtNum, fmtSigned, pct, fmtRA, fmtDec, mjdToIso, mjdToYear, klassLabel,
  pretty, jumpTo, dateToMjd,
} from './util.js';
import { createFigure, figureTable, seriesCsv, gaiaV } from './figure.js';
import { stamp, stampLegend, ladder, statusPill, agentBlock, emptyNote, sectionHead, starterPrompt } from './components.js';
import { renderMarkdown, inline } from './markdown.js';
import { trialTeaser } from './pages.js';

const SURVEY_NAMES = { gaia: 'Gaia DR3', neowise: 'NEOWISE', aavso: 'AAVSO', ztf: 'ZTF', asassn: 'ASAS-SN', tess: 'TESS' };

export function renderCase(payload, { home = false, index = null } = {}) {
  const c = payload?.case ?? {};
  const id = c.id ?? 'OS-?';
  const target = c.target ?? {};
  const ledger = new Map(arr(payload.ledger).map((k) => [k.id, k]));
  const claims = arr(c.claims);
  const claimIds = new Set(claims.map((x) => x.id));

  const annotations = arr(c.predictions).filter((p) => p.check && Number.isFinite(p.check.start)).map((p) => ({
    id: p.id, start: p.check.start, end: p.check.end, baseline: p.check.baseline ?? null, resolved: !!p.resolution,
  }));

  const credits = observerCredits(payload.provenance);

  // ---- header ----
  const gaiaAlias = arr(target.aliases).find((a) => /^Gaia DR3/i.test(a));
  const head = h('header', { class: 'case-head' },
    home ? h('p', { class: 'home-intro' },
      h('strong', null, 'A real star, its data, and the argument about what it is.'), ' ',
      'Oddsky is an open observatory for curious people and their AI agents: every claim is tagged, every number has a receipt, and predictions are graded by the sky.') : null,
    h('div', { class: 'case-tabline' },
      h('span', { class: 'case-tab' }, h('span', { class: 'case-tab-k' }, 'Case file'), h('span', { class: 'mono' }, id)),
      h('span', { class: 'case-coords mono' },
        target.name ? h('span', { class: 'target-name' }, target.name) : null,
        target.ra != null ? h('span', null, `α ${fmtRA(target.ra)}`) : null,
        target.dec != null ? h('span', null, `δ ${fmtDec(target.dec)}`) : null,
        gaiaAlias || target.gaia_source_id ? h('span', { class: 'hide-md' }, gaiaAlias ?? `Gaia DR3 ${target.gaia_source_id}`) : null),
      h('div', { class: 'case-status', title: 'Where this case stands on the discovery ladder' }, ladder(c.status, { compact: true }))),
    h('h1', { class: 'case-title' }, c.title || target.name || id),
    c.hook ? h('p', { class: 'case-hook' }, inline(c.hook)) : null,
  );

  // ---- figure ----
  const fig = createFigure(payload, { annotations, caseId: id });
  const table = figureTable(payload);
  const csvBtn = h('button', { type: 'button', class: 'linkish' }, 'Download all points (CSV)');
  csvBtn.addEventListener('click', () => {
    const blob = new Blob([seriesCsv(payload)], { type: 'text/csv' });
    const a = h('a', { href: URL.createObjectURL(blob), download: `${id}-lightcurves.csv` });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  });
  const figSection = h('section', { class: 'case-fig', id: 'figure', 'aria-label': 'Light curves' },
    fig,
    h('figcaption', { class: 'fig-caption' }, caption(payload, credits, annotations)),
    table ? h('details', { class: 'fig-table' }, h('summary', null, 'Data as a table'), table, h('p', null, csvBtn)) : null,
    facts(payload),
  );

  // ---- rail ----
  const rail = h('aside', { class: 'rail' }, h('div', { class: 'rail-sticky' },
    agentBlock(id),
    toc(c, payload),
  ));

  // ---- the argument ----
  const body = h('div', { class: 'case-body' },
    home ? trialTeaser(index) : null,
    c.summary ? h('section', { class: 'summary', id: 'summary' }, renderMarkdown(c.summary, { headingOffset: 2 })) : null,
    claimsSection(claims, ledger, id),
    hypothesesSection(arr(c.hypotheses), claimIds, new Set(claims.filter((x) => x.retracted).map((x) => x.id))),
    predictionsSection(arr(c.predictions), arr(c.hypotheses)),
    skepticSection(payload.skeptic, id),
    provenanceSection(payload.provenance, credits),
    investigationsSection(arr(payload.investigations), id, ledger),
    literatureSection(arr(c.literature)),
  );

  return h('article', { class: 'case' }, h('div', { class: 'case-grid' }, head, figSection, rail, body));
}

// ---- figure caption -------------------------------------------------------------------------
function caption(payload, credits, annotations) {
  const ser = payload.series ?? {};
  const keys = Object.keys(ser).filter((k) => arr(ser[k]?.t).length);
  const parts = [h('span', { class: 'fig-num' }, 'Figure 1.'), ' '];
  const name = payload.case?.target?.name ?? 'This star';
  parts.push(`${name} on one time axis. `);
  const opt = keys.filter((k) => !k.startsWith('NEOWISE') && !k.startsWith('TESS'));
  if (opt.length) {
    const aavso = credits.find((x) => x.survey === 'aavso');
    const bins = [...new Set(opt.map((k) => ser[k].binned_days).filter(Boolean))].sort((a, b) => a - b);
    parts.push(h('em', null, 'Optical: '), aavso ? aavso.text : opt.map((k) => k.replace(':', ' ')).join(', '),
      bins.length ? `; dense series are plotted as ${bins.length > 1 ? `${bins[0]}–${bins[bins.length - 1]}` : bins[0]}-day medians` : '', '. ');
    if (opt.some((k) => /vis\.?$/i.test(k))) parts.push('Visual (by-eye) estimates are drawn as faint grey dots. ');
    if (gaiaV(payload.context?.gaia) != null) parts.push('The dark rule is Gaia’s 2014–17 mean brightness converted to V (Riello et al. 2021), extended as a dashed reference. ');
  }
  if (keys.some((k) => k.startsWith('NEOWISE'))) {
    const n = ser['NEOWISE:W1']?.t?.length ?? 0;
    parts.push(h('em', null, 'Infrared: '), `NEOWISE W1 (3.4 µm) and W2 (4.6 µm), ${n ? `${n} visits, ` : ''}one point per ~6-month visit with ±1σ error bars; `,
      'the colour panel pairs W1 and W2 taken within a day (up is redder, i.e. relatively more 4.6 µm light, as from warm dust). ');
  }
  if (keys.some((k) => k.startsWith('TESS'))) parts.push(h('em', null, 'TESS: '), 'each sector is a ~27-day sliver, so it gets its own small panel below. ');
  parts.push('Magnitude axes are inverted: up is brighter. ');
  if (annotations.length) parts.push('Dashed brackets mark the windows in which sealed predictions will be checked; light shading marks their baselines. ');
  return parts;
}

/** "observers (good points): HMB:7115, ABC:12" → credit lines (the note lists the top observers only). */
function observerCredits(prov) {
  const out = [];
  for (const [key, p] of Object.entries(prov ?? {})) {
    for (const note of arr(p?.notes)) {
      const m = /^observers?[^:]*:\s*(.+)$/i.exec(note);
      if (!m) continue;
      const obs = m[1].split(/[,;]\s*|\s+/).map((x) => x.split(':')).filter((x) => x[0]).map(([code, n]) => ({ code, n: +n || 0 })).sort((a, b) => b.n - a.n);
      const listed = obs.reduce((t, o) => t + o.n, 0);
      const total = Math.max(listed, p.rows_kept ?? 0);
      const text = obs.length === 1 && listed >= total
        ? `${fmtInt(total)} measurements by AAVSO observer ${obs[0].code}`
        : `${fmtInt(total)} measurements by AAVSO observers, led by ${obs.slice(0, 3).map((o) => o.code).join(', ')}${obs.length > 3 ? ' and others' : ''}`;
      out.push({ survey: key, observers: obs, total, text });
    }
  }
  return out;
}

// ---- rail: facts & contents ------------------------------------------------------------------
function facts(payload) {
  const g = payload.context?.gaia ?? {};
  const t = payload.case?.target ?? {};
  const rows = [];
  const add = (k, v, note) => { if (v != null && v !== '' && v !== '–') rows.push(h('div', null, h('dt', null, k), h('dd', null, v, note ? h('span', { class: 'muted' }, ` ${note}`) : null))); };
  add('Gaia G', g.G != null ? fmtNum(g.G, 2) : null, 'mag');
  const dr3 = arr(t.aliases).find((a) => /^Gaia DR3/i.test(a))?.replace(/^Gaia DR3\s*/i, '') ?? t.gaia_source_id;
  add('BP − RP', g.bp_rp != null ? fmtNum(g.bp_rp, 2) : null);
  add('Teff', g.teff_gspphot != null ? fmtInt(g.teff_gspphot) : null, 'K');
  add('Distance', g.distance_pc != null ? fmtInt(g.distance_pc) : null, g.parallax_over_error ? `pc (ϖ/σ ${fmtInt(g.parallax_over_error)})` : 'pc');
  add('Abs. G', g.abs_G != null ? fmtNum(g.abs_G, 2) : null, 'mag');
  add('RUWE', g.ruwe != null ? fmtNum(g.ruwe, 2) : null);
  add('Gaia DR3', dr3 ? h('span', { class: 'id-long' }, String(dr3)) : null);
  const nb = arr(payload.context?.neighbors);
  if (nb.length) {
    const near = nb.filter((n) => n.sep_arcsec <= 6.1);
    add('Neighbours', `${near.length} within 6.1″`, near.length ? `(brightest ${pct(Math.max(...near.map((n) => n.flux_ratio_G || 0)), 1)} of G flux)` : '');
  }
  const series = Object.entries(payload.series ?? {});
  const bySurvey = {};
  for (const [, s] of series) {
    const k = s.survey;
    bySurvey[k] ??= { n: 0, t0: Infinity, t1: -Infinity, bands: [] };
    bySurvey[k].n += s.n_raw ?? arr(s.t).length;
    bySurvey[k].bands.push(s.band);
    if (arr(s.t).length) { bySurvey[k].t0 = Math.min(bySurvey[k].t0, s.t[0]); bySurvey[k].t1 = Math.max(bySurvey[k].t1, s.t[s.t.length - 1]); }
  }
  const dataRows = Object.entries(bySurvey).map(([k, v]) => h('div', null, h('dt', null, k), h('dd', null, fmtInt(v.n),
    h('span', { class: 'muted' }, ` pts · ${Number.isFinite(v.t0) ? `${Math.floor(mjdToYear(v.t0))}–${Math.floor(mjdToYear(v.t1))}` : ''}`))));
  if (!rows.length && !dataRows.length) return null;
  return h('section', { class: 'facts', 'aria-label': 'The star and the data' },
    rows.length ? h('div', { class: 'facts-col' }, h('h3', { class: 'rail-h' }, 'The star'),
      describeStar(g) ? h('p', { class: 'facts-lede' }, describeStar(g)) : null, h('dl', { class: 'facts-dl' }, rows)) : null,
    dataRows.length ? h('div', { class: 'facts-col' }, h('h3', { class: 'rail-h' }, 'The data'), h('dl', { class: 'facts-dl' }, dataRows)) : null);
}

function describeStar(g) {
  if (g.teff_gspphot == null || g.abs_G == null) return '';
  const t = g.teff_gspphot, M = g.abs_G;
  const kind = t > 7500 ? 'hot' : t > 5200 && t < 6300 ? 'Sun-like' : t >= 6300 ? 'F-type' : t > 3900 ? 'K-type' : 'cool M-type';
  const lum = M < 1.5 && t < 5500 ? 'giant' : M < 2.5 ? 'bright' : 'main-sequence';
  return `By its Gaia colour and luminosity, a ${kind} ${lum} star ${g.distance_pc ? `about ${fmtInt(Math.round(g.distance_pc / 10) * 10)} pc away` : ''}.`;
}

function toc(c, payload) {
  const items = [
    ['figure', 'Light curves'],
    ['claims', 'Claims', arr(c.claims).length],
    ['hypotheses', 'Hypotheses', arr(c.hypotheses).length],
    ['predictions', 'Predictions', arr(c.predictions).length],
    ['skeptic', 'Skeptic', payload.skeptic ? arr(payload.skeptic.checks).length : 0],
    ['provenance', 'Provenance', Object.keys(payload.provenance ?? {}).length],
    ['investigations', 'Investigations', arr(payload.investigations).length],
  ];
  return h('nav', { class: 'toc', 'aria-label': 'On this page' },
    h('h3', { class: 'rail-h' }, 'In this file'),
    h('ol', null, items.map(([id, label, n]) => h('li', null,
      h('button', { type: 'button', class: 'toc-link', onclick: () => jumpTo(id) }, label, n != null ? h('span', { class: 'toc-n mono' }, String(n)) : null)))));
}

// ---- claims ----------------------------------------------------------------------------------
function claimsSection(claims, ledger, caseId) {
  const nRetracted = claims.filter((x) => x.retracted).length;
  const sec = h('section', { class: 'sec', id: 'claims' }, sectionHead('claims', 'Claims', nRetracted ? `${claims.length - nRetracted} + ${nRetracted} retracted` : claims.length, 'Every claim says how we know it. Every number has a receipt: the tool calls it rests on.'));
  sec.append(stampLegend());
  if (!claims.length) {
    sec.append(emptyNote('No claims yet.', 'The data is in; the argument hasn’t started. Point your agent at this case and it can add the first one, tagged honestly.'));
    return sec;
  }
  const list = h('ol', { class: 'claims' });
  for (const cl of claims) {
    const receipt = h('div', { class: 'receipt', hidden: true });
    const calls = arr(cl.calls);
    const btns = calls.map((k) => {
      const b = h('button', { type: 'button', class: `receipt-btn mono ${ledger.has(k) ? '' : 'is-missing'}`, 'aria-expanded': 'false' }, k);
      b.addEventListener('click', () => {
        const open = b.getAttribute('aria-expanded') === 'true';
        btns.forEach((x) => x.setAttribute('aria-expanded', 'false'));
        if (open) { receipt.hidden = true; return; }
        b.setAttribute('aria-expanded', 'true');
        receipt.replaceChildren(ledgerEntry(k, ledger.get(k)));
        receipt.hidden = false;
      });
      return b;
    });
    list.append(h('li', { class: `claim claim-${cl.tag} ${cl.retracted ? 'is-retracted' : ''}`, id: `claim-${cl.id}` },
      h('div', { class: 'claim-gutter' }, h('span', { class: 'claim-id mono' }, cl.id), stamp(cl.tag, cl.id)),
      h('div', { class: 'claim-main' },
        h('p', { class: 'claim-text' }, inline(cl.text)),
        cl.retracted ? h('p', { class: 'claim-retracted' }, h('span', { class: 'retracted-k' }, 'Retracted'), ' ', typeof cl.retracted === 'string' ? inline(cl.retracted) : '') : null,
        h('div', { class: 'claim-meta' },
          h('span', { class: 'by' }, cl.author || 'unknown'), cl.at ? h('span', null, fmtDate(cl.at)) : null,
          h('span', { class: 'receipts' }, calls.length ? ['receipts ', ...btns] : h('span', { class: 'no-receipt' }, 'no receipt'))),
        receipt)));
  }
  sec.append(list);
  return sec;
}

function ledgerEntry(id, k) {
  if (!k) return h('div', { class: 'ledger missing' }, h('p', null, h('strong', { class: 'mono' }, id), ' is cited but missing from this case’s ledger. A claim without a receipt should not be trusted.'));
  return h('div', { class: 'ledger' },
    h('div', { class: 'ledger-head' }, h('span', { class: 'mono ledger-id' }, k.id), h('code', { class: 'ledger-tool' }, `${k.tool}()`),
      h('span', { class: 'muted' }, [k.author, k.at ? fmtDate(k.at) : null].filter(Boolean).join(' · '))),
    h('pre', { class: 'ledger-args' }, h('code', null, pretty(k.args ?? {}))),
    h('p', { class: 'ledger-digest' }, h('span', { class: 'muted' }, 'result digest '), h('code', null, k.digest ?? '–'),
      h('span', { class: 'muted' }, ' · sha256 of the tool’s output; rerun it and compare')));
}

// ---- hypotheses ------------------------------------------------------------------------------
const STATUS_ORDER = { favored: 0, live: 1, disfavored: 2, rejected: 3 };

function hypothesesSection(hyps, claimIds, retracted = new Set()) {
  const sec = h('section', { class: 'sec', id: 'hypotheses' }, sectionHead('hypotheses', 'Hypotheses', hyps.length, 'Competing explanations. Each must say what evidence would sink it.'));
  if (!hyps.length) {
    sec.append(emptyNote('No hypotheses yet.', 'What could make a star do this? Dust, a companion, the instrument, a neighbour? Each idea goes here with the observation that would kill it.'));
    return sec;
  }
  const sorted = [...hyps].sort((a, b) => (STATUS_ORDER[a.status] ?? 1) - (STATUS_ORDER[b.status] ?? 1) || (b.confidence ?? 0) - (a.confidence ?? 0));
  const ref = (ids, cls) => arr(ids).map((cid) => h('button', { type: 'button', class: `claim-ref mono ${cls} ${claimIds.has(cid) ? '' : 'is-missing'} ${retracted.has(cid) ? 'is-retracted' : ''}`, title: retracted.has(cid) ? `${cid} was retracted` : null, onclick: () => jumpTo(`claim-${cid}`) }, cid));
  sec.append(h('div', { class: 'hyps' }, sorted.map((x) => h('article', { class: `hyp hyp-${x.status ?? 'live'}`, id: `hyp-${x.id}` },
    h('header', { class: 'hyp-head' }, h('span', { class: 'hyp-id mono' }, x.id), h('span', { class: 'hyp-klass' }, klassLabel(x.klass)), statusPill(x.status)),
    h('p', { class: 'hyp-statement' }, inline(x.statement)),
    x.confidence != null ? h('div', { class: 'conf', title: `confidence ${pct(x.confidence)}` },
      h('span', { class: 'conf-label' }, 'confidence'),
      h('span', { class: 'conf-track' }, h('span', { class: 'conf-fill', style: { width: `${Math.max(0, Math.min(1, x.confidence)) * 100}%` } })),
      h('span', { class: 'conf-val mono' }, pct(x.confidence))) : null,
    h('dl', { class: 'hyp-links' },
      arr(x.supports).length ? h('div', null, h('dt', null, 'supported by'), h('dd', null, ref(x.supports, 'is-for'))) : null,
      arr(x.conflicts).length ? h('div', null, h('dt', null, 'in tension with'), h('dd', null, ref(x.conflicts, 'is-against'))) : null),
    x.would_falsify ? h('p', { class: 'falsify' }, h('span', { class: 'falsify-k' }, 'Would be falsified by'), ' ', inline(x.would_falsify)) : null,
    x.author ? h('p', { class: 'hyp-by muted' }, x.author) : null,
  ))));
  return sec;
}

// ---- predictions -----------------------------------------------------------------------------
const STAT = { median: 'the median', faintest: 'the faintest nightly median', brightest: 'the brightest nightly median', amplitude: 'the amplitude (faintest minus brightest nightly median)' };
const fmtMag = (v) => String(+Math.abs(v).toPrecision(v !== 0 && Math.abs(v) < 0.1 ? 2 : 3));

export function checkInEnglish(ch) {
  if (!ch) return '';
  const ser = String(ch.series ?? '').replace(':', ' ');
  const stat = STAT[ch.statistic] ?? ch.statistic ?? 'the median';
  const win = `between ${mjdToIso(ch.start)} and ${mjdToIso(ch.end)}`;
  const vv = fmtMag(Number(ch.value));
  let rel;
  if (Array.isArray(ch.baseline) && ch.baseline.length === 2) {
    const base = `its median over ${mjdToIso(ch.baseline[0])} to ${mjdToIso(ch.baseline[1])}`;
    if (ch.statistic === 'amplitude') rel = `${ch.op === '<' ? 'less' : 'more'} than ${vv} mag larger than over ${base.replace('its median over ', '')}`;
    else if (ch.op === '>') rel = ch.value >= 0 ? `more than ${vv} mag fainter than ${base}` : `no more than ${vv} mag brighter than ${base}`;
    else rel = ch.value > 0 ? `less than ${vv} mag fainter than ${base} (or brighter)` : `more than ${vv} mag brighter than ${base}`;
  } else if (ch.statistic === 'amplitude') {
    rel = `${ch.op === '<' ? 'less than' : 'more than'} ${vv} mag`;
  } else {
    rel = ch.op === '>' ? `fainter than ${fmtNum(ch.value, 2)} mag` : `brighter than ${fmtNum(ch.value, 2)} mag`;
  }
  return `${stat.charAt(0).toUpperCase()}${stat.slice(1)} of ${ser} ${win} will be ${rel}.`;
}

const OUTCOME = { true: 'came true', false: 'did not happen', unresolvable: 'unresolvable' };

function predictionsSection(preds, hyps) {
  const sec = h('section', { class: 'sec', id: 'predictions' }, sectionHead('predictions', 'Predictions', preds.length,
    'Sealed in advance, stated as a check the archive can run by itself, with a probability attached. The sky grades them, not us.'));
  if (!preds.length) {
    sec.append(emptyNote('No sealed predictions yet.', 'A hypothesis that predicts nothing can’t lose. The first one to commit to a number goes here.'));
    return sec;
  }
  const hypMap = new Map(hyps.map((x) => [x.id, x]));
  const now = dateToMjd(new Date());
  sec.append(h('div', { class: 'envelopes' }, preds.map((p) => {
    const r = p.resolution;
    const open = !!r;
    const hyp = p.hypothesis ? hypMap.get(p.hypothesis) : null;
    const due = p.resolve_by ? Math.round((new Date(`${p.resolve_by}T00:00:00Z`) - Date.now()) / 86400000) : null;
    const checkStarted = p.check && now >= p.check.start;
    return h('article', { class: `envelope ${open ? `is-open outcome-${r.outcome}` : 'is-sealed'}`, id: `pred-${p.id}` },
      h('div', { class: 'env-flap', 'aria-hidden': 'true' }),
      h('div', { class: 'env-paper' },
        h('header', { class: 'env-head' },
          h('span', { class: 'env-id mono' }, p.id),
          h('span', { class: 'env-prob', title: 'stated probability that the check comes out true' }, h('span', { class: 'mono' }, pct(p.probability)), h('span', { class: 'env-prob-k' }, 'likely'))),
        hyp ? h('button', { type: 'button', class: 'env-hyp', onclick: () => jumpTo(`hyp-${hyp.id}`) }, `if ${hyp.id} · ${klassLabel(hyp.klass)} is right`) : p.hypothesis ? h('span', { class: 'env-hyp' }, `if ${p.hypothesis} is right`) : null,
        h('p', { class: 'env-statement' }, inline(p.statement)),
        p.check ? h('p', { class: 'env-check' }, h('span', { class: 'env-check-k' }, 'The check'), ' ', checkInEnglish(p.check)) : h('p', { class: 'env-check is-missing' }, 'No machine-checkable form yet; this one will need a human referee.'),
        p.check ? h('details', { class: 'env-raw' }, h('summary', null, 'machine-readable'), h('pre', null, h('code', null, pretty(p.check)))) : null,
        h('dl', { class: 'env-meta' },
          h('div', null, h('dt', null, 'sealed'), h('dd', null, fmtDate(p.registered_at) || '–')),
          !open && p.check ? h('div', null, h('dt', null, 'window closes'), h('dd', null, fmtDate(mjdToIso(p.check.end)))) : null,
          h('div', null, h('dt', null, open ? 'opened' : 'opens by'), h('dd', null, open ? fmtDate(r.resolved_at) : (fmtDate(p.resolve_by) || '–'),
            !open && due != null ? h('span', { class: 'muted' }, due > 0 ? ` · in ${fmtInt(due)} days` : checkStarted ? ' · due now' : ' · overdue') : null)),
          p.author ? h('div', null, h('dt', null, 'by'), h('dd', null, p.author)) : null),
        open ? h('div', { class: 'env-result' },
          h('span', { class: `verdict verdict-${r.outcome}` }, OUTCOME[r.outcome] ?? r.outcome),
          h('p', null, r.observed != null ? ['observed ', h('strong', { class: 'mono' }, `${fmtSigned(r.observed, 3)} mag`), ` from ${fmtInt(r.n_points)} points. `] : null, r.note ? inline(r.note) : null)) : null,
      ),
      !open ? h('div', { class: 'env-seal', 'aria-hidden': 'true' }, h('span', null, p.id)) : null,
    );
  })));
  return sec;
}

// ---- skeptic ---------------------------------------------------------------------------------
const GLYPH = { pass: '✓', warn: '!', fail: '✗', skip: '–' };

function skepticSection(sk, caseId) {
  const sec = h('section', { class: 'sec', id: 'skeptic' }, sectionHead('skeptic', 'The Skeptic', sk ? arr(sk.checks).length : null,
    'Code, not a vibe: the boring ways a star can fool you, checked mechanically before anyone gets excited.'));
  if (!sk) {
    sec.append(emptyNote('The Skeptic hasn’t run on this case yet.', h('p', null, 'Run it yourself: ', h('code', null, `oddsky skeptic ${caseId}`), ', or ask your agent to start there.')));
    return sec;
  }
  const checks = arr(sk.checks);
  const counts = ['fail', 'warn', 'pass', 'skip'].map((k) => [k, checks.filter((c) => c.status === k).length]).filter(([, n]) => n);
  sec.append(h('div', { class: 'skeptic-summary' },
    h('p', { class: 'tally' }, counts.map(([k, n]) => h('span', { class: `tally-item st-${k}` }, h('span', { class: 'glyph' }, GLYPH[k]), ` ${n} ${k}`))),
    sk.summary ? h('p', null, inline(sk.summary)) : null,
    sk.generated_at ? h('p', { class: 'muted small' }, `generated ${fmtDate(sk.generated_at)}${sk.version ? ` · oddsky ${sk.version}` : ''}`) : null));
  sec.append(h('ul', { class: 'checklist' }, checks.map((ch) => {
    const nums = ch.numbers && !isEmpty(ch.numbers) ? ch.numbers : null;
    return h('li', { class: `check st-${ch.status}` },
      h('span', { class: 'check-box', title: ch.status, 'aria-label': ch.status }, GLYPH[ch.status] ?? '?'),
      h('div', { class: 'check-main' },
        h('p', { class: 'check-title' }, ch.title ?? ch.id, h('span', { class: 'check-status' }, ch.status)),
        ch.finding ? finding(ch.finding) : null,
        nums ? h('details', { class: 'check-nums' }, h('summary', null, 'numbers'), numbersTable(nums)) : null));
  })));
  return sec;
}

/** Long findings (one lists 200+ observers) are clipped with a "show all" toggle. */
function finding(text) {
  const LIMIT = 320;
  if (text.length <= LIMIT) return h('p', { class: 'check-finding' }, inline(text));
  const cut = text.lastIndexOf(',', LIMIT) > 200 ? text.lastIndexOf(',', LIMIT) : LIMIT;
  const p = h('p', { class: 'check-finding' }, `${text.slice(0, cut)} … `);
  const more = h('button', { type: 'button', class: 'linkish' }, `show all (${fmtInt(text.length)} characters)`);
  more.addEventListener('click', () => p.replaceChildren(...inline(text)));
  p.append(more);
  return p;
}

function numbersTable(nums) {
  return kvTable(Object.entries(nums), 0);
}

const MAX_INLINE_KEYS = 8;
const MAX_LIST = 12;

function kvTable(entries, depth) {
  return h('table', { class: 'kv' }, h('tbody', null, entries.map(([k, v]) => h('tr', null,
    h('th', null, String(k).replace(/_/g, ' ')), h('td', null, kvValue(v, depth))))));
}

/** Numbers can be scalars, short lists, small dicts (inline) or huge dicts (e.g. 200 observers: scroll box). */
function kvValue(v, depth) {
  if (v == null) return h('code', null, '–');
  if (typeof v === 'number') return h('code', null, Number.isInteger(v) ? fmtInt(v) : String(+v.toPrecision(5)));
  if (typeof v !== 'object') return h('code', null, String(v));
  if (Array.isArray(v)) {
    if (v.every((x) => x == null || typeof x !== 'object')) {
      const shown = v.slice(0, MAX_LIST).map((x) => (typeof x === 'number' ? +x.toPrecision(5) : x)).join(', ');
      return h('code', null, `[${shown}${v.length > MAX_LIST ? `, … +${v.length - MAX_LIST} more` : ''}]`);
    }
    return h('div', { class: 'kv-scroll' }, h('pre', null, h('code', null, pretty(v))));
  }
  let entries = Object.entries(v);
  if (entries.length <= MAX_INLINE_KEYS && depth < 2) return kvTable(entries, depth + 1);
  if (entries.every(([, x]) => typeof x === 'number')) entries = entries.sort((p, q) => q[1] - p[1]);
  return h('div', { class: 'kv-scroll' }, h('p', { class: 'kv-count muted' }, `${fmtInt(entries.length)} entries`), kvTable(entries, depth + 1));
}

// ---- provenance ------------------------------------------------------------------------------
function provenanceSection(prov, credits) {
  const entries = Object.entries(prov ?? {});
  const sec = h('section', { class: 'sec', id: 'provenance' }, sectionHead('provenance', 'Provenance', entries.length,
    'Where every row came from, when, and which cuts removed what.'));
  if (!entries.length) { sec.append(emptyNote('No archive queries recorded yet.')); return sec; }
  for (const cr of credits) {
    sec.append(h('div', { class: 'credit' }, h('span', { class: 'credit-k' }, 'With thanks'),
      h('div', null,
        h('p', null, h('strong', null, `Optical light curve: ${cr.text}.`), ' Amateur astronomers have watched this star night after night; their measurements are the backbone of this case.'),
        cr.observers.length > 1 ? h('ul', { class: 'observers' }, cr.observers.map((o) => h('li', null, h('span', { class: 'mono obs-code' }, o.code), h('span', { class: 'mono muted' }, fmtInt(o.n))))) : null)));
  }
  const order = { ok: 0, empty: 1, unavailable: 2 };
  entries.sort((a, b) => (order[a[1]?.status] ?? 0) - (order[b[1]?.status] ?? 0));
  sec.append(h('div', { class: 'prov-list' }, entries.map(([key, p]) => {
    const raw = p.rows_raw ?? 0, kept = p.rows_kept ?? 0;
    const frac = raw ? Math.min(1, kept / raw) : 0;
    return h('article', { class: `prov st-${p.status ?? 'ok'}` },
      h('header', { class: 'prov-head' },
        h('h3', null, SURVEY_NAMES[key] ?? key), h('span', { class: `prov-status st-${p.status}` }, p.status ?? 'ok'),
        h('span', { class: 'prov-archive' }, p.archive ?? '')),
      h('div', { class: 'prov-rows' },
        h('span', { class: 'mono' }, fmtInt(raw)), h('span', { class: 'arrow' }, ' rows → '), h('span', { class: 'mono' }, fmtInt(kept)), ' kept',
        raw ? h('span', { class: 'kept-bar', title: `${pct(frac, 1)} kept` }, h('span', { style: { width: `${frac * 100}%` } })) : null,
        p.retrieved_at ? h('span', { class: 'muted prov-when' }, `retrieved ${fmtDate(p.retrieved_at)}`) : null),
      arr(p.cuts).length ? h('ul', { class: 'prov-cuts' }, arr(p.cuts).map((c) => h('li', null, h('code', null, c)))) : null,
      arr(p.notes).length ? h('ul', { class: 'prov-notes' }, arr(p.notes).map((n) => h('li', null, n))) : null,
      p.query && !isEmpty(p.query) ? h('details', { class: 'prov-query' }, h('summary', null, 'query'), h('pre', null, h('code', null, p.query.adql ?? pretty(p.query)))) : null);
  })));
  return sec;
}

// ---- investigations & literature -------------------------------------------------------------
function investigationsSection(invs, caseId, ledger = new Map()) {
  const sec = h('section', { class: 'sec', id: 'investigations' }, sectionHead('investigations', 'Investigations', invs.length, 'Write-ups, one per investigator, kept next to the data they argue about. [C3] links to a claim; (K12) opens the tool call behind a number.'));
  if (!invs.length) {
    sec.append(emptyNote('No write-ups yet.', h('p', null, 'Start one: ', h('code', { class: 'inline-prompt' }, starterPrompt(caseId)))));
    return sec;
  }
  const expand = (g) => {
    const m = /K(\d+)\s*[-–]\s*K?(\d+)/.exec(g);
    if (!m) return [g.trim()];
    const a = +m[1], b = +m[2];
    return b >= a && b - a < 25 ? Array.from({ length: b - a + 1 }, (_, i) => `K${a + i}`) : [`K${a}`, `K${b}`];
  };
  const cite = {
    claims: (ids) => h('span', { class: 'cite' }, '[', ids.map((cid, i) => [i ? ', ' : '', h('button', { type: 'button', class: 'cite-claim mono', title: `jump to claim ${cid}`, onclick: () => jumpTo(`claim-${cid}`) }, cid)]), ']'),
    receipts: (groups) => h('span', { class: 'cite' }, '(', groups.map((g, i) => {
      const ids = expand(g);
      const b = h('button', { type: 'button', class: `cite-receipt mono ${ids.every((k) => ledger.has(k)) ? '' : 'is-missing'}`, 'aria-expanded': 'false', title: 'show the tool call' }, g.replace(/\s*-\s*/, '–'));
      b.addEventListener('click', () => {
        if (b._panel) { b._panel.remove(); b._panel = null; b.setAttribute('aria-expanded', 'false'); return; }
        const panel = h('div', { class: 'cite-panel' }, ids.map((k) => ledgerEntry(k, ledger.get(k))));
        const block = b.closest('li, p, td, blockquote') ?? b.parentElement;
        if (block.tagName === 'LI' || block.tagName === 'TD') block.append(panel); else block.after(panel);
        b._panel = panel; b.setAttribute('aria-expanded', 'true');
      });
      return [i ? ', ' : '', b];
    }), ')'),
  };
  for (const inv of invs) {
    sec.append(h('article', { class: 'notebook' },
      h('header', { class: 'notebook-head mono' }, `investigations/${inv.file}`),
      renderMarkdown(inv.markdown, { headingOffset: 2, cite })));
  }
  return sec;
}

function literatureSection(lit) {
  if (!lit.length) return null;
  return h('section', { class: 'sec', id: 'literature' }, sectionHead('literature', 'Literature', lit.length),
    h('ul', { class: 'lit' }, lit.map((r) => h('li', null,
      h('a', { class: 'mono', href: `https://ui.adsabs.harvard.edu/abs/${encodeURIComponent(r.bibcode)}/abstract`, rel: 'noopener', target: '_blank' }, r.bibcode),
      r.note ? [' — ', inline(r.note)] : null))));
}
