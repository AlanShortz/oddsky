# Review: the "Tonight" page (independent, sceptical)

Reviewed 2026-11-11 in worktree `porto-v1`: `site/build.py` (`build_tonight`, `tonight_markdown`, `/tonight` route),
`site/tonight.json`, `web/js/tonight.js`, `web/js/skycalc.js`, the `.tn-*` CSS, `tests/test_tonight.py`, the build output
(`dist/data/tonight.json`, `dist/tonight.md`), both screenshots, and the case JSON for all 37 cases.

## Verdict

1. **Do not ship as is.** Five things on the page are wrong or would mislead an AAVSO observer: observer shares that are off
   by up to 20x, "last measured N days ago" that measures the age of our archive copy, two stars wrongly said to be absent
   from VSX, an eclipse ask (OS-0015) the case itself says is unobservable, and an ASASSN-21qj note that would damage its own grading.
2. The idea, the sky arithmetic (correct at every place and date I tried bar the morning case) and the "graded on AAVSO, cannot be
   graded without data" claim are sound: the grader really does return `unresolvable` below 3 points.
3. All five blockers are small fixes (one denominator, dates instead of ages, two `aavso` names, three rewordings). About half a day.

## What I checked and how

- Rebuilt (`python3 site/build.py`): 18 targets. Recomputed `n_90d`, `in_window`, typical magnitude, latest point and observer
  shares for all 18 from `web/data/cases/OS-*.json`. `n_90d`, `in_window`, `latest` reproduce exactly. Shares and typical
  magnitude do not mean what the page says (B1, S2).
- Read the grader, `src/oddsky/tools.py:678` (`evaluate`), and the AAVSO loader, `src/oddsky/data/aavso.py:48-75`.
- Queried the VSX copy at `vizier.idia.ac.za` (`B/vsx/vsx`, 5 arcsec cone) for the six Gaia-ID stars and NSV 1302.
- Ran `skycalc.js` under node for 12 edge cases (morning visit, date line, lon 210, midnight sun, polar night, low-culmination
  stars, the OS-0015 eclipse window).
- Links: Aladin Lite URL returns 200 with the expected page. `aavso.org` answers curl with a Cloudflare challenge (403), so the
  VSX and WebObs links could not be fetched; both formats match the documented ones (`index.php?view=results.get&ident=`, `/webobs`).
- House rules: no advisor name, no AI-run claim and no "discovery" wording in `tonight.json`, `tonight.js`, `tonight.md` or
  `dist/data/tonight.json`. Observers appear by code only. (The sealed statements themselves say "candidate" where relevant.)

---

## Blocking

### B1. "X supplies N%" is wrong, by up to 20x

`build_tonight` divides the top observer's count by the sum of the **top 12** listed in the provenance note
(`aavso.py:72` writes `counts.head(12)`), not by all good points. `provenance.aavso.rows_kept` is the true total.

| case | shown | true (top / rows_kept) |
|---|---|---|
| EE Cep | WGR 38% | 26.1% (19,313 / 73,878) |
| R CrB | FJQ 39% | 2.2% |
| R Cyg | MVD 27% | 1.2% |
| SS Cyg | SHPI 21% | 8.6% (76,939 / 895,999) |
| KIC 8462852 | HBB 28% | 21.0% |
| AA Tau | MJB 37% | 36.3% |

This breaks "every number comes from the data" and attaches a false figure to a named observer code. "12 or more AAVSO
observers" is literally true but silly for R CrB and SS Cyg (hundreds). The counts are also all-time, under a heading in
the present tense ("who is watching").

Fix in `build_tonight`:

```python
aav = (payload.get("provenance") or {}).get("aavso") or {}
...
if counts:
    listed = sum(v for _, v in counts)
    total = aav.get("rows_kept") or listed
    observers = {"n": len(counts), "truncated": len(counts) >= 12, "top": counts[0][0],
                 "top_share": round(counts[0][1] / total, 3), "listed_points": listed, "total_points": total,
                 "read": (aav.get("retrieved_at") or "")[:10]}
```

and in `tonight.js`:

```js
ob ? (ob.n === 1 && ob.listed_points === ob.total_points
      ? `one AAVSO observer, ${ob.top}: all ${ob.total_points.toLocaleString('en-US')} points in the archive as read ${ob.read}`
      : ob.truncated ? `many AAVSO observers; the largest contributor, ${ob.top}, ${pct(ob.top_share)} of ${ob.total_points.toLocaleString('en-US')} points`
      : `${ob.n} AAVSO observers; the largest contributor, ${ob.top}, ${pct(ob.top_share)}`)
```

Rename the label "who is watching" to "who has measured it". Update `test_numbers_come_from_the_case…` to give the fixture a
`rows_kept` larger than the listed sum.

HMB specifically: accurate. `rows_raw = rows_kept = 7115`, one observer, across B, V, R, I (V alone is 2,116). Naming a code is
within the house rule. Say "all bands" or drop the count's implication that these are V points.

### B2. "Last measured N days ago", "not measured in 4 months" and "no points in the window yet" measure our copy, not the sky

- Every AAVSO series was read on 2026-10-27 (HM Sge about 2026-11-03). So ASASSN-21qj shows "17 days ago" although HMB observes
  it most clear nights; an observer who opens the AAVSO light curve generator sees the page is wrong within a minute.
- Every ZTF series in the casebook ends at MJD 60935-60969 (2025-10-21 at the latest). That is the public-release horizon, not
  the star. The headline stat "not measured in 4 months: 4" is AA Tau (real in our copy: last point 2026-03-18) plus OS-0010,
  OS-0011 and OS-0012, which are ZTF-horizon artefacts for which ATLAS was never fetched. Three of four are not true.
- The footnote says the data are "as of the last site build". False: they are as of each archive read; the build only re-reads the case files.

Fix: carry the read date into `tonight.json` (`provenance[survey].retrieved_at[:10]`, null when missing as for HM Sge AAVSO) and
show dates, not ages:

- fact row: `last in our copy` → `13.52 (AAVSO V) on 2026-10-25; archive read 2026-10-27`
- drop the stat "not measured in 4 months", or replace it with "no AAVSO data at all" (count of targets with `aavso_n_365d == 0`
  and no observers), which is true and is the useful number;
- `is-stale` only when the series is AAVSO or ATLAS and the gap is measured to the read date, not to now;
- judged row, window open: `${j.in_window} points in the window in our copy (read ${read}).`
- footnote: "Brightness and the last point come from each case's copy of the archives, read on the dates shown; the AAVSO
  may hold newer data. Rise and set are computed in your browser…"

### B3. Two stars are in VSX and the page says they are not; two are not and the page asks for data nobody can submit

VSX (VizieR copy, 5 arcsec): OS-0011 = `Gaia DR3 2037357495383317504`, OID 7332020, type VAR, P 0.037067 d. OS-0012 =
`Gaia DR3 4482344869315388928`, OID 6779524, VAR, P 0.0249833 d. Both cases' own claim C1 says "VSX lists it only as a Gaia
'VAR'". The page prints "Not in the AAVSO index yet: registering it is on us" for both. Add to `site/tonight.json`:

```json
"OS-0011": {"aavso": "Gaia DR3 2037357495383317504", ...
"OS-0012": {"aavso": "Gaia DR3 4482344869315388928", ...
```

and what "is on us" is a VSX *revision* (type and period), not a registration.

OS-0015 and OS-0014 have no VSX entry (confirmed). WebObs will not accept a star that is not in VSX, so those two asks cannot
be acted on. Replace the muted text with: "Not in the AAVSO index yet, so WebObs cannot take it. We are submitting it; until
it appears, keep your measurements." Better: submit both to VSX before shipping and move them out of the asks until accepted.

NSV 1302 is in VSX (OID 39926, range 13.9-14.7, no type). The card says "surveys only: no AAVSO record", which reads as
contradicting the "AAVSO entry" link beside it. Use: "no observations in the AAVSO database". Note the case's AAVSO query used
the ident `Gaia DR2 219832339066395776`, not `NSV 1302`, so "no observations" is not yet verified under the VSX name: re-query before stating it.

### B4. OS-0015: the ask is for an eclipse nobody can observe, and the "only way this gets an answer" line is not true of the sealed check

- Ephemeris from the case (C21): P = 385.7 d, T0 = MJD 58702.2. Next minima: 2026-12-29 (solar conjunction, as the statement
  says) and 2028-01-17. Claim C23 in the case: the P1 window has the star 10-41 degrees from the Sun and "P1 is therefore very
  likely unresolvable". My node check agrees: at mid-eclipse the star is 12 degrees up at the end of nautical darkness from
  30 N and 1 degree from 35 S; on the last day of the window it reaches 19 degrees from 35 S. The first eclipse an amateur can
  reach at a sane airmass is about 2029 February (morning sky) or 2030 late February.
- "wanted: … nightly near a predicted eclipse" gives no date, and the honest date is three years off.
- "Independent photometry may be the only way this gets an answer": the check is sealed on `ZTF:ZTF_r`. Amateur photometry cannot
  grade it; the outcome would be `unresolvable` whatever anyone observes.
- "The last public ZTF r point in this case is 13 months ago" is true of our copy (last point MJD 60960.1, read 2026-10-27) but
  is the release horizon (see B2), and reads as a complaint about ZTF.

Replacement `tonight.json` entry:

```json
"OS-0015": {"bands": "r, R or clear", "cadence": "weekly through the 2027 season (February to November)",
  "settles": "Whether the star stays quiet between eclipses, as sealed prediction P2 says, and whether the small dimming near phase 0.4 recurs.",
  "note": "The eclipses themselves (P = 385.7 d) fall at solar conjunction on 2026 Dec 29 and 24 degrees from the Sun on 2028 Jan 17. The first one a backyard telescope can reach is early 2029."}
```

Replacement for the `quiet` sentence in `judgedRow`:

```js
quiet ? h('span', null, `Our copy of the public ${j.survey} archive ends ${isoDay(mjdToDate(j.judge_last_mjd))}. Public releases lag; if none reaches this window the check is recorded as unresolvable. Photometry filed with the AAVSO would still show what the star did, and we would report it beside the verdict, not as the verdict.`) : null
```

For P1 add (from C23): "The window is within 41 degrees of the Sun; the case records that this prediction is very likely unresolvable."

### B5. ASASSN-21qj: the note invites exactly what would spoil the grade

P1 and P2 compare the median of *all* `AAVSO:V` points in 2027-01-01..06-15 with the 2026 median, thresholds 0.05 and
**0.005 mag** (`evaluate` pools every observer, no per-observer offsets, median over points not nights). The 2026 baseline is
one observer, one telescope, one comparison sequence. A second observer's zero point will differ by a few hundredths of a
magnitude, ten times P2's threshold, and a dense time series from a newcomer would move the pooled median. "A second
observatory would make the grading independent of any one telescope" is the opposite of what happens: it makes P2 (and
possibly P1) ungradable in any meaningful sense. Any CCD observer will see this.

Replacement:

```json
"OS-0001": {"aavso": "ASASSN-21qj", "bands": "V", "cadence": "weekly while it is up (January to May from the south)",
  "settles": "Whether the debris from the suspected planetary collision has cleared for good, or still crosses the star.",
  "note": "All of the photometry so far is one observer's (HMB). The two median predictions rest on that single, consistent series; a second observer's zero point would differ by more than their margins, so new V data serve best as an independent check and as cover for a new dip (P3), which needs no fine calibration. Use the AAVSO comparison sequence."}
```

and decide, before the window opens on 2027-01-01, whether the grader for baseline checks should use only observers present
in both windows. That is a change to a sealed check and must be published as such; say so on the case, not on this page.

---

## Should-fix

### S1. HM Sge P3: the window that needs data is open now and the page says "opens in 6 months"

P3's check has `baseline: [61314, 61405]` = 2026-10-01 to 2026-12-31 in `AAVSO:I`. Our copy holds 10 I points in it (last
2026-10-24). Fewer than 3 would make P3 unresolvable; a thin, phase-biased baseline on a 540-day Mira makes it noisy. This is
the most useful thing an observer can do this month and it is not on the page. Same structure, later: EE Cep (baseline
2030-09-01..2031-04-30), ASASSN-21qj (baseline closed, 278 points, fine).

Add to each judged item in `build_tonight`:

```python
"baseline": [mjd_to_date(b[0]).isoformat(), mjd_to_date(b[1]).isoformat()] if (b := ch.get("baseline")) else None,
"in_baseline": sum(1 for x in sv["t"] if b[0] <= x <= b[1]) if b else None,
```

and in `judgedRow`, after the window sentence: `Compared with ${j.baseline[0]} to ${j.baseline[1]}: ${state of that window}, ${j.in_baseline} points in our copy.`
with the head line showing "baseline window open, closes in 51 days" when it is. Sort open-baseline cases first.

"If nobody observes, it cannot be graded" is literally true, with one precision worth printing: the grader needs **3 points**
in the window (and 3 in the baseline). Suggested: "Fewer than three measurements in that window and it cannot be graded."

### S2. "about mag X" mixes bands, surveys and years

`typical` is the median of the last 30 points of *every* ground series pooled: B with I, ATLAS cyan with orange, and series
whose last 30 points are years old (HM Sge `AAVSO:CR` ends 2014, ZTF g ends 2025). Results against the series the card quotes:

| case | shown | last-30 median of the quoted series |
|---|---|---|
| HM Sge | 12.9 | V 13.21 (the sealed statement on the same card says 13.18) |
| AA Tau | 14.8 | V 15.7, I 12.8 (CV 15.04) |
| OS-0019 | 15.7 | ATLAS o 14.28 |
| OS-0028 | 16.4 | ATLAS o 15.10 |
| OS-0021 | 15.4 | ATLAS o 14.86 |
| R Cyg | 9.5 | V 9.6 (a Mira: "about" means little) |

An observer sets exposure from this number. It also drives the reach cut: OS-0028 survives at 16.4 while OS-0029 (o 16.1,
c 17.7) is cut, on colour alone. Fix: `typical` = median of the last 30 points of the `latest` series (after the V
preference), restricted to the last 2 years, and print the band: "about 13.2 in V", "about 14.3 in ATLAS o (red)". Apply the
reach cut to that number.

### S3. HM Sge: the stated physics is not what V and I measure in a symbiotic nova

In HM Sge the V band is mostly nebular emission ([O III], He II, continuum); the Mira is seen in I and redder. The case's own
H1 and H2 say so ("the nebular B and V"). So "Dust dims blue light more than red, so V and I together tell dust from a change
in the star itself" is wrong for this star: the observed pattern is the reverse (R, I down 1.6-2 mag, B, V down 0.9), and V - I
compares two different light sources. Filter-to-filter differences on emission-line objects are also large; observers know this.

```json
"OS-0036": {"aavso": "HM Sge", "bands": "V and I, the same night", "cadence": "weekly, and I as often as you can before 31 December",
  "settles": "Which part of the system is fading. V is mostly the glowing nebula, I is mostly the Mira: if I keeps falling faster than V, dust is thickening in front of the Mira; if they fall together, the 1975 outburst is ending.",
  "note": "The Mira pulsates every 540 days, so a season of points counts, not one. This is an emission-line star: note your filter and stay with the same comparison stars."}
```

### S4. The label "One more measurement would help settle" over-claims on every card

One point settles none of these, and HM Sge's own note says "single points mislead". Use "What observing it would help
settle". Same in the lede ("what one more measurement of each would settle" → "what watching each would help settle") and in the
route description in `build.py:603`.

### S5. Eclipse asks give nothing to act on, and OS-0011 over-claims

No period, epoch, depth or duration is shown. For OS-0012 (P = 11.9 d, 5 h eclipse) a blind "run of a few hours" catches an
eclipse about 2% of the time. "The true orbital period … a single well-timed eclipse does it" is not right either: the case
already has P = 2.52961 d from 11 years of Gaia and ZTF; one timing refines the ephemeris and confirms it has not drifted.
OS-0012 is a **closed** case ("nothing anomalous remains"); say so.

```json
"OS-0011": {"aavso": "Gaia DR3 2037357495383317504", "bands": "any, unfiltered is fine", "cadence": "one run of 7 hours or more across a predicted eclipse",
  "settles": "A modern eclipse time for an Algol-type binary that VSX lists with the wrong period (0.037 d). It would confirm P = 2.52961 d and anchor the ephemeris for the VSX revision.",
  "note": "Primary minimum = MJD 57377.958 + 2.52961 E (from survey data, good to tens of minutes at best; start early). 0.86 mag deep in r, about 6 hours long."},
"OS-0012": {"aavso": "Gaia DR3 4482344869315388928", "bands": "any, unfiltered is fine", "cadence": "one run across a predicted eclipse",
  "settles": "Eclipse times for an ordinary pair of K dwarfs (a closed case: nothing strange remains), to keep its ephemeris from drifting before the VSX revision.",
  "note": "Primary minimum = MJD 57099.3619 + 11.900804 E, 0.9 mag deep, about 5 hours; secondary 0.4 mag at phase 0.404."}
```

The case does not say whether T0 is heliocentric or what its uncertainty is. Establish both before printing, and ideally
compute "next eclipse visible from your place" in the browser from `period` and `t0` fields (the sky code is already there).

### S6. Other asks

- **OS-0014**: "Another dip would make it an orbit" over-claims (the case: "nothing requires periodicity"; periods under 12.9 yr
  are excluded, 98% of those allowed exceed 30 yr; ATLAS already samples it every few nights, 20 points in 90 days). Replace:
  `"settles": "Whether the star ever disappears again. The 2017 event lasted three months; surveys already watch most nights, and a repeat is not expected for decades, so this is a long watch with a small chance.", "cadence": "monthly"`.
  Or move it to the third group. (And B3: it cannot be submitted yet.)
- **NSV 1302**: "never classified" sits oddly with the case, which already favours a disc "dipper" at 0.85. Weekly V will not
  classify what 450 ZTF points did not. Replace: `"settles": "Whether the irregular dips of up to 1.2 mag continue, and how deep they go in V: the record a classification in VSX needs.", "bands": "V, and I if you can"`.
- **EE Cep**: the sealed baseline is 2030-09-01..2031-04-30, so data taken now do not enter the grade. Replace `settles` with
  "How steady the star is outside eclipse (it is a Be star and wanders by hundredths of a magnitude), which is what the 2031 eclipse depth will be judged against. The graded baseline itself is September 2030 to April 2031." It is also already well observed (139 points in 90 days): say "already well watched".
- **AA Tau**: "V or I" → "V and I the same night" (colour is what separates extinction from a real change); warn that V is
  near 15.7 while I is near 12.8. "has begun to come back" is fair.
- **ASASSN-21qj** at Dec -39: "weekly while it is up" is fine; the page correctly says "Never gets 30° above your horizon" at 40 N.
- **Gaia-ID stars at 14.5-15.3**: reachable unfiltered with 20-30 cm; say "CV (clear, V zero point)" not "unfiltered is fine",
  since that is how the AAVSO wants it reported.

### S7. `night()` shows last night to a morning visitor

Before local solar noon the noon-to-noon window is the one that began yesterday. At 08:00 local on 11 Nov the page says "Up
tonight … highest at 05:50 PM", which is the evening already gone (node: `darkStart 11-10T22:50Z`, `darkEnd 11-11T10:30Z` for
`from = 11-11T13:00Z`). Fix in `skycalc.js`, replacing the body after `start` is found:

```js
const scan = (start) => { /* the existing for-loop, returning the result object */ };
let res = scan(start);
if (!res.darkEnd || from.getTime() > res.darkEnd.getTime()) {
  const next = scan(new Date(start.getTime() + 86400000));
  if (next.darkEnd) res = next;          // keep today's (darkless) result at the midnight sun
}
return res;
```

Add a test: `night(HM Sge, 40, -75, 2026-11-11T13:00Z).darkStart > from`.

### S8. "Not up" wording gives the wrong reason; season string hides gaps

- `everUp` true but `season` empty: a star that culminates within a degree of 30 (OS-0028, Dec -20.93, from 39 N) gets "Too
  close to the Sun from here for now" all year, including at opposition. Use the returned `maxAlt` and `hoursDark`:

```js
const why = n.hoursDark === 0 ? 'No darkness tonight at this latitude.'
  : n.maxAlt < 30.5 ? 'Barely reaches 30° from here.'
  : n.best && n.best.alt >= 30 ? 'Above 30° for only a few minutes of darkness tonight.'
  : 'Up only in daylight or twilight for now.';
return h('p', { class: 'tn-sky is-down' }, `Not up in the dark tonight. ${why}`, wrap ? ` In season ${wrap}.` : '');
```

- "Back in season Mar-Nov" prints in November when tonight has under 0.5 h (the season test samples the 15th and needs 1 h;
  on 1 December HM Sge is still "Up tonight for 1.7 h … Season: Mar-Nov"). "In season" avoids the contradiction.
- A non-wrapping season with a gap is printed as one span: HM Sge from 58 N is `[Apr, Aug..Dec]` and prints "Apr-Dec". Build
  the string from runs of consecutive months (join runs with ", "), which also replaces the special wrap code.
- The 30 degree floor is stricter than practice (many work to 20-25). With it, OS-0015 is "Never" north of 46 N. Either lower
  to 25 or say "30°" in the "Never" line as it does now (fine) and in the footnote (already there).

### S9. Place guess

- Latitude 40 N is not "a guess from your clock"; a Sydney visitor is told ASASSN-21qj never rises. Text: "40°N assumed,
  longitude from your clock: set yours". Cheap improvement: default to 35 S when
  `Intl.DateTimeFormat().resolvedOptions().timeZone` starts with `Australia/`, `Pacific/Auckland`, `Africa/Johannesburg`,
  `America/Sao_Paulo`, `America/Argentina`, `America/Santiago`.
- UTC+13/+14 gives longitude 195/210: the arithmetic is right (checked) but it prints "210°E". Normalise: `((lon + 540) % 360) - 180`.
- Daylight time shifts the guess 15 degrees and wide zones (China, Spain) by more; times can be an hour off until a place is
  set. The label covers it. Preset buttons show no selected state.

### S10. What is listed (18)

Correct to list: OS-0036, 0001, 0003, 0007, 0010, 0011, 0015, 0002, 0004, 0005, 0006.
Questionable:
- **OS-0016, 0017, 0019, 0021, 0028** (finished microlensing events/candidates, mag 14-15.7): single events that do not
  repeat; nothing an observer can add. "Watched, or quiet for now … within reach" invites wasted nights. Drop them, or give
  the third group the lede "In the casebook and within reach. Nothing here needs you tonight."
- **OS-0012**: closed case; keep only with the S5 wording.
- **OS-0014**: see S6.
Missing:
- **OS-0013** (V 13.4): excluded because `GROUND` has `"ASASSN"` but the series key is `ASAS-SN:V`, so that entry never
  matches anything (also drops the only V series of OS-0014). If the key is fixed OS-0013 lists with a last point in 2018, which
  is honest and arguably the best "nobody is watching" example in the casebook. Decide deliberately.
- **OS-0037** (BD+28 4177, a bright B giant): no ground series in the export, so not listed. Fine, but it is the easiest target in the book.
Controls are excluded by title prefix "Control"; `sky_cases` uses the ids. Use one rule.

Sort order and group split behave as written. Resolved and non-ground predictions are correctly left out (HM Sge P2, Gaia).

### S11. Copy

- Headline "The sky grades us. Somebody has to look." and "No measurements, no verdict" lean on the reader. HMB, WGR and the
  SS Cyg observers have been looking for years. Suggested: h1 "The sky grades us. Observers hold the pen."; group lede "Sealed
  predictions that will be graded on photometry in the AAVSO database. Without measurements in the window there is no verdict."
- Stat label "predictions your data grades" presumes the reader's data: "predictions graded on AAVSO photometry".
- Say once, at the top rather than only in the footer, where data go: add to the lede "Measurements go to the AAVSO, as for any
  variable star, not to us; we read them from there." The link text "Report as "HM Sge"" should read "Report to the AAVSO as "HM Sge"".
- "window opens in 55 months" → years above 24 months ("in 4.6 years").
- The page prints the check's dates beside the statement's: HM Sge P1 says "2027 Jun 1 - Dec 31", the card says "2027-06-02 to
  2028-01-01" (the sealed check starts at MJD 61558.0 = 2 June and ends 61771.0 = 1 January 00:00). Either show the end as the
  last full day or add "(the sealed check's exact bounds)".
- Sealed statements carry internal asides ("the coin-flip one", "BRIGHTER"). They are sealed; leave them, but they read oddly here.

### S12. Mobile

In `.context/tonight-mobile.png` every line is cut at the right edge (nav "SIGN I", the lede, card text). The text wraps at a
width larger than the 420 px image, so either the capture cropped a wider headless window or something forces the page wider
than the viewport. I could not tell which without a browser. Check on a real phone before shipping; candidates are the header
nav and `.tn-facts` (`1fr 1fr` with mono text: use `minmax(0, 1fr)`), and add `overflow-wrap: anywhere` to `.tn-j-head`. On
desktop the two-column card grid leaves a large hole beside EE Cep; acceptable.

---

## Notes

- N1. `evaluate` takes the median over points, not nights, so one observer's time series can dominate a window median. Relevant
  to B5; not a page defect.
- N2. `n_90d` (markdown only) pools all bands and surveys and counts bins for binned series (`binned_days` 1-128), and is
  relative to build time over a copy read two weeks earlier. Say "points in our copy in the 90 days before it was read", or drop it.
- N3. `AAVSO_BANDS` omits TB, TR, SG, SR, SI, CR; harmless for `latest`, but `aavso_n_365d` undercounts DSLR and Sloan observers.
- N4. Flagged points and upper limits: the exported series already exclude them (`flagged` is separate), so `latest` and
  `in_window` use good points only. Correct.
- N5. `judge_last_mjd` > 180 d is the only "quiet" trigger; with B4's wording that is fine.
- N6. Tests cover the fixture and four altitude spot checks. Missing: the share denominator, a baseline window, the morning
  case, a season with a gap, a place with no darkness.
- N7. `tonight.md` inherits B2, S2 and the asks; it prints "graded on ZTF ZTF_r" (say "ZTF r").
- N8. Aladin survey id `P/DSS2/color` works; `fov=0.25` (15 arcmin) is a sensible finder field.

---

## Re-check (after the rewrite)

Rebuilt (12 targets), re-read `site/tonight.json`, `build_tonight`, `tonight.js`, `skycalc.js`, `dist/tonight.md`,
`dist/data/tonight.json` and both screenshots; ran `tests/test_tonight.py` (10 passed here, not 13: check the count) and the
eclipse logic under node.

**Can it ship? Yes, once R1 is fixed.** All five blockers are resolved and verified: shares divide by `rows_kept` (EE Cep 26%,
R CrB 2.2%, SS Cyg 8.6%), dates replace ages, OS-0011/OS-0012 carry their VSX names, OS-0015 and ASASSN-21qj are reworded,
the HM Sge baseline shows "open now (10 points in our copy)". Mobile at 500 px is clean. R2-R6 can follow.

Correction to my own first report: I wrote that OS-0015's first reachable eclipse is "early 2029". It is not. With the page's
own test (30 degrees up for an hour of darkness) no night within 7 days of the 2029-02-06 minimum qualifies from 40 N, 30 N or
35 S; the first is **2030-02-27, from the south only** (10 of 15 nights from 35 S, none from 30 N or 40 N).

### R1. Should-fix before shipping: `eclipseLine` tests the wrong thing for OS-0015 and is too strict for OS-0011/OS-0012

- OS-0015 (a 2-3 week eclipse, timing good to days): the code asks whether the star is up at the predicted *instant* plus and
  minus 3 h. From 35 S it prints "None in the next 4 cycles … not in your dark sky" although 10 nights around 2030-02-27 qualify.
  That sentence is false for southern visitors.
- OS-0011/OS-0012: requiring the whole run (mid plus and minus 3 h / 2.5 h) inside darkness above 30 degrees gives **zero** events
  in 60 cycles from the default place (40 N, 75 W), while mid-eclipse alone qualifies 4 and 7 times. Sixty cycles of OS-0011 is
  only 152 days, all of it the star's off-season. So all three panels read "None" by default, under a stat "with eclipse
  times to catch: 3".

Replacement:

```js
const long = e.half_width_h > 12;                       // an eclipse lasting days: ask about nights, not instants
const mins = nextMinima(e.t0_mjd, e.period_d, now, long ? 4 : Math.ceil(400 / e.period_d));
const nightsUp = (d) => { let n = 0; const w = Math.round(e.half_width_h / 24);
  for (let k = -w; k <= w; k++) if (night(x.ra, x.dec, place.lat, place.lon, new Date(+d + k * 86400000)).hoursUp >= 1) n++; return n; };
const up = (t) => observable(x.ra, x.dec, place.lat, place.lon, t);
const ok = long ? mins.filter((d) => nightsUp(d) >= 3)
  : mins.filter((d) => up(d) && (up(new Date(+d - half)) || up(new Date(+d + half))));   // minimum plus one branch
```

List long events as `around ${isoDay(d)}: ${nightsUp(d)} nights within a week of it` (no clock time), short ones with
`(mid-eclipse, your clock; ${up(start) && up(end) ? 'whole eclipse' : up(start) ? 'ingress and minimum' : 'minimum and egress'} in your dark sky)`.
The "None" text: `None from here in the next ${long ? mins.length + ' eclipses' : '400 days'}.` and drop "not in your dark sky".
Stat label: "with an ephemeris" (not "with eclipse times to catch").

### R2. EE Cep sorting first

The sort is now brightest-first within the group, so the page opens on the card whose windows are 4.6 years away and which says
"already well watched", ahead of HM Sge, whose I-band baseline closes in 51 days. Sort by urgency:

```python
today = mjd_to_date(now).isoformat()
def urgency(x):
    js = [j for j in x["judged"] if j["amateur"]]
    open_base = any(j["baseline"] and j["baseline"][0] <= today <= j["baseline"][1] for j in js)
    nxt = min((j["window"][0] for j in js if j["window"][1] >= today), default="9999")
    return (not js, not open_base, nxt, not x["ask"], x["typical_mag"])
out.sort(key=urgency)
```

Result: HM Sge, ASASSN-21qj, EE Cep.

### R3. Time system of the ephemerides (OS-0012 T0 is the right one)

C14's T0 = MJD 57099.3619 with P = 11.900804 d is the current ephemeris: C20 (the non-retracted summary) repeats it, and
C2's 57099.3195 belongs to the retracted 2.38-day fold. Correct choice; citing C20 would be slightly better, since C14 is a
referee note about a model run "outside the tools".

The fits mix ZTF and NEOWISE times (MJD, UTC, at the observatory) with Gaia epochs (barycentric, TCB). Nothing was reduced to
HJD or BJD. The error is at most about 8 minutes plus a minute of time-scale offset, below the ephemeris uncertainty, so it is
fine to print, but say so. Replace the last line of the panel with:

"Predicted from MJD … + … × E (claim Cn), from survey photometry: times are UTC with no heliocentric correction (up to 8
minutes) and have not been checked against a timed eclipse. Report your own times in HJD or BJD as usual."

And the two notes: "could be off by tens of minutes" → "could be off by half an hour or more" (OS-0011's period is quoted to
1e-5 d over about 1,570 cycles).

### R4. "none yet: surveys only" is not verified

For NSV 1302 the AAVSO query used the ident `Gaia DR2 219832339066395776`, and OS-0011/OS-0012 were never queried under their
VSX names. Print "none in our copy: surveys only" until re-queried.

### R5. OS-0015 ask with nowhere to file

The card asks for weekly photometry and says it cannot be submitted. Add to the note: "Keep your measurements until the star
is in the index." Change the note's first sentence to "The next three eclipses (to 2029) fall too close to the Sun; the first
within reach is February 2030, from the south."

### R6. Small wording

- "Not 30° up in the dark tonight. It is: Apr-Sep." → "Not 30° up in the dark tonight. In season Apr-Sep."
- HM Sge "weekly" → "weekly; I-band before 31 December counts toward P3's baseline".
- No remaining over-claims found in `settles`. No advisor name, AI-run claim or "discovery" wording.
