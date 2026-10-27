# Referee report: OS-0013 (Gaia DR3 5792808347020475136), "the K dwarf that lit up in 2018"

Referee: claude-referee, 2026-10-27. Referee claims: C1–C9. Call IDs refer to `ledger.jsonl`; my calls are K10–K30. Checks marked "outside the tools" used IRSA Gator, Gaia TAP, VizieR, ASAS-SN Sky Patrol, SkyMapper DR4 or pandas directly.

## Verdict

**The infrared step survives. It is real, astrophysical, and on the K dwarf to within ~0.2″.**

- I could not attribute it to the instrument, the field, a neighbour, or a moving or new source.
- What the step *is* remains open. Two-band photometry cannot distinguish newly made circumstellar dust from other dusty phenomena (for example ejecta after a planet engulfment).
- The optical light curve is flat across the onset (ASAS-SN, SkyMapper), so there was no large dip and no large flash.

Confidence that the excess is astrophysical and belongs to this star: ~93%.

## Attacks and results

1. **NEOWISE systematics** (C1; outside the tools).
   - The star is at ecliptic latitude −56°, so it is not in the south-ecliptic-pole cap. Visits have 16–36 exposures, and the scan pattern did not change in 2018.
   - I pulled every NEOWISE exposure within 300″ of the star. Twenty-seven field stars with W2 9.5–12.5 changed by +0.006 (W1) and +0.014 (W2) mag across the step, with robust scatter 0.005. None brightened by more than 0.1 mag.
   - Every visit's field zero-point is within ±0.02 mag.
   - The target's −0.17 / −0.36 step is a >30σ outlier.
   - Fainter field stars (W2 ~14.7) show only noise-level excursions.
2. **Blends, moving and new sources** (C2, C3).
   - Relative to the Gaia position propagated with proper motion (22 mas/yr, i.e. 0.2″ over the decade, which is negligible), the WISE centroid moves by 0.013 ± 0.008″ across the step.
   - rchi2 is unchanged, and nb = 1 throughout.
   - Any contaminant must therefore be within ~0.2″.
   - The closest IR neighbours are:
     - an unWISE W1-only source at 7.4″ (5% of the W1 flux);
     - a CatWISE W1 14.7 source at 9.4″;
     - AllWISE sources at 13″ and 16″;
     - a W1 8.75 star at 32″, which sets the halo flag both before and after the step.
   - All of these are flat across 2018.
   - An asteroid would affect one visit, not six years. A comet or transient within 0.2″, steady for six years, is implausible.
   - A background AGN or nuclear transient within 0.2″ would have to rise from undetectable (W2 > 16) to W2 ≈ 12.3 and then hold steady for six years. Over 18 M stars a few chance AGN alignments within 0.2″ are expected, but almost none would brighten by that factor of ~30 into a plateau.
3. **Saturation and nonlinearity.** None. W1 ~11.0 and W2 ~10.9 are 3 mag fainter than saturation. w1sat = w2sat = 0 and ph_qual is AA in all visits.
4. **Stellar explanations** (C5, C6).
   - Dereddened, the star sits on the K3V main sequence (M_G0 ≈ 6.31, (BP−RP)0 ≈ 1.17) with logg 4.58. It is not a pre-main-sequence star with a disk turning on.
   - UVW = (−24, −18, −3) km/s is >12 km/s from Chamaeleon, ε Cha and LCC.
   - Gaia RV from 17 transits is unremarkable, and RUWE is 1.02, so there is no evidence of a close massive companion.
   - Not a Be/shell star (4770 K).
   - Flaring M companion: excluded, because the excess has persisted for six years.
   - A K-dwarf photosphere cannot brighten by 17% at 3.4 µm.
   - Photospheric before the step: AllWISE 2010 matches 2014–17, W1−W3 = 0.17 ± 0.10, and Ks−W1 = 0.06 (C4).
5. **Excess properties** (C4, C5; K15, K16).
   - Onset between 2018 Feb 26 and Aug 8.
   - The first visit after onset is the brightest. The excess then plateaus at T ≈ 1040–1050 K through 2024.
   - Blackbody L_IR/L* ≈ 0.02 at ~0.04 AU. This is extreme for a main-sequence K dwarf, and keeping it up for six years at such small radii needs continuous replenishment.
6. **Optical** (C7, C8).
   - TESS:
     - Sectors S100–S101 are dominated by systematics: ramps and a 0.6-mag five-day offset.
     - The "~11 d" period is not robust (per-sector peaks at 6.6–20 d).
     - The TIC contamination ratio is 3.78. The star supplies only ~21% of the aperture flux, so the "no dips >5%" limit is only ~25% on the star itself.
   - ASAS-SN V:
     - Flat at 13.41 (robust scatter 0.036) through 2014–2018, including Feb–Apr and Jul–Sep 2018.
     - There is a gap in May–June 2018.
     - The photometry is diluted by about 1.6× by the 16″ neighbour and by HD 128641 (V 9.66, F0V) at 32″.
   - SkyMapper on 2018-04-24, inside the onset window: u/v/g/r match 2014 to 0.03 mag.
7. **Novelty** (C9).
   - VarWISE (Paz et al. 2026) already lists the WISE variability: W1/W2 amplitudes 0.18/0.375, classified "lpv". That classification is wrong for a K3V dwarf.
   - The detection of variability is therefore not new. The identification as a newly appeared ~1000 K excess on a main-sequence K dwarf is.
   - Nothing else in SIMBAD, VSX (only Gaia [ROT]) or the literature.
   - Not in the Chamaeleon, ε Cha or LCC membership lists.

## Most plausible explanation

Hot circumstellar dust that appeared abruptly in 2018 and has been resupplied since. The most likely source is a collisional event close to the star (an extreme-debris-disk-like brightening, in the sense of ID8 or ASASSN-21qj), but on an apparently mature K dwarf.

| Explanation | Probability |
|---|---|
| Collisional or debris dust | ~45% |
| Dusty outflow from a star–planet interaction or engulfment (cf. ZTF SLRN-2020; a flash would have to hide in the May–June 2018 ASAS-SN gap) | ~8% |
| Activity or event on an unresolved companion within 0.2″ | ~10% |
| Unrelated background object (AGN etc.) within 0.2″ | ~3% |
| Unexplained or instrumental | ~34% |

The instrumental share is low after the field test. Most of the residual is in "unexplained".

## Wording requirements

- Credit VarWISE (Paz et al. 2026) as the first catalogue of the variability, and note that it misclassifies the star as an LPV.
- Say "an infrared excess appeared". Do not say "the star lit up": there is no evidence the photosphere changed.
- Describe the temperature as "a two-band colour temperature of ~1000 K".
- "K dwarf, likely ≳100 Myr" needs lithium before any age claim.
- Do not state an 11-d rotation period.
- Do not write "TESS rules out dips". TESS is diluted ~5× and starts in 2019.
- No collision claim without spectra or mid-IR data.

## Decisive follow-ups

1. **Close the May–June 2018 optical gap and get a de-blended light curve:**
   - Gaia DR4 epoch photometry (to January 2020; due Dec 2026) resolves the 16″ neighbour;
   - ATLAS-South;
   - ASAS-SN g after 2018 with difference imaging.

   An optical flash means engulfment or merger; dips mean transiting dust; flat light means optically thin dust.
2. **Spectra:**
   - Li 6708 and Hα/Ca II for age and activity;
   - RV epochs for any companion;
   - a near-IR spectrum (or SPHEREx 0.75–5 µm, now public) for the excess shape and CO/H₂O.
3. **Mid-IR** (VISIR, or JWST MIRI): a 10-µm silicate feature would show small, freshly made grains; the 10–25 µm SED gives the dust mass.
4. **Optical monitoring** for ASASSN-21qj-like dips. Prediction: if the dust is orbiting at ~0.04 AU, any transiting structure recurs on ~3–10 d.
