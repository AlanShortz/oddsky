# Referee report: Gaia DR4 sealed predictions (H-0009 follow-up)

Author: claude-referee (adversarial pass), 2026-10-30. Reviewed: `dr4_proposal.md`, `dr4_proposal.json`, `work/` (p1-p10,
gaialib, models, GOST exports), the grader (`oddsky.tools.evaluate`, `Toolbox._frame(grading=True)`, `case.model.Check`),
the Gaia fetcher (`oddsky.data.gaia_epoch`), the case fetcher (`oddsky.fetch`), and the Sky Ledger seal/grade path
(`oddsky.hosted.sky`, `hosted.app`). New tests were run from throwaway scripts outside the repo (described in §4 so they can be
re-run). No repo file other than this one was changed.

## 1. Verdict

**Not ready to seal as written. Two blockers, then a cut from 13 seals to 6.**

1. **Blocker: no `resolve_by`.** The JSON entries have no `resolve_by`. `sky.seal()` then defaults to window end + 30 d,
   which is in **2015-2018** for every check. Two consequences:
   - The public ledger would show resolve-by dates nine years in the past.
   - Any check that has fewer than 3 points on the first DR4 fetch is closed as "unresolvable" for good, with no grace
     period (`late` is already true).

   Fix: set `resolve_by` explicitly on every seal (§5).
2. **Blocker: four of the six targets have no case.** Only OS-0020 (J163539) and OS-0021 (J173150) exist. The hosted grader
   fetches Gaia by `case.target.gaia_source_id`, so J124517, J160706, J131026 and J154239 need cases first. Open them as
   `Gaia DR3 <id>` and check that `target.gaia_source_id` equals the JSON `gaia_id` before sealing.
   - The case fetcher takes the brightest source within 3″ of the coordinates. That picks the right star for all six,
     including J154239: its G 17.58 neighbour is 3.2″ away and fainter.
3. **Record inflation.** The ledger scores every seal on its own (`sky._board`). It does not score "one bet per target",
   which is the proposal's own caveat. Several second predictions are 95-99% determined by the first:
   - J163539 alone would carry three ~0.9 seals. If Gaia does not see that event, the record takes three failures at once.
   - Keep one seal per target (§2).

**What holds up.** The mechanics are right. The grader replica in `gaialib.grade` matches `evaluate` line for line, and the
time systems agree (§3.1). Every window holds 5-10 forecast transits, and no forecast transit is within 3.7 d of any window
or baseline edge. The lens and ATLAS models are evaluated at the baseline epochs too, so lens wings in the baseline are
simulated, not ignored. I reproduced the per-scenario MC numbers.

Two pieces of the proposal's evidence were broken or uncalibrated. I re-ran both on new tests:
- **p7 (Gaia flags).** p7 is invalid as written. Its corrected version still supports the 3% flag branch.
- **p6 (CCD deficit).** Calibrated on 47 DR3 lenses, the CCD deficit turns out to be *stronger* evidence than the proposal
  claimed.

The "no Gaia alert" worry is weak once measured: Gaia alerted only 5 of 12 comparable DR3 lenses.

## 2. Per-prediction table

Keep six, all with `resolve_by: "2027-12-31"`. The kept Checks are unchanged. Only the statement, scenario and `resolve_by`
change.

| # | target | verdict | why | corrected fields |
|---|---|---|---|---|
| 1a | J163539 | **keep (fix wording)** | Cleanest test in the set: needs Gaia to see ≥ ~0.45× the ATLAS excess flux (MC: k = 0.4 gives P 0.52; k ≥ 0.65 gives 1.00). No-alert evidence is weak (§3.4). | probability 0.93; statement S1a; resolve_by 2027-12-31 |
| 1b | J163539 | **drop** | P(1b \| 1a) ≈ 0.99, and P(1b \| not 1a) ≈ 0. Its window is inside the DR3 span, and the DR3 CCD-deficit argument already uses those transits, so it is the least blind check. The proposal concedes it does not separate lens from bump. | – |
| 1c | J163539 | **drop** | P(1c \| 1a) ≈ 0.99. Its 0.07 mag threshold is the most exposed to intrinsic variability: red noise of 0.05 mag rms cuts it from 0.99 to 0.95. Adds no independent information. | – |
| 2a | J173150 | **keep (fix wording)** | Needs k ≳ 0.4. Note that DR4 flagging of the bright transits makes it **false**, not unresolvable, because the faint Feb-Mar transits stay in the window. The proposal's 3% flag branch already counts this. | probability 0.90; statement S2a; resolve_by 2027-12-31 |
| 2b | J173150 | **drop** | P(2b \| 2a) ≈ 1. Same bet. | – |
| 3a | J124517 | **drop** (or keep *instead of* 3b) | Outlier-exposed: the Jul 27 night has a single transit, so N passes at 0.02. Also passes for half of short outbursts. | – |
| 3b | J124517 | **keep (fix wording)** | Median, so outlier-proof (N 0.00). It is the claim that matters for a long-lens hunt: a weeks-long brightening on the Gaia star. Fix the "(lens)" overclaim: slow non-lens events pass at 0.91. | probability 0.50; statement S3b; scenario Sc3b; resolve_by 2027-12-31 |
| 4a | J160706 | **keep (fix wording)** | Margin is huge: model median ≈ −2.3 vs threshold −0.5. The baseline wing (rise tE ~250 d gives ≈ −0.1 at 2016-07) is modelled and irrelevant at this threshold. | probability 0.74; statement S4a; resolve_by 2027-12-31 |
| 4b | J160706 | **drop** | P(4b \| 4a) ≈ 0.96. Not an achromaticity test: L vs R is only 0.96 vs 0.81 (ratio 1.2). "G amplitude ≥ W1" assumes fs_G ≥ fs_W1, which a bluer unresolved blend breaks. | – |
| 5a | J131026 | **keep (fix wording)** | Robust. Intrinsic red noise of 0.06-0.10 mag rms (the DR3 excess) gives P(true \| N) ≤ 0.003. The DR3 deficit, after calibration, supports the stake (§3.3). | probability 0.70; statement S5a; scenario Sc5a; resolve_by 2027-12-31 |
| 5b | J131026 | **drop** | P(5b \| 5a) ≈ 0.96. Same achromaticity objection as 4b. | – |
| 6a | J154239 | **drop** (or keep *instead of* 6b) | Brightest-night test: N passes at 0.02-0.025 from outliers, and short outbursts pass at 0.59-0.63. | – |
| 6b | J154239 | **keep (fix wording)** | Median, outlier-proof, the lens-relevant claim. | probability 0.45; statement S6b; scenario Sc6b; resolve_by 2027-12-31 |

If the team insists on a second seal anywhere, only 3a (beside 3b) and 6a (beside 6b) carry real extra information: they
separate short outbursts from slow events. Even so, P(3b \| 3a) ≈ 0.88 and P(6b \| 6a) ≈ 0.93, so I would not.

### Corrected statements (exact text to seal)

All of them share a wording template. It names the source and the DR4 cross-match, gives MJD bounds, says the window ends at
00:00 of the end date, says "more than" (the grader's `<` is strict), and calls the transit counts forecasts.

- **S1a:** "Gaia DR4 G epoch photometry of Gaia DR3 6020322385418675200 (or the DR4 source cross-matched to it): the median
  G of the transits in MJD 57949-58042 (2017-07-15 to 2017-10-16 00:00; forecast 6 transits on Jul 29, Aug 20 and Sep 19)
  is more than 1.2 mag brighter than the median G in MJD 56863.5-57570 (2014-07-25 to 2016-07-01). Model: 1.6-2.1 mag."
- **S2a:** "Gaia DR4 G epoch photometry of Gaia DR3 5952322268527918208 (or the DR4 source cross-matched to it): the
  brightest nightly-median G in MJD 58150-58400 (2018-02-01 to 2018-10-09 00:00; forecast 10 transits on 6 nights) is more
  than 1.0 mag brighter than the median G in MJD 56863.5-57935 (2014-07-25 to 2017-07-01). Model: 1.4-1.85 mag, on 2018
  Aug 9."
- **S3b:** "Gaia DR4 G epoch photometry of Gaia DR3 5862971688685406976 (or the DR4 source cross-matched to it): the median
  G of the transits in MJD 58255-58340 (2018-05-17 to 2018-08-10 00:00; forecast 6 transits on May 26, Jun 19 and Jul 27) is
  more than 0.15 mag brighter than the median G in MJD 56863.5-57935 (2014-07-25 to 2017-07-01)."
- **S4a:** "Gaia DR4 G epoch photometry of Gaia DR3 5932843350525331968 (or the DR4 source cross-matched to it): the median
  G of the transits in MJD 57945-58025 (2017-07-11 to 2017-09-29 00:00; forecast 5 transits on Jul 23, Aug 17 and Sep 16) is
  more than 0.5 mag brighter than the median G in MJD 56863.5-57570 (2014-07-25 to 2016-07-01)."
- **S5a:** "Gaia DR4 G epoch photometry of Gaia DR3 5863586423081438848 (or the DR4 source cross-matched to it): the median
  G of the transits in MJD 57185-57300 (2015-06-12 to 2015-10-05 00:00; forecast 6 transits on 4 nights) is more than 0.2
  mag brighter than the median G in MJD 57600-58868 (2016-07-31 to 2020-01-20)." The proposal says "2016-08", but the
  check starts on Jul 31.
- **S6b:** "Gaia DR4 G epoch photometry of Gaia DR3 5882495205642608896 (or the DR4 source cross-matched to it): the median
  G of the transits in MJD 57945-58020 (2017-07-11 to 2017-09-24 00:00; forecast 5 transits on Jul 21, Aug 17 and Sep 15) is
  more than 0.15 mag brighter than the median G in MJD 56863.5-57630 (2014-07-25 to 2016-08-30)."

The three corrected scenario fields:
- **Sc3b:** "weeks-to-months brightening of the Gaia star (lens, or slow non-lens outburst) vs short outburst, artifact or
  event on another star".
- **Sc5a:** "months-long event on the Gaia star (lens or slow non-lens) vs artifact, flare or event on another star".
- **Sc6b:** "brightening of the Gaia star lasting more than ~2 weeks (lens or slow non-lens) vs short outburst, artifact or
  event on the G 17.6 neighbour".

The kept Checks are unchanged. For the record, they are (series GAIA:G, op `<`):

| # | start | end | statistic | baseline | value |
|---|---|---|---|---|---|
| 1a | 57949 | 58042 | median | 56863.5-57570 | −1.2 |
| 2a | 58150 | 58400 | brightest | 56863.5-57935 | −1.0 |
| 3b | 58255 | 58340 | median | 56863.5-57935 | −0.15 |
| 4a | 57945 | 58025 | median | 56863.5-57570 | −0.5 |
| 5a | 57185 | 57300 | median | 57600-58868 | −0.2 |
| 6b | 57945 | 58020 | median | 56863.5-57630 | −0.15 |

## 3. Findings

### 3.1 Mechanics (all checked against the code)
- **Time system: consistent.**
  - `gaia_epoch.to_series` sets `t_mjd = g_transit_time + 55197`. The DR3 column is BJD(TCB) − 2455197.5, so `t_mjd` is
    BJD_TCB − 2400000.5.
  - The GOST times used in the MC come from the `ObservationTimeAtBarycentre[BarycentricJulianDateInTCB]` column − 2400000.5,
    the same system.
  - TCB/barycentric vs UTC MJD differs by ≤ ~10 min. The nearest forecast transit to any window or baseline edge is 3.7 d
    away (J131026), and the others are 5-14 d, so the time system cannot change any outcome.
- **Window ends.** `register_prediction` passes numeric ends through unchanged (`_t(…, end=True)` adds 0.99999 only to ISO
  date strings), so "to Oct 16" means Oct 16 00:00. The corrected statements say so.
- **Statistics.**
  - median = median of all transits in the window, not of nights.
  - brightest = the minimum of `stats.daily_bins` medians, binned on floor(t_mjd). No forecast pair straddles an integer MJD.
  - Both have the baseline median subtracted, with negative meaning brighter.
  - The grader needs ≥ 3 points in both the window and the baseline. Baselines hold 18-83 forecast transits.
- **Statements vs Checks.** All dates and numbers in the 13 statements match their Checks except:
  - "at least" should be "more than", because the grader's `<` is strict;
  - J131026's baseline starts 2016-07-31, not "2016-08";
  - 1b's "model 0.18-0.37" is the per-transit range; the median-level model is 0.19-0.35 (moot if dropped).
- **NaN rows.** `series.normalize` drops rows with NaN time or magnitude. In DR3 every `rejected_by_photometry` transit has
  NaN G and NaN time, so the grader never sees rejected transits either way. Losing them can only make a check
  unresolvable or cut its margin. It cannot add a false bright point.
- **Lens wings in baselines: modelled, and harmless.**
  - J173150: even the tE = 493 d variant gives only ≤ 0.05 mag in 2017-11, and the baseline ends 2017-07-01.
  - J160706: the slow rise gives ≈ −0.1 mag at the baseline end (2016-07). It shifts the baseline median by a few hundredths
    against a 0.5 threshold.
  - J131026: the baseline starts ≥ 2 tE after t0.
  - J163539: the baseline ends ≥ 2.2 tE before the peak.
- **No check is trivially true.** Every check has P(true \| Gaia sees nothing) ≤ 0.025, and every one is resolvable with
  ≥ 95% probability at 10% transit loss.

### 3.2 p7 is invalid as written; the corrected test still supports the flag branch
- **Why p7 cannot work.** p7 counts flags after `gaia_epoch.fetch`, so after `normalize` has dropped NaN rows. In raw DR3
  epoch photometry of the same 25 lenses, all 11 `rejected_by_photometry` transits (of 929) have null G and null time. p7
  therefore could never see a rejected transit: its "0 of 918 rejected" and "0 without mag" are artifacts of the code.
- **Corrected test.** I mapped `transit_id` to time with a linear fit to the valid rows (residual ≤ 0.006 d) and placed the
  11 rejected transits on each lens's Paczyński model. The rejection rate does not rise with magnification:

  | model magnification A | transits | rejected |
  |---|---|---|
  | 1-1.1 | 782 | 8 (1.0%) |
  | 1.1-1.5 | 65 | 2 (3.1%) |
  | 1.5-3 | 52 | 1 (1.9%) |
  | > 3 | 30 | 0 |

  At about 1% per transit this is already inside the MC's 10% random loss. The 3% whole-event flag branch is a reasonable
  allowance for DR4 processing changes.
- **Fix the proposal text.** Replace the p7 paragraph with this result.

### 3.3 The DR3 CCD deficit, calibrated (it was uncalibrated, and was circular for J163539)
- **The problem.** The proposal used J163539 as its own "calibrator", which is circular.
- **The calibration sample.** I took the 47 Gaia DR3 microlensing events (I/358/vmicro) that peaked between 2016-07-01 and
  2017-05-28 and whose own DR3 epoch photometry shows a nightly median ≥ 1 mag up. For each I computed CCD observations per
  matched transit (`o_Gmag/MatchObs`, I/355) against stars within 2′ and ±0.5 mag.
- **Result.** These lenses sit at a median **6th percentile** of their fields. 34% are at ≤ 2.5th percentile and 81% at ≤ 15th
  (5%, 2.5% and 15% by construction for field stars). So "missing CCDs" really is a fingerprint of brightened transits:
  - the likelihood ratio is ≈ 9 at ≤ 5th percentile;
  - the bright transits stay unflagged in epoch photometry, which is consistent with §3.2.
- **Confounder.** In the targets' 5′ fields, stars with RUWE 1.4-3 or IPD multi-peak ≥ 1 fall below 7.2 CCDs/transit 3-4×
  as often as clean stars (J131026 field: 7.5% vs 1.6%).
- **Per target, after the confounder:**

  | target | DR3 deficit | likelihood ratio | baseline used |
  |---|---|---|---|
  | J131026 (RUWE 2.17, IPD 1) | 1.4th pct | ≈ 0.51 / 0.075 ≈ 7 | high-RUWE field stars |
  | J163539 (IPD 1) | 2.3rd pct | ≈ 5-14 | IPD 1 and clean field stars |
  | J160706 | 12th pct | ≈ 4-5 | field stars |

- **Implication.** The proposal's prior shifts correspond to likelihood ratios of only ≈ 1.2-2. Its 4a and 5a stakes are
  therefore conservative, not inflated. I leave them unchanged because the scenario split for dusty stars has its own
  uncertainty (§3.5).

### 3.4 "No Gaia alert" is weak evidence (measured)
- **Measured with the same 146 DR3 lenses that peaked 2016-07 to 2017-05, matched within 2″ against the local alerts index
  (`hunts/H-0005/alerts.csv`, 27,077 alerts):**

  | DR3 lenses peaking 2016-07 to 2017-05 | alerted by Gaia |
  |---|---|
  | ≥ 1.5 mag up and brighter than G 17 | 5 of 12 |
  | ≥ 1 mag up | 5 of 47 |

  So q = P(no alert \| Gaia recorded the brightening) ≈ 0.6-0.9.
- **Effect on 1a/2a.** With the proposal's 0.97 prior that Gaia sees each event, P(seen \| no alert) ≈ 0.95-0.96 per star.
  The proposal's shading to 0.93 / 0.90 already covers this.
- **The referee's open question is closed.** Gaia did scan both peaks, and Gaia Science Alerts simply missed most such lenses
  at this time.

### 3.5 Probabilities
- **Reproduction.** I reproduced the per-scenario MC values (J163539, J173150, J131026 and J154239 checks; my values exclude
  the flag branch, which explains the ~0.03 offset): L ≈ 1.00, R 0.88-0.99, F 0.10-0.63, N 0.00-0.03.
- **Kept stakes are honest.** For 3-6 they are, in effect, the judgement priors P(L ∪ R), and the per-scenario numbers are
  published so anyone can reweight. The base rate supports them: of the 7 atlas10 events followed with ATLAS, all were real
  and 1 was on the wrong Gaia star.
- **Missing scenario.** "Real IR event with little or no G response" is not modelled. That is a disk or dust change in a
  dusty star: J124517 has W1−W4 5.6 and J131026 has 4.3. R's U(0.3, 2) × W1 lower bound is generous. This case belongs with
  N. It argues against raising 3b or 5a, not for lowering them.
- **J173150 2a.** Flagged bright transits make 2a false, not unresolvable. That risk is ~3% and is already in the MC.
  - Optional: switching to the Aug 9-Oct 9 window (58330-58400) would turn that into "unresolvable". It would raise the stake
    to 0.95, but P(unres) rises to 0.08-0.21.
  - I do not require the change.
- **DR4 risks not in the MC.** All of them lead to "pending" or "unresolvable", not to a wrong grade, except the
  source_id-reuse case in §3.6. They do not change the stakes.

### 3.6 Global risks to fix or record before sealing
- **The grader's DR4 path is untested.**
  - `gaia_epoch.fetch` swallows any DR4 exception (renamed columns, a different `RELEASE` string) and silently falls back to
    DR3. These sources have no DR3 epoch photometry, so the seals would sit pending (FileNotFoundError path) until the
    fetcher is fixed.
  - The grade is whatever the grader code does on the day it runs. Recommended: put the grader commit (`evaluate`,
    `_frame`, `to_series`) in the seal's `extra`/provenance. Also commit now that the DR4 adaptation will only *map columns*
    (time, G mag, `rejected_by_photometry`, variability reject) and will not change the grading rules.
- **DR4 source_id mapping.**
  - If a DR3 id is absent from DR4, the seal sits pending forever. That costs nothing, but it is lost.
  - If a DR3 id is reused for a *different* star in the same HEALPix pixel, the grader would grade the wrong star, most
    likely "false". Gaia warned at EDR3 that ids are not guaranteed stable and to use the neighbourhood cross-match tables.
  - Higher risk: J131026 (RUWE 2.17, IPD multi-peak) and J163539 (IPD multi-peak).
  - Mitigation: before grading, check that the DR4 source lies within 0.5″ of the DR3 position and that its baseline median
    G is within 0.3 mag of DR3. The corrected statements name "the DR4 source cross-matched to it", so a mis-mapped grade can
    be voided against the sealed text.
- **The proposal's optional neighbour seal for J154239: do not seal it.** Grading it would need a separate case whose target
  is the neighbour, and "exactly one of the two brightens" cannot be written as one Check.

## 4. Re-runnable tests behind §3 (scripts were throwaway, outside the repo)
- **Raw DR3 flags.** Datalink `EPOCH_PHOTOMETRY`, `RELEASE=Gaia DR3`, `VALID_DATA=false`, for the 25 ids in
  `work/dr3_ml_sample.csv`. Read the raw CSV *before* `to_series` and count `rejected_by_photometry` rows and null
  `g_transit_mag` / `g_transit_time`. Fit `g_transit_time` against `transit_id` on the valid rows to date the rejected ones.
- **CCD calibration.** VizieR (vizier.idia.ac.za) `I/358/vmicro` with `TmaxP0` 2373..2704; their DR3 epoch photometry as
  above; `I/355/gaiadr3` cones of 2′ (`o_Gmag`, `MatchObs`). The RUWE/IPD control uses 5′ cones, G ± 1, around J131026,
  J163539 and J160706.
- **Alert completeness.** The same 146 events, matched within 2″ against `hunts/H-0005/alerts.csv`.
- **MC sensitivity.** `work/gaialib.simulate` + `grade` with `models.atlas_draws` / `scenario_draws`. Branches: flag > 0.5 and
  > 1.0 mag; Ornstein-Uhlenbeck red noise of 0.03-0.10 mag (τ 60-100 d); excess flux rescaled to effective k = 0.3-0.5.
- **Note:** the ESA TAP server was not answering on 2026-10-30 evening, so the gaia_source queries went through VizieR. The
  datalink server worked throughout.

## 5. Resolve-by date
- **Proposed: `resolve_by: "2027-12-31"` on every seal.**
- **What `resolve_by` controls.** `grade_due` grades true/false as soon as the data allow, whatever the date. `resolve_by`
  only controls how long a check with fewer than 3 points waits: until `resolve_by` + 60 d. After that it is graded
  "unresolvable", which does not count in the score.
- **Why 2027-12-31 rather than 2027-06-30.** A later date costs nothing. It allows a ~6-month DR4 slip plus time to adapt the
  fetcher to the DR4 data model.
- **If DR4 slips past ~2028-02-29.**
  - With no DR4 data at all, the seals simply stay pending: no case file, so the grader errors and does not close them.
  - With partial data, checks with ≥ 3 points are graded normally, and checks with fewer are closed as "unresolvable".
- **Sealing procedure.** Pass `resolve_by` to `register_prediction` (it feeds the seal), or add it to every JSON item if the
  genesis importer is used. Without it, the default puts the date in 2015-2018 (§1, blocker 1).
