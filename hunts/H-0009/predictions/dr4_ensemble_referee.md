# Referee report: Gaia DR4 ensemble forecast (`dr4_ensemble.md`)

Author: claude-referee (adversarial pass), 2026-10-31. Reviewed: `dr4_ensemble.md`, `dr4_ensemble_sample.csv`,
`dr4_ensemble_grade.py`, `work/ensemble/` (e1, e3, e4, e5, logs, `forecast.json`, `scenario_pass.csv`, `excluded.csv`,
`gost_sample.csv`, `dr3_test/`), `src/oddsky/data/gaia_epoch.py` and `series.py`, the DR3 sweep (review, `gaia_dr3_sweep.csv`,
`calib_known.csv`, `cones.csv`, `gost_transits.csv`), `work/sky4_strong.csv`, `dr4_referee.md`, `dr4_proposal.md`, and the
cases OS-0020..0025. My checks ran from throwaway scripts in `/tmp/oddsky_ens_ref/` (r1-r13). They import the grader and write
nothing into the repo; the live DR3 self-test and the DR3 dry run were redirected to `/tmp`. This file is the only repo file
I changed.

## 1. Verdict

**Not ready to seal. Nine fixes are needed first.** All of them can be made before the seal: two parameter changes in e4 and
`draw_fL`, one small grader change, and text. After them, re-run e4, e5 and `--test-dr3` and regenerate every number in the
document.

The two fixes that move the forecast:

1. **The lens fraction is calibrated on a different quantity from the one DR4 tests (R1).** The DR3 calibration counts a
   VARIABLE Gaia source *anywhere within 4″*, and one of its three detections, J172057, was a lens on a neighbour, not on the
   matched star. The DR4 rule grades only the matched star. Recalibrated on the matched star, and on the ≥ 2-transit subset
   that the test actually uses, the headline falls from **11.3 to about 8.8 (80% 5-13)**.
2. **The centroid likelihood ratios use an off-target rate that includes the frame artifacts (R2).** The sample excludes
   those artifacts. The corrected ratios are 0.48 / 1.16, not 0.35 / 1.30.

The rest (R3-R9) are a grader hole (a duplicated transit can make a PASS), gaps in the "what may change" clause, a sealed
statement misquoted in the overlap table, overclaiming wording in the falsification and overlap sections, and gradability
details.

**What holds up.**
- **The sample.** I re-derived 118 → 64 → 50 → 47 from the source tables. Every tested star is the brightest Gaia DR3 source
  within 3″, and the GOST counts match.
- **The arithmetic.** An independent re-implementation gives 11.31 (80% 6-17, 90% 5-19; lens passes 8.04), against 11.28
  in e4. The falsification thresholds at f_L = 0.20 (≤ 5 / ≥ 16 at the expected resolution; ≤ 6 / ≥ 17 if all 47 resolve)
  are the same for five seeds, and their tail probabilities are not close to 0.05.
- **The DR3 data.** The saved DR3 self-test files are identical to a live re-fetch made today, and all three events pass.
- **The negative control.** Sliding the event time across the DR3 span of the three stars (one fake time every 5 d, at least
  180 d from the real event) gives **0 passes in 180 testable trials** (222 others had too few transits).
- **The rule itself.** It is unambiguous on window, baseline, scatter and threshold.
- **The DR4 endpoint.** It returns HTTP 500 today for `RELEASE="Gaia DR4"`. The grader then prints "fetch failed" and stops,
  which is the right failure mode.

## 2. Required fixes (exact text)

### R1. Calibrate f_L on the matched star (or count the neighbour)

**The problem.**
- `draw_fL` uses 3/28 events with a VARIABLE source within 4″, over 14/23 known lenses.
- For J172057 the VARIABLE source (…175552, 0.59″) is not the survey's matched star (…175808, 2.2″): see `gaia_dr3_sweep.csv`
  (`survey_source_id` ≠ `gaia_source_id`).
- For the known lenses, all 14 flagged sources are the matched star (`calib_known.csv`, `matched_var`).
- So the calibration measures "lens on some Gaia source within 4″", but scenario L in e3, and the DR4 count, mean "lens on the
  matched star".
- The centroid ratios (1.30 / 0.35) are built to preserve the population mean. The model therefore asserts that the
  matched-star lens fraction equals the any-source fraction.
- Section 3.2's sentence "'L' therefore means lens-like on a Gaia-visible star, which is what that calibration measures" is
  exactly where the gap sits.

A second, smaller mismatch: every testable event has ≥ 2 GOST transits within ±30 d, so the flag efficiency should come from
the known lenses with ≥ 2 transits (14/20 = 0.70; the sweep's own table) rather than 14/23. The same subset of strong events is
2/27 (J044653 has no transits).

**Effect** (r10, r12; centroid fix R2 included in the last row):

| calibration | f_L median | expected PASS | 80% | in-span / after |
|---|---|---|---|---|
| as written: any source, 3/28 over 14/23 | 0.21 | 11.3 | 6-17 | 2.9 / 8.4 |
| matched star, 2/28 over 14/23 | 0.15 | 9.7 | 5-15 | 2.4 / 7.4 |
| matched star, ≥ 2 transits, 2/27 over 14/20 | 0.14 | 9.0 | 5-14 | 2.0 / 7.1 |
| the same, plus R2 | 0.14 | **8.8** | **5-13** (90% 4-15) | 1.9 / 6.8 |

Lens passes fall from 8.0 to 5.6 and achromatic passes from 4.6 to 3.4 (80% 1-6).

**Fix.** Replace `draw_fL` in `dr4_ensemble_grade.py`:

```python
def draw_fL(rng, n):
    """Lens fraction ON THE SURVEY-MATCHED STAR among strong events (Gaia DR3 sweep, s5/s7), restricted to events like the
    test's (>= 2 GOST transits within +-30 d): P(VARIABLE matched star | in-span strong event) = 2/27 (J180402, J180839;
    J172057's lens was on a neighbour, not on its matched star) over P(VARIABLE matched star | known lens) = 14/20, flat
    priors, clipped to [0, 1]. Returns (f_L, P(VARIABLE | lens)); the second is reused as the DR3 flag efficiency for
    lenses."""
    po = rng.beta(2 + 1, 25 + 1, n)
    pk = rng.beta(14 + 1, 6 + 1, n)
    return np.clip(po / pk, 0, 1), pk
```

Replace the f_L bullet in section 3.2 with:

> - **The only complete sample is the DR3 sweep.** Among in-span strong events with ≥ 2 Gaia transits within ±30 d, 2 of 27
>   have their **matched** Gaia star flagged VARIABLE (J180402, J180839). The third Gaia-confirmed event, J172057, was a lens on
>   a neighbour 2.8″ from the matched star, which this test would grade as "not counted". Among known lenses with ≥ 2 transits,
>   14 of 20 have the matched star flagged. That gives f_L ≈ 0.14 (80% 0.06-0.27) for **a lens-like brightening of the matched
>   star**, the quantity DR4 tests here. The sweep's "≈ 0.2" counts any Gaia source within 4″ and is about 1.4× larger.

Then state the tested hypothesis as "**~20% of strong events are lens-like brightenings of the survey-matched Gaia star**"
everywhere it appears (headline table, 2.6, 3.5). Holding f_L at 0.20 is still a reasonable test value: it lies inside the
matched-star interval. But the document must not call it the sweep's estimate.

**Alternative.** Count a PASS on the pre-registered `alt_source_id` (only J173525 and J180255 have one) as a PASS of the event.
That brings the statistic closer to the any-source calibration. It needs its own pass and scenario model for those two events,
so the recalibration is the simpler fix.

### R2. Centroid likelihood ratios without the frame artifacts

**The problem.** "P(off) = 31/122 for strong events" includes the 10 frame artifacts. Nine of the ten are off-target
(`sky4_strong.csv`: off_target × frame_artifact gives 22/90 among the 112 kept, 9/1 among the artifacts). The sample excludes
those artifacts, so the right rate is 22/112 = 0.196.

**The corrected ratios.** P(off | not on the star) = (0.196 − 0.3 × 0.111) / 0.7 = 0.233. That gives LR_off = 0.111 / 0.233 =
**0.48** and LR_on = 0.889 / 0.767 = **1.16**.

**Fix.** In e4, set `LR_OFF, LR_ON = 0.48, 1.16`, and in the docstring and section 3.3 replace the derivation with:

> Derivation: P(off | event on the star) ≤ 13/117 (known lenses) and P(off) = 22/112 for strong events once the frame artifacts
> (9 of which were off-target) are removed. With about 30% of strong events on the star, P(off | not on the star) = 0.233, so
> the likelihood ratios are 0.111/0.233 = 0.48 (off-target) and 0.889/0.767 = 1.16 (on-target).

Alone, this lowers the headline from 11.3 to 11.0.

### R3. A duplicated transit can make a PASS

**The problem.** `grade_series` counts rows, not transits. I added one copy of a single bright transit to the J180839 DR3 file,
at a quiet fake event time: one bright transit gives FAIL, and the same transit listed twice gives **PASS** (r6). DR4 tables, a
per-CCD → per-transit aggregation or a careless merge could all produce duplicates. The "two transits" rule must mean two
distinct transits.

**Fix in the grader** (`grade_series`, replacing the first two lines):

```python
    ok = ((df.flag.astype(str) != "rejected_by_photometry") & np.isfinite(df.mag.astype(float))
          & np.isfinite(df.t_mjd.astype(float)))
    # One row per (band, transit id): a transit listed more than once counts once (median magnitude).
    d = (df[ok].groupby(["band", "camera"], as_index=False, sort=False)
               .agg(t_mjd=("t_mjd", "first"), mag=("mag", "median"), err=("err", "max"), flag=("flag", "first")))
```

**Fix in the text.** Add to 2.1, under "Which transits count":

> - **A transit** is one field-of-view crossing: one `transit_id` in the DR4 per-transit table (GOST counts the same thing).
>   If a `transit_id` appears more than once in a band, it counts once, with the median of its magnitudes. Window and baseline
>   counts, and the "at least 2 above threshold", are counts of distinct transits.

Then add a duplicate-row case to e5, and re-run e5 and `--test-dr3`. Neither result changes, because the DR3 files have no
duplicates.

### R4. The "what may change after DR4" clause is too narrow in some places and too loose in others

**Too narrow.** As written, only "names of time, magnitude, error and flag columns" may change. Several things DR4 may
plausibly need are not covered:
- a different release label or endpoint (today the label is rejected with HTTP 500);
- a different time zero-point;
- flux instead of magnitude;
- a different per-CCD layout.

A strict grader would have to declare the forecast ungradable.

**Too loose.** The grader depends on the shared module `gaia_epoch.py`, which anyone may edit for other reasons before
December. One example: dropping variability-flagged transits there would silently change this grade.

**Fix.** Replace section 2.5 with:

> ### 2.5 What may change after DR4 (and nothing else)
>
> The grade uses `dr4_ensemble_grade.py`, `src/oddsky/data/gaia_epoch.py` and `src/oddsky/data/series.py` **as they are at the
> commit that seals this file**, with only these changes allowed:
>
> 1. **Retrieval.** The release label passed to `--release`, the endpoint and the request parameters of
>    `gaia_epoch._fetch_release`, or reading DR4's bulk files instead, provided the per-transit values are DR4's as published.
> 2. **Column mapping** in `gaia_epoch.to_series`: the names of the time, magnitude (or flux), error, transit-id and flag
>    columns.
>    - Time is converted to BJD(TCB) − 2400000.5 with whatever zero-point DR4 states.
>    - If DR4 gives only flux, G = −2.5 log10(flux) + DR4's published zero point.
>    - "rejected_by_photometry" means DR4's transit-level photometric rejection flag. All other DR4 flags are ignored.
> 3. **Per-CCD data.** If DR4 publishes only per-CCD G, the transit's G is −2.5 log10 of the median of its valid (unflagged,
>    finite) per-CCD fluxes, with DR4's zero point. A transit with no valid CCD is dropped.
> 4. **The DR3 → DR4 source-id map** `work/ensemble/dr4_idmap.csv` (`dr3_source_id,dr4_source_id`), built from DR4's
>    DR3-neighbourhood table.
>    - It takes the **nearest** DR4 source within 0.5″ whose G differs by at most 0.3 mag.
>    - With no such source, the DR3 id is used as is.
>
> The grade is published together with `git diff <seal commit> -- src/oddsky/data/gaia_epoch.py src/oddsky/data/series.py
> hunts/H-0009/predictions/dr4_ensemble_grade.py`. Any change outside items 1-4 voids the grade.

Also have the grader print `numpy.__version__` and `pandas.__version__`, and record them here (sealed with numpy 2.5.4,
pandas 2.3.3, Python 3.12.16). `pyproject.toml` allows numpy ≥ 1.26, `uv.lock` is untracked, and NumPy does not promise
identical `Generator` streams across versions.

### R5. OS-0025's sealed statement is misquoted

Table 1.3 gives OS-0025 as "brightest night in 2017 Jul 11-Sep 24 > 0.4 mag brighter (0.45)". That is the proposal's 6a, which
the referee dropped. The sealed P1 (`cases/OS-0025/case.yaml`, ledger K3) is 6b, a median test with a 0.15 mag threshold.

Replace the row with:

> | OS-0025 | J154239 | median G in 2017 Jul 11-Sep 24 > 0.15 mag brighter (0.45) | *(regenerated)* |

### R6. The overlap with the sealed cases: say it without claiming the seals were wrong

The current text says "If the ensemble's calibration is right, OS-0022, OS-0024 and OS-0025 were staked too high." Four
problems:

- **Different statements.** The sealed cases test medians or brightest nights over 75-250 d windows. The ensemble P(pass) is for
  its own ±30 d, two-transit rule. The two columns are not like-for-like. For L and R the sealed median tests pass about as often
  as the ensemble rule; for F, less often.
- **The new evidence postdates the seals.** The seals were registered 2026-10-31T03:31 UTC. The DR3 sweep, the source of the
  population calibration and of the non-flag conditioning, came later that day. Those stakes could not have used it.
- **J131026's evidence is underweighted without a stated reason.** The ensemble multiplies L and R by 2 for the DR3 CCD deficit.
  The sealed-case referee calibrated that deficit on 47 DR3 lenses at a likelihood ratio of **≈ 7** (`dr4_referee.md` §3.3).
  - With 7, the ensemble gives J131026 P(pass) **0.40** instead of 0.23 (r3).
  - If the ρ-depletion is also dropped for this one event, it gives 0.56. That is defensible because the deficit is itself
    evidence that DR3's transits did catch a brightening.
  - Either use ≈ 7 or state why 2.
  - With that, "OS-0024 was staked too high" does not survive.
- **J154239's specific evidence** (the neighbour 3.2″ away holding half the G flux) is not in the ensemble. The case's high N
  prior came from it.

**Fix.** Replace the "Why the numbers differ" and "What it implies" bullets with:

> - **These are different bets.** Each sealed case has its own window, statistic and threshold. The ensemble's P(pass) is for
>   the ±30 d two-transit rule of section 2, so the two columns are not directly comparable.
> - **Why the ensemble's numbers are lower.** The sealed priors (lens 0.30-0.55) came from the ATLAS follow-up record, a
>   lens-selected sample. The ensemble uses the Gaia DR3 population calibration (section 3.2). That calibration was computed
>   after the cases were sealed (sweep of 2026-10-31; seals registered 2026-10-31 03:31 UTC). For J131026 it also applies the
>   missing DR3 VARIABLE flag. The ensemble does not use J154239's neighbour (OS-0025).
> - **What this means for the record.** On present evidence the ensemble model would stake less on J124517 and J154239 (and,
>   depending on how the J131026 CCD deficit is weighted, on J131026). That compares two models. It does not correct the
>   sealed cases. The sealed stakes stand and are scored as registered. After DR4, each case is scored on its own statement,
>   and the ensemble's per-event probabilities are scored on the ensemble rule. Neither is rescored against the other.

If the authors want a like-for-like comparison, run each sealed Check (window, statistic, baseline, threshold) through e3's
simulator with the ensemble's weights. Seal those numbers here as "the ensemble model's probability of the sealed statement"
(optional, O9).

### R7. The falsification statement: name the hypothesis and say how conditional it is

**The problem.** "'~20% lenses' is falsified if ≤ 5 or ≥ 16" reads as a test of the lens fraction. With f_L held at 0.20 and
all 47 resolved, the variance of the count splits as 5.6 from lens passes and 4.4 from non-lens passes (r3). The non-lens part is
set by judgement priors. How far the thresholds move under the document's own sensitivity cases (r3, r4, r5):

| at f_L = 0.20, all 47 resolved | thresholds |
|---|---|
| as written | ≤ 6 / ≥ 17 |
| f_R = f_F = 0 | ≤ 4 / ≥ 14 |
| f_R mean 0.15, f_F mean 0.10 (section 3.6's row) | ≤ 7 / ≥ 20 |
| on-star pass probabilities ×0.85 (section 3.6's row) | ≤ 4 / ≥ 15 |
| flat-star pass rate 5% instead of 1% | ≤ 7 / ≥ 18 |
| **nuisance bounds** (low side: f_R = f_F = 0 and q ×0.85; high side: f_R 0.15, f_F 0.10, flat-star rate ≥ 3%) | **≤ 3 / ≥ 20** |

What that does to the power of the test:

| true f_L | P(count in the "too few" region): as written / nuisance bounds | P(count in the "too many" region): as written / nuisance bounds |
|---|---|---|
| 0 | 0.76 / 0.18 | – |
| 0.4 | – | 0.56 / 0.22 |

The achromatic-pass thresholds barely move with f_R and f_F (≤ 1 / ≥ 8-9 in every case above, ≤ 0 / ≥ 8 at q ×0.85),
because R and F rarely read achromatic. But that test has less power.

The caveat in section 6 ("a 'falsified' verdict is conditional on them") is right, but the headline and section 3.5 do not
carry it. "The count can reject f_L ≲ 0.05 and f_L ≳ 0.4" overstates. It does so about half the time under the document's own
priors, and about one time in five under the nuisance bounds.

**Fix in the grader.** After the existing verdict in `run_grade`, add a robustness tier:

```python
    # Robustness of a "falsified" verdict to the judgement-based non-lens priors (pre-registered nuisance bounds)
    low = full.copy()
    for s_ in "LRF":
        low[f"q_{s_}"] = low[f"q_{s_}"] * 0.85
    high = full.copy()
    high["q_N"] = np.maximum(high.q_N, 0.03)
    r_lo = ensemble_mc(low, n=20000, fL=0.20, use=use, resolved_known=True, fR_ab=(1e-3, 1e3), fF_ab=(1e-3, 1e3))
    r_hi = ensemble_mc(high, n=20000, fL=0.20, use=use, resolved_known=True, fR_ab=(3, 17), fF_ab=(2, 18))
    firm = ((p_le < 0.05 and np.mean(r_lo["npass"] <= k) < 0.05) or (p_ge < 0.05 and np.mean(r_hi["npass"] >= k) < 0.05))
    tier = "firm" if firm else ("conditional on the non-lens priors" if "FALSIFIED" in verdict else "")
    robust_lo, robust_hi = falsification_thresholds(r_lo["npass"])[0], falsification_thresholds(r_hi["npass"])[1]
```

Add `verdict_tier=tier, robust_falsified_if_at_most=robust_lo, robust_falsified_if_at_least=robust_hi` to `summ`.

**Fix in the text.** Replace the headline row with:

> | **"~20% of strong events are lens-like brightenings of the matched Gaia star" is falsified if** | the PASS count is in a 5%
> tail of the forecast's Monte Carlo with f_L held at 0.20, recomputed by the grader for the events that resolve (for
> orientation, if all 47 resolve: ≤ *a* or ≥ *b*). The verdict is **firm** if it also holds at the pre-registered nuisance
> bounds (≤ *c* or ≥ *d* if all 47 resolve); otherwise it is **conditional on the non-lens priors**. |

Fill a-d from the regenerated e4. With the current model: a = 6, b = 17, c = 3, d = 20.

Replace "What it can and cannot tell" in 3.5 with:

> - **What it can and cannot tell.** Under the stated priors, a true f_L of 0 would put the count in the "too few" region about
>   three times in four, and f_L = 0.4 would put it in the "too many" region about half the time. At the nuisance bounds those
>   chances fall to about one in five. A firm verdict needs an extreme count. A conditional verdict means "20% is inconsistent
>   with the count, given our judgement of how often non-lens brightenings occur". The count cannot tell 0.15 from 0.25. The
>   two tails are tested separately at 5% each, so the combined false-alarm rate at f_L = 0.20 is about 8%.

### R8. The DR3 self-test: say which star J172057 was graded on

"All three pass" is true for the sources graded. But J172057 was graded on …175552, the neighbour, not on the matched star.
Under this forecast's own rule, J172057 would not have counted.

Add under the self-test table in section 5:

> J172057 is graded here on 5959812622743175552, the neighbour where DR3 saw the lens. The survey matched 5959812622743175808
> (2.2″ from the AllWISE position, 2.8″ from the lens star). Under this forecast's rule J172057 would be graded on …175808, with …175552 reported as `alt_status (not counted)`.
> The test shows the rule detects a real event on the star it is given. It does not show that the matched-star rule catches
> every lens (section 3.2).

Also add the sliding control: "Sliding the event time over the three stars' DR3 span (one fake time every 5 d, ≥ 180 d from
the event): 0 passes in 180 testable trials."

### R9. Gradability details

- **2.2.** After step 5 add: "Transits between 30 and 150 d from t are used for neither the window nor the baseline."
- **2.3, step 4.** Add as the first undetermined case: "fewer than 5 BP or fewer than 5 RP baseline transits".
- **2.6, the PASS count.** Replace the sentence with: "The forecast interval is hit if 6 ≤ count ≤ 17 (inclusive, using the
  regenerated interval), however many events resolve; it is not recomputed."
- **Section 4: give the colour forecast a hit condition.** Add: "The colour forecast is hit if at least 40% (inclusive) of
  the passes with a determined colour are achromatic. With no determined colour it is not graded."
- **Headline table, colour row.** Replace "about 38% of passing events will have no usable BP" with "about 38% of passing
  events will have an undetermined colour". Undetermined also covers e_D > 0.05 and missing pairs.
- **3.1, N row.** "the brief's ~2%" means nothing to a stranger. Replace it with "an earlier estimate of ~2%".
- **Section 4.** Replace "Noise passes are random" with "noise passes on stars with a measurable BP read achromatic about half
  the time (a flat star has no colour change)". `scenario_pass.csv`: a_N 0.4-0.67 for bright stars.

## 3. Answers to the brief, point by point

**1. The rule.**
- **Unambiguous points.**
  - The window is ±30 d around `t_event_mjd`, the NEOWISE peak-visit MJD fixed in the CSV.
  - The baseline is every valid transit more than 150 d away. It includes other events and variability, but its median and
    MAD are robust, and e3 simulates lens wings in the baseline.
  - The scatter is 1.4826 × MAD of the baseline flux ratios, and the threshold is 1 + max(0.15, 5s).
  - The flags: only `rejected_by_photometry` and non-finite values are dropped.
- **Counting** is per DR4 row, which should mean per `transit_id` (one field-of-view crossing, as GOST counts); R3 makes that
  explicit.
- **Edge cases tested (r6).**
  - NaN magnitudes and times are dropped cleanly.
  - With BP removed, a pass reads "undetermined (too few BP or RP baseline transits)".
  - Too few baseline transits, or no G rows, give "untestable (data)".
  - The DR3 dry run gives 47 × "no epoch photometry" and "no event resolved".
  - Duplicates give a false PASS (R3).
- **Two smaller notes.**
  - The DR3 confirmations passed on transits from *different* epochs (J172057 at −7 and +25 d, J180402 at −9 and +20 d), not on
    the 106-minute pair. The sentence "A single outlier transit cannot make a pass" is true, but a single-epoch artifact seen in
    both fields of view can (O1).
  - `fL_posterior` is non-monotone at counts 0-2 (median 0.05, 0.00, 0.006) because the Monte Carlo has few hits there, and it
    is capped at 0.8 (O6). It is descriptive, not a verdict.

**2. The sample.**
- **The counts.** Re-derived exactly: 64 in the DR4 span; 3 with DR3 epoch photometry; 11 with no source within 4″ (7 in the
  DR3 span); 50 left, 25 of them in the DR3 span; 3 untestable by design.
- **Selection on DR3 information.** Removing the 3 DR3-flagged events and keeping the unflagged in-span ones *is* selection on
  DR3 variability. It is handled correctly, because the forecast conditions those events on the missing flag. That is not
  double counting: P(L_i | D) = ∫ P(L_i | f, d_i) p(f | D) df.
- **Off-target events** keep the matched star. That is right for a no-choice-after-data rule. The problems are in the inputs:
  the likelihood ratios (R2) and the calibration (R1).
- **Crowding**, checked from `cones.csv`:
  - only 2 of 47 tested stars have a catalogued Gaia neighbour within 2″ and within 2 mag (J172130: 1.1″, +1.1; J161048:
    1.6″, +1.2);
  - 3 have RUWE > 1.4 (J130153 4.2, J170153 8.3, J131026 2.2).
  So scan-angle contamination is a risk for about 5 events, not for the sample. Name them in the crowding caveat (O5).

**3. The forecast.**
- **Arithmetic.** Reproduced twice (above). After R1 and R2 the numbers change.
- **The DR3 non-flag depletion** (2.9 in-span against 8.4 after) is applied correctly: weights × (1 − e), and pass
  probability (q − e)/(1 − e) under nesting.
- **Two caveats on it.**
  - For J180744, J211957 and J192602, q_L < e_L, so "the flag is a subset of passes" cannot hold. The non-flag should be less
    informative for faint 2-transit events, not equally so (O3). The effect on the total is negligible.
  - "Three times as often" mixes in the follow-up events. In the blind core alone it is 0.12 against 0.31 per event, about
    2.5× (r11).
- **Noise.** The G noise (DR3 floor ×1.5) matches the three DR3 baselines (flux MAD 0.018, 0.025, 0.006). The 5s term makes
  stationary variability (the red giants' semi-regular jitter) harmless. A 1% flat-star rate is plausible given the neighbour
  statistics above.
- **Scenario fractions** are judgement, as stated. The issue is the headline's framing, not the priors (R7).

**4. The colour forecast.** Sound in construction: a pair-matched ΔBP − ΔRP, an honest error floor, and a BP-faint cut. The
expected achromatic share (66%, 80% 40-100%) is so wide that only "< 40%" can miss. That is fine if it is stated as the hit
condition (R9). The achromatic-pass count is the more prior-robust lens statistic (R7 table), which is worth saying in
section 4.

**5. Wording.** A stranger can run the grader, but cannot today:
- resolve a renamed release, endpoint or schema (R4);
- know whether a verdict is "firm" (R7);
- know whether the interval is inclusive and not recomputed (R9).

Overclaims:
- "~20% lenses" for what is "lens-like brightenings of the matched star" (R1, R7);
- "can reject f_L ≲ 0.05 and ≳ 0.4" (R7);
- "OS-0022/0024/0025 were staked too high" (R6);
- "All three pass" without the J172057 caveat (R8).

**6. The overlap.** The direction is plausible for OS-0022 and OS-0025, but it is a comparison between two models of different
statements, made with evidence that appeared after the seals. For OS-0024 it depends on the unexplained ×2. R6 gives the
wording.

## 4. Optional suggestions

- **O1.** Consider requiring the ≥ 2 passing transits to come from ≥ 2 distinct epochs (separated by more than 0.5 d). Only 3 of
  47 testable events have all their GOST window transits in one epoch, and the three DR3 confirmations would all still pass. It
  closes the single-epoch contamination route, but it changes q_F and needs e3 re-run. Not required, given the neighbour
  statistics.
- **O2.** The 23 events after the DR3 span also have unflagged stars over 2014-2017. That is evidence against recurrent
  variables (scenario R, e.g. young stars such as J182120) and irrelevant for one-off lenses. Applying it would lower R slightly
  for those events.
- **O3.** Make e_L event-specific (scale it with P(pass | L) of DR3's transits), so that faint 2-transit events are not
  depleted as much as well-sampled ones.
- **O4.** Have the grader also report the f_L test on the 39-event blind core. The 8 follow-up events have fixed weights that do
  not depend on f_L, so they only add noise to the f_L test. Section 6 already calls the blind core "the clean test".
- **O5.** Name J172130, J161048, J130153, J170153 and J131026 in the crowding caveat.
- **O6.** In `fL_posterior`, warn when fewer than about 50 Monte Carlo realisations match k_obs, and widen the grid past 0.8.
- **O7.** Before DR4, measure the flat-star false-pass rate empirically: run `judge` at random fake times on DR3 epoch
  photometry of low-amplitude bulge VARIABLE sources at G 16-20. That is an upper bound on the N rate and replaces the assumed 1%.
- **O8.** In the blind core the in-span / after ratio is about 2.5×. Say so next to "three times".
- **O9.** Seal the ensemble model's probability of each sealed statement (R6), so that the two calibrations can be compared on
  the same bets after DR4.
- **O10.** J161946's lens draws have an effective sample size of 73, below the 300 target even after the 1.5-million-sample
  redraw. Its q_L (1.000) is barely affected, but note it.

## 5. Reproduction

Scripts in `/tmp/oddsky_ens_ref/`, each run with `uv run python -I <script>` from the repo root:

| script | what it checks |
|---|---|
| r1 | e4 reproduction, seed stability, tail probabilities |
| r2 | independent Monte Carlo |
| r3-r5 | sensitivity, nuisance bounds, achromatic robustness, power |
| r6 | offline self-test, sliding control, grader edge cases including duplicates |
| r7 | posterior at extreme counts |
| r8 | neighbours and RUWE |
| r9 | sample re-derivation, matched-star check, single-epoch windows |
| r10, r12 | f_L recalibration, centroid ratios, combined effect |
| r11 | in-span against after-span in the blind core |
| r13 | live DR3 self-test and DR3 dry run (output in /tmp), DR4 endpoint probe |
