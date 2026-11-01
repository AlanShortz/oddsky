## 1. Verdict

Referee: Claude (adversarial pass), 2026-11-01. Scope: `src/oddsky/imaging/`, `tests/test_imaging.py`, `hunts/H-0012/`
(README, scripts, work/, figures/), the cached data in `~/oddsky-runs/imaging/`, the builder's session transcript
(used as git-free provenance), and the literature to 2026-11. Re-analysis scripts and outputs are in
`hunts/H-0012/reviews/claude-referee-2026-11-01/`. Nothing else was edited.

| # | Claim | Verdict |
|---|---|---|
| 1 | Blind recovery of M31-2014-DS1, light curve matching De et al., #1 of 33 rise-then-fade, #8 by DS1-likeness without dipoles | **Confirmed, with two corrections.** The ranking is robust: DS1 stays #14 overall (#8 without dipoles) and #1 to #3 in its class under 9 of 10 threshold perturbations. But (a) the unWISE bitmask was added *after* the first full run had put DS1 at #26 overall and #2 of 48 in class; the README should say so. (b) Our flux changes are 9% (W1) and 5% (W2) larger than De et al.'s. The W1 slope is about 3.5σ from 1, so this is a real, unexplained flux-scale offset, not agreement "within errors". |
| 2 | DS1's fade continued to 2024 Jul; about 15% of the 2010 W1 flux left | **Not supported as stated.** After the paper's last epoch (2021 Dec), the change to the 2022-24 mean is −0.020 ± 0.042 mJy in W1 (−0.5σ) and −0.056 ± 0.045 mJy in W2 (−1.2σ), with the error set by 150 non-variable control stars of similar flux. The 2021-24 trend is −0.019 ± 0.010 (W1) and −0.022 ± 0.014 (W2) mJy/yr, under 2σ. "15% left" uses our 9%-inflated scale; on De et al.'s scale it is 22% in W1 (the same as their 2021 Dec value) and 27% in W2 (theirs: 34%). The honest version: W1/W2 consistent with a plateau or slow decline after 2021, no significant further fade. Literature: no published WISE photometry after 2021. JWST (2024 Nov) gives one epoch: De et al. 2026 report continued bolometric fading, while Beasor et al. 2026 report flat flux at ≥10 µm. |
| 3 | N6946-BH1 W1/W2 step between 2010 and NEOWISE | **Real astrophysical fade at BH1's position; not instrumental. But not a new result.** Using the same method on 1,392 (W1) and 1,376 (W2) real point sources across the whole window and every flux range, and on 713 positions within 2.5′ of BH1 (bright structured regions included), no source or position reaches −5σ. The minimum is −4.0σ, against BH1's −9.3σ and −7.0σ. There is no flux-proportional step: median (NEOWISE − 2010)/flux is ≤ +1.3% and positive, the wrong sign. The step survives a NEOWISE-only reference, a 2010-only reference, a 2010-epoch PSF, a 7×7 kernel and no mesh background (W1 −32 to −35 µJy, W2 −45 to −54 µJy). The known 1.8-2.5% brightness of the first WISE pass shows up in the kernel normalization (W1 +1.4%, W2 +3.5% for the 2010 Jun epoch) and is absorbed by it. The amplitude and timing match the published Spitzer IRAC fade (Adams et al. 2017; Basinger et al. 2021) and JWST's 1.3-1.8 µJy at 3.6 µm in 2023. **The mid-IR fade of BH1 is already published (Spitzer, 2011-2018). What is new is an unpublished WISE light curve that anchors the flux in 2010 and shows it flat from about 2016 to 2024.** |
| 4 | M31 leads 11.0014 +42.3396 and 9.3360 +40.2771 | **Neither is a failed-SN candidate, and neither is an artefact.** 9.3360 +40.2771 is a *published* M31 luminous blue variable (LGGS J003720.65+401637.7; Huang et al. 2019, ApJ 884, L7), and its mid-IR fade parallels a fade of about 1 mag in the optical, Pan-STARRS to Gaia. 11.0014 +42.3396 lies beyond D25, has W1−W2 = 0.90 (AGN colours) and a very red, extended Pan-STARRS counterpart (r = 20.6, i_PSF − i_Kron = 0.53): most likely a background (dusty/fading) AGN. Of the other leads, 10.5671 +40.3267 is the known background Seyfert 1 IV Zw 29 (z = 0.10); 10.8769 +41.7422 is unidentified (inner disk, W1−W2 = 1.31, no Gaia/SIMBAD). §5. |
| 5 | Tool quality | Tests pass (16/16, 1.8 s). No bug invalidates the acceptance results. Real weaknesses: self-inclusion of the epoch in its own median reference; the season label is per-tile relative timing; the classifier mixes bands (min η and min turns taken independently); sensitivity is per-epoch only, injected after subtraction, and plateaus at 85-96% completeness in M31, not 100%; the candidate gate (≥ 2 epochs × both seasons at 5σ) cannot find a BH1-like slow fader, although a stacked NEOWISE − 2010 channel would. Details in §6. |
| 6 | Data source | **Caveat confirmed and widened.** The time-resolved images have no official release, licence or README; the official unWISE, IRSA, AWS and Legacy Survey trees hold only full-depth coadds and the unTimely catalogue, which ends 2020 Dec. The 25 "neo11" epochs are a concatenation of at least eight unWISE code builds made between 2017 and 2025. Neither the BH1 step nor the DS1 2021-24 comparison crosses a build boundary. The only official route for the scale-up is to rebuild epochs from the IRSA L1b frames with `unwise-coadds --epoch`. §7. |

Required corrections are collected in §8.

## 2. Claim 1: DS1 acceptance and honesty of the ranking

### 2.1 Was the score tuned after seeing DS1? (git-free evidence)

There is no git history for the new files, so I reconstructed the order of events from the builder's session
transcript (`~/.claude/projects/…/subagents/agent-a2c6066f1351821a8.jsonl`) and file mtimes. Note that the US DST
change at 02:00 EDT makes local `ls` times ambiguous. All times below are UTC.

| UTC | Event |
|---|---|
| 05:15 | Builder reads De et al. (2410.14778), including the DS1 light-curve description |
| 05:28:57 | `metrics.py` written. `classify()` thresholds already final: η < 1.2, turns ≤ 3, rise > 5 & fade > 3, score penalty `turns − 2` |
| 05:33 | Turn threshold changed to max(3σ, 15% of amplitude); season alignment added. Before any real-data run; tested on synthetic data only |
| 05:34-05:36 | **Development run on tile 0118p408, the tile containing DS1.** Builder prints the top 25 by ds1_score; DS1 is #3 in that tile, rise-then-fade |
| 05:40 | `burst_frac` / "transient" class added (moves short bursts out of the one-way classes) |
| 05:47 | `delta_neo` statistic added, right after looking at BH1's forced light curve (disclosed in the README) |
| 06:02:52 | First full M31 acceptance run: **DS1 rank #26 overall, #2 of 48 rise-then-fade** |
| 06:04:32 | unWISE bitmask masking added (`fetch.ARTIFACT_BITS`, `Config.unwise_mask`); M31 re-run |
| 06:16 | Acceptance again: **#14 overall, #1 of 33 rise-then-fade** (the README numbers) |

Assessment:

- The class thresholds and score formula predate any real data. They were, however, designed by someone who had just
  read DS1's light-curve description, so "DS1-likeness" is DS1-shaped by construction. That is legitimate for an
  acceptance test, but the test shows the pipeline *can recover a known morphology*. It does not measure blind
  discovery efficiency for other kinds of event.
- Two changes came after DS1 had been seen in real data: the burst class and the bitmask. Both are generic,
  physically motivated artefact and class fixes, and neither touches DS1's own metrics. The bitmask is the one that
  moved DS1 from #26 to #14 and from #2 of 48 to #1 of 33. The README says the mask "was added after the first full
  run" because saturated-star artefacts topped the list, but it does not give DS1's rank before the change.
  **Correction: state the pre-mask ranks (#26; #2 of 48).**
- The development run used DS1's own tile. This should be disclosed too. The README's "DS1's position is used only
  in the acceptance script" is true of the code but not of the development process.

### 2.2 Robustness of the rank (`ds1_checks.py`)

All 16,145 candidates were re-classified from `lightcurves.parquet` under perturbed thresholds:

| variant | DS1 rank (all) | rank (no dipoles) | rank in class / class size |
|---|---|---|---|
| baseline (reproduces README) | 14 | 8 | 1 / 33 |
| η cut 1.0 / 1.5 | 14 / 14 | 8 / 8 | 1/25, 1/61 |
| rise > 3 & fade > 3 | 14 | 8 | 3 / 78 |
| rise > 5 & fade > 5 | 14 | 8 | 1 / 23 |
| penalise every turn (`/(1+turns)`) | 35 | 13 | 1 / 33 |
| no burst class | 14 | 8 | 2 / 36 |
| no smoothness factor | 15 | 9 | 1 / 33 |
| turn threshold 3σ only | 14 | 8 | 1 / 32 |
| plain "most negative W2 late − 2010 significance" (no DS1-shaped design) | 10 | 8 | — |

The ranking is honest and not knife-edge. DS1 is a top-10 to top-35 object under any reasonable scoring, including
a scoring with no morphology at all. All README counts checked out: 4,532 with var_sig > 5; 6 dipoles among the
13 above DS1; 53 in the top 100; 90 in total.

### 2.3 Does the light curve really match the paper?

The comparison file is De et al.'s own `photometry.csv` (GitHub/Zenodo). This is Table S1 of v1; v2 of the paper
(Science 2026) moved the data to Fig. S1. It holds **total** NEOWISE fluxes at 20 epochs per band, 2010-01-15 to
2021-12-28. The paper has no difference-flux table and reports no data from 2022. `compare_published()` correctly
re-zeroes it on the three 2010-11 epochs (W1 0.993, W2 1.006 mJy).

- **Confirmed:** r = 0.994 / 0.999, the peak at the same epoch (2017-01-05; the README's "2016 Dec" is MJD 57758),
  and the same 2021 Dec level (ours −0.80 vs theirs −0.77 mJy in W1).
- **Caveat 1:** the W1 slope of 1.087 is about 3.5σ from unity (slope error about 0.025 for 20 points with σ = 0.05
  over a 1.3 mJy range), and our W1 peak is 24% above theirs (+0.64 vs +0.52 mJy). Our PSF fluxes are on a
  different scale from De et al.'s ZOGY fluxes. Possible causes include PSF normalization within 9 px, the reference
  choice, or the aperture correction. This matters for every flux and luminosity quoted (DS1's "1.1×10⁴ L☉ peak
  change" uses our +0.64 mJy; De's +0.52 gives 8.6×10³ L☉). **Correction: calibrate forced PSF fluxes of isolated
  stars against the unWISE/unTimely catalogue fluxes, and quote the 9% offset until that is done.**
- **Caveat 2:** χ²ᵣ = 1.3 / 0.8 "on our errors" is a weak test, because our per-epoch errors are about 5× theirs.

## 3. Claim 2: did DS1 keep fading after 2021?

`ds1_checks.py` re-measures DS1 and 150 non-variable reference stars within 13.75′ in the same tile, with W1
reference flux within ×3 of DS1's, at least 8″ from any candidate with var_sig > 3, and photometered identically.

| | W1 | W2 |
|---|---|---|
| DS1, (mean of 2022 Jul-2024 Jul) − (2021 Dec), zero-point corrected | −0.020 mJy | −0.056 mJy |
| null σ of that statistic (control stars) | 0.042 | 0.045 |
| significance | **−0.5σ** | **−1.2σ** |
| linear trend 2021 Dec-2024 Jul | −0.019 ± 0.010 mJy/yr | −0.022 ± 0.014 mJy/yr |
| per-epoch zero points from the controls | ≤ 0.017 mJy (worst epoch) | ≤ 0.021 mJy (2024 Jul) |
| fraction of the 2010 flux left in 2024 Jul, our scale (README) | 0.15 | 0.24 |
| same, on De et al.'s scale (÷ 1.087 / 1.047) | **0.22** | **0.27** |
| De et al., 2021 Dec | 0.22 | 0.34 |

- Epoch systematics are small (the controls' zero points are at the 0.01-0.02 mJy level), so this is not a
  systematics problem. The post-2021 signal is simply small compared with the noise.
- W1 is flat since 2021 Dec.
- W2 suggests a further decline of about 6% of the 2010 flux at about 1.2-1.6σ.
- **Correction:** replace "DS1 kept fading after 2021 … about 15% of its 2010 W1 flux and 23% of its W2 flux
  remain" with: "In 2022-24 the W1 flux is consistent with the 2021 level (22% of the 2010 flux on De et al.'s
  scale); W2 is marginally lower (27% vs 34%, 1.2σ). The WISE data neither require nor exclude a slow continued
  decline."

**Literature, checked to 2026-11:**

- No paper publishes WISE/NEOWISE photometry of DS1 after 2021-12, or any unTimely light curve.
- The only later infrared epoch is JWST (DDT 6809, PI De; 2024-11-28: NIRSpec 1-5 µm, MIRI LRS and imaging).
  - De et al. 2026 (arXiv 2601.05774, ApJL): log L ≈ 3.88 L☉, about 7-8% of the progenitor, τ ≳ 50. The source
    "continues to fade in luminosity".
  - Beasor et al. 2026 (arXiv 2601.05317, MNRAS 546): the near-IR has faded about 50× since 2022, but the flux at
    ≥ 10 µm "has remained constant" since 2012. They favour a merger or LRN-like origin.
- The NIRSpec G395H spectrum covers W1 and W2. Synthetic W1/W2 photometry from it is a direct check of the 2024
  NEOWISE values. **Recommended** before anything about DS1's late behaviour is written up.
- The WISE plateau is mildly interesting in the context of that dispute, but it is a 1σ statement, not a result.

## 4. Claim 3: the N6946-BH1 step

### 4.1 What the brief asked, and what was run (`bh1_step_test.py`, `bh1_controls_summary.py`, `bh1_step_test.png`)

The NGC 6946 window (tile 3090p605, 425 × 438 px, 24 epochs) was re-differenced in memory with the pipeline's own
functions. The 2010→NEOWISE statistic (`delta_neo`) and the pre-defined late-vs-2010 statistic (`delta_late`) were
then measured exactly as `acceptance.py` does.

**(a) Real point sources, not empty sky.** These are all reference-image local maxima in the window: in the disk,
in the outskirts, and over every flux range. A calibration step that scales with source flux would appear as a
trend of `delta_neo` with flux, and as a population of significant negative steps among sources as bright as BH1
was in 2010 (about 130 nmgy W1).

| W1 reference flux (nmgy) | n | median Δ (µJy) | median Δ/flux | median σ | robust std | min σ |
|---|---|---|---|---|---|---|
| < 10 | 75 | −0.4 | — | −0.10 | 1.06 | −3.6 |
| 10-30 | 32 | +0.3 | +4% | +0.08 | 1.28 | −2.3 |
| 30-100 | 176 | +0.4 | +1.5% | +0.09 | 1.34 | −3.1 |
| 100-300 | 303 | +0.6 | +1.0% | +0.16 | 1.09 | −2.8 |
| 300-1000 | 381 | +2.2 | +1.3% | +0.49 | 1.29 | −3.2 |
| 1000-3000 | 238 | +2.7 | +0.5% | +0.32 | 0.88 | −2.3 |
| > 3000 | 187 | +0.6 | +0.06% | +0.03 | 0.66 | −3.4 |
| **all 1,392** | | | | +0.20 | 1.04 | **−3.6** (none < −5) |
| **BH1** | | **−34.9** | | **−9.3** | | |

- W2: 1,376 sources, robust std 1.02, minimum −3.9σ, none below −5. Median Δ/flux is between −1.9% and +0.5% across
  bins. BH1 is at −7.0σ.
- Bright stars show at most a 0.0-1.3% residual scale offset, and in W1 it has the wrong sign (brightening).
- For a flux-proportional calibration error to turn BH1's 2010 flux into a −35 µJy step, it would have to be about
  85% of the flux.

**(b) Resolved bright regions near BH1.** 713 positions on a 3-px grid within 2.5′ of BH1 were sorted by the local
high-pass (compact-structure) brightness of the reference.

- Overall: robust std 0.88 (W1) and 1.06 (W2); minimum −4.0 and −3.3; none below −5.
- In the top 3% brightest structure: median −0.33σ (W1) and −1.0σ (W2), minimum −1.5 and −3.2.
- BH1 itself sits on smooth disk light (reference 71 nmgy/px against a sky of 17; high-pass ≈ 0), not on a
  compact bright region.

**(c) Reference, PSF and kernel choices** (BH1's statistics under each variant):

| variant | W1 Δneo (µJy, σ) | W2 Δneo (µJy, σ) | W1 Δlate (σ) |
|---|---|---|---|
| pipeline | −34.9, −9.3 | −53.2, −7.0 | −6.4 |
| NEOWISE-only reference | −34.8, −8.6 | −54.1, −6.3 | −6.2 |
| 2010-11-only reference (De et al.'s choice) | −32.4, −13.1 | −45.3, −9.4 | −5.8 |
| PSF built from the 2010 epoch | −34.1, −9.7 | −50.9, −7.1 | −6.7 |
| 7×7 kernel | −35.0, −9.4 | −53.0, −7.0 | −6.5 |
| no mesh background | −34.7, −8.5 | −52.9, −6.4 | −6.0 |

The step does not depend on the reference season, the PSF season or the kernel.

**(d) Known 2010-vs-NEOWISE calibration offsets.**

- unTimely (Meisner et al. 2023, §V): in COSMOS, bright stars are about 1.8% (W1) and 2.5% (W2) brighter during
  the *first* WISE pass than in all later passes, which agree to ≲ 1%.
- AllWISE: 4-band cryo W1 was 0.011 mag too bright; post-cryo zero points drifted with temperature.
- NEOWISE-R: W2 drifts ≤ 0.03 mag, about 0.06 mag in the final months of 2024.
- The pipeline's fitted kernel normalizations for the two 2010 epochs show the same effect: W1 1.014 and 0.989,
  W2 1.035 and 0.984 (NEOWISE median 1.001). The first pass (2010 Jun) reads 1.4% / 3.5% bright. Because the kernel
  is fitted freely per epoch (512-px blocks; here one block covers the whole galaxy), this global offset is
  absorbed. Part (a) shows that no flux-dependent residual survives.

**(e) The pre-defined statistic.**

- `delta_late` (2010-11 vs the last three epochs) was in `metrics.py` before any data were seen.
- At BH1 it gives −6.4σ in W1 and −2.7σ in W2.
- Against the real-source null (robust std 1.14; 0 of 1,392 below −5 in W1, 1 of 1,376 in W2), that is about
  −5.6σ in W1 alone.
- The post-hoc `delta_neo` choice inflates the headline from about 6σ to 9σ, but does not create the signal.
- The look-elsewhere factor is about 4 (2 statistics × 2 bands); the position was fixed a priori.

### 4.2 Literature and consistency

No published WISE/NEOWISE/unWISE light curve of BH1 exists. I checked Adams et al. 2017 (arXiv 1609.01283),
Basinger et al. 2021, Neustadt et al. 2021, Beasor et al. 2024, Kochanek et al. 2024, and Forés-Toribio &
Kochanek 2026 (arXiv 2604.05019); De et al. 2026 note that "the MIR coverage of NGC 6946-BH1 is sparse". The fade
itself is published, from Spitzer:

| | 3.6 µm | 4.5 µm | WISE (this pipeline, change since 2010) |
|---|---|---|---|
| 2011.6 | 46 µJy | 52 µJy | — (gap) |
| 2012.2 | 28 | 38 | — |
| 2014.2-2014.8 | 19 | 23-27 | W1 −22 / −34; W2 −27 / −54 |
| 2016.1 | 10 (Basinger: 12) | 19 | W1 −25 to −39; W2 −32 to −60 |
| 2018.7 | — | 11 | W1 −24 to −49; W2 −40 to −68 |
| 2023 (JWST) | 1.3-1.8 (F360M) | — | flat |

- The IRAC fluxes are 2.4″-aperture fluxes that include blends; JWST shows BH1 itself is only 1.3-1.8 µJy at
  3.6 µm.
- If BH1 contributed about 38 µJy of the 46 µJy at 3.6 µm in 2011.6, then WISE's 2010 → late drop of 35-39 µJy
  (W1) is what you would expect, and W2's 36-53 µJy matches 4.5 µm's ≥ 41 µJy decline from 2011.6 to 2018.7.
- The WISE curve adds two things not in the literature: the flux level in 2010 (Spitzer has no 2009-2010 epoch),
  and a flat W1/W2 curve from about 2016 to 2024.
- JWST MIRI and Forés-Toribio & Kochanek identify the mid-IR source with BH1; the four near-IR neighbours within
  0.1″ are unrelated red giants. WISE's 0.4″ ± 0.4″ localization (with about 0.5″ systematic, from DS1) is
  consistent with this but cannot establish it alone.

**Verdict on claim 3: real astrophysical fade, measured at BH1's position and consistent in amplitude and timing
with the published Spitzer decline. Not instrumental. Not novel as a "fade". It is novel only as a WISE
measurement with a 2010 anchor.**

**README corrections:**

- Delete "So the step is not a noise or WISE-versus-NEOWISE calibration artefact of the method", which was asserted
  from empty-sky nulls that cannot test it. Replace it with the source-based control above, and report the
  existing `null_on_sources` result (17 sources), which the README omits.
- Replace "not yet checked against the literature" with the Spitzer/JWST comparison.
- "WISE measures the decline of BH1's mid-IR remnant" should become "WISE independently confirms the Spitzer-era
  decline and shows it had levelled off by about 2016".

## 5. Claim 4: the M31 leads

**Sources checked:**

- SIMBAD, through the Harvard mirror because CDS timed out.
- Gaia DR3: direct TAP queries plus the ARI mirror.
- VizieR (LGGS J/AJ/131/2478, Massey 2016 J/AJ/152/62, Milliquas v8 VII/294) and Pan-STARRS DR2.
- The pipeline's own reference fluxes and masks.

**Artefact checks.** All four leads are compact peaks in the reference, 160-290 px from the window edges, outside
the detection mask (7-64 px from the nearest masked pixel), and carry only unWISE bit 10 ("big object: M31").
Their light curves are coherent in both bands and both seasons. None is an artefact.

| lead | what it is | evidence |
|---|---|---|
| **9.3360 +40.2771** (`transient`, #1 by ds1_score) | **Known LBV in M31** (LGGS J003720.65+401637.7 = 2MASS J00372064+4016376; Huang et al. 2019, ApJ 884, L7, "A new luminous blue variable in the outskirts of the Andromeda galaxy"; also Liu et al. 2022; 2025ApJ...981..176L) | Gaia DR3 380754490083950080, 0.15″: G = 16.63, BP−RP = 0.15, VARIABLE; parallax −0.12 ± 0.06; PM (0.21 ± 0.05, 0.00 ± 0.05) mas/yr. The 4σ pmRA is below the pipeline's foreground cut and inconsistent with a nearby star given the negative parallax. Gaia DSC says star (P = 1.0); its variability classifier gives BE/GCAS/SDOR/WR; GSP-Phot Teff ≈ 19,500 K. LGGS V = 15.85 (pre-2005), Pan-STARRS r = 15.58, Gaia 2014-17 G = 16.63, so it faded by about 1 mag in the optical as the mid-IR fell by 84%. This is S Dor-type variability of a known LBV, not a vanishing star. Reference W1−W2 = 0.19. |
| **11.0014 +42.3396** (`fading`, #3) | **Probably a background AGN / dusty galaxy** | Elliptical radius 1.12 R25, beyond the disk, 28′ off the major axis. W1−W2 (reference) = 0.90 Vega, above the Stern et al. 2012 AGN cut of 0.8. The fade is smooth (η = 0.08, no turns): 55-62% of the 2010 flux gone over 14 years, the shape of an AGN dust-echo or changing-look decline. No SIMBAD, LGGS, Massey or Milliquas entry. The Pan-STARRS counterpart (0.36″) is very red and extended: g 21.35, r 20.63, i 19.94, z 19.41, y 18.59; i_PSF − i_Kron = 0.53. The only Gaia source within 5″ is a quiet foreground dwarf 3.6″ away (G = 18.0, PM 1.4 mas/yr), not the variable. **Next step:** NED and a spectrum. At M31's distance its W1 = 14.6 would mean M_W1 ≈ −9.8 with no optical star (r ≈ 20.6, extended), which argues against an M31 star. |
| 10.5671 +40.3267 (`brightening`, #2) | Known background Seyfert 1 **IV Zw 29 = 2E 141 = 1ES 0039+40.0**, z = 0.10 | SIMBAD (47 refs) and Milliquas. Gaia DR3 369120145234465024: DSC P(quasar) = 1.0, in the Gaia celestial reference frame, AGN variability class. Once mis-catalogued as an M31 globular cluster. |
| 10.8769 +41.7422 (`transient`, #6) | Unidentified; a dusty M31 AGB star or red supergiant is favoured | Inner disk (0.46 R25). Nothing in PHAT or Massey 2016 within 5″. The nearest Pan-STARRS objects are 2.6-4.6″ away and seen only in i/z (about 21.9/20.9). HST/MAST, NED and Spitzer catalogues were not checked for any lead. Mid-IR bright in 2010-11 and down by 2014, then flat. W1−W2 = 1.31. No SIMBAD, Gaia or Milliquas source. Remains the only open M31 lead of the four. It needs the PHAT/HST and Spitzer (Khan et al. 2017) check, and a search for an M31 optical transient around 2009-2010 (novae, LRN/ILRT lists). |

**Process lessons:**

- Two of the top three non-dipole "one-way" sources are a catalogued LBV and a catalogued Seyfert, and the third is
  probably an AGN. The triage in the scale-up plan (SIMBAD, Milliquas, Gaia DSC, W1−W2 colour) must run *before*
  anything is called a lead.
- `gaia_flags.py` already pulls the Gaia source. Adding `classprob_dsc_combmod_quasar` and an AGN colour flag
  (W1−W2 > 0.8 with the source outside D25) would have removed L3 and flagged L1 automatically.
- `gaia_M31.csv` stores `gaia_id` as a float (3.807544900839501e+17), which corrupts the source ID. Write it as
  int64 or a string.

## 6. Tool quality

**Tests:** `uv run pytest tests/test_imaging.py` gives 16 passed in 1.8 s. They are synthetic only: no 2010-vs-NEOWISE
PSF or zero-point change, no multi-tile grouping, no bitmask handling, and no check of the noise model under
crowding.

**Code review.** No bug invalidates the acceptance results. Findings in order of consequence:

1. **No blind channel for slow, faint, one-way changes.** A candidate needs at least two 5σ single-epoch detections
   in both seasons. BH1 (about 4σ per epoch) and anything like it at 5-10 Mpc can never enter the list. Yet the
   NEOWISE-minus-2010 stack in `localize.py` reaches −6.3σ at BH1. **Recommend** a third detection channel for the
   scale-up: run matched-filter detection on the reference-free (NEOWISE mean − 2010 mean) and (last 3 − 2010)
   stacks per season. This is the statistic the sensitivity section relies on ("6-7 Mpc by averaging"), but the
   search never uses it.
2. **Sensitivity is per epoch, injected after subtraction, and not at candidate level** (`sensitivity.py`).
   - Sources are added to the *difference* image, so the kernel fit, which could partly absorb a change on a bright
     star, is never tested.
   - Completeness plateaus well below 1 in M31: W1 85% at 2.5× the 5σ flux and 96% at 4×; NGC 6946 86% and 94%.
     That is blending, masking and the 1.5-px match. The README quotes only the 50% point ("0.07-0.11 mag brighter
     than the limit").
   - Depth varies by up to 0.8 mag between epochs (NGC 6946 W2: 15.7-16.5); only 4 epochs were used.
   - **Correction:** quote the completeness plateau and the per-epoch range. State that the candidate-level
     completeness (≥ 2 epochs, both seasons) is unmeasured. Inject into the raw epoch images before subtraction.
3. **The epoch is part of its own reference.** `diff.references` takes the median over all of a season's epochs,
   including the one being subtracted. With about 12 epochs this biases large single-epoch excursions low by a few
   percent and correlates the residual noise. The empirical rescaling absorbs most of it (empty-sky null σ =
   1.04-1.09). For transients, a leave-one-out median is cleaner and cheap.
4. **Correlated reference errors are treated as independent.** All epochs of a season share one reference, but
   `band_metrics` computes `delta_late_sig`, `delta_neo_sig`, χ² and η as if errors were independent. Within a season
   the reference noise cancels in Δ statistics, so the quoted σ is conservative there. It is not conservative for
   χ² or `var_sig`. The empirical nulls cover it for BH1; document it.
5. **The classifier mixes bands.** `classify` takes min η and min turns independently across W1 and W2, but the
   variability gate uses the band with the larger χ². A source can therefore pass the smooth/few-turns cut on the
   noisy band while the good band is LPV-like. It is harmless for DS1 (both bands smooth). Use the metrics of the
   band that passed the gate, or require both bands.
6. **Season labels are per-tile relative timing.** `stack.seasons` labels by `round((mjd − min)/182.6) % 2`. For M31
   all five tiles agree (checked), but nothing guarantees a common labelling across tiles in other fields, and
   `candidates_from` counts "both seasons" across tiles. A wrong label lets one-season artefacts pass. Label by
   calendar half-year of the scan (or the header scan direction).
7. **Noise floor.** `local_scatter(floor=0.5)` can deflate errors by up to 2×. In practice 47-69% of pixels have a
   factor below 1 (1st percentile 0.75-0.87), so no pixel is near the floor. A factor below 1 means the nominal
   errors (with the 3% residual floor) are overestimated, which is safe. But a floor at 0.5 rather than about 0.8
   is a latent risk in sparse fields.
8. **Flux scale:** see §2.3. There are 9% / 5% offsets against De et al., and no calibration against a catalogue.
9. **Moving-star flag.** `dipole_flags` needs both ends to be candidates with |Δlate| > 5σ within 10″. A
   high-proper-motion star with one end masked or below threshold is missed. Run the Gaia DR3 proper-motion
   cross-match (as `gaia_flags.py` does for the top) on every one-way candidate in the scale-up.
10. **Minor:**
    - `vanish_frac` labels are on our flux scale.
    - Hard-coded MJD boundaries (55700, 56600) are correct for the WISE/NEOWISE-R gap.
    - `list_epochs` caches forever.
    - `photometer` silently drops candidates within 13 px of a window edge; they keep NaN classes in
      `candidates.csv`. The README's denominators differ: 4,532 have var_sig > 5, but "#1 of 33" counts all 16,145
      candidates.

**Masking:**

- `fetch.ARTIFACT_BITS` excludes bits 6, 9 and 10. I checked this against Meisner et al. 2019, Table 2: 6 is
  "center of pixel not primary", 9 "resolved galaxy", 10 "big object (LMC, SMC, M31)". That choice is correct.
  Bits 21-22 ("may contain bright star centroid") are masked, which is conservative.
- The 2-px dilation is fine.

**PSF per season:**

- Empirical PSFs come from about 300 stars (M31) and about 40 (NGC 6946) per tile, band and season, with FWHM
  2.75-2.99 px.
- Building the PSF from the 2010 epoch instead of the median reference changes BH1 by under 1 µJy (§4.1c), so the
  per-season median PSF is adequate for the 2010 epochs.
- PSF normalization within r ≤ 9 px drops the far wings, which is consistent across epochs and cancels in
  differences, but it affects the absolute scale (§2.3).

## 7. Data source and provenance

**What the source is.** `https://portal.nersc.gov/project/cosmo/temp/ameisner/neo11/` sits in A. Meisner's
personal web area inside the NERSC "cosmo" project space, alongside about 1,500 unrelated personal files.

- It holds `e000`…`e426`, `tr_neo11_index.fits` (892,803 tile-band-epoch rows) and `time_resolved_neo11-atlas.fits`.
- There is no README and no licence for the coadds.
- "temp" is the owner's naming, not a NERSC purge area. NERSC gives no purge policy for project web space, but it
  also says the portal "is not a web hosting service", so there is no permanence guarantee.

**No official equivalent exists.**

- The official tree `portal.nersc.gov/project/cosmo/data/unwise/neoN/unwise-coadds/` has only `fulldepth/` for every
  build (neo1-neo9, neo11; there is no neo10).
- IRSA serves unWISE full-depth images (neo3) and the unTimely *catalogue* (neo7, 2010-2020 Dec), but no
  time-resolved images. The AWS Open Data bucket `s3://nasa-irsa-wise/unwise/` likewise holds only unTimely
  Parquet.
- The Legacy Survey viewer's unWISE layers are full-depth only.
- WiseView serves neo11-era epoch data (24 epochs to 2024-07) only as PNG cutouts from a private AMNH bucket.
- The 2018 release (`unwise.me/tr_neo2`) and the neo4 time-resolved release (`neo4-coadds.github.io`) are dead links.
- unTimely has not been extended past 2020 Dec.

**Licensing:**

- unwise.me asks for citations (Lang 2014; Meisner et al. 2016, 2017, 2018/2023) and states no data licence.
- IRSA-hosted products are public with an acknowledgement request.
- No terms are stated for the temp directory. Using the files is very likely fine scientifically, since De et al.
  used the same products. But a 400 GB automated pull from a personal directory needs the owner's permission
  (the README already says "ask Meisner first"; make it a hard gate), and any publication must cite the unWISE
  papers and say where the epoch coadds came from.

**A new provenance caveat that matters for the science.** The 25 "neo11" epochs are not one uniform build. FITS
headers (`UNW_VER`, `UNW_DATE`) show at least eight code versions:

| epochs | build | built |
|---|---|---|
| e000-e004 | v3.5-15 | 2017-01 |
| e005-e006 | v3.5-20 | 2017-11 |
| e007-e009/e010 | v3.5-22 | 2018-05 |
| e010/e011-e012 | v3.5-28 | 2019-08/09 |
| e012 or e013 | neo6 / neo7 | 2020-04 / 2021-06 |
| e015-e016 | neo8 | 2022-05 |
| e017-e018 | neo9 | 2023-05 |
| e019-e024 | neo9-5 | 2024-12 to 2025-01 |

The same pattern holds in tiles 3090p605 and 0118p408. Epoch-to-epoch zero points and PSFs can therefore jump at
build boundaries. unTimely already documents a 1.8% (W1) and 2.5% (W2) brighter first WISE pass. The pipeline's
free kernel normalization absorbs global jumps, and control stars show the residual zero points are ≤ 0.02 mJy.

For the two claims:

- BH1's step happens between e001 and e002-e004, which are all built with the same 2017 code. It cannot be a build
  boundary.
- DS1's 2021-2024 comparison (e019-e024) is also within a single build.

**For the scale-up:** record `UNW_VER` per epoch in `meta.json`, and add a per-build zero-point check on control
stars to the pipeline output.

**Can official products replace it?**

- *unTimely catalogue (IRSA/AWS, neo7):* it ends in 2020 Dec, and its crowdsource photometry is unreliable in
  crowded galaxy disks. It is a useful cross-check for isolated sources, but cannot replace difference imaging, and
  misses 2021-2024.
- *IRSA L1b frames + `unwise-coadds`:*
  - The code is GPL-2.0, maintained (last commit 2025-06), and has `--epoch` / `--before` / `--after` switches that
    write `EPOCH`. The L1b frames are public on `s3://nasa-irsa-wise/wise/{allsky,cryo-3band,postcryo,neowiser}/`.
  - This is the only fully official, reproducible route, and the right long-term fallback. It would also give a
    *uniform* build (removing the version heterogeneity above) and sub-epoch cadence.
  - Cost: it needs the astrometry.net package, the L1b frame indexes and zero-point lookups, and about 100× more
    input than the epoch coadds. It is a real engineering task (days, not hours), but for about 400 tiles it is
    feasible on cloud batch with input next to the S3 bucket (us-east-1).
  - Recommendation: request permission and a stable mirror from Meisner (or ask IRSA whether the neo11 epoch
    coadds can be hosted), and in parallel prototype the L1b route on one tile, validating it against the temp
    files.

## 8. Required corrections (summary)

To `hunts/H-0012/README.md` before this hunt is committed:

1. **DS1 ranking provenance:**
   - State that the development run was on DS1's tile (0118p408).
   - State that the unWISE bitmask was added after the first full run, which had DS1 at #26 overall and #2 of 48
     rise-then-fade.
   - Add the robustness table (§2.2): DS1 stays #14 (#8 without dipoles) under threshold perturbations.
2. **DS1 flux scale:**
   - Report the W1 slope of 1.087 (about 3.5σ) and the W2 slope of 1.047 as a calibration offset, not as agreement.
   - Quote DS1's peak change on De et al.'s scale, or say which scale is used.
3. **DS1 "kept fading" must go.**
   - Replace with: no significant change after 2021 Dec (W1 −0.5σ, W2 −1.2σ); 22% / 27% of the 2010 W1 / W2 flux
     on De et al.'s scale.
   - Mention the 2024-11 JWST epoch and the De et al. 2026 vs Beasor et al. 2026 disagreement.
   - Optional: compare synthetic W1/W2 photometry from the NIRSpec spectrum.
4. **BH1:**
   - Delete the claim that empty-sky nulls exclude a calibration artefact. Replace it with the real-source and
     structured-region controls (§4.1), which do exclude it.
   - Report the existing `null_on_sources` result.
   - Lead with the pre-defined statistic (`delta_late`, W1 −6.4σ; about −5.6σ against the source null) and give
     `delta_neo` as secondary.
   - Add the literature: the fade is already published from Spitzer (Adams et al. 2017, arXiv 1609.01283; Basinger
     et al. 2021), and JWST measures 1.3-1.8 µJy at 3.6 µm (Beasor et al. 2024; Kochanek et al. 2024;
     Forés-Toribio & Kochanek 2026).
   - The new content is only the WISE light curve: the 2010 anchor and the flat 2016-2024 level.
5. **Sensitivity:**
   - Quote the completeness plateau (85-96% in M31 W1, not 100%) and the per-epoch depth range (up to 0.8 mag).
   - State that candidate-level completeness is unmeasured and that injection bypasses the subtraction.
   - The "6-7 Mpc by averaging" claim relies on a statistic the blind search does not use. Either add a stacked
     (NEOWISE − 2010) detection channel, or drop the claim for blind search.
6. **Data provenance:**
   - Record that there is no official release or licence for time-resolved images, and that the epochs are a
     multi-build concatenation (§7).
   - Make "ask Meisner" a hard gate before the 400 GB pull.
   - Fix citations: the 2018 time-resolved coadd paper is arXiv 1710.02526; unTimely is Meisner, Caselden, Schlafly
     & Kiwy 2023.
7. **M31 leads:** see §5. Present 9.336 +40.277 as a known LBV (Huang et al. 2019), 10.567 +40.327 as the Seyfert IV Zw 29, and 11.0014 +42.3396 as a probable background AGN. Only 10.877 +41.742 remains open. Add Gaia DSC quasar probability and W1−W2 to the triage, and store Gaia IDs as integers.
8. **Code (before the scale-up, not blocking this README):**
   - Make season labels absolute.
   - Use a leave-one-out reference median.
   - Use the gated band's metrics in `classify`.
   - Raise the `local_scatter` floor to about 0.8.
   - Record `UNW_VER` per epoch.
   - Add a test with a 2010-vs-NEOWISE PSF and zero-point change.

## 9. Files

- `claude-referee-2026-11-01/bh1_step_test.py`: re-differencing variants; BH1 vs real-source and grid controls →
  `bh1_step_test.json`.
- `claude-referee-2026-11-01/bh1_controls_summary.py`: the tables in §4.1.
- `claude-referee-2026-11-01/bh1_figure.py` → `bh1_step_test.png`: control histograms with BH1 marked; WISE vs
  Spitzer light curves.
- `claude-referee-2026-11-01/ds1_checks.py` → `ds1_checks.json`: DS1 late-fade test with control-star zero points;
  ranking robustness.
