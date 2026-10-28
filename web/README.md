# Oddsky web viewer

A static case viewer. No build step, no dependencies: `index.html`, ES modules in `js/`, one
stylesheet in `css/`, and JSON in `data/`. It works from any static host at any sub-path
(GitHub Pages included) because every URL is relative and routing uses the hash.

## Design

Two registers. **The night** is the home page: `js/sky.js`, a WebGL planetarium of 90,020 Hipparcos stars
(`data/sky/stars.bin`, packed by `site/sky_stars.py`) under a procedural Milky Way laid out in real galactic
coordinates, with every case at its true position, its brightness played back from its own light curve
(`data/sky/cases.json`, built by `site/build.py`), a guided tour, and a time scrubber. `/?star=OS-0014` flies to a
case. A plain scroll always scrolls the page; pinch, ⌘/Ctrl+scroll or the +/− buttons zoom the sky, and on phones
vertical swipes scroll while horizontal ones turn the sky. **The journal** is everything else: case files, hunts, the docket, the ledger. Calm, dense, precise.

- The mark is a finding chart: two tick marks pointing at one star in a field, the way variable-star papers mark
  their target. On the home page the ticks slide in, acquiring it.
- Cobalt (`--accent`) is the instrument. Pink (`--odd`, `--night-odd`) is only ever the anomaly.
- Type: Archivo (display, expanded widths), Source Serif 4 (reading), IBM Plex Mono (data). Self-hosted in `fonts/`.
- Red-light mode (the masthead toggle) keeps night vision, sky included.

## The public site (oddsky.ai)

`site/build.py` turns this folder into the public site in `dist/` (standard library only; Vercel runs it, see
`vercel.json`). It adds what a hash-routed viewer can't do: a real URL per page (`/case/OS-0014`) with its own
title, description and link preview (`og/<ID>.png`), a text prerender for crawlers and agents that don't run
JavaScript, `/hunts` and `/hunt/<ID>` (from `site/hunts.json` and each hunt's README), `/docket` plus
`docket.ics` (every sealed prediction, subscribable as a calendar), and the agent door: `/llms.txt`, and a
Markdown dossier per case (`/case/<ID>.md`).

```sh
python3 site/build.py --serve        # build and preview with clean URLs on :8765
heavy bash site/cards.sh             # (with the preview running) regenerate og/*.png, then rebuild
vercel deploy --scope tango-98e9ccfa # protected preview; see site/DEPLOY.md before --prod
```

## Regenerate the data

```sh
oddsky export-web          # writes web/data/index.json and web/data/cases/<ID>.json
```

Don't hand-edit `data/`; it is overwritten on every export.

## Serve locally

```sh
cd web && python3 -m http.server 8765
# open http://localhost:8765/
```

Opening `index.html` from `file://` won't work, because browsers block `fetch` there.

## Routes

| URL | View |
|---|---|
| `#/` | the featured case (`featured: true` in index.json, otherwise the first case) |
| `#/case/OS-0001` | one case |
| `#/cases` | the casebook, with each case's place on the discovery ladder |
| `#/trials` | blind and hindsight trial scorecards (`scorecards` in index.json) |
| `#/about` | what Oddsky is |

## Dev switches

| Query | Effect |
|---|---|
| `?fixture=1` | loads `dev/fixture-index.json` and `dev/fixture-<ID>.json` (sample claims, hypotheses, predictions, skeptic, ledger, investigation, flagged points, scorecards). Falls back to the real files when a fixture is missing. A "fixture data" badge is shown. |
| `?theme=dark` / `?theme=light` | force red-light (dark) or paper (light) mode. Otherwise the OS setting is used, and the masthead toggle's choice is saved in `localStorage`. |
| `?card=1` | bare 1200×630 composition used to make `og.png`. |

Query strings go before the hash: `http://localhost:8765/?fixture=1#/case/OS-0001`.

Rebuild the fixtures after re-exporting the real data:

```sh
python3 web/dev/make_fixtures.py   # standard library only; reads web/data, writes web/dev
```

The numbers in the sample claims are computed from the real light curves, but the argument
itself is sample text. `dev/fixture-scorecards.json` is hand-written sample scorecards.

## Link preview image

`og.png` is a screenshot of `?card=1#/` at 1200×630:

```sh
heavy "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
  --window-size=1200,630 --virtual-time-budget=5000 --screenshot=web/og.png "http://localhost:8765/?card=1#/"
```

Some link scrapers need an absolute `og:image`. Once the site has a public URL, change
`content="og.png"` in `index.html` to the full URL.

## Files

```
index.html          masthead, footer, meta tags; sets the theme before first paint
css/oddsky.css      the whole design: paper and red-light palettes, stamps, envelopes, figure styles
js/main.js          hash router and theme toggle
js/data.js          loading (relative URLs, ?fixture=1, Gaia source ids kept as strings)
js/figure.js        the hero figure: stacked panels on one time axis, hover, drag to zoom, table, CSV
js/case.js          the case page: claims with receipts, hypotheses, sealed predictions, skeptic, provenance
js/pages.js         casebook, trials, about, error pages
js/components.js    epistemic stamps, discovery ladder, status pills, "investigate with your agent"
js/markdown.js      a small safe Markdown renderer for investigations (builds DOM nodes, never parses HTML)
js/util.js          DOM helpers, MJD ↔ calendar, formatting
dev/                fixtures and the script that builds them
```

## Trials page

`#/trials` reads `index.json` → `scorecards`. Scorecards for the same `trial` are shown side by side. The page includes:

- the sealed hash with the `oddsky trial verify` command
- a metric comparison with the uniform-guess baseline (parsed from `summary.baseline_note`)
- a contamination callout built from per-case `recognised` flags
- a packet-by-packet table linking each packet to `real_case`
- hindsight forecasts as envelopes: `pending` ones stay sealed, with "opens <date>" taken from the MJD in the forecast's `note`
- an erratum box when `grader_v1.why_changed` is present, showing v1 against v2 outcomes

A one-line teaser for the trial appears on the home page. In investigations, `[C3]` links to the claim and `(K12)` / `(K36-K38)` open the ledger entries.

## Figure notes

- **Default view.** If the shown series span more than 25 years (R CrB, R Cyg, SS Cyg, EE Cep go back
  to the 1960s, and visual estimates to 1784), the figure opens on 2010 to now. "Full record" spans
  whatever series are currently switched on.
- **Which bands show by default.** Johnson-Cousins B V R I (and non-AAVSO surveys) are shown. Other AAVSO
  bands (CV/CR unfiltered, TB/TG/TR DSLR, SG/SR/SI Sloan, U) sit behind "+ N more bands". The AAVSO
  visual series (`Vis.`) is drawn as faint grey dots, hidden when a CCD V series exists. Series with no
  usable points (only flagged rows) aren't plotted.
- **Gaia reference.** When a V-like series is visible, the optical panel shows Gaia DR3's 2014–17 mean
  converted to V (Riello et al. 2021): `V = G − (−0.02704 + 0.01424c − 0.2156c² + 0.01426c³)`, `c = BP−RP`,
  for −0.5 < c < 5. It's solid over the Gaia epoch (MJD 56863–57901) and dashed elsewhere.
- **NEOWISE missing.** If NEOWISE was queried but gave no usable visits, the infrared panel is a one-line
  note saying why (saturation is detected from flagged rows or the Skeptic's `wise_saturation` check).
- **TESS** gets one small panel per sector below the main figure, using `context.tess.sectors`
  (t_start/t_end) when present, otherwise split at gaps longer than 5 days. All sectors share one y-range.
- **Bad JSON.** The loader reads bare `NaN`/`Infinity` (Python's `json.dumps` default) as `null`, and
  keeps 16+-digit `source_id`s as strings.


- x is the calendar year, `2000 + (MJD − 51544.5) / 365.25`. The hover readout gives the date and MJD.
- Panels: (a) optical (AAVSO, ASAS-SN, ZTF…), (b) NEOWISE W1/W2, (c) W1 − W2 for visits whose
  W1 and W2 times agree within 1 day, then the TESS sector panels. Each panel has its
  own y-range, refit to the visible points when you zoom. Magnitude axes are inverted.
- Colour follows the band (B blue, V green, R vermilion, I plum, W1 ochre, W2 crimson); shape
  follows the survey (squares for R/I/W2, triangles for ASAS-SN, diamonds for ZTF) as a second
  channel. The palettes were checked with the dataviz validator against both paper surfaces.
- Dense series (more than 160 points in view) are drawn as one `<path>`; sparse ones get error bars.
- Prediction windows (`check.start`/`end`) are bracketed and dashed; their `baseline` is shaded.
- `series[key].flagged` points are hidden until "show flagged points" is ticked, then drawn as
  hollow grey rings with the reason in the tooltip.
