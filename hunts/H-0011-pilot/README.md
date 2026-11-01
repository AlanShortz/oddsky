# H-0011 pilot: vanishing red supergiants (failed-supernova candidates)

Pilot run 2026-10-31 / 11-01. Nothing here is committed or posted. ATLAS tasks were queued, not fetched (see the end).

**Question.** Can Oddsky's archival photometry (NEOWISE 2014-2024 visits, AllWISE 2010, Gaia DR3 mean and epoch
photometry, ATLAS) find or rule out a failed supernova among the luminous red supergiants (RSGs) of the Magellanic
Clouds and the bright Galactic RSGs? A failed supernova is a direct collapse to a black hole: a weak transient, then
the optical vanishes while a fading infrared remnant lingers.

**Answer in one paragraph.** Yes, the data can do it, and for the Clouds they do it well. We have light curves for
598 of the 601 LMC/SMC RSGs with log L/Lsun >= 4.5. Injecting real failed-SN templates into those light curves
recovers an M31-2014-DS1-like event for 100% of stars when the onset falls in 2005-2018.5. An N6946-BH1-like event
is recovered for 98-100% of stars with onsets in 2005.5-2015.5. The false-positive rate is 0.17% (1 star in 598).
The search finds **no failed-SN candidate**. One star has a 0.46 mag secular infrared fade (SP77 54-41). It is not
failed-SN-like and is being checked with ATLAS. WOH G64 is handled correctly: it is not flagged, and its published
NEOWISE behaviour is reproduced. The problem is the number of stars, not sensitivity. The expected number of failed
supernovae in this sample over the window is about 0.002, so a full hunt as specified would almost certainly return
a null that constrains nothing. **Recommendation: no-go on a dedicated full hunt.** Instead keep two zero-cost re-runs
(Gaia DR4 in December 2026, SPHEREx 2025-27). If Oddsky wants real odds, pivot to image differencing of the nearest
star-forming galaxies (plan below).

---

## 1. Literature anchors (what the signal looks like)

| object | progenitor | infrared | optical | source |
|---|---|---|---|---|
| M31-2014-DS1 | log L ~ 5.0, Teff ~ 4500 K, ~13 Msun initial | mid-IR +50% over ~2 yr from 2014 (found in NEOWISE image subtraction), back below the progenitor level ~1 yr after peak, still fading in 2022 | faded >= 100x from 2016 to 2019 and >= 10^4x by 2022/23 | De et al. 2024 (arXiv:2410.14778, *Science* 2026) |
| N6946-BH1 | log L ~ 5.3, 18-25 Msun | IR/NIR faded ~2x in 2015-17, 6-8 yr after the outburst; JWST 2023: 13-25% of the progenitor, very red dust | ~1e6 Lsun outburst in 2009, then >= 5 mag below the progenitor | Gerke+2015, Adams+2017, Basinger+2021, Beasor+2024, Kochanek+2023 (arXiv:2310.01514) |
| failed-SN fraction | f = 0.16 (+0.23 / -0.12), 90% confidence | | | Neustadt+2021 (arXiv:2104.03318) |
| WOH G64 (LMC) | log L 5.45-5.75, RSG to yellow hypergiant | NEOWISE W1 ~ constant (W2 saturated); brightenings in mid-2019, mid-2021 and mid-2023 | V +2 mag, V-I -1.8 within one year, 2013.5-2014.5 | Munoz-Sanchez+2024 (arXiv:2411.19329) |

For a log L ~ 5 RSG this means a W1 rise of ~0.4 mag for 1-3 years, then a fade through the progenitor level to
1-2+ mag below it within ~5-8 years. W1-W2 may redden as the dust cools. The optical drops by many magnitudes within
2-5 years of onset. NEOWISE's ~6-month cadence samples this well. What it cannot see is the part after mid-2024.

## 2. Sample (`scripts/01_sample.py`, `01b_calibrators.py` -> `work/sample_*.csv`)

CDS (VizieR, cdsarc) was down on 2026-10-31. Every VizieR mirror tried also failed: idia.ac.za answered every request
with a 302 back to CDS, and china-vo, iucaa and cfa timed out. The **SIMBAD mirror at simbad.harvard.edu worked**, so
catalogue membership was recovered from SIMBAD's object-to-paper links (`has_ref`, by bibcode):

* **Magellanic Clouds**: Neugent+2012 (LMC YSG/RSG, 1994 objects), Yang+2020 (SMC RSGs, 1243),
  Gonzalez-Fernandez+2015 (both Clouds, 910), Massey & Olsen 2003 (300), Neugent+2020 (31), Davies+2018 (58).
  Union: 3804 objects. Steps applied in order:
  1. Keep stars within 9 deg of the LMC or 5 deg of the SMC.
  2. Keep red stars: J-Ks >= 0.75, or spectral type K3 or later / M. This removes Neugent's YSGs.
  3. Drop foreground stars with parallax > 0.25 mas (1380 objects, mostly from Neugent's foreground list).
  4. Keep log L >= 4.5. L comes from 2MASS Ks with BC_K = 2.69 (Davies+2018), mu = 18.477 (LMC) and 18.977 (SMC).
* **Galaxy**: Messineo & Brown 2019 (K-M class-I stars in Gaia DR2), 934 objects.
* **Calibrators** (21): WOH G64; dusty/OH-IR RSGs (IRAS 05280-6910, 05346-6949, 05402-6956, 05558-7000); luminous
  RSGs (HV 888, HV 5870, HV 12501); TZO candidates (HV 11417, HV 2112); LBVs (S Dor, R71, R110, R127, HD 269582,
  LHA 120-S 61); B[e]/post-RSG stars (IRAS 04530-6916, HD 269953, HD 269723, IRAS 05298-6957).

| sample | stars | NEOWISE light curve (>= 8 visits) | 2010 AllWISE baseline usable | Gaia DR3 match | Gaia DR3 epoch photometry |
|---|---|---|---|---|---|
| LMC, log L >= 4.5 | 378 | 375 | | | |
| SMC, log L >= 4.5 | 223 | 223 | | | |
| **MC total** | **601** | **598** (median 21 visits) | 495 (W1 >= 7.5) | 595 | **432 (72%)** |
| Galactic (MB2019) | 934 | 621 (548 of them at W1 2-5, deeply saturated) | ~0 | 922 | 272 |

log L of the MC sample: 4.50-5.47, median 4.73. Three MC stars have no light curve: HD 269578 and SP77 53-19 lose
their exposures to the `nb == 1` deblending cut, and H88 298 has a poor 1988 position. All three are detected in
NEOWISE at W1 7.5-8.8, so none of them has vanished.

## 3. Data and method

**NEOWISE** (`02_neowise.py`). One bulk IRSA TAP query with an uploaded position list (pyvo), against
`neowiser_p1bs_psd` and `allwise_p3as_mep`:
* 3" cone; the nearest detection per exposure is kept.
* About 0.6 M single exposures for the Clouds. The Clouds sit near the south ecliptic pole, so each visit has
  ~40-180 exposures.
* The same `quality_cuts` and `visits` as `src/oddsky/data/neowise.py`, with one change. Lowercase `cc_flags`
  (h halo, d spike, o ghost, p persistence: contaminated by a neighbour) are tolerated and counted (`cc_frac`).
  Uppercase (likely spurious) still fail. The stock cut removed 99% of exposures for bright stars with bright
  neighbours, including HV 12501 and HV 2112.
* Saturation is kept and marked: `saturated` (W1 < 8), `saturated_pixels` (w1sat > 0.05). 116 of 598 MC stars have
  W1 < 8.

**Gaia DR3** (`03_gaia.py`). From `gaia_source`, `vari_summary` and `vari_long_period_variable`, by source_id. Epoch
photometry comes from `gaia_epoch.fetch_report(releases=("Gaia DR3",))`.

**Two systematics found and corrected.** These are the main technical result of the pilot:

1. **NEOWISE saturation drift** (`figures/drift.png`, `work/saturation_drift.csv`). Saturated stars get brighter in
   NEOWISE profile-fit photometry over 2014-2024. The median late-minus-early W1 change is -0.21, -0.48, -0.38,
   -0.17 and -0.09 mag in the W1 bins 2-3, 3-4, 4-5, 5-6 and 6-7. It is zero fainter than W1 = 7.5. Kendall tau
   follows the same pattern, so a naive search "finds" one-way brightenings in every saturated star. WOH G64's raw
   W1 change of -0.56 mag (W1 ~ 4.5) is this artefact. Every star is now judged against the median and robust scatter
   of stars of its own W1 brightness (MC + Galactic, 1217 stars).
2. **AllWISE (2010) to NEOWISE offset for saturated stars.** NEOWISE reads 0.05 mag brighter at W1 7-7.5, 0.25 mag at
   6-7 and ~0.9 mag below 6. The 2010 baseline is therefore used only for W1 >= 7.5.

Also fixed in passing: 19-digit Gaia ids silently became float64 in two places (the sky1-bug pattern). They are now
carried as strings / Int64 throughout.

**Statistics per star** (`04_search.py`). For W1 and W2:
* early = median of the first 4 NEOWISE visits (2014.0-15.6); late = median of the last 4 (2022.6-24.5);
* drift-corrected change `W1_dc`, and its significance against stars of the same brightness;
* Kendall tau against time (one-way-ness);
* strongest 2-visit brightening and fade after the peak;
* 2010-to-2024 change;
* W1-W2 colour change;
* change over the Gaia era (2014-2017.5).

For Gaia: dG = median of the last quarter of G transits minus the first quarter (2014.6-2017.4), Kendall tau, and
the BP/RP changes. Gaia G is also compared with the 1990s V from SIMBAD against the population's G-V vs V-K relation.

**Flags.**

| flag | meaning | criterion |
|---|---|---|
| A | optical fade, IR holds | Gaia dG >= 0.5 mag, z >= 4, Gaia tau >= 0.4, and W1 flat or rising over 2014-17 |
| B | large one-way IR change | drift-corrected abs(W1 change) >= 0.4 mag and >= 5x the same-brightness scatter, and abs(tau) >= 0.4; or the 2010 baseline at >= 0.5 mag / 5 sigma (W1 >= 7.5 only) |
| C | Gaia-era optical deficit | G-V residual >= 1.5 mag (faded since the V epoch) |
| D | failed-SN shape | W1 rise >= 0.3 mag, then a fade >= 0.8 mag from that peak, ending >= 0.5 mag below 2014-15 |

The tau >= 0.4 requirement in flag A was added after the first pass. Without it, flag A fired on three Gaia
long-period variables caught at different phases: HV 859, HV 2572 and HV 2576 (periods 569, 620 and 257 d;
amplitudes 1.24, 1.09 and 0.55 mag).

**The variability the signal has to beat** (`figures/population.png`). MC RSGs are quiet in the mid-IR: the median
W1 visit-to-visit scatter is 0.027 mag. The 2014-to-2024 W1 change has a robust scatter of 0.020 mag at W1 > 8.5 and
a 1st-99th percentile range of -0.20 to +0.18 mag. A DS1-like event ends 1-4 mag down, 50-200 sigma off this
distribution.

## 4. Sensitivity: what would be caught (`05_sensitivity.py`, `figures/sensitivity.png`)

**Method.** Templates are multiplied, in flux, into each of the 598 MC stars' own NEOWISE light curves, so the star's
real pulsation, noise, saturation and cadence are all included. Onsets t0 run on a 0.5-yr grid from 2005 to 2023.
Visits fainter than W1 = 15 are dropped as non-detections. Each injected curve then goes through exactly the
statistics and flags of step 4.

**IR templates** (flux ratio to the progenitor):
* **DS1**: +50% over 2 yr, then an exponential decline through the progenitor level 1 yr after peak (tau 2.47 yr in
  W1, 3.5 yr in W2).
* **BH1**: x1.3 for 1 yr, flat for 5 yr, then a factor-2 fade (tau 2.9 yr) to a floor of 15%.
* **SHROUD**: IR rises x2 and stays (a dust-enshrouded, merger-like case).
* **SLOW**: a bare 1-mag W1 fade spread over 6 yr.

**Optical templates**, injected into the 432 real Gaia DR3 epoch light curves:
* **DS1-opt**: fade starts at t0+2 yr, 1.5 mag/yr.
* **BH1-opt**: fade starts at t0+1 yr, 2.5 mag/yr.

| template | onsets recovered for >= 90% of RSGs | mean recovery, onsets 2014-2021 | W1 < 8 (saturated) vs not |
|---|---|---|---|
| NEOWISE DS1 | 2005.0-2018.5 (89% at 2019.0, 21% at 2019.5, ~0 after) | 74% | 73% / 74% |
| NEOWISE BH1 | 2005.5-2015.5 (89% at 2016.0) | 35% | 33% / 35% |
| NEOWISE SHROUD (IR rises, stays) | 2016.5-2021.0 | 86% | 60% / 93% |
| NEOWISE SLOW (1 mag over 6 yr) | 2012.0-2020.5 | 97% | 93% / 98% |
| Gaia DR3 DS1-opt | 2010.5-2014.0 (x 72% of stars with epochs) | | |
| Gaia DR3 BH1-opt | 2013.0-2015.0 (x 72%) | | |
| **false positives (un-injected sample)** | **0.17% (1/598)** | | |

**What it means.**
* A DS1-like failed SN is caught in essentially every MC RSG if it began between ~2005 and 2018.5. The effective
  control time is ~14.5 yr per star for DS1 and ~11 yr for BH1.
* Recovery of very early onsets (before 2011) assumes the remnant keeps fading through 2014-24. With a bright
  plateau remnant, the conservative window is about 2011-2018.5 (~8 yr).
* **What is missed:**
  * DS1-like onsets after ~2019.5: NEOWISE ended in mid-2024, before the fade.
  * BH1-like onsets after 2016: that fade starts only 6 yr after onset.
  * A failed SN whose IR stays flat while only the optical vanishes. NEOWISE alone cannot see it, Gaia DR3 sees it
    only for onsets in ~2010-2015, and after 2017 only ATLAS (or Gaia DR4 to 2020) could.
* About 0.5% of the sample (3 stars) has no light curve: 2 are lost to deblending and 1 to its position.
* **Galactic RSGs.** 88% sit at W1 2-5, where the drift is 0.2-0.5 mag and the same-brightness scatter is
  0.13-0.15 mag. The flag-B threshold there is 0.68-0.75 mag. A 1-2 mag fade would still stand out, but saturated
  photometry changes calibration as a star fades, and that effect is not modelled. Galactic sensitivity is
  qualitative only: no injection test was run on that sample.

## 5. Results: candidates

**No failed-SN candidate.** No star passes flag A or flag D. Four stars carry a flag
(`work/flags_mc.csv`, `work/flags_gal.csv`, `figures/candidates_mc.png`, `figures/candidates_gal.png`):

| star | flag | numbers | assessment |
|---|---|---|---|
| **SP77 54-41** (LMC, K5Iab-Ib, log L 4.64, G 12.68) | B | W1 -> +0.46 mag fainter over 2014-24 (13 sigma for its brightness, tau +0.45); W2 +0.53; colour change -0.08; superposed 0.5 mag visit-to-visit swings | Not failed-SN-like: grey, slow, no precursor, only 0.5 mag. It was optically quiet in Gaia (2014-17): G-flux variability proxy 0.017, about half its peers' median of 0.034; no DR3 epoch photometry. It is isolated in Gaia (brightest neighbour within 12" is 5.9 mag fainter; within 6" all are >= 6.9 mag fainter) but has a strong IR excess (W1-W2 = 0.74). So the IR change is most likely circumstellar dust or an IR-only blend (embedded YSO?) in the 6" beam. ATLAS queued. Spitzer SAGE (1.7") would resolve the blend question. |
| [MG73] 94 (LMC, K4Iab) | C | G - V residual +1.82 mag | Artefact: Gaia G steady at 12.86 throughout 2014-17, W1 flat (-0.03 mag), signs of blending (ipd_frac_multi_peak 11%, RUWE 1.49, 100% neighbour-flagged in NEOWISE). The SIMBAD V = 10.64 is an old, probably blended, measurement. ATLAS queued. |
| TYC 5974-2539-1 (Galactic, K3Iab) | B | drift-corrected W1 +0.75 mag (raw +0.37) | Not credible: W1 4.6 (saturated), only 10 usable visits, 69% of exposures deblended (nb > 1), 100% neighbour-contaminated. Mostly drift correction on bad photometry. |
| RS Cen (Galactic, M1Ib-IIe) | C | G - V residual +1.79; Gaia dG +0.70 | Known long-period variable; V and G taken at different phases. Not monotonic (no flag A). |

Also worth noting: IRAS F00486-7308 (SMC, M8II) has the sample's largest monotonic Gaia fade, 3.0 mag (tau 0.81)
over 2014.6-2017.4. It is correctly kept out of flag A by the IR veto: its W1 follows a periodic ~0.5 mag Mira cycle
that fully recovers. ATLAS was queued to confirm.

## 6. WOH G64 and the other calibrators (`figures/calibrators.png`, `work/stats_cal.csv`)

**WOH G64 is not flagged, which is correct, and its published NEOWISE behaviour is reproduced.**
* Raw W1 change 2014-24 is -0.56 mag. At W1 ~ 4.5 that is entirely the saturation drift. Drift-corrected it is
  -0.18 mag (z = -1.3, tau corrected +0.20).
* Our W1 light curve shows the three brightenings of Munoz-Sanchez+2024 at 2019.4, 2021.4 and 2023.4, each of
  ~0.5-0.9 mag.
* Gaia DR3 G changed by only +0.20 mag over 2014.6-2017.4, from a post-transition G ~ 15.1, with no monotonic trend.
* The 2010 AllWISE points are ~1 mag fainter than NEOWISE. That is the saturated-photometry offset (section 3), not a
  change in the star.
* The real event, the RSG-to-YHG transition of 2013.5-2014.5, was an optical change with constant I band and IR. It
  happened before Gaia and at NEOWISE's first visit, so it is invisible to this pipeline by construction, as it would
  be to any IR-led search.

The lesson for the hunt: optical-only changes in dusty RSGs need optical time series, and saturated stars need the
drift correction or they produce false one-way trends.

**The other calibrators show the pipeline catches large slow changes and ignores pulsation:**
* R71 (post-outburst LBV decline): W1 fades 0.99 mag smoothly over 2014-24 (z = 15, tau 0.87). Flagged B.
* R127 (LBV): W1 +1.01 mag. Flagged B and D.
* S Dor (LBV): -0.41 mag brightening. Flagged B.
* HD 269582 and IRAS 05298-6957 (dusty, rise-then-fade): flagged D.
* Normal and dusty RSGs, OH/IR stars and the TZO candidates are not flagged: HV 888, HV 5870, HV 12501, HV 11417,
  HV 2112, IRAS 05280-6910, IRAS 05346-6949, the OH/IR Miras, and the B[e]/YSG stars. HV 11417's -0.58 mag
  late-minus-early comes from Mira phase (tau -0.11) and is correctly rejected.

## 7. Why a full hunt is not worth running: expected yield

**MC sample.** The core-collapse rate in the sample is N_RSG / t_RSG = 600 / (0.5-1 Myr) = (0.6-1.2) x 10^-3 per yr.
* Over the ~8-14 yr window the search is sensitive to, that gives 0.005-0.017 core collapses.
* Multiplied by the failed fraction f = 0.16, that gives **~0.001-0.003 expected failed SNe**.
* Cross-check from star formation: the LMC+SMC CCSN rate is ~0.0025 per yr; ~40% of collapses have log L >= 4.5
  progenitors; times f, over ~10 yr, that is ~0.002.
* The Galactic sample is a similar size, with weaker sensitivity.

So P(at least one event) is ~0.3%. Even if every collapse failed (f = 1), we would expect ~0.01-0.02 events, so a
null result says nothing about f. Sensitivity is not the bottleneck: the data catch a DS1-like event in nearly every
star. The bottleneck is that too few RSGs are monitored.

Extending to log L >= 4.0 (~2000 RSGs plus AGB confusion), or running ATLAS on every star, would cost weeks of
shared-queue time. ATLAS runs ~3 stars/hour per account. It would buy at most a factor of ~3 in yield.

## 8. Go / no-go

**No-go** for a dedicated full H-0011 hunt over Magellanic and Galactic RSGs. For the Clouds this pilot is already
effectively the full hunt: every log L >= 4.5 RSG has been processed, injection-tested and flagged. Its result is a
null with known sensitivity, documented here.

**Keep warm (near-zero cost, pre-registered):**
1. **Gaia DR4 (December 2026).** Epoch photometry for every source over 2014.7-2020.0. `03_gaia.py` already uses
   `gaia_epoch.fetch_report`, which tries DR4 first, so the step is: drop `releases=("Gaia DR3",)` and re-run steps
   3-6. This gives all 595 matched MC stars a 5.5-yr optical baseline (DR3: 2.8 yr for 72%). It closes the
   "IR flat, optical vanishes" gap for onsets in ~2012-2018.
2. **SPHEREx (all-sky 0.75-5 um, 6" pixels, 6-month cadence, 2025-27).** Synthetic 3.4/4.6 um photometry for the
   598 MC RSGs, compared with NEOWISE 2024. This extends the IR baseline past mid-2024 and closes the DS1 late-onset
   gap (2019.5-2022).
3. **Fetch the 3 queued ATLAS tasks** and add the optical 2015-2026 light curves for SP77 54-41, [MG73] 94 and
   IRAS F00486-7308 to section 5. Fetch with `atlas.status(url)`, then `atlas.download(result_url)` and
   `atlas.parse`.

**Conditional go (if Oddsky wants real odds): a volume pivot.** This is "H-0012: mid-IR disappearing and brightening
stars in the nearest star-forming galaxies", the De et al. 2024 method extended beyond M31/M33.
* **Targets:** galaxies within ~4 Mpc with significant star formation: NGC 300, NGC 55, NGC 247, NGC 253, M81, M82,
  IC 342, NGC 4945, Cen A, IC 10, NGC 6822, plus M31/M33 as the control on DS1.
* **Method:** difference imaging of the unWISE / unTimely 6-month coadds (2010-2024) plus SPHEREx (2025-27). Find
  2-epoch-persistent mid-IR brighten/fade sources. Cross-match to Gaia, HST and Spitzer progenitors. Vet with this
  pilot's drift, crowding and pulsation lessons.
* **Reach:** a log L >= 5.2 RSG has W1 ~ 16-16.5 at 3-3.5 Mpc, about the unTimely per-epoch depth, so the
  high-mass end is reachable.
* **Odds:** total SFR is ~20 Msun/yr, dominated by dusty starbursts. That corresponds to ~0.1-0.2 CCSN/yr, so over
  ~14 yr roughly **0.05-0.3 expected failed SNe**: 20-100x this pilot. It would also yield luminous IR transients
  (ILRTs, SPRITEs, obscured SNe) almost guaranteed.
* **Cost:** a new capability for Oddsky (image-level differencing). Prototype it on M31 first, where recovering
  M31-2014-DS1 is the acceptance test.

## 9. Files

* `scripts/01_sample.py`, `01b_calibrators.py`: samples from SIMBAD (Harvard mirror), 2MASS luminosities.
* `scripts/02_neowise.py`: bulk IRSA TAP (NEOWISE-R + AllWISE-MEP), quality cuts, visits.
* `scripts/03_gaia.py`: Gaia DR3 tables and epoch photometry (resumable).
* `scripts/04_search.py`: statistics, saturation-drift calibration, flags.
* `scripts/05_sensitivity.py`: injection-recovery.
* `scripts/06_figures.py`, `plotlib.py`: figures.
* `scripts/07_atlas_submit.py`: queues ATLAS (at most 5).
* `work/`: `sample_*.csv`; `neowise_exp_*.parquet` (raw exposures); `allwise_mep_exp_*.parquet`;
  `neowise_visits_*.parquet`; `gaia_*.csv`; `gaia_epoch_*.parquet`; `stats_*.csv` (every statistic for every star);
  `flags_*.csv`; `saturation_drift.csv`; `sensitivity_ir.csv`; `sensitivity_gaia.csv`; `atlas_tasks.json`; logs.
* `figures/`: `population.png`, `drift.png`, `sensitivity.png`, `calibrators.png`, `candidates_mc.png`,
  `candidates_gal.png`.

Re-run order: `01_sample`, `01b_calibrators`, `02_neowise {mc,gal,cal}`, `03_gaia {mc,gal,cal}`, `04_search`,
`05_sensitivity`, `06_figures`. Steps 2 and 3 are cached and resumable.

**ATLAS tasks queued 2026-11-01 04:32 UTC** (reduced images, MJD >= 57200; not waited on):

| star | task |
|---|---|
| SP77 54-41 | https://fallingstar-data.com/forcedphot/queue/5277887/ |
| [MG73] 94 | https://fallingstar-data.com/forcedphot/queue/5277888/ |
| IRAS F00486-7308 | https://fallingstar-data.com/forcedphot/queue/5277889/ |
