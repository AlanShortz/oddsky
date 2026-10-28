# Referee report: OS-0015 (Gaia DR3 4152421080966024704), "a red giant eclipsed every 386 days by something 80 suns wide"

Referee: claude-referee, 2026-10-27. Referee claims: C11-C20. Call IDs refer to `ledger.jsonl` (my calls are K39-K89). Checks that used pandas/scipy on `data/*.parquet`, IRSA per-epoch ZTF metadata, raw NEOWISE exposures, VizieR, SIMBAD or the Gaia archive are marked as outside the tools.

## Verdict

**The eclipses survive; the story around them does not.** Four consecutive full-depth (1.5-1.65 mag r, 1.8-2.2 g), reddening events on a strict 385.7-d ephemeris (O-C under 0.7 d) are on the target, in both ZTF programs, with clean metadata, constant neighbours and no alias that works. But the primary is not a red giant, the star is already in two variable-candidate catalogues, the "2023 ingress" is not on the ephemeris, the baseline is not flat, and the depth changes from orbit to orbit. Probability that a mundane explanation (artifact, blend, wrong period, random dust puffs) is correct: **about 5 per cent**. The title and summary as written are not defensible; see section 4.

## Attacks and results

1. **Period and aliases: survives** (C11, C12; K41-K49, K58-K63; template fit outside the tools).
   - `eclipse_period` at depth 0.5 (r+g) and 1.0 (r): 387.0 and 387.4 d, all deep points within 0.012 in phase.
   - P/2, 365.25 d, 182.6 d leave the odd cycles flat (0.06, -0.03, 0.04 mag vs 1.40, 0.43, 1.37). 2P and 3P put full-depth events at phase 0.51 and 0.67. The +/-1 c/yr aliases predict flat epochs that are deep.
   - The investigators missed the **fourth** full-depth event, cycle 1 (Aug 2020): g 18.18 on MJD 59086.2 (2.19 mag), r 16.34 on 59087.1, i 14.60 on 59084.2 (C12). Cycles 0-3 all eclipse; mid-times 58701.6, 59088.6, 59473.9, 59858.8; P = 385.69 d, T0 = 58702.2, O-C -0.6, +0.7, +0.3, -0.4 d.
   - Cycles -1, 5, 6 fall in ZTF gaps (no point within 8 d). Cycle 4 is under attack 4.
   - Shape: FWHM 7.9 d, 14 d wide at 0.05 mag, about 18 d of contact. Depths are **not** identical: g 2.19 (2020), >= 2.08 (2021), 1.84 (2022); r 1.64, 1.57, 1.5-1.8, 1.54 with a flat 4-d bottom in 2022.
2. **Instrument artifacts: none** (C14; K61-K66; IRSA metadata outside the tools).
   - 50 in-eclipse epochs, catflags 0: airmass 1.61 (quiet 1.63), limiting mag 20.6 (20.5), chi 0.94 (0.77), sharp 0.03 (-0.01), zero-point rms 0.022 (0.028); nightly scatter of 5-11 exposures 0.008-0.015 mag; centroid shift 0.06".
   - Both programs see it (2 in 2019-20, 1 in 2021-22). The catflags-rejected epochs (58698, 58702, 59085, 59086, 59470) lie on the same curve. All in-eclipse data are field 333 CCD 15; the 11 field-1376 points are out of eclipse, so no second field has confirmed it yet.
   - Neighbours at 8.2" (G 16.1), 17" (15.2) and 17.9" (13.8) are constant to 0.01-0.02 mag on every eclipse night and on the 2023 nights.
   - Events in Aug 2019, Aug 2020, Sep 2021, Oct 2022 advance 20 d/yr through the season. No seasonal systematic does that. H3 is dead.
3. **Blends: cannot cause it** (C15; K52; UKIDSS outside the tools). The 3.0" neighbour has 3.3 per cent of G and K = 16.1 against 9.9. Two UKIDSS K = 13.3-13.6 sources at 4.0-4.4" have no Gaia counterpart (embedded). Nothing in the PSF can remove 78 per cent of the r flux; dilution is under 5 per cent.
4. **"No X" claims** (C13, C16, C20; K43, K49, K61, K74-K78).
   - **"Fourth event caught in ingress" (C3): wrong.** The 2023 points (60251-60254, 0.22 -> 0.29 mag, still fading) are 7.3-10.3 d *after* the predicted minimum 60245.0, where cycles 0, 2, 3 were 0.07-0.28 mag deep and recovering. No ZTF point exists between dt = -12.7 and +7.3 d: the 2023 eclipse was never observed. The template fits neither at zero shift (chi2 10490, n 23) nor at +15 d (4744). Most likely the eclipse happened on time in the gap and 2023 had a longer or structured egress; it is not an ingress and does not confirm the ephemeris.
   - **"No secondary": holds at phase 0.5 only** (12 r, 9 g points; medians 0.05/0.10, maxima 0.09/0.14). Phases 0.25-0.45 are covered in one cycle, where a slow 0.13 (r) / 0.20 (g) dimming occurs at phase 0.33-0.41 (MJD 60750-60790, d(g)/d(r) = 1.7). Not a secondary, but an eccentric-orbit secondary away from 0.5 is untested.
   - **"Flat at 0.02 mag" (C1): wrong.** Out-of-eclipse nightly medians span 0.22 mag (g) and 0.17 (r); season medians drift 0.09 (g); out-of-eclipse g and r co-vary with slope 1.23. Gaia DR2 saw 0.22 mag in 2014-16 (hence the LPV flag); ATLAS 2015-17 rms 0.064.
   - Gaia DR2 epoch photometry (17 transits, MJD 56915-57505) misses cycle -4 (57158) by 56 d. No NEOWISE visit falls inside an eclipse (closest dt = +11.5 d). Earlier cycles are unconstrained.
5. **Physical self-consistency** (C18, C19; K43, K50, K51, K71, K72).
   - For M_tot = 1/2/3 Msun: a = 1.04/1.31/1.50 AU, v = 29/37/42 km/s, so 18 d of contact is a chord of 67/85/97 Rsun. **That chord is R_occulter + R_star**, which C9 and the title ignore.
   - The eclipse is chromatic (d(g)/d(r) = 1.30; g/i about 1.5), so a translucent cloud of tau_r ~ 1.5 covers the whole star: R_occ >= R_star. That needs a small primary, and the primary is small: at A_V = 3-4, M_G = +0.4 to -0.5; Gaia DR2 M_bol = 1.5 +/- 0.7; L ~ 20-100 Lsun, R <~ 10 Rsun. A 30-60 Rsun giant makes the geometry impossible. **"Red giant" is unsupported**; the SED (J-H 1.09, H-K 1.02, K-W1 1.6, W2-W3 3.0; SPICY Class II) and the environment (attack 6) say reddened intermediate-mass pre-main-sequence star, or at most a low-luminosity giant.
   - RUWE 1.81 (excess noise 0.29 mas, 19.6 sigma) matches a 0.4-mas photocentre wobble on a 1-AU orbit at 2.4 kpc: consistent with a binary, not proof.
   - Depth changes of 0.2-0.4 mag per orbit mean a clumpy, evolving dust structure, not a rigid opaque disk.
   - NEOWISE W1/W2 are 0.09-0.12 mag brighter within 60 d of eclipse phase than at phase 0.55-0.75 in both parities; with two visits a year and a secular W1 fade this is a lead, not a result.
6. **Novelty: partly false** (C17; K70; VizieR/SIMBAD outside the tools).
   - **ATLAS Heinze+2018** lists ATOID J275.2295-13.6792 (0.23"), class "dubious", long-period fit 406.8 d, 0.15 mag. **Gaia DR2** lists it as an LPV candidate. Neither reports eclipses. SIMBAD: "AB?" (AGB candidate, Robitaille+2008). Not in VSX (46" to nearest), ASAS-SN, ZTF Chen+2020, Gaia DR3 vari, Marton+2019.
   - **IRAS 18180-1342 lies 4.3" away**, an intermediate-mass star-forming region (Arvidsson+2010; Lundquist+2014, 2015); two YSO candidates at 17-18", molecular cloud SDG G17.308+0.392 at 28". W3/W4 may be partly nebular.
7. **Untapped data.** ATLAS forced photometry (2015-2026) is still pending; Heinze's 2015-17 data span cycle -3 (June 2016), so ATLAS can test the ephemeris backwards and cover the 2024-2025 cycles ZTF missed. ASAS-SN g (2018+) could show 2019-2022 diluted. No TESS 2-min data; FFI cutouts not tried.

## Most plausible mundane explanation remaining

None of the mundane ones work. What remains is a reinterpretation: a reddened young or weakly evolved star (L ~ 20-100 Lsun) in the IRAS 18180-1342 star-forming region, occulted every 385.7 d by a dust clump or warped-disk segment carried by a companion on a 1.0-1.5 AU orbit, with a column that changes between orbits. That is H2 (KH 15D-like) at least as much as H1. The strict period over four cycles kills H4 (dust puffs) and H3 (artifact).

## Required wording changes

- **Title:** retract "red giant" and "80 suns wide". Suggested: "A dust-enshrouded star in a star-forming region goes dark for a week every 385.7 days".
- **Hook and summary:** "three eclipses + a 2023 ingress" -> "four full-depth eclipses in four consecutive cycles (2019-2022); later eclipses fell in gaps". "Flat for years" -> "steady to 0.1-0.2 mag". "Not previously catalogued as variable" -> "a dubious ATLAS variable and Gaia DR2 LPV candidate; the eclipses were never reported". Drop or qualify "ZTF, Gaia and VSX had all missed it because each eclipse lasts 4 per cent of the orbit" (DR2 never sampled an eclipse).
- **C1:** -> "14.76 +/- 0.03 per night with 0.1-0.2 mag season-to-season and multi-week excursions (C20)".
- **C2:** add the 2020 event (C12); note the 2022 event is 0.35 mag shallower in g and flat-bottomed.
- **C3:** retract "caught in ingress"; use C13's wording.
- **C4:** keep; state P = 385.7 +/- 0.5 d, T0 = 58702.2 from four cycles.
- **C6, C10:** "no secondary deeper than 0.1 mag within +/-8 d of phase 0.5; phases 0.25-0.45 covered in one cycle (C16)". Remove "even and odd cycles identical" (C18).
- **C7:** add the IRAS source, SPICY Class II, the UKIDSS 4" companions.
- **C8:** replace "VSX has no entry" with C17.
- **C9:** retract "far larger than any star" and "60-100 Rsun occulter"; replace with C18's chord statement and the requirement R_star <~ 10 Rsun.
- **H1:** live, 0.4, without "opaque" and "red giant". **H2:** 0.4. **H3:** rejected (C14). **H4:** rejected (C11).
- **Predictions:** P1's window brackets my 61787.7; keep. P2 is only at risk if the 0.2-mag wandering worsens; keep.
- **Ladder:** stay at **anomaly**; "reproduced" only when ATLAS shows the same eclipse on the same ephemeris.

## Decisive follow-ups

1. **ATLAS forced photometry** (queued): June 2016 (cycle -3, MJD 57544 +/- 3), 2019-2022, and above all November 2024 (60629 +/- 3) and December 2025 (61015 +/- 3) when ZTF was blind. Two more on-time events settle the period; a missed one kills it.
2. **One spectrum** out of eclipse: giant vs pre-main-sequence (Li, H-alpha, CO bands, gravity). It fixes R_star, hence the occulter size, and decides the title.
3. NEOWISE through 2024, folded with the trend removed (K71/K72 lead).

## Tool fixes

- `find_excursions` missed a 2.2-mag single-night event (59086): single deep nights must be listed.
- The ZTF fetch should keep `catflags = 32768` rows as flagged rather than drop them (five more in-eclipse epochs and the i-band eclipse point).
- `fold` should report per-cycle depth and mid-time; "even and odd identical" was read off max_delta.
- `skeptic_report` passed "onset seen" for a dip whose predicted minimum lies in a data gap; it should check the ephemeris, not just the gap.
- The novelty check must query ATLAS (J/AJ/156/241), Gaia DR2 LPV (I/345/lpv) and SIMBAD otype, not VSX alone; `case_overview` should surface the SIMBAD otype and nearby IRAS/YSO entries.
