# Oddsky web viewer

A static case viewer. No build step, no dependencies: `index.html`, ES modules in `js/`, one
stylesheet in `css/`, and JSON in `data/`. It works from any static host at any sub-path
(GitHub Pages included) because every URL is relative and routing uses the hash.

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

## Figure notes

- x is the calendar year, `2000 + (MJD − 51544.5) / 365.25`. The hover readout gives the date and MJD.
- Panels: (a) optical (AAVSO, ASAS-SN, ZTF…), (b) NEOWISE W1/W2, (c) W1 − W2 for visits whose
  W1 and W2 times agree within 1 day, (d) TESS (relative mag), only if present. Each panel has its
  own y-range, refit to the visible points when you zoom. Magnitude axes are inverted.
- Colour follows the band (B blue, V green, R vermilion, I plum, W1 ochre, W2 crimson); shape
  follows the survey (squares for R/I/W2, triangles for ASAS-SN, diamonds for ZTF) as a second
  channel. The palettes were checked with the dataviz validator against both paper surfaces.
- Dense series (more than 160 points in view) are drawn as one `<path>`; sparse ones get error bars.
- Prediction windows (`check.start`/`end`) are bracketed and dashed; their `baseline` is shaded.
- `series[key].flagged` points are hidden until "show flagged points" is ticked, then drawn as
  hollow grey rings with the reason in the tooltip.
