# Referee report: OS-0012 (Gaia DR3 4482344869315388928), "the star with an invisible companion"

Referee: claude-referee, 2026-10-27. Referee claims: C11-C18. Call IDs refer to `ledger.jsonl` (my calls are K32-K77). Checks that used pandas on `data/*.parquet`, IRSA per-epoch ZTF metadata, a TESScut cutout, or my own eclipse model are marked as outside the tools.

## Verdict

**The anomaly does not survive. Do not announce.** The eclipses are real and on the target. But the period is wrong by a factor of five. The true period is **P = 11.900804 d** (T0 = MJD 57099.3619), and at that period there is a **secondary eclipse at phase 0.404, 0.42 mag deep in r and about 0.4 mag in W1**. Phase 0.404 is almost exactly 2/5. Folding at P/5 = 2.38016 d therefore stacks the secondary onto the primary, and the "phase 0.5" bin becomes empty quarter-orbits. The system is an uncatalogued, detached, mildly eccentric (e ≈ 0.15) K1V + K4V eclipsing binary. I would put the probability that the mundane explanation is correct above 99%.

## Attacks and results

1. **Period / aliases.** This is fatal to the claim (C11, C13; K37, K57-K68; per-cycle table from pandas).
   - At 2.38 d, 15 of the 40 cycles predicted to dip by more than 25% are flat (under 5%) in good ZTF data. Example: cycles 531 and 660, 129 cycles apart, at the same phase, one flat and one 0.9 mag deep. The claimed P = 2.380206 is also about 1 h off over the ZTF baseline; the best 2.38-d value is 2.3801607.
   - The flat cycles follow cycle number mod 5:
     - all 21 cycles ≡ 0 are deep;
     - all 21 cycles ≡ 1, 3 or 4 are flat;
     - cycles ≡ 2 show a shallower eclipse about 1.1 h late.
   - The case checked P/2, 2P and 3P, but not 5P. The `eclipse_period` score rewards "all deep points at one phase", which favours a subharmonic that merges two eclipses. With depth > 0.6 mag (primaries only) the same tool returns 11.9016 d (K64).
   - A V-template scan over 0.3-30 d prefers 2.38016 d over the 1 c/d aliases, P/2, 2P and 3P. That scan models one eclipse per period, so it cannot see the two-eclipse solution.
2. **Data artifacts.** None found (C17; IRSA metadata outside the tools).
   - In-eclipse and "missing" points have normal airmass, chi, sharp, limiting magnitude and zero-point RMS, and catflags = 0.
   - Both ZTF fields (537 and 1532) show the eclipse.
   - The in-eclipse centroid shift is under 0.02″.
   - Gaia caught the eclipse in both FOV transits of cycle 0 (0.87, then 0.19 mag 106 min later) and again at cycle 215.
3. **Blends.** Ruled out as the cause. Gaia (about 0.4″) sees the full 0.89-mag depth, and the ZTF centroid is stable. The nearest Gaia neighbours are 6.6 mag fainter at 7″. The G = 13.97 star 25.7″ away matters only for TESS: the fitted third light there is 0.68.
4. **"No secondary."** Wrong (C13). At 11.9 d the secondary is detected in every band:
   - ZTF r +0.35 mag (bin), g +0.33;
   - W1 +0.36 to +0.40, W2 +0.38 to +0.43;
   - TESS cycle 1427 (diluted).

   The phase-0.5 limits in C4 and C5 are correct numbers, but they measure the wrong place.
5. **Size and temperature (the crux)** (C14, C15; own model outside the tools).
   - The fit: eccentric two-sphere model with quadratic limb darkening, joint ZTF g/r + Gaia G + W1/W2 + TESS, reduced chi2 = 1.16 over 11,651 points.
   - Parameters: e cos ω = −0.1508, e ≈ 0.15, near-central, R2/R1 = 0.874, R1/a = 0.0304. Primary 5.0 h; secondary 5.0 h.
   - With M_tot = 1.4-1.7 Msun: a = 24.5-26.2 Rsun, so R1 = 0.75-0.80 Rsun and R2 = 0.65-0.70 Rsun.
   - Surface-brightness ratios: g 0.46, r 0.61, W1 0.88. These give T2 ≈ 4450-4720 K for T1 ≈ 5150 K.
   - C8 assumed a = 7.1 Rsun (P = 2.38 d), which forces an occulter of about 0.9 Rsun. At the true period, two normal K dwarfs reproduce both the depths and the durations.
   - The blue-deeper primary (C3) and the shallower W1 primary (C9) are what you expect when the hotter star is eclipsed by a cooler one.
6. **Is the "K dwarf" a composite?** Yes (C15).
   - Gaia's R = 1.07, L = 0.65 and log g 4.35 come from single-star fits. FLAME/GSP-Phot do not know it is binary, and DSC says "star" with 0.9999 probability.
   - The modelled pair gives L ≈ 0.56 Lsun, a single-star-equivalent R ≈ 1.0 Rsun, and about 0.4 mag of overluminosity.
   - StarHorse puts it about 0.7 mag above a single K0V (M_G0 = 4.89 at (BP−RP)0 = 0.86).
   - RUWE 1.05 is expected: the separation is about 0.12 AU, or 0.2 mas.
   - The Gaia RV is 39.1 ± 7.1 km/s from 10 transits, a large error for G_RVS = 13.2. This hints at line blending or orbital motion; it is not proof.
   - A hot-subdwarf or white-dwarf configuration is unnecessary and doesn't fit (two 5-h eclipses with comparable durations).
7. **Novelty** (C18; VizieR, SIMBAD and web outside the tools).
   - VSX: Type VAR, P = 0.025 d (a Gaia short-timescale artifact).
   - SIMBAD: a bare Gaia entry.
   - Absent from: ASAS-SN, ATLAS (J/AJ/156/241), ZTF Chen+2020, Gaia DR3 EB/classification/NSS, Prša+2022, and Kostov+2025 (only in its unvetted input table); LAMOST, APOGEE and RAVE also have no entries.
   - No papers found. It appears to be an uncatalogued eclipsing binary. That is a legitimate but routine VSX submission.
8. **TESS.** Sector 80 exists (TIC 399415572; the case's TESS fetch only requested pipeline light curves). It shows the 11.9-d pattern directly in consecutive cycles (C12).

## Most plausible mundane explanation remaining

A detached, eccentric (e ≈ 0.15, ω ≈ 180°) K1V + K4V eclipsing binary at about 515 pc with P = 11.9008 d. Probability above 99%. Nothing about it is anomalous.

## Required wording changes

- **Title, hook, summary:** retract "invisible companion", "gives off no light", "opaque disk" and the 2.380206-d period. Suggested summary: "An uncatalogued detached eclipsing binary of two K dwarfs, P = 11.9008 d, e ≈ 0.15. Primary 0.9 mag, secondary 0.4 mag at phase 0.404. An early fold at P/5 hid the secondary."
- **C2:** "The deep points phase up at 2.38016 d because the true period is 5× that (11.900804 d) and the secondary falls at phase 0.404 ≈ 2/5."
- **C4, C5:** retract; replace with C13.
- **C6:** keep as a methods note, but it no longer contrasts with anything.
- **C7:** add "the Gaia single-star parameters describe a composite of two K dwarfs".
- **C8, C9, C10:** retract (based on the wrong period).
- **H1, H4:** set status to refuted. Add an eclipse_companion (EB) hypothesis at high confidence.
- **Status:** anomaly → explained.

## Decisive follow-ups

1. **Spectroscopy:** two RV epochs near quadrature (phases about 0.2 and 0.7 of 11.9 d) should show a double-lined K+K spectrum with K1, K2 ≈ 50-60 km/s.
2. **Confirm the next eclipses** at the 11.9008-d ephemeris: primary at T0 + n·P, secondary at phase 0.4038.
3. **Tool fixes:** `fold` and the case checklist should test 3P, 4P and 5P and report "secondary anywhere", not only P/2 and 2P. The case fetch should include TESS FFI cutouts.
