## 1. Verdict

Author: claude-referee (atlas10 pass), 2026-10-30. Scripts, logs and figures are in `reviews/claude-referee-atlas10-2026-10-30/`
(r1-r10, run from the repo root with `uv run python`). I reduced the seven ATLAS files myself from the raw forced photometry
(`oddsky.data.atlas.parse`) and did not import the investigators' scripts. The fits are my own code in **excess-flux space**
(`fitlib.py`); the magnification and parallax geometry come from `oddsky.analysis.lensing`. Everything else is an outside
service: Gaia alerts pages, TNS, IRSA ZTF, ALeRCE, VizieR (idia mirror), SIMBAD (CfA) and the Gaia TAP.

| star | verdict | P(microlensing) | P(mundane) | P(other / unexplained) | safe public wording |
|---|---|---|---|---|---|
| **J163539.69-355208.3** | lens candidate (strong) | 0.75 | 0.10 | 0.15 | "an apparently unreported microlensing candidate: a smooth, achromatic ×6-9 brightening in 2017 Aug (tE ≈ 120-190 d)" |
| **J173150.73-444549.3** | lens candidate, parallax-dependent | 0.55 | 0.15 | 0.30 | "an apparently unreported long microlensing candidate (peak 2018 Jul 11-14); a point lens fits only with annual parallax, and tE is not constrained (≈ 120-490 d)" |
| **J174440.98-365619.1 = Gaia23boj** | lens candidate (strong) | 0.70 | 0.10 | 0.20 | "Gaia23boj (AT 2023gcb), never classified, behaves like a microlensing event: achromatic, peak 2023 Mar 8-11, tE ≈ 75-125 d" |
| **J191120.59+134303.3 = Gaia21atr** | lens candidate (possible high magnification) | 0.55 | 0.20 | 0.25 | "Gaia21atr (AT 2021cwl), never classified, is a microlensing candidate peaking 2021 Mar 19-20 at ≈ ×30-50 of the Gaia star's flux; tE and u0 are not constrained" |
| **J075219.97-325515.6** | inconclusive (real event, shape undetermined) | 0.30 | 0.35 | 0.35 | "a real, month-long brightening in 2018 Mar-Apr (not a single-night spike); too sparsely sampled to classify" |
| **J185846.27+033028.5** | not a lens | < 0.02 | 0.90 | 0.08 | "an eruptive red infrared source (YSO candidate), bright for over a year; not a lens. The Gaia star matched to it is not the variable." |
| **J182120.84-143232.7** | not a lens (IR variable) | 0.05 | 0.80 | 0.15 | "an infrared variable (SIMBAD YSO candidate) that brightened again in 2021; not a lens" |

The headline corrections to the first reading:

- **The "single-night spikes" are not single-night.**
  - J191120 has 20 ATLAS nights above 5σ, in two units and both bands, from −32 to +64 d. Gaia, NEOWISE and ZTF see the same
    event.
  - J075219 has 6 nights above 5σ in two units and both bands, from −23 to +6 d.
- **The "×110" and "×48" are artifacts of the reduction.** They are ratios to ATLAS reduced-image baselines that sit far below
  the stars' true flux. In these crowded fields the ATLAS c baselines are *negative*. The investigators' ratio code divided the
  c fluxes by negative medians, which flipped the events into dips and pinned c's fs at the 0.02 bound.
  - J191120 peaks at ≈ ×30-50 of the Gaia star's flux, not ×110.
  - J075219 peaks at ≈ ×5-8, not ×48.
- **For J191120 the lens is not 7900 in χ² better than a bump.** With fair fits in excess flux it beats the best non-lens shape
  by Δχ² 65-117 in most reduction choices, and by only 12-40 in four of them. Its u0 ≈ 0.007 and "Amax 138 / 2417" are not
  robust.

## 2. Findings

### 2.1 Re-reduction (r1, r9, r10)

**Cuts.**
- c and o only; err = 0; duJy > 0; mag5sig > 17.5.
- A chi/N cut scaled with flux (the fixed chi/N < 10 removes 39 of 73 near-peak rows for J174440 and 55 of 93 for J173150).
- Nightly per-unit weighted means, with a 4σ clip.
- Baseline at |Δt| > 400 d. The error floor is the baseline's excess robust scatter.

Yearly per-unit medians and PSF widths are in `r1_reduce.log`.

**Systematics found.**

- **PSF-width dependence again.** The early-era fluxes depend on PSF width, as found for J180624 in the last pass. In the
  wide-PSF years (02a 2015-16, maj 3.8-6 px; 01a 2017-18, maj 3-5.6 px) the forced flux falls by up to the whole baseline in
  crowded fields:
  - J191120 o 02a: −436 uJy in 2016 vs +114 in 2025.
  - J163539 o 02a: 134 vs 186 uJy in 2016.
  - J182120 2016 fluxes are negative.
  - None of the 2017-2023 event seasons of the four candidates is affected beyond the 01a rise points of J163539 (rise amplitude
    0.71 ± 0.09 of the global value in 01a vs 1.10 ± 0.05 in 02a, r8).
- **Additive (sky) bias in crowded fields.** I compared the ATLAS baselines with the o flux expected from Gaia (G and RP, about
  0.2 mag uncertain; `r2b_gaia_vizier.log`):
  - J191120 ≈ 0.4×, with negative c.
  - J075219 ≈ 0.3×, with negative c.
  - J182120 ≈ 0.5×.
  - J163539, J173150 and J174440: 0.7-1.0×, consistent within the conversion error.
  - J185846: 0.1×, because the AllWISE source is 2.8″ from the Gaia star it was matched to (§2.6).
- **Consequences of that bias.** Excess flux (night − baseline) is unbiased by an additive offset, but flux ratios are not.
  Hence I fit in excess flux and take blend fractions only from Gaia, ZTF and NEOWISE.
- **The investigators' ratio series.** The per-unit baseline medians are c −11 and −17 uJy for J191120 and −16 uJy for J075219,
  so the event ratios become −7.9, −2.9 and −1.7 (`r10_checks.log`).

**Frame checks of the two "spikes" (r9).** Every >5σ night has its excess in every frame, at 2-3 different detector positions.
Frame-to-frame scatter is close to the formal error, except where noted.

- **J191120, 2021 Mar 20 (peak).**
  - 4 frames in 01a: 8456, 8792, 7819 and 8179 uJy, at 3 positions. PSF, mag5sig and sky are normal for the season.
  - chi/N is 177-1136. That is a PSF-model mismatch which grows about as flux²: 26 at 2500 uJy on Mar 24 and 5 at 1000 uJy.
    The frame-to-frame scatter (11× the formal error) is the same mismatch.
  - The neighbouring nights continue the decline in another unit (02a: 1005 uJy on Mar 30).
  - Not a satellite or ghost: it repeats over many nights, units and pointings. Ecliptic latitude is +35.8°, and an asteroid is
    excluded by the multi-night persistence. Not a flare: it lasts months.
- **J075219.**
  - Mar 7, 8 and 10 (02a): +110-130 uJy, each at 3 positions.
  - Mar 16 (c): +44 uJy.
  - **Mar 30 (01a, the "×48"): +684 uJy, on the season's worst frames.** PSF 1.8 px wider than the season median, mag5sig
    0.8 mag shallower, sky 1.75 mag brighter (full moon was Mar 31).
  - Apr 5 (02a, 8 frames at 6 positions): +395 uJy.
  - NEOWISE Apr 8: ×5.7 in both W1 and W2. The visits before (−157 d) and after (+210 d) are flat to 0.05 mag.
  - Real and month-long, but the Mar 30 peak amplitude is unreliable. Ecliptic latitude is −52.5° and the event spans weeks, so
    not an asteroid. Not a flare: it lasts weeks.

### 2.2 Fits and robustness (r3: 14 reduction variants per star; J182120 default only, `r3_fits_J182120_quick.log`)

**Models.** Every model gets the same per-series freedom: an amplitude for each series, solved exactly.
- Point lens, static and with annual parallax (both signs of u0).
- Lens with separate rise and fall tE (the symmetry test).
- Pearson VII, symmetric and two-sided.
- A Norris FRED.
- A "nova" shape: exponential rise to a cusp, then a power-law decline.

**Variants.** chi cut (scaled / < 10 / none), baseline span 300/400/600 d, error floor on/off, PSF correction, PSF < 3.3 px
only, ±800-d window, o-only, ATLAS-only, without Gaia/ZTF, free offsets, and fs ≤ 1 for the lens. The non-lens numbers in the
`fs<=1` rows are a bookkeeping error (the cap was also applied to the bump amplitudes); ignore them.

Ranges across variants (`r3_fits_*.log`):

| | t0 | tE (d) | \|u0\| | Amax | πE | Δχ² static→parallax | Δχ² best non-lens − best lens |
|---|---|---|---|---|---|---|---|
| J163539 | 57982.0-57984.3 (2017 Aug 15-18) | 121-189 | 0.086-0.15 | 6.7-11.7 | 0.31-0.43 (N +0.31..+0.42) | 30-78 | +14 to +43 (static alone *loses* to a symmetric PV7 by ≈ 28) |
| J173150 | 58309.8-58313.0 (2018 Jul 11-14) | 123-493 (parallax) | 0.04-0.21 | 5-23 | 0.24-0.40 | 173-3347 | +25 to +566 |
| J174440 | 60010.9-60013.7 (2023 Mar 8-11) | 76-124 | 0.13-0.21 | 4.8-7.6 | 0.09-0.28 | 24-35 (348 without floor) | +20 to +50 (199 without floor) |
| J191120 | 59293.1-59294.3 (2021 Mar 19.1-20.3) | 39-245 | 0.003-0.02 | 30-340 | 0.17-1.3 | 14-52 | +65 to +117 in 10/14; +12 to +40 for ATLAS-only, no Gaia/ZTF, no floor, peak night removed |
| J075219 | 58203-58209 | 26-3000 | ~0 | undefined | – | 2-9 | −1.5 to +1.4: indistinguishable |

**J163539.**
- The static lens fits with fs ≈ 1.0-1.1 (relative to the ATLAS baseline) but is beaten by a symmetric PV7 (default: 856 vs 829).
- The lens wins only with parallax. The signal is consistent across variants (πE,N ≈ +0.38, πE,E ≈ −0.05) and
  fs ≤ 1 costs nothing (Δχ² 0.2).
- The rise is ~20% steeper than the decline (tE_rise/tE_fall 0.75-0.84). Parallax absorbs this.
- FRED is excluded (Δχ² > 1500).
- NEOWISE confirms the wings: W1 ×1.32 at −165 d and ×1.2 at +200 d, where the lens gives 1.29 and 1.15.
- The investigators' numbers (tE 150-160 d, parallax 844 vs PV7 875) are confirmed. But "smooth symmetric" should become
  "mildly asymmetric; a lens is preferred only with parallax".

**J173150.**
- A static lens needs fs ≈ 3: the source would have to be three times brighter than everything in the aperture. With fs ≤ 1 it
  is worse by Δχ² ≈ 3300. **A static point lens is excluded.**
- Parallax gives fs 0.77-0.91 (W1 0.78) and beats every non-lens shape. But tE runs from 123 to 493 d and πE from 0.24 to 0.40
  along the degeneracy. The investigators' "tE 130-260 d" is too narrow.
- Mild chromaticity:
  - c rises at 0.87 ± 0.05 of its global amplitude, and W2 at 0.91 ± 0.05.
  - c/o excess goes 0.36 → 0.41 from −55 d to the peak.
  - The o peak is 12.64 AB, near ATLAS saturation. 02a chi/N is 37-88, and 01a/02a disagree by up to 9% on the same night.
  - Some peak compression is possible.

**J174440 (Gaia23boj).**
- The lens beats the nova shape and the PV7 by 20-50 with fs ≈ 1.0-1.2 (Gaia fs 1.0-1.15); fs ≤ 1 costs 0.8.
- The investigators' parallax fit hit the fs = 1.5 bound in ATLAS o 03a (fs 1.41-1.50 in every series). It is unphysical and
  was not reported.
- **The rise is not entirely unobserved:**
  - Gaia: ΔG −0.07 on 2022 Sep 2 and −0.13 on Oct 3.
  - NEOWISE: ΔW1 −0.11 at −190 d and −0.13 at +175 d.
  - These wings are about 2× brighter than the point-lens model: Gaia rise amplitude 1.53 ± 0.19, W1 2.07 ± 0.37 of the model.
    That is ~2-3σ evidence for broader wings than a point lens.

**J191120 (Gaia21atr).**
- The lens reproduces:
  - the Gaia rise (×1.77 on Feb 12, ×2.75 on Feb 26);
  - the ATLAS cusp (8380 uJy on Mar 20, then 2440, 900, 720, 500 uJy on +4, +10, +12, +16 d);
  - NEOWISE (+23 d);
  - Gaia (+69 d);
  - the ZTF r tail (+67 to +110 d).
  The chi2 is dominated by the 2015-16 wide-PSF baseline nights, which do not involve the model; see `r3_*_series.csv`.
- The cusp is sampled by one night, and the 1/|t − t0| wings make **F_s·tE, t0 and t_eff = u0·tE ≈ 0.5-1.3 d** the only
  robust quantities.
  - tE is 58-72 d when Gaia, ZTF and NEOWISE are included with error floors, and 97-245 d from ATLAS alone or without floors.
  - Amax follows tE.
- The fits prefer a rise ~25% faster than the decline (tE_rise/tE_fall 0.71-0.78).
- Gaia-relative blend: fs_G 0.78-0.97, fs_r (ZTF) 0.8-1.1, fs_W1 0.76-0.99. So the source is essentially the whole G = 18.39
  star.

**J075219.** Every shape fits equally (Δχ² ≤ 1.5). The lens solutions are degenerate (u0 → 0, tE 26-3000 d). It cannot be
classified from these data.

**J185846 and J182120.**
- J185846: the "lens" solutions are pathological (tE 3000 d, u0 → 0, NEOWISE fs 0).
- J182120: the ATLAS amplitudes come out *negative* in the 2016 window (PSF systematics) while NEOWISE is positive.
- Neither is a lens fit in any sense.

### 2.3 Achromaticity (r5, r8, r10)

**A caveat on W1 = W2.** W1 = W2 is a weak test for these stars. Their quiescent W1 − W2 is ≈ 0, and any hot or Rayleigh-Jeans
addition also has W1 − W2 ≈ 0. Both non-lenses here (J185846, J182120) brightened equally in W1 and W2, and J182120 did so twice.

**The test that discriminates is optical against infrared, or blue against red.** On a red star, a hot or flat-Fν (nova,
free-free, CV disc) component raises the blue band 10-100× more in fractional terms than a lens would.

- **J191120.**
  - Gaia alert BP/RP spectra on the rise transits (×1.7-2.85): BP and RP rise by the same factor (ratio change 0.86-1.25, mean
    ≈ 1.05). A flat-Fν component would give ≈ 2.
  - At +90 d, ZTF g is 0.05 ± 0.12 and r is 0.21 ± 0.02 in fractional excess. A flat-Fν or nebular component would give a g
    excess ≈ 10× r's (≈ 2), excluded at > 10σ.
  - G, r and W1 give the same fs to within ~20% at different phases.
  - On optical and infrared colour evidence, the added light has the star's colour.
- **J174440.** Gaia BP/RP ratio change 1.01-1.10 at ×2.2-5.9. c/o excess is constant within errors (0.26 at −8 d, 0.22 at
  +40 d). Every series' amplitude in the decline is 0.98-1.08 of its global value.
- **J163539.**
  - c/o excess is 0.34 at −81 d and +29 d, and ~0.41 near the peak once o is interpolated. Achromatic to ~10-20%.
  - The W2 amplitude is unreliable. Only 3-8 of ~10 NEOWISE W2 exposures per visit are detected, so the W2 baseline is biased
    bright. AllWISE W2 = 15.58 is quality B and flagged halo ('h'); W1 is flagged diffraction spike ('d'); W3 and W4 are upper
    limits.
  - The apparent W1 − W2 = −1.14 and "W2 − W3 = 3.3 excess" are artifacts. **"W1 = W2 ×8" should not be quoted as an
    achromaticity test for this star.** Use c/o and o/W1 instead.
- **J173150.** About 12% bluer at the peak; see §2.2.

### 2.4 Alternatives, per star (r2, r2b, r6, NEOWISE visits)

| | J163539 | J173150 | J174440 | J191120 | J075219 |
|---|---|---|---|---|---|
| star (Gaia DR3) | G 18.31, BP−RP 2.13, ϖ 0.007 ± 0.21, RUWE 0.98, no source within 4″ (GSP-Phot "dwarf at 683 pc" contradicts ϖ at 7σ) | G 15.07, BP−RP 1.85, ϖ 0.08 ± 0.03, RUWE 1.03; neighbours G 16.9-17.7 at 4-5″ (Gaia-only share 0.95) | G 16.19, BP−RP 2.91, K giant (Teff 4550, logg 2.7, R 7 R☉), ϖ 0.015 ± 0.07, **RUWE 1.26, IPD multi-peak 14%, a G 19.9 source at 0.84″** | G 18.39, BP−RP 3.09, ϖ 0.05 ± 0.15, RUWE 0.99, nearest neighbour G 20.4 at 3.3″ | G 19.38, BP−RP 3.11, ϖ 0.22 ± 0.26, alone within 10″ |
| repeats | none 2015-26 (o baseline rob 8%); NEOWISE flat 2014-24 except the event | none; W1 flat to ~0.01 mag 2014-24 | none; W1 rms ~0.02 | none in ATLAS 2017-26; Gaia 2014-23 flat at 18.4 ± 0.03 | NEOWISE flat 2014-24 except Apr 2018 |
| Gaia DR3 G scatter (2014.6-17.4) | 94.5th percentile (the rise had begun by May 2017; consistent) | 44th | 89th | 26th | 53rd |
| CV / dwarf nova | no: months-long, achromatic | no | no | no: 5-week achromatic rise, achromatic g/r tail | not excluded by shape; o vs W1 rise nearly equal (×4-7 vs ×5.7), against a hot disc |
| nova / symbiotic | no | no | no (K giant, achromatic) | **the main alternative**: the fast decline (t2 ≈ 8 d) fits, but the 5-week achromatic precursor and the g-faint tail argue against it | no IR-blue signature; unclear |
| YSO burst | no IR excess (the excess is an artifact); achromatic | no | no | no IR excess (W1−W2 −0.21; W3 C-quality); achromatic | J−K 1.73, W1−W2 0.02; not excluded |
| flare | no (months) | no | no | no (months) | no (weeks) |
| Be / LPV / R CrB | no | no Be colours; not periodic | VSX SR\|M star at 27″ is a different star (outside the PSF) | VSX "L" star at 13.8″ (0.16 mag range) cannot make ×30 | – |
| artifact / asteroid | no: 3 units, NEOWISE; β −13.7° but months-long | no | no | no: multi-night, 3 surveys | no: 2 units, NEOWISE |

### 2.5 Gaia alerts, TNS, novelty (r4, r5, r6)

**Gaia21atr = AT 2021cwl.**
- Alerted 2021-02-12 at G 17.87, with the comment "red galactic plane source rises by 0.6 mag".
- The alert page has no ATels, no AstroNotes, no other-survey detections and no classification. TNS has no classification
  report.
- The alert light curve: baseline 18.41; −0.04 on 2020-12-08; −0.57 on Feb 12; −1.07 on Feb 26; −0.28 on May 28; back to
  baseline by 2021-09-04. There are no Gaia transits between Feb 26 and May 28.

**Gaia23boj = AT 2023gcb.**
- Alerted 2023-03-10 at G 14.18. TNS has no classification.
- The alert light curve: 16.17-16.19 baseline; 16.12 on Sep 2 and 16.06 on Oct 3 2022; 14.18 on Mar 10; 15.00 on Apr 12; 15.29
  on Apr 29; 16.11 on Sep 13 2023.

**TNS 60″ cone** (HTTP 200, valid header, 30 s pacing; no 429s this time): only those two objects. Nothing for the other five.

**Gaia alerts index** (27,076 alerts to 2025-01-15): nothing within 60″ of J163539 (nearest 42′), J173150 (135′), J075219
(77′), J185846 (50′) or J182120 (79′).

**Gaia DR3 vari_* tables, SIMBAD, VSX, ASAS-SN variables.**
- No vari_* entry for any of the seven. **Gaia DR3 vari_microlensing has none of them.**
- SIMBAD has nothing within 10″ of the four candidates or J075219. J185846 and J182120 are YSO candidates ("Y*?").
- VSX has nothing at any target. Only unrelated neighbours appear, at 27″ (J174440) and 13.8″ (J191120).
- ASAS-SN variables (II/366): none.

**Microlensing lists** (`ext/`, plus the live OGLE EWS pages for 2017, 2018 and 2023):
- J163539, J173150 and J075219 are outside the OGLE and KMT footprints. Nearest events of any kind: ≥ 200′ (GVS, Gaia DR3 ML),
  ≥ 513′ (KMT) and ≥ 553′ (OGLE EWS of the event year).
- **J191120:** nearest ZTF lens 71′. The Gaia alerts list has no nearby microlensing alert.
- **ZTF on J191120.** The DR has no 2021 data before May 26 (MJD 59361). ALeRCE has no object within 60″. **ZTF did not
  observe the peak.** The DR shows only the tail: r 18.35 on May 26 vs 18.70-18.74 baseline.
- **J174440 is inside OGLE's 2023 footprint.** 5 OGLE-2023 events lie within 60′, the nearest at 21′. OGLE-IV events exist at
  6.9′ (2024) and 10′ (2016). The live EWS 2023 page also has nothing nearer than 20.9′. KMT has no event within 30′ in 2016-24,
  so the star is probably outside KMT fields. The likely reason OGLE did not alert it is saturation (I ≈ 14.4 quiescent, ≈ 12.4
  at peak), but that is an inference. It is the main novelty caveat for this star.
- **MOA:** the moaprime alert pages for 2017, 2018 and 2023 return HTTP 200 with **empty tables**, so MOA is unchecked. The KMT
  2023 web page could not be parsed (0 coordinates).

**Web search.** No hits for "Gaia21atr", "Gaia23boj", "AT 2021cwl" or "AT 2023gcb".

**Not done:**
- ADS full text: I did not rerun the investigators' ADS pass.
- ASAS-SN Sky Patrol light curves.
- GOST scanning-law checks. These matter: J163539 (G ≈ 16 at peak for months in 2017) and J173150 (G ≈ 13 in 2018) were never
  Gaia-alerted, which needs either a scanning gap or an explanation.

### 2.6 The two non-lenses

**J185846.**
- The AllWISE source is 2.83″ from the Gaia star matched to it. That star has a normal DR3 G scatter (37th percentile) over
  2014.6-2017.4, while ATLAS at the WISE position was 2-8× its baseline in 2015-16. So the variable is not the Gaia star.
- The variable is the very red 2MASS source (J − K 3.0, W1 − W2 +0.34; SIMBAD Y*? nearby). NEOWISE shows large intra-visit
  scatter (rchi 20-60) at every visit.
- An eruptive YSO-like source, not a lens. The investigators' verdict stands; the Gaia identification is wrong.

**J182120.**
- NEOWISE brightened again in 2021: ΔW1 −0.50 and −0.45 at two visits six months apart (59298, 59462), with W2 equal.
- The optical barely moved: ZTF r −0.04 mag and ATLAS o +3-5% in 2021. So that episode was strongly chromatic.
- There is also a slow 0.2-0.3 mag W1 drift over 2014-2024. SIMBAD lists it as a YSO candidate, and its Gaia DR3 G scatter is
  in the 93.7th percentile in a window that contains the 2016 event.
- ATLAS 2016 (from Apr 4, 9 d after the NEOWISE visit) is fainter than the PSF-corrected baseline, not brighter, but it is
  dominated by wide-PSF systematics.
- Verdict: "not a lens (recurrent IR variable)". This is firmer than the investigators' "inconclusive".

## 3. Corrections the investigators must make

1. **J191120.**
   - Replace "one ATLAS night at ×110" with the multi-survey event: Gaia rise Feb 12-26, ATLAS peak Mar 20 at o ≈ 14.1 then 20
     nights >5σ in 2 units, NEOWISE +23 d, ZTF tail.
   - Quote the amplitude against the Gaia star: ≈ ×30-50.
   - Withdraw u0 ≈ 0.007, Amax 138 and Amax 2417. State "t0 2021 Mar 19.1-20.3, t_eff ≈ 1 d, tE not constrained (40-250 d)".
   - Replace "lens 1418 vs PV7 9293" with Δχ² 65-117, or 12-40 depending on reduction.
   - Say ZTF did not observe the peak (no 2021 data before May 26; no ALeRCE object).
2. **J075219.** It is not a single-night spike. The "×48" is a ratio to a 01a baseline of ~15 uJy, from the season's worst
   frames (moon, PSF +1.8 px). Report it as a month-long event, peak ≈ ×5-8, unclassifiable.
3. **All stars: ratios.**
   - Do not form flux ratios to ATLAS reduced-image baselines that are ≈ 0 or negative.
   - Fit excess flux and take fs from Gaia, ZTF or NEOWISE.
   - Fix `ratio_series`: it silently sign-flips series with negative medians (J191120 and J075219 c), which is why c fs sat at
     the 0.02 bound.
4. **J174440.**
   - Report that the parallax fit hit the fs = 1.5 bound.
   - Quote tE 76-124 d, u0 0.13-0.21.
   - Say the rise wing is seen by Gaia (2022 Sep-Oct) and NEOWISE, and that the wings are somewhat broader than a point lens.
   - Note the star lies in OGLE's 2023 footprint without an EWS alert (probably saturation).
   - Note RUWE 1.26 and a G 19.9 companion at 0.84″.
5. **J163539.**
   - Say the lens beats a symmetric bump only with parallax (static lens loses by ≈ 28).
   - Drop "W1 = W2 ×8" as an achromaticity argument: the W2 baseline is detection-biased and AllWISE W2/W1 are halo/spike
     flagged.
   - Quote tE 120-190 d.
6. **J173150.**
   - Say a static lens is excluded (it needs fs ≈ 3) and the lens interpretation depends on parallax.
   - Widen tE to ≈ 120-490 d.
   - Note the mild c/W2 chromaticity on the rise and possible peak saturation (o 12.6).
7. **J182120.** Change "inconclusive" to "not a lens". It brightened again in W1 in 2021 by 0.5 mag over six months while the
   optical stayed flat, and it is a SIMBAD YSO candidate.
8. **J185846.** Keep "not a lens", but drop the Gaia G 17.85 identification: it is 2.8″ away and was constant.
9. **General.** W1 = W2 equality is not a lens test for stars with W1 − W2 ≈ 0; two non-lenses here pass it. The optical vs
   infrared and BP vs RP tests are the ones that discriminate.

## 4. What remains unchecked

- **GOST scanning law** for J163539 (2017) and J173150 (2018). Why did Gaia not alert either?
- **ASAS-SN Sky Patrol light curves.** J173150 at V ≈ 13 and J174440 should be in ASAS-SN.
- **MOA 2017/2018/2023** (the alert pages are empty). **KMT 2023** web page (the local list was used instead). **OGLE** directly
  for J174440 (saturated photometry?).
- **ADS full text** for the five non-alert stars and the two TNS names (not rerun).
- **Spectra.** None exists for any of the seven. A spectrum of Gaia21atr's and Gaia23boj's quiescent stars would fix source
  type and distance.
- **Neighbour photometry in the J191120 and J075219 frames.** It was not needed: the events are multi-night, multi-unit and
  multi-survey.
- **Three ATLAS tasks have not returned:** J075928, J175634 and J174744.

Files:
- `r1_reduce` (cuts, yearly baselines, event nights, frames) and `r2_catalogs`/`r2b_gaia_vizier` (Gaia DR3, neighbours, scatter).
- `r3_fits` with `fitlib` (14 variants per star; `data/r3_*.json`, `data/r3_*_series.csv`).
- `r4_tns`, `r5_gaia_spectra` (`r5_gaia_spectra.png`), `r6_novelty`, `r7_figure` (`r7_lightcurves.png`), `r8_chromatic`,
  `r9_spike_frames` and `r10_checks`.
- Data: `data/gsa_*` (Gaia alert light curves and pages), `data/ztf_*.csv` and `data/tns_*.html`.
