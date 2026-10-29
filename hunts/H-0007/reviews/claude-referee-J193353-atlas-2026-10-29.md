# Referee report: J193353.06-211813.4, ATLAS follow-up (H-0007)

Author: claude-referee, 2026-10-29. Scope: `work/atlas_J193353.txt` (task 5271652, reduced-image forced photometry, 3,943 frames
2015-2026; identical to `~/oddsky-runs/h0007/atlas_J193353.txt`), `scripts/hunt_h0007_j193353_fit.py`, and the investigators' claims.
I wrote my own scripts in `reviews/claude-referee-J193353-atlas-2026-10-29/` (a1-a8). They use pandas, scipy, MulensModel 3.12 and emcee,
outside the Oddsky tools. Run a2 first, then a3. a3 also needs the first referee's `/tmp/j1933ref/target_exp.parquet` and `ztf_zoff.csv`
(their b1, b3 and b9). a4-a8 read `/tmp/j1933atl/`.

## Verdict

ATLAS reproduces the event. It is on the star, it is achromatic, and it looks like microlensing. Two units (01a, 02a) and both bands see it on 88
nights, and ATLAS agrees with NEOWISE to 2% on Apr 8-10. **But the peak was in mid/late March, not on Apr 10, and it reached ≥ ×2.4.**
That means the first referee's fit (t0 Apr 10 ± 7 d, A 1.95) failed its detailed predictions. A static point lens, the investigators' model, also leaves a
systematic rise/decline asymmetry, seen the same way by ATLAS, NEOWISE and ZTF. Annual parallax removes it (Δχ² = 255 for 2 parameters)
with a physically ordinary lens. **P(mundane) = 0.02.** Ladder status: **reproduced**.

## Attacks and results

**1. Is it real and on the star? (a1, a2, a6, a7)**
- *Coverage.* The 2020 event is observed by 01a (o, 47 nights) and 02a (o 18, c 23) only. 03a and 04a start in 2022.
- *Per-unit baselines.* Baselines from 2015-2018 and 2021+ agree to 1.5%: o 2915-2959 µJy, c 1823-1874 µJy.
  - A constant per-unit offset of that size cannot fake ×2.4.
  - The two units measure the same excess: in o, the scale relative to the model is 0.994 ± 0.007 for 01a and 1.036 ± 0.014 for 02a.
  - Consecutive nights from different units agree: Apr 8 01a ×2.03 vs Apr 10 02a ×1.99; May 14 01a ×1.30 vs May 16 02a ×1.29.
- *Frame quality.* The event frames have normal depth (mag5sig 18.3-19.6) and errors of 20-50 µJy.
  - chi/N rises from a median of 2.4 to 6.1 (01a) and from 3.0 to 9.5 (02a). That is expected when the star is ×1.5-2.4 brighter: PSF mismatch scales with S/N.
  - Baseline nights of this star also reach chi/N 20-45 (e.g. 2020 Sep 15 at ×1.01). This is not a sign of a blend.
- *Reference/difference imaging.* Not applicable: this is PSF photometry on reduced images, with no reference. The only Gaia source within 15" (G = 19.94 at 9.7") is ≤ 1.6% of the flux.
- *Dropout night.* On 2020 Jul 17 (01a) four frames read 0 ± 0.1 of the flux at normal depth. This is a forced-photometry failure. The investigators' "drop nights < 0.8×" cut removes it, but the cut should name it.
- *Other events.* Outside 2020, with good frames only (dujy < 150, mag5sig ≥ 17.5), 0 of 927 nights exceed ×1.10. The largest is 2023 Oct 21, 04a o ×1.099; 04a's baseline scatter is 0.026.
  - The investigators' four "> ×1.15 nights" are all shallow frames (mag5sig 14.2-17.0).
  - But only 2018 Nov 10 and 2023 Oct 30 have a normal frame on the same night. The 2022 Nov 8 frames (×2.38 and ×−0.01) and 2026 Oct 19 frames (×0.63-1.46) are all shallow.
- **Result: a single event on this star in 2015-2026.**

**2. The peak and the parameters (a3, a4, a5)**
- *What the data constrain.* Nothing between 2019 Nov 14 (×1.013) and 2020 Mar 11 (×2.42), then nothing until Apr 8 (×2.03).
  - The peak is therefore **≥ ×2.42 and unobserved**.
  - Mar 11 > Apr 8 puts the peak before Mar 25 for any symmetric curve.
- *The investigators' fit.* I reproduce it exactly: t0 58925.6, tE 62.7, u0 0.434, χ² 352/190.
  - Its formal errors (±0.8 d, ±1.1 d, ±0.007) are not credible, because the residuals are structured.
  - In the joint static fs = 1 fit (a4), the 2019 Sep-Nov rise wing sits **below** the model in ATLAS o (−0.024), NEOWISE W1 (−0.028) and ZTF g/r (−0.022/−0.020). The decline sits **above** it in Jun-Sep (+0.02 to +0.05 in c, o, g and r).
  - The under-predicted NEOWISE (1.944 vs 1.98) and ZTF tail (1.124/1.061 vs 1.169/1.086) belong to this same pattern. They are not noise.
  - The pattern is not a calendar systematic. In Oct-Nov of other years, o sits at 0.994-1.011 (2017-2026), and in Jun-Aug at 0.993-1.007.
- *Blending (fs free).* Freeing blending cannot remove the asymmetry: the rise wing stays at −0.03.
  - It opens the usual degeneracy instead: ATLAS alone gives fs 0.28-0.31, u0 0.13, tE 107 d, A_max 7.6, χ² 330 against 419 for fs = 1.
  - Jointly, fs = 0.34-0.37 in all three surveys, tE 92 d, χ² 658/699 against 715/702.
- *Annual parallax* (MulensModel, Earth-based; the star is 0.4° from the ecliptic and peaked at 66° elongation):
  - Joint fit: χ² 715 → **460/700** for fs = 1; 459/697 with fs free. ATLAS alone: 419 → 244/277.
  - With parallax the residuals are flat in every window and survey (|mean| ≤ 0.013, apart from the c band at +0.017).
  - An ad hoc asymmetric Paczynski (separate tE before and after t0) reaches only 568. The parallax-specific shape is what fits.
- *Joint MCMC* (parallax, one fs per survey, errors rescaled per survey; 95% ranges):
  - t0 = MJD 58928.3-58929.8 (2020 Mar 20-21); tE = 40-55 d (median 45).
  - u0 = ±(0.25-0.40). The sign is two-fold degenerate, as expected near the ecliptic.
  - π_E = 0.39-0.80 (π_E,E 0.37-0.70); fs = 0.60-1.04 in each survey, consistent with no blend.
  - Observed peak ×2.66-2.94 (source A_max 2.6-4.1).
- *Lens.* With μ_rel 5-15 mas/yr, θE ≈ 0.6-1.8 mas, so M ≈ 0.13-0.4 M☉ and π_rel ≈ 0.3-1.0 mas, i.e. D_L ≈ 1-2 kpc.
  An M dwarf there has G ≈ 20-23, consistent with fs ≈ 1. Nothing about the parallax solution is exotic.
- **Honest ranges.**
  - Peak date: 2020 Mar 17-22 across all models (data-only: Mar 11-25).
  - Peak: ×2.45 (static) to ×2.9 (parallax); ≥ ×2.42 measured.
  - tE: 40-55 d (parallax). The static 62-63 d and blended 90-107 d are biased by the asymmetry.
  - u0: 0.25-0.44 in absolute value.

**3. Achromaticity (a6, a7).**
- With the parallax shape fixed and a free baseline, the c (02a) excess is **1.05 ± 0.03** times o. On the same unit, o 02a gives 1.036.
- 01a and 02a differ by 4% in o, so ATLAS's unit-to-unit systematics are about this size. The c 02a seasonal zero point wanders by 0.95-1.03 (2015 is low).
- Across instruments: ATLAS o ×2.03/1.99 (Apr 8/10) matches NEOWISE W1 = W2 ×1.98, and ZTF g = r on the tail to 0.01. **Achromatic from g to W2 to ≈ 5%.**

**4. Shape against transient decays (a8).** The fits use the ATLAS decline only, 2020 Mar 11 to Nov (90 nights).
- *Fits.* Exponential excess: χ² 413/88. Power law from a peak ≤ Mar 11: 728/87. Static lens: 181/87. Parallax lens: 79/85.
- *The decline rate is not monotonic.* d ln(excess)/dt is −0.013/d from Mar 11 to Apr 10, then −0.034/d to May 5, −0.022/d to Jun 3, and −0.019 to −0.024/d through Aug.
  - It accelerates after the first month. A flare, eruption or background transient that peaked by Mar 11 decelerates.
  - This curvature, flat-topped and then steepening, is the lens signature.
- *No rise data.* The only constraint on the rise is the 2019 wing (excess ≤ 0.02 at about −130 d), which is what drives the parallax.
- An R CrB-like recovery has the wrong sign: there is no dip anywhere in 2015-2026.

**5. Contradictions with the first referee.**
- *Their fit (t0 Apr 10, Apr 2-17; A_max 1.95; "the NEOWISE visit is at the peak") is wrong.* The peak was about 3 weeks earlier and ≥ ×2.4.
  - Mar 11: the old model gives −0.48 mag; ATLAS measured −0.96.
  - May 15: it predicted −0.42; ATLAS measured −0.28 (×1.30).
  - Apr 10: it predicted −0.72; ATLAS measured −0.75. This one passed.
  - The investigators' original "peaking before Apr 9" was right in substance.
- *Their deletion of the "slow decline within the visit" still stands.* The lens declines at 0.019 mag/d on Apr 8-12 (ATLAS ×2.03 → ×1.89), but the W1 slope is 0.083 ± 0.022.
- *The Apr 14 moon-masked frame* (W1 ×1.74, W2 ×2.00) brackets ATLAS's ×1.83 interpolated between Apr 12 and Apr 16. It is still not evidence.
- *Gaia.* The new predictions are ΔG = **−0.62 (Feb 28, 2 transits), −0.98 (Mar 12, 3 transits), −0.60 (Apr 17)** (95% ±0.05). The old ones were −0.35/−0.49/−0.71.
  - Hodgkin et al. 2021 (A&A 652, A76, §2.6) defines two detectors. OldSourceDeltaMag needs ≥ 2 transits ≥ 1 mag (and ≥ 3σ) from the historic mean within 40 d. OldSourceMeanRms needs ≥ 0.15 mag and ≥ 6σ.
  - So DeltaMag was borderline and MeanRms should have raised a candidate. It was then lost to GoF or neighbour filtering or to vetting.
  - ATLAS measured ×2.42 one day before the Mar 12 transit. The silence therefore says nothing against the brightening; it bears only on the completeness of Gaia's alerts.
  - I now put its likelihood ratio at about 1, not 0.6-0.8.

**6. Novelty.** Nothing new was searched. Gaia and ATLAS both had this event in their data and neither reported it.
ASAS-SN is still unread, and MOA 2020 is still unchecked.

## Most plausible mundane explanation remaining

An unknown achromatic, months-long brightening of a quiet halo K giant that mimics a parallax point lens: a decline that
accelerates and then decelerates, a ×2.5-3 peak, and nothing else in 11 years. No known class does this.

The residual 0.02 comes from three things:
- The peak and the rise are unobserved.
- The parallax detection rests on a 2-3% wing deficit in 2019 Oct-Nov, although four instruments agree on it.
- A binary lens or xallarap could also produce asymmetry. That changes the parameters, not the mundane/astrophysical verdict.

## Required wording changes (`J193353.md`, the README paragraph, and the investigators' fit claims)

1. **Status: "candidate" becomes "reproduced (ATLAS, 2026-10-29)".** Still not announced and not a case.
2. **Title:** change "doubled in brightness in April 2020" to "brightened ×2.4 or more in March 2020".
3. **Add an Observed (ATLAS) bullet:**
   > Reduced-image forced photometry, 88 nights in 2020 from units 01a and 02a, in o and c: ×2.42 on Mar 11 (first night of the season); ×2.03 Apr 8; ×1.99 Apr 10;
   > ×1.65 Apr 20-22; ×1.30 May 14-16; ×1.10 in July; ×1.05 in Sep; within 2% by Oct. Per-unit baselines agree to 1.5%, the two units measure the
   > same excess to 4%, c/o = 1.05 ± 0.03, and no other night in 2015-2026 exceeds ×1.10 in good frames.
4. **Replace the referee's "Computed" fit bullet** (t0 Apr 10, A 1.95, "the NEOWISE visit is at the peak"). Those were superseded and failed their ATLAS predictions on Mar 11 and May 15. Use:
   > The peak (Mar 11 to Apr 8) is unobserved. A static point lens (t0 Mar 17, tE 63 d, u0 0.43, ×2.46) leaves a rise/decline asymmetry seen
   > identically in ATLAS, NEOWISE and ZTF. Annual parallax removes it (joint χ² 715 → 460, ATLAS alone 419 → 244). Its 95% ranges are: t0 2020 Mar 20-21,
   > tE 40-55 d, |u0| 0.25-0.40, π_E 0.39-0.80, fs 0.6-1.04, observed peak ×2.66-2.94.
5. **The investigators' fit claims.** Do not quote "t0 = 58925.6 ± 0.8, tE = 62.7 ± 1.1, u0 = 0.434 ± 0.007, A_max 2.46" as the result or with those errors.
   - "NEOWISE predicted 1.944 vs 1.98, ZTF 1.124/1.061 vs 1.169/1.086" must be described as a systematic under-prediction that parallax removes. It is not "agreement".
   - "c and o residual means 0.015/0.009" should become "c/o excess 1.05 ± 0.03 (unit systematics about 4%)".
   - Change "baseline by Oct" to "within 2% by Oct".
6. **The four > ×1.15 nights:** change "with normal frames the same night" to "all shallow frames (mag5sig 14-17); two of the four nights have a normal frame
   at baseline, the other two have only shallow frames, scattering both ways." Name the 2020 Jul 17 01a zero-flux dropout instead of hiding it in the 0.8× cut.
7. **Gaia:** change "predicted ΔG −0.35, −0.49, −0.71" (both places) to "−0.6 (Feb 28), −1.0 (Mar 12), −0.6 (Apr 17)". Add:
   > This is above the OldSourceMeanRms threshold (≥ 0.15 mag, ≥ 6σ) and at the DeltaMag one (≥ 1 mag), so the absence of an alert reflects Gaia
   > alert completeness. ATLAS measured ×2.42 the day before.
8. **Alternatives:** change "would not decay smoothly over three months" and "fits both data sets with no free blending" to:
   > The decline accelerates (d ln excess/dt −0.013 → −0.034/d) and then slows. Exponential and power-law decays fit it with χ² 413 and 728,
   > against 79 for the parallax lens (90 nights). A blend is not needed (fs 0.6-1.04).
9. **Next steps:** remove the ATLAS prediction paragraph, which has been tested. Keep ASAS-SN and Gaia DR5 with the new numbers (follow-ups below).
10. **Assessment:** "Real and astrophysical: very high (NEOWISE, ZTF and ATLAS; P(mundane) 0.02). Microlensing: very likely, probably with
    annual parallax; peak and rise unobserved."

## Decisive follow-ups

1. **ASAS-SN** (id 360778295746), g in 2020 Feb 15-Mar 25: the only survey that may have the rise and the peak.
   - The parallax and static models differ by about 0.17 mag on Feb 28: ΔG −0.62 against −0.79.
   - The parallax model predicts the peak on Mar 20-21 at −1.1 mag (×2.7-2.9).
2. **Gaia DR5 epoch photometry:** predicted ΔG −0.62, −0.98 and −0.60, with BP = RP. The Feb 28 point tests the parallax-induced rise.

## Tool fixes

- `hunt_h0007_j193353_fit.py` needs four changes:
  - Report profile ranges, not covariance errors, when the peak is unsampled.
  - Always try annual parallax (and fs free) and print wing residuals by season.
  - Use per-unit baselines.
  - Fit the 2019 wing explicitly, because it is the only rise information.
- `oddsky.data.atlas.nightly_bins`: flag zero-flux dropouts and shallow frames (mag5sig < 17.5) explicitly, not with a ratio cut that would also delete a real fade.
- Referee practice: a prediction from a fit whose peak is pinned by one survey epoch (here NEOWISE) should carry the profile range of the peak date, not Δχ² < 4 alone.
  The first referee's Apr 2-17 range was 2-3 weeks off.
