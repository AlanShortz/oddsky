# Hunt H-0015: weighing Oddsky's lenses with Gaia DR4 epoch astrometry

**Question.** Microlensing photometry gives the Einstein time tE and, with annual parallax, the microlensing parallax piE.
It does not give the lens mass. A lens also deflects the light centroid of the source, by up to theta_E/sqrt(8) for a dark
lens, so astrometry measures theta_E, and M = theta_E / (kappa piE) with kappa = 8.144 mas/Msun. Gaia DR4 (2 December 2026)
publishes every along-scan position Gaia measured in 2014.6-2020.1. Oddsky's lists hold 120 events in or near that span
(section 4): 6 Oddsky lens cases with photometric fits, 36 lens candidates from H-0010 (Gaia's classifier saw them; nobody
reported them), 28 catalogued OGLE/KMTNet lenses that Gaia DR3's catalogue left out (known events, included as targets and
positive controls, not as Oddsky discoveries), 47 strong NEOWISE brightenings, most of them unlikely to be lenses (median
P(lens) 0.07, effectively null controls), and 3 lens cases that peak after DR4. Can DR4 weigh any of their lenses, and is any
of them a black hole?

Only one isolated stellar-mass black hole is confirmed, OGLE-2011-BLG-0462 (Sahu et al. 2022; Lam et al. 2022; Mróz,
Udalski & Gould 2022). Long events (tE > 100 d) are where heavy lenses sit.

**Status: tool built, acceptance-tested, targets ranked, release-day stage dry-run on DR3 (2026-11-02); revised the same day
after the referee's report ("seal after changes"; every required and strongly recommended change applied, see the
forecast's section 7). Forecasts drafted, NOT sealed.** Nothing here is a detection or a claim.

## 1. What DR4 will contain, and what limits it (research, 2026-11-02)

Tags: **[S]** a source states it; **[I]** our inference.

| | | source |
|---|---|---|
| product | `epoch_astrometry`: one row per source and field-of-view (FoV) transit, per-CCD quantities as 10-element arrays (index 0 = sky mapper, not used by AGIS; 1-9 = AF1-AF9). 129.6 billion rows, 62 TB, for "all sources treated in the main astrometric processing" [S] | [DR4 page](https://www.cosmos.esa.int/web/gaia/dr4); draft data model 2026-06-26 (`gaia-dr4-prerelease-draft-data-model_2026-06-26.zip`, §3.1) |
| columns | `obs_time_tcb` (ns since J2010.0, TCB, per CCD), `obs_time_bary_corr`, `scan_pos_angle` theta (deg; sin and cos are dw/dalpha* and dw/ddelta), `parallax_factor_al`, `centroid_pos_al` (local-plane along-scan coordinate w, mas, relative to `ra0`, `dec0`), `centroid_pos_error_al`, `used_by_agis_al`, plus `agis_source_excess_noise`, IPD and gating flags. `centroid_pos_ac` is empty: **the data are one-dimensional** [S]. 16.4 million `centroid_pos_al` values fall outside the window and must be ignored [S] | draft data model |
| access | **DataLink only**, `RETRIEVAL_TYPE=EPOCH_ASTROMETRY` (`EPOCH_ASTROMETRY_BRIGHT` for the 49 brightest stars); `all_source_flags.has_epoch_astrometry`; 50 ids per request anonymous, 5,000 logged in [S/I] | draft data model; [DataLink products](https://www.cosmos.esa.int/web/gaia-users/archive/datalink-products) |
| precedent | the Gaia BH3 pre-release (Gaia Collaboration, Panuzzo et al. 2024, A&A 686, L2, App. B): per-CCD w ± sigma (mas), BJD(TCB), AL parallax factor, scan angle (deg from local north), outlier flag; reference epoch J2017.5 [S] | arXiv:2404.10486 |
| precision | per-CCD along-scan scatter of EDR3 residuals (Lindegren et al. 2021, A&A 649, A2, Fig. A.1, as digitised in astromet's `scatteral_edr3.csv`): 0.14 mas at G 13, 0.25 at 15, 0.66 at 17, 1.19 at 18, 2.3 at 19, 4.8 at 20 [S]. Per FoV transit (÷√8, + 0.05 mas floor in quadrature) [I]: **0.07, 0.10, 0.24, 0.42, 0.82, 1.69 mas**. Klüter et al. (2020, A&A 640, A83, eq. 15) give similar numbers; Rybicki et al. (2018, MNRAS 476, 2013, table 3) pre-launch errors are ~2x worse at G 15-18 (our pessimistic case). Gating flattens precision for G < 13 [S] | as cited |
| scanning law | GOST (https://gaia.esac.esa.int/gost/) forecasts every FoV transit of a position with time, scan angle, CCD row and AL/AC parallax factors; it ignores dead time (~80% of transits reach the ground) [S]. We fetched it for all 120 targets and OGLE-2011-BLG-0462 over DR4's span (49-180 transits each, median 75) and checked its convention: the AL parallax factor equals fE sin(theta) + fN cos(theta) to 0.0014 (test) | `data/gost_transits.csv.gz` |
| literature | Belokurov & Evans 2002 (MNRAS 331, 649); Dominik & Sahu 2000 (ApJ 534, 213; blended/luminous-lens shift formulas, used here); Rybicki et al. 2018 (M > 10 Msun lenses with G ≲ 15.5 weighed to a few-15%; BH astrometric events ~4e-7 per source per year); Klüter et al. 2018, 2020, and 2022 (AJ 163, 176) (predicted Gaia astrometric events); McGill et al. 2023 (LAWD 37, 0.56 Msun, HST); Jabłońska et al. 2022 (GaiaDR3-ULENS-001, a DR3 astrometric anomaly); Kruszyńska et al. 2024 (A&A 692, A28; 11 DR3 dark-lens candidates); **Kaczmarek, Sweeney, Wyrzykowski & Bastian 2026 (A&A 714, A374; arXiv:2609.10705): 322 ± 70 DR4 events whose maximum astrometric shift exceeds the per-CCD precision (a lenient threshold, not a detection forecast; blending ignored); of the 49 remnant lenses with both an astrometric and a photometric signal, 8 are black holes; they note piE stays uncertain, limiting mass determination** [S] | as cited |
| OGLE-2011-BLG-0462 | Mróz, Udalski & Gould 2022 (ApJL 937, L24): t0 HJD 2455763.33, tE 239.7 d, u0 0.0026, piE (N, E) = (0.073, -0.050), theta_E 5.68 ± 0.40 mas, **M 7.88 ± 0.82 Msun**, D 1.49 kpc; source I_S 19.8 with ~20x more blend light (a neighbour 0.38" away). Sahu et al. 2022: 7.1 ± 1.3 Msun; Lam et al. 2022: 1.6-4.4 Msun; Sahu et al. 2025: 7.15 ± 0.83 Msun [S]. We found no published discussion of Gaia astrometry for it [S/I] | as cited |

What this means for us [I]: DR4 gives one-dimensional positions per transit, so the deflection is seen only as its
projection on each scan direction, sampled ~15 times a year; the lens must have shifted the source by a few times the
per-transit error over several transits, i.e. theta_E ≳ 1 mas at G 15 and ≳ 3-5 mas at G 18. Blended light dilutes the
deflection and a neighbour inside Gaia's window adds a centroid pull that follows the magnification; both are modelled.

## 2. The tool: `src/oddsky/analysis/astrolens.py` (+ `lenspop.py`)

A joint photometric + along-scan astrometric point-lens model, in `lensing.py`'s conventions (Gould 2004 geocentric
parallax; the trajectory's direction is piE's):

- **photometry:** flux ratios per series (Gaia G/BP/RP, ATLAS, NEOWISE...), source fraction fs per series, annual parallax;
- **astrometry:** w = position offset + proper motion + parallax (AL factor from the data) + theta_E x deflection(t) +
  blend-offset pull. The deflection includes third light at the source's position and optionally lens light (Dominik & Sahu
  2000 eqs. 93-99, tested); its dilution uses the Gaia G fs. The **blend-offset pull** (a neighbour inside the window,
  direction unknown: two linear terms, profile ∝ 1/(A fs + 1 - fs) - 1) is in both the deflection and the no-deflection
  model, so a detection must beat what a blend can do;
- **fit:** five nonlinear parameters (t0, tE, u0, piE_N, piE_E); everything else is solved linearly at each step; theta_E ≥ 0;
  outliers removed by a robust pass on deleted residuals (candidates from a position + proper motion + parallax fit, which
  cannot bend to one point), RUWE-like error rescaling, then one-at-a-time 5-sigma clipping; **one along-scan offset per
  Gaia window class** (`g_class`) in both models, so a calibration step at G ~ 13, which a bright event crosses at peak,
  cannot imitate a deflection; **likelihood-ratio test** Delta chi^2 = chi^2(no deflection) - chi^2(deflection);
  theta_E upper limit by profiling; **mass by profile likelihood** (at fixed M, theta_E = kappa M |piE| and the trajectory is
  refitted) giving M_best, 68/95% intervals, the 95% upper limit and the significance of M > 3 Msun;
- **fast expected signal:** `expected_dchi2` (noise-free Delta chi^2 with the trajectory known), validated against full fits;
- **Galactic prior** (`lenspop.py`): disc + Dwek bar densities, disc/bulge kinematics, the source's Gaia proper motion,
  event-rate weighting; samples theta_E, mu_rel and piE for a given lens mass and the event's tE/piE constraints; a lens mass
  function (Kroupa stars, WDs, NSs, BHs; BHs 0.9% of all bulge events, 21% of tE > 120 d events).

Tests: `tests/test_astrolens.py` (21: geometry, conventions incl. GOST's scan angle, the fitter, mass profile, the
blend-offset nuisance, Asimov = noise-free fit, Galactic prior, wild outliers, a strong deflection surviving the robust pass,
window-class steps), `tests/test_dr4day_astrometry.py` (10: format reading and the sanity checks, duplicated responses, the
dry run) and `tests/test_h0015_grade.py` (5).

## 3. Acceptance test (`scripts/s4_acceptance.py`; `acceptance/summary_full.json`; `figures/acceptance.png`)

2,900 simulated targets, each fitted blind: dark lenses at the **real positions of our 120 targets** (their GOST transits,
20% dropped for dead time), lens distance and motion drawn from the Galactic model for that sight line and mass, t0
anywhere in DR4's span, |u0| < 1, fs 0.5-1, **Gaia G photometry only** (conservative: real targets also have ATLAS/NEOWISE),
t0 known to ±20 d and tE to ×1.35 as for our targets. Detection = Delta chi^2 ≥ 25.

**(a) Detection probability** (30 per cell; ±0.09), nominal EDR3 errors / pessimistic (Rybicki+18):

| lens \ G | 12 | 14 | 16 | 18 | 20 |
|---|---|---|---|---|---|
| 0.1 Msun | 0.07 / 0.0 | 0.03 / 0.0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.3 Msun | 0.27 / 0.3 | 0.20 / 0.2 | 0.13 / 0.0 | 0 / 0 | 0 / 0 |
| 1 Msun | 0.43 / 0.7 | 0.57 / 0.4 | 0.23 / 0.2 | 0.03 / 0.0 | 0 / 0 |
| 3 Msun | 0.57 / 0.7 | 0.77 / 0.9 | 0.53 / 0.4 | 0.23 / 0.1 | 0.03 / 0 |
| 10 Msun | 0.77 / 1.0 | 0.80 / 0.8 | 0.57 / 0.4 | 0.23 / 0.2 | 0.10 / 0.2 |
| 30 Msun | 0.97 / 1.0 | 0.87 / 1.0 | 0.80 / 0.8 | 0.47 / 0.2 | 0 / 0 |

By timescale (G ≤ 18, all masses): 0.04 for tE < 30 d, 0.26 for 30-100 d, **0.65 for 100-300 d**, 0.62 above. A random
Galactic black-hole event is not guaranteed even at G 14 (t0 near the span's edges, unfavourable scan geometry, lenses near
the source with small theta_E); a known event's t0 and tE make the per-target numbers in section 4 sharper.

**Mass precision** of detections (profile likelihood, Gaia G photometry only): median sigma(M)/M 0.13-0.5 for 1-30 Msun at
G 12-18 (0.8 for 1 Msun at G 18), ~2.5 at G 20 (piE is then barely constrained); P(mass to ±50%) 0.3-0.57 at G ≤ 16 for M ≥ 1 Msun. The intervals are
calibrated in simulation (the same model generates and fits the data): **68% intervals contain the true mass 69% of the
time, 95% intervals 93%**; theta_E pulls have robust sigma 1.01.
The Gaussian (covariance) mass intervals cover only 58% and are not quoted.

**The fast approximation used for ranking holds:** predicted mean detection probability 0.324 against 0.322 observed in the
full fits, and within a few per cent in every Delta chi^2 bin.

**(b) OGLE-2011-BLG-0462** at its real Gaia scan times (55 transits), with the Gaia DR3 source at its position as source +
blend (4056442477683080960, G 17.93, 0.17" from the OGLE position; fs ≈ 0.05 from OGLE's blend ratio):

| scenario | expected Delta chi^2 | P(detect) | result of 100 fits |
|---|---|---|---|
| as it happened (peak 2011, 3-8 tE before/after DR4), blended | 0.0 | 0 | unconstrained (the 0.5-1.2 mas tail is a slow drift absorbed by the proper motion; theta_E error with the trajectory known ~970 mas) |
| as it happened, unblended | 0.01 | 0 | same |
| peaking mid-DR4 (2017 Mar), blended as observed | 1.0 | 0 | theta_E < 24 mas (95%) |
| peaking mid-DR4, unblended at G 17.9 | 186 | **0.99** | theta_E 5.74 (median), **M_best 7.9 Msun**, M < 10 (95%) |
| peaking mid-DR4, unblended at G 16 | 1,160 | 1.00 | M_best 7.9 Msun, M < 8.6 |

So Gaia could not have detected OGLE-2011-BLG-0462 (too early, and 95% of the light in Gaia's window is the neighbour's),
consistent with the literature's silence; but **the same black hole in the middle of DR4's span, unblended at G ≲ 18, would
be detected and weighed to ~10-15%**. Kaczmarek et al. (2026) find its parameters "consistent with" their simulated black-hole distributions.
`figures/ob110462.png`.

**(c) False positives** (300 each, theta_E = 0, Delta chi^2 ≥ 25): clean errors 0/300; errors underestimated by 30% 1/300
(the rescaling recovers 1.27); 3% 8-sigma outliers 2/300; an unresolved neighbour 50-300 mas away inside the window 0/300 —
but **that null is circular**: it injects exactly the functional form the fitted blend-offset terms remove (without them it
fakes a deflection, test). Real neighbours, binary sources and calibration offsets are not tested by it.

**(d) Re-check after the referee** (`acceptance/summary_recheck.json`; 1,520 targets; the final robust fitter; "significant"
as graded: Delta chi^2 ≥ 25, error scale ≤ 3, 0 < theta_E ≤ 50 mas):

| simulated | n | significant | note |
|---|---|---|---|
| injections (subset, 10 per mass x G cell) | 300 | as before | the robust pass removed no point and clipped none: identical to the original fitter. Profile coverage 58% (68%) and 95% (95%) on 83 detections (the original 2,900: 69%/93%); theta_E pulls 1.08 |
| clean / underestimated errors / 3% 8-sigma outliers / one 100-mas value | 610 | 1 (0.16%) | the 100-mas null: 0/160 (a first robust version let 7/160 through with Delta chi^2 ≥ 25: a short lens or a tiny bump times a huge blend offset bent to fit the point) |
| circular neighbour null | 150 | 0 | |
| **astrometric binary source under DR3 RUWE 1.4** (the referee's recipe) | 160 | **3 (1.9%)** | theta_E 1.9-4.9 mas; binaries return large theta_E, i.e. large "masses" |
| control-like stars (flat photometry, fake hints), clean / binary | 150 / 150 | 0 / 1 (0.7%) | theta_E 6.8 mas |

The forecast's false-positive model: (1 - f_b) x 0.33% + f_b x 2.5% + up to 0.5% for what no simulation contains, with
f_b = 5-25% of stars hiding such a binary: ~0.9% per target, ~1.0 spurious detection among F1's 109 targets. Hence the
control sample (F5) and the referee check before any claim.

## 4. Ranked targets (`scripts/s5_rank.py`; `data/ranked_targets.csv`; `figures/ranked.png`)

120 targets (`scripts/s1_targets.py`): H-0010's 67 classifier-only Gaia lenses (28 catalogued OGLE/KMTNet lenses with
survey tE, 36 candidates, 3 cases), the 47 other strong NEOWISE events of the sealed H-0009 ensemble sample with a Gaia star,
and the lens cases (OS-0016, OS-0020, OS-0021, OS-0026, OS-0027, OS-0029; OS-0017/18/19 peak after DR4 and are listed as
pre-event tails). Gaia DR3 inputs fetched 2026-11-02 (`scripts/s2_gaia_dr3.py`; 120/120 sources, 95 neighbours within 3",
0 errors): positions, proper motions, parallaxes, errors, RUWE, excess noise, IPD flags, GSP-Phot. GOST transits for all
(`scripts/s3_gost.py`; 0 errors).

Per target: the AL error scale k (DR3 parallax_error against our model's prediction from its DR3-span transits; median
0.85, i.e. our curve is ~15% conservative; floored at 1), the source distance, the blending prior, and for dark lenses of
1, 5 and 10 Msun (and for the Galactic lens population) the Galactic-model theta_E, the expected Delta chi^2 at the target's
transits and P(Delta chi^2 ≥ 25), nominal and with errors 1.7x worse. Rank = P(lens) x max(P_det of the population's lens,
P_det of a 5 Msun lens): the probability that DR4 measures the lens's mass or can measure/exclude a 5 Msun dark lens.
Gaia16aye (a binary lens) is listed but not ranked. The `role` column says what each target is for: the catalogued
OGLE/KMTNet events are known lenses (positive controls; their teams' own photometry would measure their masses better),
and the strong NEOWISE events are mostly null controls (median P(lens) 0.07).

| rank | target | set | G | P(lens) | tE (d) | P_det 1 / 5 / 10 Msun | theta_E if 5 Msun (mas) | P_det population (pess.) | pop. lens: median M, theta_E | P(BH \| lens) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | OS-0020 J163539.69-355208.3 | case | 18.3 | 0.75 | 120-190 | 0.08 / 1.00 / 1.00 | 12.4 | 0.15 (0.10) | 0.74 Msun, 2.5 | 0.09 |
| 2 | J180510.80-294545.7 | known lens (control) | 14.5 | 0.97 | 43-71 | 0.53 / 0.75 / 0.79 | 1.0 | 0.40 (0.15) | 0.63 Msun, 0.6 | 0.01 |
| 3 | OS-0016 J040025.77+323527.4 | case | 14.0 | 0.95 | 47-56 | - / - / - | - | 0.70 (0.46) | 0.27 Msun, 1.8 | 0.00 |
| 4 | OS-0026 J172057.05-414200.7 | case | 17.9 | 0.65 | 20-190 | 0.45 / 0.88 / 0.94 | 6.9 | 0.13 (0.03) | 0.46 Msun, 1.9 | 0.01 |
| 5 | OS-0021 J173150.73-444549.3 | case | 15.1 | 0.55 | 120-490 | 0.96 / 1.00 / 1.00 | 3.1 | 0.90 (0.62) | 0.83 Msun, 1.7 | 0.23 |
| 6 | J172157.74-293725.3 | known lens (control) | 16.3 | 0.97 | 84-131 | 0.20 / 0.50 / 0.67 | 1.4 | 0.22 (0.04) | 0.81 Msun, 0.7 | 0.25 |
| 7 | J072830.43-204112.5 | h0010 | 17.1 | 0.60 | 94-912 | 0.44 / 0.80 / 0.85 | 5.1 | 0.36 (0.15) | 0.66 Msun, 1.8 | 0.07 |
| 8 | J200958.93+321427.9 | h0010 | 17.7 | 0.45 | 14-130 | 0.36 / 0.72 / 0.78 | 3.5 | 0.11 (0.04) | 0.33 Msun, 1.0 | 0.00 |
| 9 | J184837.12-051620.2 | h0010 | 17.9 | 0.30 | 37-362 | 0.24 / 0.78 / 0.85 | 6.9 | 0.11 (0.03) | 0.57 Msun, 2.2 | 0.03 |
| 10 | J175343.19-325527.6 | known lens (control) | 17.2 | 0.97 | 43-79 | 0.12 / 0.24 / 0.33 | 1.1 | 0.08 (0.01) | 0.62 Msun, 0.5 | 0.03 |
| 11 | OS-0024 J131026.53-612259.2 | NEOWISE (null control) | 17.7 | 0.26 | 5-150 | 0.33 / 0.86 / 0.89 | 6.6 | 0.09 (0.02) | 0.30 Msun, 1.4 | 0.00 |
| 12 | J182539.91-125139.3 | h0010 | 17.0 | 0.35 | 14-136 | 0.18 / 0.56 / 0.65 | 5.2 | 0.05 (0.01) | 0.34 Msun, 1.3 | 0.00 |
| 13 | OS-0029 J180839.95-151910.4 | case | 16.0 | 0.50 | 10-94 | 0.13 / 0.38 / 0.45 | 1.3 | 0.04 (0.01) | 0.36 Msun, 0.5 | 0.01 |
| 14 | J013600.31+612130.4 | NEOWISE (null control) | 12.8 | 0.18 | 60-500 | 1.00 / 1.00 / 1.00 | 4.7 | 0.96 (0.84) | 0.56 Msun, 1.4 | 0.03 |
| 15 | J071033.70-021828.0 | NEOWISE (null control) | 11.6 | 0.18 | 60-500 | 0.96 / 0.98 / 1.00 | 4.7 | 0.76 (0.47) | 0.52 Msun, 1.1 | 0.01 |

`-`: no Galactic-model lens of that mass fits the event's tE and piE (OS-0016's photometry already excludes it).
J180510.80-294545.7 is OGLE-2017-BLG-0055 = KMT-2017-BLG-0568, J172157.74-293725.3 OGLE-2017-BLG-0114, J175343.19-325527.6
OGLE-2017-BLG-0329 (catalogued lenses that Gaia DR3's catalogue left out; H-0010). P(BH | lens) rests on a few heavy,
high-weight Galactic-model draws and is uncertain by a factor ~2 (OS-0020: 0.09 here, 0.035 in the 3x larger draw used for
F2; OS-0021: 0.23 and 0.22).

Reading the table [I]:
- **OS-0020** ranks first not because it is likely heavy but because DR4 settles it: its photometric piE (~0.38) means a
  5 Msun lens would have theta_E ~12 mas and shift the source by ~3 mas, impossible to miss even at G 18.3, while an ordinary
  lens (median 0.7 Msun in the model) is detected only 15% of the time.
- **OS-0016** (G 14.0, piE 0.6-1.6, tE ~50 d): a ≥ 1 Msun lens is already excluded by the photometry and the Galaxy, but the
  lens the model expects (a prior, median 0.27 Msun, theta_E ~1.8 mas) gives a detectable deflection 70% of the time, and with piE
  already measured, DR4 has roughly an even chance (F4, P ~0.5) of detecting OS-0016's deflection, which with the measured
  piE would give its lens mass.
- **OS-0021** (G 15.1, tE 120-490 d): the brightest long event; P_det 0.90 for its expected lens and ~1 for any lens ≥ 1 Msun.
  With ATLAS's light curve for piE it is the best place to measure, or exclude, a heavy dark lens.
- The two G 11.6-12.8 NEOWISE events (J013600, J071033) would be weighed easily if they were lenses, but P(lens) is 0.18.

**Full simulated fits at each top target** (`data/rank_fits.csv`; 40 realisations per hypothesis with the target's own
transits, G, error scale, photometric constraints and, for OS-0016/20/21, ATLAS's real cadence and errors; 2,120 fits):

| target (rank, G) | P(detect): 1 / 5 / 10 Msun / model lens | P(M > 3 at 3 sigma): 5 / 10 Msun / model lens | sigma(M)/M of detections, model lens | M_ul95 if 1 Msun (median) |
|---|---|---|---|---|
| OS-0020 J163539.69-355208.3 (1, 18.3) | 0.07 / 1.00 / 1.00 / 0.15 | 0.65 / 1.00 / 0.15 | 0.11 | 1.5 |
| J180510.80-294545.7 (2, 14.5) | 0.57 / 0.75 / 0.68 / 0.47 | 0.00 / 0.03 / 0.00 | 0.50 | unbounded |
| OS-0016 J040025.77+323527.4 (3, 14.0) | - / - / - / 0.70 | - / - / 0.00 | 0.12 | - |
| OS-0026 J172057.05-414200.7 (4, 17.9) | 0.42 / 0.93 / 0.97 / 0.15 | 0.23 / 0.72 / 0.03 | 0.61 | unbounded |
| OS-0021 J173150.73-444549.3 (5, 15.1) | 0.93 / 1.00 / 1.00 / 0.90 | 0.97 / 1.00 / 0.33 | 0.11 | 1.2 |
| J172157.74-293725.3 (6, 16.3) | 0.15 / 0.55 / 0.60 / 0.17 | 0.03 / 0.12 / 0.00 | 0.63 | 4.3 |
| J072830.43-204112.5 (7, 17.1) | 0.47 / 0.85 / 0.93 / 0.38 | 0.45 / 0.90 / 0.07 | 0.19 | 1.8 |
| J200958.93+321427.9 (8, 17.7) | 0.40 / 0.85 / 0.78 / 0.15 | 0.28 / 0.62 / 0.00 | 0.45 | 2.4 |
| J184837.12-051620.2 (9, 17.9) | 0.20 / 0.62 / 0.90 / 0.05 | 0.10 / 0.65 / 0.00 | 0.29 | unbounded |
| J175343.19-325527.6 (10, 17.2) | 0.17 / 0.30 / 0.28 / 0.05 | 0.00 / 0.00 / 0.00 | 13.33 | unbounded |
| OS-0024 J131026.53-612259.2 (11, 17.7) | 0.38 / 0.85 / 0.95 / 0.10 | 0.38 / 0.85 / 0.00 | 0.45 | 1.7 |
| J182539.91-125139.3 (12, 17.0) | 0.12 / 0.60 / 0.50 / 0.03 | 0.10 / 0.33 / 0.00 | 0.83 | 23.4 |
| OS-0029 J180839.95-151910.4 (13, 16.0) | 0.07 / 0.45 / 0.47 / 0.05 | 0.00 / 0.00 / 0.00 | 245.80 | unbounded |
| OS-0027 J180402.30-181847.8 (76, 18.7) | 0.00 / 0.00 / 0.00 / 0.00 | 0.00 / 0.00 / 0.00 | - | unbounded |

The fits were run before the ranking's population draws were enlarged (5x); the fixed-mass rows are unaffected, the
"model lens" rows used the smaller draws (so their black-hole share is noisy; the forecasts use a separate 400,000-lens draw).
No fit among the 2,120 claimed M > 3 Msun at ≥ 3 sigma for a lens lighter than 3 Msun. Where piE is measured (OS-0016,
OS-0020) or measurable from a bright, long light curve (OS-0021, J072830) a detection gives the mass to 10-20%; for bulge
events with small, unmeasured piE (the catalogued OGLE lenses, OS-0029) DR4 can measure theta_E but not the mass from Gaia
photometry alone (adding OGLE's light curves on the day would help; not done here).

## 5. Release-day stage (`src/oddsky/dr4day/astrometry.py`, stage `astrolens` of `scripts/dr4_day.py`)

After `search`, before `report`: read `data/ranked_targets.csv`, map ids with the `idmap` stage, fetch
`EPOCH_ASTROMETRY` through DataLink (cached per source; a failed chunk is an error with its ids, never "no data"),
normalise (DR4's per-transit arrays or a BH3-like per-CCD table; sky mapper, unused and out-of-window CCDs dropped; TCB ns
since J2010.0 + barycentric correction -> MJD; CCDs averaged per transit with the 0.05 mas floor of the acceptance test),
check the format (every time inside DR4's span ± 5 d; `parallax_factor_al` equal to fE sin(theta) + fN cos(theta) from the
ephemeris to 0.02, trying degrees then radians, which settles the scan angle's unit, zero point and direction; constant
`ra0`/`dec0`; any failure makes the target ineligible, never fitted silently), carry `blended`, `multipeak`, `g_class`,
`gates`, `transit_proc_flags` and `agis_source_excess_noise` into the results, join the run's Gaia epoch photometry
(fetching it for sources the H-0014 epochs stage did not cover) and the cases' ATLAS light curves, fit, write
`astrolens/results.csv`, `status.csv`, `summary.json` and the id map (extended to the controls), copied to
`hunts/H-0015/dr4/` (or `dryrun_dr3/`). The same stage runs the **325 sealed control stars** (`data/controls.csv`, Gaia DR3
stars matched in G and position to the F1 targets, each with a fake event hint; fetched 2026-11-02 by `scripts/s7_controls.py`,
0 errors). Behind the release switch: `Release.has_epoch_astrometry`
(false for DR3, true for DR4) and `retrieval_epoch_astrometry` (overridable with `--set`).

**Dry run on DR3** (`uv run python scripts/dr4_day.py --release dr3 --stages astrolens`, 53 s): "epoch astrometry not
available in dr3 (Gaia DR3 has no EPOCH_ASTROMETRY product)"; the archive's DataLink, asked for the first target, offers no
EPOCH_ASTROMETRY. It then built DR4-format tables (10-element per-CCD arrays with the quality columns) for the top 12 targets
and 4 controls from their real scanning law, read them back through the sanity checks (parallax-factor deviation ≤ 0.003,
degrees detected), joined real DR3 Gaia photometry and ATLAS where they exist, and fitted all 16. The positive control, a
5 mas deflection injected into OS-0020 (G 18.3, piE 0.4: truth 1.5 Msun), came back at theta_E 5.4 mas, Delta chi^2 35,
M_best 1.7 Msun (M < 2.4 at 95%); the 11 target nulls and 4 controls had Delta chi^2 ≤ 6 (`dryrun_dr3/`). The grader refuses
these simulated rows (all five forecasts UNRESOLVABLE on the dry run).

**On the day:** `scripts/dr4_day.py --release dr4` runs it with the rest (~5-10 minutes for 120 targets: 3 anonymous
DataLink requests). Check the probe output first: if DataLink names the product differently, `--set
retrieval_epoch_astrometry=...`; if columns are renamed, add aliases in `astrometry.ALIASES` (column names only, the change
the draft forecast allows; the time unit and zero point and the scan-angle unit as ESA documents them). Then
`uv run python -I hunts/H-0015/predictions/dr4_astrometric_grade.py` (it stops if `hunts/H-0015/dr4/idmap.csv` is missing).

## 6. Forecasts (drafted, NOT sealed): `predictions/dr4_astrometric_forecast.md`

| | statement (graded from DR4's epoch astrometry by the H-0015 stage; rules in section 2) | model | P(TRUE) | resolve by |
|---|---|---|---|---|
| **F1** | of the 109 ranked targets in DR4's span with Gaia DR3 RUWE ≤ 1.4, **between 2 and 6 inclusive** show a significant deflection (Delta chi^2 ≥ 25) | mean 3.5: 3.3 (nominal errors) or 1.6 (1.7x worse) from real lenses, 1.0 spurious | **0.80** | 2027-03-31 |
| **F2** | **OS-0020** (J163539.69-355208.3): DR4 bounds the lens below the black-hole range, **profile 95% mass upper limit finite and < 3 Msun** | P(lens) 0.75; limit < 3 Msun for every simulated 0.3-1 Msun lens (85% with errors 1.7x worse) and every fit without deflection, 6% at 3 Msun, 0 at ≥ 5; P(M > 3 \| lens) 0.018 (discounted) | **0.90** | 2027-03-31 |
| **F3** | **OS-0021** (J173150.73-444549.3, G 15.1, tE 120-490 d), graded only if DR4 bounds piE: the **95% mass upper limit is < 5 Msun** (no significant deflection with M_lo95 ≥ 5) | resolved in 100% of simulations; P(lens) 0.55, P(M ≥ ~4 \| lens) ~0.12 (BH share discounted), limit < 5 Msun for every simulated lens ≤ 3 Msun and every non-lens brightening | **0.93** (conditional on resolution) | 2027-03-31 |
| **F4** | **OS-0016** (J040025.77+323527.4, G 14.0, piE 0.6-1.6) **shows a significant deflection** | P(lens) 0.95 x P(detect \| lens) 0.73 nominal / 0.40 pessimistic | **0.54** | 2027-03-31 |
| **F5** | of the 325 sealed control stars (matched in G and position to the F1 targets, given fake event hints), **fewer than 1.5%** (at most 4) show a significant deflection | false positives per control 1.0% (5-95%: 0.8-1.3%) | **0.75** | 2027-03-31 |

F1 and F5 go together: about 30% of F1's expected count is false positives, so an F1 TRUE means something only if the
controls stay clean (F5). F2 and F3 are near-certain statements whose FALSE would matter: a heavy dark lens, or a precision
far worse than simulated. Probabilities mix the nominal and 1.7x-worse error scenarios (0.5/0.5), use per-target fits with
the final fitter (`data/forecast_fits.csv`, `scripts/s8_forecast_sims.py`), the false-positive model of section 3(d), the
referees' P(lens), and **one black-hole-share calibration: the Galactic model's, halved**. Grader:
`predictions/dr4_astrometric_grade.py` (`--self-test` passes; `tests/test_h0015_grade.py`).

## 7. Honest odds

- **Some deflection is likely.** Our model expects ~3 real deflections among 109 targets with nominal errors and ~1.6 with
  pessimistic ones; P(at least one real deflection) ≈ 0.8-0.95. The most likely are OS-0021 (0.49 = P(lens) x P_det),
  OS-0016 (0.66), OGLE-2017-BLG-0055 (0.39), J072830 (0.22) and OGLE-2017-BLG-0114 (0.21). Each would be a lens mass or
  theta_E nobody has measured: OS-0016's and OS-0021's lenses could be weighed to ~10-15%.
- **A black hole is unlikely but not negligible.** With the Galactic model's lens mass function, black-hole share halved
  (the model makes too few ordinary long events, median tE 14 d against ~20 d observed, so its 21% black-hole share of
  tE > 120 d events is about 2x generous), the expected number of significant deflections by black-hole lenses is 0.25, and
  the expected number of black-hole **mass claims** (a significant deflection with M > 3 Msun at ≥ 3 sigma) is 0.14, i.e.
  P(≥ 1) ≈ 0.13. OS-0021 carries most of it.
- **Our honest number: about 10% (range 5-20%) that DR4 yields a black-hole mass claim from Oddsky's targets.** Beyond the
  calibrated model: P(lens) for most candidates is a referee's judgment; luminous lenses and unresolved neighbours dilute
  deflections more than modelled; DR4's real per-transit errors in crowded fields are unknown (the 1.7x scenario halves
  every detection rate); and **an astrometric binary source can imitate a deflection with a large theta_E** (1.9% of
  binaries under RUWE 1.4 in our simulations, ~1 spurious detection expected in the sample), which would read as a large
  mass. No claim without the referee checks of the forecast's section 2 (NSS orbits, window classes and gates, blended and
  multi-peak transits, per-CCD residuals) and a clean control sample (F5).
- **If a black hole is there, OS-0021 is where.** A dark lens of ≥ 5 Msun in front of OS-0021 would be detected with
  P ≈ 1 and weighed to ~6-10% (simulations with ATLAS's real light curve). Conversely F3 (P 0.93) says DR4 will most likely
  rule it out. Caveat: OS-0021's ATLAS peak "may be partly saturated" and its rise is "mildly chromatic" (case file), and its
  piE rests on that light curve.
- Nothing will be claimed from the stage's output alone: a significant deflection goes to a referee (binarity in DR4's
  NSS tables, neighbours, scan-angle systematics, per-CCD residuals) before it becomes a case claim.

## Files

| | |
|---|---|
| `scripts/s1_targets.py` ... `s8_forecast_sims.py` | target list, DR3 fetch, GOST, acceptance test (+ `--parts recheck`), ranking, figures, control stars, per-target forecast fits (`common.py` shared) |
| `data/` | `targets_input.csv`, `gaia_dr3.csv`, `gaia_dr3_neighbours.csv`, `ob110462_dr3.csv`, `gost_transits.csv.gz`, `ranked_targets.csv`, `rank_fits.csv`, `rank_summary.json`, `controls.csv`, `forecast_fits.csv`, error logs (empty) |
| `acceptance/summary_full.json`, `summary_recheck.json` | acceptance test and the referee re-check (every realisation: `~/oddsky-runs/h0015/acceptance/`) |
| `predictions/` | the draft forecast, its sample, grader (`--self-test`) and `work/forecast.py` |
| `dryrun_dr3/` | the release-day stage's DR3 dry run |
| `src/oddsky/analysis/astrolens.py`, `lenspop.py`, `src/oddsky/dr4day/astrometry.py` | the tool, the Galactic prior, the stage |
