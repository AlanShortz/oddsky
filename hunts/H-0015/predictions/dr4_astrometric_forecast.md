# Gaia DR4 epoch astrometry of Oddsky's lenses: five forecasts

Author: claude (H-0015), 2026-11-02; revised the same day after the referee's report ("seal after changes"; every required
change and the strongly recommended ones applied, section 7). **A draft for sealing. NOT sealed.** It would be sealed by the
commit that merges it into `main` before Gaia DR4 is released (2026-12-02, ~11:00 UTC); after that nothing here may change
except the adaptations in section 5.

Sample: [`dr4_astrometric_sample.csv`](dr4_astrometric_sample.csv) (targets for F1-F4, controls for F5). Grader:
[`dr4_astrometric_grade.py`](dr4_astrometric_grade.py) (`--self-test`; `tests/test_h0015_grade.py`). Numbers:
[`work/forecast.json`](work/forecast.json) from [`work/forecast.py`](work/forecast.py). Inputs: the ranking
(`../data/ranked_targets.csv`), per-target simulated fits with the final fitter (`../data/forecast_fits.csv`,
`../scripts/s8_forecast_sims.py`), the control list (`../data/controls.csv`, `../scripts/s7_controls.py`) and the
acceptance re-check (`../acceptance/summary_recheck.json`, `../scripts/s4_acceptance.py --parts recheck`). Hunt:
[H-0015](../README.md).

## The forecasts

| | statement (graded from DR4's epoch astrometry by the H-0015 stage; rules in section 2) | model | P(TRUE) | resolve by |
|---|---|---|---|---|
| **F1** | of the 109 ranked targets in DR4's span with Gaia DR3 RUWE ≤ 1.4, **between 2 and 6 inclusive** show a significant deflection (Delta chi^2 ≥ 25) | mean 3.5: 3.3 (nominal errors) or 1.6 (1.7x worse) from real lenses, 1.0 spurious | **0.80** | 2027-03-31 |
| **F2** | **OS-0020** (J163539.69-355208.3): DR4 bounds the lens below the black-hole range, **profile 95% mass upper limit finite and < 3 Msun** | P(lens) 0.75; limit < 3 Msun for every simulated 0.3-1 Msun lens (85% with errors 1.7x worse) and every fit without deflection, 6% at 3 Msun, 0 at ≥ 5; P(M > 3 \| lens) 0.018 (discounted) | **0.90** | 2027-03-31 |
| **F3** | **OS-0021** (J173150.73-444549.3, G 15.1, tE 120-490 d), graded only if DR4 bounds piE: the **95% mass upper limit is < 5 Msun** (no significant deflection with M_lo95 ≥ 5) | resolved in 100% of simulations; P(lens) 0.55, P(M ≥ ~4 \| lens) ~0.12 (BH share discounted), limit < 5 Msun for every simulated lens ≤ 3 Msun and every non-lens brightening | **0.93** (conditional on resolution) | 2027-03-31 |
| **F4** | **OS-0016** (J040025.77+323527.4, G 14.0, piE 0.6-1.6) **shows a significant deflection** | P(lens) 0.95 x P(detect \| lens) 0.73 nominal / 0.40 pessimistic | **0.54** | 2027-03-31 |
| **F5** | of the 325 sealed control stars (matched in G and position to the F1 targets, given fake event hints), **fewer than 1.5%** (at most 4) show a significant deflection | false positives per control 1.0% (5-95%: 0.8-1.3%) | **0.75** | 2027-03-31 |

**What they test.** F1: whether Gaia's one-dimensional epoch astrometry has the reach the simulations claim, on real
crowded targets. F5, its control: the same stage on matched stars where there is nothing to find, so an F1 TRUE cannot
come from systematics alone (and if F5 fails, F1 is read as contaminated). F2: that DR4 can bound OS-0020's lens below the
black-hole range. F3: the black-hole question for the brightest long event, graded only where DR4 can answer it. F4: that
DR4 detects the deflection of an ordinary lens (OS-0016's piE is measured, so a detection would give its mass).

**What they do not duplicate.** H-0009's ensemble (`hunts/H-0009/predictions/dr4_ensemble.md`) and the 15 sealed case
predictions grade Gaia **photometry**; H-0014's F1-F5 (`hunts/H-0014/predictions/dr4_search_forecast.md`) grade DR4's
microlensing **catalogue** and photometric brightenings. Nothing sealed so far uses DR4's epoch astrometry. OS-0016, OS-0020
and OS-0021 are members of F1 (F1 counts them). OS-0016's sealed photometric prediction (ledger 34) is independent of
whether its centroid moved.

**What the sample is.** F1's 109 targets: 6 Oddsky lens cases, 35 H-0010 candidates, 25 catalogued OGLE/KMTNet lenses (known
events, included as positive controls, not Oddsky discoveries) and 43 strong NEOWISE events whose median P(lens) is 0.07
(effectively null controls), all with Gaia DR3 RUWE ≤ 1.4 (Gaia16aye excluded: a binary lens). F5's 325 controls: three
Gaia DR3 stars per F1 target within 6', |ΔG| ≤ 0.3, five/six-parameter solutions, RUWE ≤ 1.4, not VARIABLE, > 10" from any
target, each given the t0/tE hint of a different F1 target.

## 1. Data and identity

- Inputs: only the outputs of the DR4-day stage `astrolens` (`src/oddsky/dr4day/astrometry.py` at the sealing commit), run
  as `uv run python scripts/dr4_day.py --release dr4` (stages `idmap`, `epochs`, `astrolens` at least), copied to
  `hunts/H-0015/dr4/astrolens_results.csv`, `astrolens_status.csv` and **`idmap.csv`** (the grader refuses to grade without
  it, exit 2).
- Identity: our ids are Gaia DR3 ids, mapped by the pipeline's `idmap` stage and, for ids it lacks (the controls), by the
  same rule inside `astrolens`: the nearest DR4 source in `dr3_neighbourhood` within 0.5" and 0.3 mag, else the DR3 id. A
  target whose release id is not that match is ineligible.
- Epoch astrometry: DataLink `EPOCH_ASTROMETRY` of release "Gaia DR4". Sky-mapper CCDs, CCDs with `used_by_agis_al` false and
  `|centroid_pos_al| > 1e6` mas are dropped; CCDs are averaged per transit (inverse-variance) with a 0.05 mas floor.
- **Format sanity checks** (each makes the target ineligible, i.e. its forecast UNRESOLVABLE, never silently FALSE): every
  time inside DR4's span ± 5 d; `ra0`/`dec0` constant per source; `parallax_factor_al` equal to fE sin(theta) + fN cos(theta)
  from the ephemeris to 0.02 (95th percentile), trying the scan angle in degrees, then radians (this fixes the unit, zero
  point and direction of the scan angle). `blended`, `multipeak`, `g_class`, `gates`, `transit_proc_flags` and
  `agis_source_excess_noise` are carried into the results.
- Photometry: the run's Gaia DR4 epoch photometry (G, BP, RP; flagged transits dropped; fetched by the stage for sources the
  H-0014 epochs stage did not cover, the controls among them) and, for cases with ATLAS forced photometry in their case
  files (OS-0016, OS-0020, OS-0021, OS-0026, OS-0027, OS-0029), ATLAS o/c (good-flag points, nightly means). Baselines: the
  median outside max(3 tE_hi, 150 d) of t0.
- The fitter: `src/oddsky/analysis/astrolens.fit_target` with the stage's arguments: t0 and tE hints from the sample (the
  controls' fake hints included); a piE prior only where the sample gives a range (OS-0016 0.6-1.6 -> 1.1 ± 0.25; OS-0020
  0.25-0.55 -> **0.40 ± 0.075**); blend-offset terms; **one along-scan offset per Gaia window class** (`g_class`) other than
  the commonest, in both models; the robust outlier pass (deleted residuals), error rescaling when chi^2/dof > 1.2 and
  one-at-a-time 5-sigma clipping; the profile-likelihood mass. A dark lens (no lens light) is assumed.

## 2. Grading rules

- **Eligible:** in the sample for that forecast, status "fitted", not simulated, ≥ 20 transits after cleaning, identity as
  above.
- **Significant deflection:** Delta chi^2 (no deflection minus deflection, both with the blend-offset and window-class
  terms) ≥ 25, error scale ≤ 3, and 0 < theta_E ≤ 50 mas.
- **F1:** significant deflections among eligible F1 targets. TRUE if 2 ≤ count ≤ 6, else FALSE. UNRESOLVABLE if fewer than
  75% of the F1 sample are eligible.
- **F2:** OS-0020 (Gaia DR3 6020322385418675200). TRUE if the profile 95% one-sided mass upper limit M_ul95 is finite and
  < 3 Msun. FALSE if eligible and not. UNRESOLVABLE if not eligible.
- **F3:** OS-0021 (Gaia DR3 5952322268527918208). FALSE if its deflection is significant with M_lo95 ≥ 5 Msun. Otherwise:
  UNRESOLVABLE if M_ul95 is unbounded (piE unconstrained: DR4 cannot answer the black-hole question); TRUE if M_ul95 < 5 Msun;
  FALSE if M_ul95 ≥ 5 Msun. UNRESOLVABLE if not eligible.
- **F4:** OS-0016 (Gaia DR3 170329679884731008). TRUE if its deflection is significant. FALSE if eligible and not.
  UNRESOLVABLE if not eligible.
- **F5:** the fraction of eligible controls with a significant deflection. TRUE if < 1.5% (with 325 controls: at most 4),
  else FALSE. UNRESOLVABLE if fewer than 75% of the controls are eligible.
- **Resolve by 2027-03-31** for all five. If DR4 publishes no epoch astrometry, or DataLink does not serve it by then, all
  are UNRESOLVABLE. A later re-release does not reopen them.
- **Before any claim (not part of the grade):** a significant deflection goes to a referee, who must check DR4's NSS tables
  for an orbit, the window classes and gates at the deflection's epochs (`g_class`, `gates`), `blended`/`multipeak`
  transits and per-CCD residuals. A binary source can return a large theta_E (section 3) and so a large "mass".

## 3. How the probabilities were computed

All numbers are in `work/forecast.json` (`work/forecast.py`). One calibration throughout: **the Galactic model's black-hole
share halved** (the model makes too few ordinary long events, median tE 14 d against ~20 d observed, so its black-hole share
of long events is about 2x generous); errors nominal or 1.7x worse, weights 0.5/0.5.

- **The fitter** (final, robust version) was re-checked on 1,520 simulated targets (`../acceptance/summary_recheck.json`).
  On the 300 injections it removed no point and clipped none, i.e. it returned exactly what the original fitter did, so the
  original acceptance calibration (2,900 targets: profile 68%/95% mass intervals cover the truth 69%/93%, theta_E pulls 1.01)
  carries over; this independent subset gives 58% (n = 83) and 95%, theta_E pulls 1.08, and detection probabilities within
  ~2 points of the fast prediction (0.277 observed, 0.293 predicted). Coverage is calibrated in simulation (the same model
  generates and fits the data).
- **False positives** (re-check; "significant" as graded):

  | null (no deflection) | significant |
  |---|---|
  | clean, errors right or 30% underestimated, 3% 8-sigma outliers, one 100-mas value | 1/610 (0.16%) |
  | an offset neighbour inside the window (matches the fitted blend term by construction: circular) | 0/150 |
  | an astrometric binary source just under DR3's RUWE 1.4 (the referee's recipe: P 0.3-3 yr, AL rms 0.2-0.95 sigma_CCD) | **3/160 (1.9%)**, theta_E 1.9-4.9 mas |
  | control-like (flat photometry, fake hints), clean | 0/150 |
  | control-like, binary | 1/150 (0.7%), theta_E 6.8 mas |

  Per target FP = (1 - f_b) FP_clean + f_b FP_binary + FP_other, with f_b ~ U(0.05, 0.25) (stars hiding such a binary) and
  FP_other ~ U(0, 0.5%) (what no simulation contains), Laplace estimates for the measured rates. Targets: 0.92% per
  target (5-95%: 0.61-1.24%), i.e. 1.0 expected spurious detections in F1. **Binary false positives
  return large theta_E** (1.9-7 mas here; one of the referee's had 7.3 mas): with OS-0020's piE prior that is 0.6-2.2 Msun,
  and a larger one would look like a black hole. Hence the referee check before any claim (section 2).
- **F1.** Per target, P = P(lens) x P_det(Galactic-model lens) + (1 - that) x FP; the count is a Poisson-binomial over the
  109 targets, mixed over the error scenarios and the FP prior. Mean 3.47; P(0) 0.03, P(1) 0.11,
  P(2) 0.19, P(3) 0.22, P(4) 0.19, P(5) 0.13, P(6) 0.08,
  P(≥ 7) 0.06. **P(2-6) = 0.80.** About 30% of the expected count is false positives, so F1 is read
  together with F5.
- **F5.** The same FP model for controls (1.03% per control), binomial over 325 controls: P(at most 4) =
  **0.75** (for comparison, P(< 2%) 0.94, P(< 2.5%) 0.99). A FALSE means the real-data false-positive rate exceeds ~1.5%,
  which would make any F1 count suspect.
- **F2.** OS-0020: P(TRUE) = P(lens) Σ_M P(M | lens) P(limit < 3 | M) + (1 - P(lens)) P(limit < 3 | no deflection). P(M | lens)
  from a 400,000-lens Galactic draw (effective sample 1,209; P(BH | lens) 0.035 in the model, 0.018 discounted). P(limit < 3 |
  M) from 30 fits per mass (nominal) and 20 with errors 1.7x worse: 1.0 nominal and 0.85 pessimistic (0.93 mixed) at 0.3 and 1 Msun, 0.06 at 3, 0 at 5 and 10, 1.0
  with no deflection. **0.90.** The referee guessed 0.5-0.7 from the median limit (1.5 Msun for a 1 Msun lens); what matters
  is how often the limit is below 3 Msun, and with OS-0020's piE prior it nearly always is. **The mass rests on that prior
  (0.40 ± 0.075 from the case's ATLAS fits):** if the true piE were half as large, every mass would double.
- **F3.** OS-0021, conditional on resolution: resolved (finite limit, or a heavy detection) in every simulated fit (light,
  heavy and non-lens). P(TRUE | M) 1.0 at 0.3-1 Msun, 0.97 at 3, 0.10 at 5, 0 at 10; a non-microlensing brightening
  (Gaussian, 10% chromatic, ATLAS peak compressed as if saturated, 2% correlated noise) always gave a finite limit far below
  5 Msun (median 0.1 Msun: the lens fit to a bump finds a large piE). P(M | lens) from a 400,000-lens draw (P(BH | lens) 0.22 in
  the model, 0.11 discounted). **0.93.** OS-0021's case file says its ATLAS peak "may be partly saturated" and the rise is
  "mildly chromatic"; piE rests on that light curve while the lens simulations used Gaussian errors, which is why an
  unbounded limit is UNRESOLVABLE rather than FALSE. F3 is therefore a statement about the black-hole question only.
- **F4.** OS-0016: P(lens) 0.95; its Galactic-model lens (a prior: median 0.4 Msun, theta_E 2.6 mas in these draws) gives a significant deflection
  in 22/30 fits nominally and 8/20 with errors 1.7x worse. **0.54.** OS-0016 brightens to G ≈ 11.9 at peak and crosses the
  G ≈ 13 window-class boundary; the per-class offset term absorbs a calibration step there (test), at some cost in power
  that the simulations above do not include (they carry no window-class labels).
- Not included: DR4 publishing epoch astrometry in a form the reader cannot use (all five UNRESOLVABLE, not FALSE).

## 4. Edge cases

| case | rule |
|---|---|
| no epoch astrometry in DR4, or `has_epoch_astrometry` false for a target | ineligible ("no epoch astrometry"); F1 and F5 need 75% of their samples |
| a format sanity check fails (time span, parallax factor vs scan angle, reference point) | ineligible ("error: ..."), never fitted |
| DataLink names the product differently | allowed adaptation: `--set retrieval_epoch_astrometry=...` |
| column renames, a different array serialisation, VOTable arrays, a per-CCD long table | allowed adaptation: aliases in `astrometry.ALIASES` / the array reader (names and serialisation only) |
| the time unit or zero point, or the scan-angle unit, documented by ESA differently from the draft | allowed adaptation: set them as ESA documents them; the sanity checks must then pass |
| a duplicated or partial DataLink response | duplicates by `transit_id` are dropped (the per-transit average uses each CCD once); a missing source counts as "no epoch astrometry" only after a re-request |
| a DR3 source split into several DR4 sources, or merged | the idmap rule decides; no other match is tried |
| the archive fails for a chunk | retried with backoff and recorded as errors with ids; re-running the stage before the resolve-by date is allowed |
| `EPOCH_ASTROMETRY_BRIGHT` | none of our targets or controls is among the 49 brightest stars |
| a target's DR4 photometry missing | the fit runs on what exists (ATLAS for the cases; astrometry with fs_ast = 1 otherwise) |
| fitter crashes for a target | "error: fit failed": ineligible; a code fix is not allowed |
| a significant deflection that a referee later traces to binarity or a neighbour | still counts for F1/F4/F5 (mechanical rules); the interpretation goes in the hunt |

## 5. Allowed adaptations after sealing

Only: (1) the DataLink retrieval-type name and release label; (2) column-name aliases and array serialisation in the reader;
(3) the time unit and zero point, and the scan-angle unit, as documented by ESA (the sanity checks of section 1 must pass
with them); (4) re-running failed archive requests. Thresholds, the samples, the fitter and its settings, the photometric
baselines and the sanity-check tolerances may not change. Any adaptation is published as a diff with the grade.

## 6. Self-test

`uv run python -I hunts/H-0015/predictions/dr4_astrometric_grade.py --self-test`: synthetic stage outputs with known answers
(all TRUE, all FALSE, mixed, F3 unresolvable and heavy, too many missing), an identity mismatch (ineligible), a missing id
map (refused), simulated rows (never graded) and the committed DR3 dry run (all five UNRESOLVABLE).

## 7. Changes after the referee (2026-11-02)

Required changes:
1. **Robust outliers.** `fit_target` now (a) picks outlier candidates from a position + proper motion + parallax fit, which
   cannot bend to one point, and removes one only if the deflection model fitted without it still misses it by > 6 robust
   sigma (a deleted residual), (b) rescales errors, then (c) clips one point at a time at 5 sigma, also on deleted
   residuals; the returned and null fits use exactly the kept points. The referee's check: one 1000-sigma value now costs 1-2
   of 72 transits (was 64), two ±300-sigma values 2 (was up to 52). Tests: `test_one_wild_outlier...`,
   `test_final_fit_contains_no_point_beyond_the_clip...`, `test_a_bright_star_with_one_100_mas_value...`,
   `test_a_real_strong_deflection_survives...`. A first version (worst-group MAD on the deflection model's residuals) failed
   the new 100-mas null at G 12 (the deflection and blend terms bend to fit one point); the final version passes it (0/160).
2. **Format sanity checks** in `normalise` (time span, parallax factor vs scan angle with degree/radian detection, constant
   `ra0`/`dec0`) raise `FormatError` and make the target ineligible; quality columns are carried to the results;
   duplicated responses are deduplicated. Tests in `tests/test_dr4day_astrometry.py`. "Time unit and zero point as documented
   by ESA" added to the adaptations (section 5).
3. **F2 reframed:** "OS-0020: M_ul95 finite and < 3 Msun" (was "M > 3 Msun at 3 sigma", P 0.02); the piE-prior dependence is
   stated.
4. **F3:** the guessed 0.8 non-lens factor is replaced by simulated non-microlensing brightenings; "piE unconstrained" is
   UNRESOLVABLE; the case file's saturation/chromaticity caveat is recorded; P recomputed conditional on resolution.
5. **F4** reads "shows a significant deflection".
6. **Control sample and F5:** 325 Gaia DR3 control stars fetched 2026-11-02 (`../data/controls.csv`, 0 errors); the stage runs
   them on the day; F5 grades their false-positive rate.
7. **Wording** in the README and here: the target breakdown (25 known OGLE/KMTNet controls and 43 NEOWISE events with median
   P(lens) 0.07 among F1's 109), the Kaczmarek et al. (2026, A&A 714, A374) paraphrase, "consistent with" for OGLE-2011-
   BLG-0462, OS-0016 softened, "calibrated in simulation", the circular neighbour null, OGLE/KMTNet events labelled controls
   (`role` column in the ranking).
8. **Identity:** the stage writes the id map (extended to the controls) to `hunts/H-0015/dr4/idmap.csv`; the grader exits 2
   without it (test).

Strongly recommended, applied: a per-window-class along-scan offset in both models (test with a calibration step at
peak); one black-hole-share calibration (the model's, halved) for F2, F3 and the honest odds; binary-source false positives
measured (1.9% of binaries under RUWE 1.4), stated to return large theta_E, and folded into F1 and F5.
