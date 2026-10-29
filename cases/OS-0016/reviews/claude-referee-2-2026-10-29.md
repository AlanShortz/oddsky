# Referee report 2: H-0007 candidate J040025.77+323527.4 (Gaia DR3 170329679884731008), the ATLAS fit and the parallax claim

Author: claude-referee (second pass), 2026-10-29. Scope: the ATLAS light curve (`work/atlas_J040025.txt`), the joint fit
`scripts/hunt_h0007_lensfit.py` → `work/lensfit_J040025.{json,csv}`, and the claims built on it (no-parallax χ² 462/69, parallax χ² 98/67,
tE = 47.6 ± 0.4 d, u0 = 0.141, πE = 1.05 ± 0.13, A_max 7.1, the out-of-sample peak check, the lens mass).
All numbers below come from my own code in `reviews/claude-referee-2-2026-10-29/` (r1-r12). It runs outside the Oddsky tools
(pandas, scipy, emcee, MulensModel 3.12), from the repo root, with `uv run python` (`--with emcee` / `--with MulensModel` where noted). The library
`r2_lib.py` is written from scratch and does not import the investigators' script. It bins per night, band **and unit**, drops frames
more than 15% from their own night's median (this removes one frame, 58027.552, at f = 1.06 among f = 2.8 frames), and gets the Sun's position from astropy `get_sun` (GCRS)
rather than the negative barycentric Earth.

## 1. Verdict

The 2017 event is microlensing, and its light curve really is asymmetric. Every variant I tried rejects a symmetric Paczyński curve
(Δχ² 85-490): both ATLAS units show the asymmetry on their own, and it is not an early-season, zero-point, saturation, NEOWISE or
difference-imaging artifact. **The parallax measurement is overstated.** The data measure a source-lens acceleration. Of that, only
π_E,∥ ≈ 0.6 is robust. π_E,⊥ supplies most of |πE|, and it moves from −0.45 to −1.4 when you allow a 1% zero point for unit 02a,
which the 2017-18 baseline itself shows. There is a second u0 solution with tE = 51.8 d. A constant-acceleration trajectory, xallarap
and (before the peak nights are added) a static binary lens fit as well as annual parallax or better. Only physical priors favour
parallax. "πE = 1.05 ± 0.13, 0.19 M☉ at 0.5 kpc" must become "an asymmetry consistent with annual parallax, |πE| ≈ 0.6-1.6; the lens mass is
not measured".

- **P(mundane, i.e. not microlensing) = 0.05.**
- **P(the asymmetry is astrophysical rather than ATLAS systematics) = 0.95.**
- **P(it is annual parallax, i.e. the parallax detection is real) = 0.80.**
- **P(πE = 1.05 ± 0.13 as quoted is an honest interval) ≈ 0.3.**

## 2. Attacks and results (numbered as in the brief)

**1. Independent re-derivation, geometry, degeneracies (r3, r4, r10).**
- *Geometry.* My Δs agrees with the investigators' to < 3.3×10⁻⁵ AU over the season. MulensModel 3.12, an independent implementation of
  Gould (2004), reproduces their magnifications to 0.5%, with the same πE (N, E) signs and **u0 of opposite sign**. MulensModel's Δβ = πE × Δs is defined with the
  opposite handedness. That has no physical consequence, because both signs are fitted, but say "u0 > 0 in our convention (u0 < 0 in MulensModel)".
  - Pitfall: MulensModel reads a bare `"60.107 32.59"` string as hours, which gives a 20% disagreement. Pass sexagesimal.
  - The projection onto N/E and the Sun-from-Earth sign are correct. The πE vector (PA ≈ 201°) is the geocentric lens-source proper-motion direction.
- *Replication.* My binning gives static χ² 453.9 and parallax χ² 89.3 (75 points), with πE = (−0.99, −0.37) and |πE| = 1.06, t0 58012.20, tE 47.75,
  u0 0.142. That is their solution. Their csv recomputes to 462.0 and 98.2 exactly.
- *Ecliptic degeneracy* (β = +11.75°). A u0 < 0 solution exists at **Δχ² = +1.9** with πE = (−1.02, −0.46) and **tE = 51.8 ± 1.6 d**. The quoted
  tE = 47.6 ± 0.4 ignores it. An emcee run seeded in both modes (r8) gives tE 68% [47.5, 52.8], 95% [47.0, 55.3].
- *πE decomposition.* The Sun's projected acceleration at t0 points to PA 255° (N, E = −0.26, −0.97), so π_E,∥ = **+0.62** and π_E,⊥ = **−0.86**.
  The large component is the poorly constrained perpendicular one.
- *Jerk-parallax degeneracy.* The full grid (r4_grid.csv, 3,162 fits) has a mirror minimum at πE = (+1.2, −1.1), i.e. π_∥ = 0.75, π_⊥ = **+1.45**,
  |πE| = 1.6, at **Δχ² = +20.5 (u0 < 0) / +32 (u0 > 0)**.
  - Divided by the error inflation the residuals need (×1.66² ≈ 2.8, item 4), that is Δχ² ≈ 7-12, so the mirror is disfavoured, not excluded.
  - The |πE| profile has Δχ² < 9 for 0.78-1.43 and < 25 for 0.6-1.8.
- *Generic acceleration.* A constant-acceleration trajectory (Δτ = ½a_τx², Δβ = ½a_βx²; the same five parameters as parallax) fits **better: χ² 78.7 against
  89.3**. Adding a jerk term gives 73.6.
  - The difference sits entirely in the Dec 2017-Mar 2018 tail, where parallax predicts A = 1.005-1.03 and the data sit at 0.97-1.03.
  - It remains when the 02a zero point is free (69.6 against 79.4).
  - Within the event itself (57940-58090) the two are identical (13.5 against 13.7).
  - So the data constrain an acceleration. They do not independently confirm Earth's orbital time dependence.

**2. ATLAS systematics (r1, r4, r5).** The asymmetry survives every attack; the value of πE does not.
- *What the asymmetry is.* The core is symmetric about MJD ≈ 58010.6-58011.5 (A = 2.8 at 57993.6 and 58027.6). The far wings are not:
  A = 1.51 (Jul 30, 01a) and 1.61 (Aug 5, 02a) at t0 − 47/−41 d, against 1.30 (02a) at t0 + 45 d. That is a 15-20% difference, against a 1.2-1.3% nightly scatter.
- *Season start, airmass.* In nine other seasons, the nights from day-of-year 205-220 have median 1.003, sd 0.011 (27 nights, airmass 1.5).
  The 2017 nights had airmass 1.2-1.3. There is no early-season excess.
- *Unit zero points.* The baselines agree to 0.3% overall (01a 11,053, 02a 11,018 µJy). But **in the 2017-18 season 01a/02a = 1.013**, and a free 02a scale
  fits 0.9895 ± 0.0033 (Δχ² = −10, 1 parameter). With it, πE = (−0.60, −0.46), |πE| = **0.76**, π_⊥ = −0.46. π_∥ stays at 0.60.
- *Saturation.* chi_n/A² for the 01a peak night (58009.6, m 11.64, FWHM ≈ 3 px) is 5-10, the same as 01a at A = 2.6.
  The 02a peak night (58007.6, m 11.85, FWHM ≈ 2 px) is at 145-375, against an 02a baseline median of 33.
  With all points included, every model leaves 58007 about 4% low and 58009 about 4% high. That fits 02a nonlinearity near m ≈ 11.9, not 01a.
- *Variants* (r4_variants.csv; Δχ²(static − parallax), |πE|):

  | variant | Δχ² | \|πE\| |
  |---|---|---|
  | baseline | 365 | 1.06 |
  | cut 11.8 (adds 58007) | 475 | 1.06 |
  | no cut (adds both peak nights) | 487 | 0.99 |
  | cut 12.5 | 358 | 1.20 |
  | cut 13.0 (wings only) | 85 | 1.57 |
  | no NEOWISE | 360 | 1.06 |
  | per-unit baselines | 374 | 1.07 |
  | 02a scale free | 349 | 0.76 |
  | fs free per band | 339 | 1.03 |
  | 01a + NEOWISE only | 187 | 1.28 |
  | 02a + NEOWISE only | 158 | 0.94 |
  | chi_n < 100 frames only | 334 | 1.13 |
  | 2% calibration floor | 132 | 1.09 |
  | drop Jul 30 + Aug 5 | 186 | 1.19 |
  | drop the post-event tail | 287 | 0.91 |
  | drop 58055-58077 | 247 | 1.49 |

- *Robustness.* A night-by-night jackknife (r4_jackknife.csv) moves |πE| only within 1.01-1.18, so no single night carries it.
  π_∥ stays at 0.55-0.82 in every variant, while π_⊥ ranges from −0.45 to −1.37.
- *NEOWISE* contributes nothing to πE (1.057 without it). It is an achromaticity check only.
- *Difference imaging* is not an issue: the photometry is forced PSF photometry on reduced images (`use_reduced=True`). The nearest Gaia neighbour is G = 19.6 at 6.3".

**3. Xallarap and binary lens (r6, r7, r11).**
- *Xallarap.* Circular-orbit xallarap fits as well as parallax or better for P ≥ 180 d: χ² 77.5 (P = 180), 75.8 (365), 74.4 (500), against 89.3.
  Shorter periods fail (P ≤ 120 d: χ² ≥ 114). The light curve cannot reject it; physics does.
  - The source's orbital semi-major axis is ξ_E·D_S·θ_E. At θ_E = 0.3 mas the P = 180 d solution needs a companion of ≥ 3.4 M☉, and P ≥ 250 d needs ≥ 9 M☉.
  - A companion that massive but dark would be a black hole. A luminous one would dominate the SED, which is a single 4,800 K giant.
  - The reflex wobble α = ξ_E·θ_E ≥ 0.25 mas at P ≈ 0.5 yr is not easy to hide behind RUWE 0.99 at G = 14.
  - Xallarap is disfavoured, not excluded.
- *Static binary lens.* Without the peak nights, s = 0.55, q = 0.70 fits at χ² 78.8, better than parallax. But it crosses caustics between the data and predicts **A = 85 on
  58009.6**, against an observed 7.3. Fitted with the peak nights, the best binary lens is χ² 124.1 (s 1.89, q 0.084, α ≈ 0°) against 117.8 for parallax, with one more
  parameter. Disfavoured, not excluded.
- *The out-of-sample peak check* is not specific to parallax. Fitted without the peak nights, the models predict 58007.6 / 58009.6 as follows:

  | model | 58007.6 | 58009.6 |
  |---|---|---|
  | observed | 5.95 | 7.28 |
  | parallax | 5.95 | 6.64 |
  | constant acceleration | 6.05 | 6.76 |
  | acceleration + jerk | 6.43 | 7.28 |
  | xallarap P = 365 d | 6.60 | 7.69 |
  | static | 11.1 | 16.1 |

  The check kills the symmetric model and nothing else. Parallax **under-predicts the 01a peak night by 9%** (≈ 5σ at the quoted errors), and that night shows no sign of saturation.

**4. Are the uncertainties honest? (r5, r8).** No.
- *Residuals.* Off-event χ² is 45 for 28 nights (the MAD floor underestimates the tails). Event-season residuals have lag-1 autocorrelation 0.37-0.44 and 12 sign runs in 43 nights.
- *emcee*, 48 walkers seeded in both u0 modes, 6,000 steps:

  | run | \|πE\| 68% | 95% |
  |---|---|---|
  | errors scaled to χ²/dof = 1 | 0.95-1.26 | 0.82-1.43 |
  | + correlated-noise factor 1.47 | 0.90-1.35 | 0.73-1.58 |
  | + free 02a zero point | 0.67-1.12 | 0.56-1.41 |

  The fitted jitter is 0.6% (68% < 0.9%).
- *A_max* 95% is 5.7-9.7 (quoted 6.2-8.4). *tE* 95% is 47-56 d (quoted 46.9-48.4).
- The investigators' MCMC started from a 10⁻³ ball around one mode, with unscaled errors. The ±0.4 d on tE and ±0.13 on πE are 4-10× too small once
  the second mode and the systematics are included.
- *Blending.* Parallax with fs free gives fs_o = 0.77 ± 0.24, fs_c 0.62 ± 0.24, fs_W 0.77 ± 0.24, and |πE| 1.22 (r12). "fs = 1.00, no blend" is an assumption, not a result.

**5. Physical plausibility and lens detectability (r9, r12).** A simple Galactic Monte Carlo (thin and thick discs, flat rotation curve, Chabrier IMF to 0.01 M☉
plus 10% white dwarfs, Gaia source proper motion, rate-weighted) for events with tE 44-56 d toward (162.8°, −15.3°) at D_S = 3 kpc:
- *πE prior.* Median πE 0.54 (5-95%: 0.18-1.38). P(πE > 0.82) = 0.22, P(> 1.0) = 0.13. **πE ≈ 1 is plausible, not exotic.**
  The measured direction is unremarkable: 18% of events lie within 30° of PA 201°.
- *Likely lens.* Among events with πE > 0.75: 90% have D_L < 1 kpc, 58% have M < 0.3 M☉, 14% are brown dwarfs and 19% white dwarfs.
  The likely lens is an M dwarf at 0.3-0.7 kpc. A brown dwarf at ≥ 1 kpc or a white dwarf is not excluded.
- *Mass range.* Along the mass-distance relation, across the range |πE| = 0.76-1.05: M = 0.19-0.36 M☉ at 0.5 kpc and 0.075-0.14 M☉ at 1 kpc.
  Over the 95% posterior with errors inflated (run E): **0.10-0.65 M☉ at 0.5 kpc and 0.04-0.26 M☉ at 1 kpc**.
- *Detectability now.* For πE = 1.05:
  - D_L = 0.4 kpc: G ≈ 19.4, Ks ≈ 15.2 (ΔKs 4.0), separation **0.14"** in 2026.8.
  - D_L = 0.5 kpc: G 20.7, Ks 16.3 (ΔKs 5.1), 0.11".
  - D_L ≥ 1 kpc: a brown dwarf at Ks > 20 within 0.05".
  - Gaia (needs ≳ 0.4" at Δm ≳ 4), 2MASS and WISE cannot see it.
  - The NEOWISE and ATLAS magnifications on the same night agree (W1 2.731 against the o-band model 2.725). So the lens supplies ≲ 3% of the W1 light, i.e. D_L ≳ 0.35 kpc for πE ≈ 1.
  - Keck or VLT AO in K could detect an M-dwarf lens at D_L ≲ 0.5 kpc from about 2030 (0.15-0.2", ΔK 4-5). A brown-dwarf lens is undetectable.

**6. Does anything kill microlensing? (r1, r5, r11).** No.
- It is a single event in eleven years: no other night is > 15% above baseline in c, and the one o outlier (2022 Jan 1) is a single 03a frame.
- With parallax the event-window χ² is 44 for 47 points. The light curve is smooth.
- NEOWISE is achromatic: W1 = W2 to 0.5%, matching the contemporaneous o-band value.
- The rise is **slower** than the decline. Novae, dwarf novae, flares and symbiotic outbursts do the opposite.
- Limits on the test:
  - The rise began during the 4-month seasonal gap (last pre-event point 2017 Mar 28, A = 1.01-1.04 in c).
  - ATLAS has only **two c nights** in the event (12 frames, A ≤ 1.10), so ATLAS gives no colour test. The 2.5σ "fs_c ≠ fs_o" in J040025.md is not significant with parallax (0.62 ± 0.24 against 0.77 ± 0.24).

**7. Novelty (2026-10-29).** Apparently unreported. ASAS-SN and ADS remain unchecked.
- VSX (vizier.idia.ac.za, 120"): only Gaia DR3 170329508086043392 (ROT) at 59.6".
- TNS: nothing within 60". Within 15', only SN 2023ucx and AT 2023npo, both 2023 ZTF objects. There is no ATLAS17 designation.
- SIMBAD (CfA mirror; the CDS host timed out): no object within 30".
- Web searches for the Gaia id, "J040025.77+323527.4" and "J04002576+3235273": no hits.
- The nearest literature events are unrelated: ASASSN-V J044558.57+081444.6 (ATel 10677, a 2014 event, tE 45 d) and Kojima-1 / TCP J05074264+2447555 (Nov 2017).
- ASAS-SN Sky Patrol is still down (maintenance banner dated 2026-10-13; the client fails).

## 3. Most plausible mundane explanation remaining

For the event itself: none. For the parallax number: a ~1% unit- and season-dependent ATLAS zero point plus PSF nonlinearity near m ≈ 12 in 02a.
These are not mundane enough to fake the 15-20% wing asymmetry. They are enough to move π_⊥, and so |πE| and the lens mass, by a factor of 2.
Xallarap from a massive dark companion is the astrophysical alternative to parallax, and it is disfavoured on physical grounds only.

## 4. Required wording changes (J040025.md and any text built on `lensfit_J040025`)

1. **"The light curve is single, smooth and symmetric with Paczyński shape (tE = 45 d)"** must become: "single and smooth, but **asymmetric**: a symmetric
   point-lens curve is rejected (Δχ² ≈ 365); annual parallax fits (χ²/dof 89/70 after binning, 1.3)."
   Remove the ATLAS-only PSPL numbers (tE 44.6 ± 1.9, "u0 unconstrained, A_max ≈ 12", "model predicts A = 2.62 at the NEOWISE visit").
   The parallax model gives A = 2.73 at the NEOWISE visit.
2. **"πE = 1.05 ± 0.13 (πE,N −0.98, πE,E −0.37)"** must become:
   "π_E,∥ = 0.62 (0.55-0.82 across all systematics variants); π_E,⊥ = −0.86, systematics-limited (−0.45 to −1.4); **|πE| ≈ 0.6-1.6**
   (95%, errors inflated for correlated residuals and a free 02a zero point). A jerk-parallax mirror solution at |πE| ≈ 1.6 is disfavoured by Δχ² ≈ 7-12 after error
   inflation."
3. **"tE = 47.6 ± 0.4 d, u0 = 0.141"** must become "tE = 47.7 d (u0 = +0.14) or 51.8 d (u0 = −0.14, Δχ² = 1.9); 95% 47-56 d". Also note that the u0 sign convention is
   opposite to MulensModel's.
4. **"A_max 7.1 (6.2-8.4)"** must become "A_max ≈ 7 (5.7-9.7, 95%)".
5. **"No-parallax χ² 462/69; parallax 98/67"**: keep, but add "a constant-acceleration trajectory (same number of parameters) fits better (χ² 78.7 on the same
   data), as does xallarap with P ≥ 180 d (74-78); the data measure an acceleration, and the parallax interpretation rests on its physical
   plausibility (xallarap would need a ≥ 3 M☉ dark companion)."
6. **The out-of-sample check** must read: "it rejects the symmetric model (predicted ×11 and ×16); parallax, acceleration and xallarap all predict the
   peak nights to within 10%. Parallax predicts 58007.6 (02a) exactly and under-predicts 58009.6 (01a) by 9%." It is not evidence for parallax over the alternatives.
7. **"Implied lens ~0.19 M☉ at 0.5 kpc, ~0.075 M☉ at 1 kpc"** must become "**the lens mass is not measured** (θE unknown). Along the mass-distance relation,
   0.1-0.65 M☉ at 0.5 kpc and 0.04-0.26 M☉ at 1 kpc; most likely an M dwarf within 1 kpc."
   Do not write "brown dwarf" or "0.19 M☉" in a title, hook or brief.
8. **"The source fraction comes out at 1.00 when bounded (no blend)"** must become "fs = 1 is assumed. With parallax, fs_o = 0.77 ± 0.24."
9. **Achromaticity**: "ATLAS c has only 12 points in the event" must become "two c nights (12 frames) at A ≤ 1.10; no ATLAS colour test. The
   per-band fs difference is 0.4σ with parallax."
10. **Gaia DR4 predictions** (Prediction 1) must be updated to ΔG = −0.40 (2017 Jul 27), −0.88 (Aug 22), −2.07 (Sep 18 16:35 UT) for every asymmetric
    model. The static model gives −0.28 / −0.81 / −2.49. Equal BP and RP changes are still required.
11. **Novelty**: add "SIMBAD (CfA mirror): nothing within 30"; TNS 15': only two unrelated 2023 objects; no ATLAS17 designation". ADS is still unchecked.
12. **Ladder status**: *reproduced* (two instruments) is correct for the event. The parallax should be labelled *candidate measurement*, not *measured*.
    Nothing about the lens mass is publishable.

## 5. Decisive follow-ups

1. **Gaia DR4 (Dec 2026): epoch photometry and epoch astrometry** for 170329679884731008.
   - Photometry: the Sep 18 transit (predicted ΔG −2.07, A ≈ 6.7) fixes the peak height independently of ATLAS saturation.
   - Astrometry: the astrometric-microlensing centroid shifts at the four transits are 0.32, 0.22, 0.22 and 0.07 θE, i.e. **0.3-0.5 mas for θE = 1-1.6 mas**.
     At G = 13-14 that is likely detectable. **θE gives the mass**, and the shift direction gives the μ_rel direction. Comparing that with PA(πE) ≈ 200° separates parallax from xallarap.
   - The full DR4 astrometric time series also bounds any source orbit (xallarap).
2. **ASAS-SN Sky Patrol (id 17180188199)** once the service returns: V/g at a 1-3 d cadence through 2017 Aug-Oct, unsaturated at V ≈ 12. That is a third
   instrument for the wing asymmetry, free of the ATLAS unit zero points. A joint fit with per-instrument scales should settle π_⊥.
3. Lens imaging with Keck or VLT AO in K around 2030 (expected separation 0.15-0.2" if D_L ≲ 0.5 kpc).

## 6. Tool fixes

- `scripts/hunt_h0007_lensfit.py`:
  - Seed the MCMC in both u0 modes and in the jerk-parallax mirror, and rescale the errors to χ²/dof = 1 (or fit a jitter term).
  - Report π_∥ and π_⊥, not only (πE,N, πE,E).
  - Fit per-unit (and per-season) zero points as nuisance parameters.
  - Fit parallax with fs free.
  - Fit the generic-acceleration and xallarap models as standard controls.
  - Its "out-of-sample" check should be run against those controls, not only the static model.
- Nightly binning with `floor(mjd − 0.3)` splits Hawaii nights at 07:12 UT (e.g. 57789.285 / 57789.316 land in different "nights"). Use `floor(mjd − 0.9)` for
  01a/02a, or bin by site-local date.
- `oddsky.data.atlas`: return the unit (obs[:3]) as a column, and flag frames brighter than m ≈ 12.2 with FWHM < 2.3 px (02a), where
  chi_n/A² rises.
- Add a MulensModel cross-check to the lens-fit tooling, and pass coordinates as SkyCoord: a bare decimal string is read as hours.

Scripts: `reviews/claude-referee-2-2026-10-29/`
- r1_explore.py: season, unit and saturation diagnostics.
- r2_lib.py: the library.
- r3_geometry.py: geometry and MulensModel check; needs `--with MulensModel`.
- r4_fits.py: variants, `--jack`, `--grid`; writes r4_variants.csv, r4_jackknife.csv and r4_grid.csv.
- r5_extra.py: unit scale, windows and residual correlation.
- r6_xallarap.py: writes r6_xallarap.csv.
- r7_binlens.py: binary lens, `[--all]`; needs `--with MulensModel`.
- r8_mcmc.py: needs `--with emcee`; writes r8_mcmc.json.
- r9_galaxy.py: Galactic Monte Carlo.
- r10_grid_binpred.py: grid minima and binary-lens peak prediction.
- r11_allpoints.py: peak-night predictions per model.
- r12_blend_gaia_lens.py: blending, Gaia predictions and lens brightness.
