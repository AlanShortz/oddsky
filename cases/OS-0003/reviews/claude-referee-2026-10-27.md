# Referee report: OS-0003 (EE Cep), November 2025 eclipse depth

Referee: claude-referee, 2026-10-27. Referee claims: C13-C22. Call ids refer to `ledger.jsonl`. Where a check used pandas on `data/aavso.parquet` instead of a tool, it says so.

## Verdict

**The headline survives, with some wording that has to change.** The November 2025 eclipse was 1.44 ± 0.03 mag deep in V at minimum, about twice 2014's 0.70 *in magnitudes*. In blocked light it is 1.5x (73% vs 48%). The depth is robust to removing any single observer, including ATE. Two parts of the case are wrong: C5's colour ratios and C6's faintest-point depths for the visual era. Three are overstated: "agree to 0.03 mag", "lasted about as long", and novelty. The deep/shallow/deep history survives qualitatively but is already in the literature.

## What I checked

- **Observers** (K53, K78, K83; per-night table from pandas). ATE's 838 points miss the two deepest nights (MJD 60991-60993). On those nights eight other observers, each against their own baseline, give 1.44 (range 1.35-1.47, robust spread 0.02). On shared nights ATE agrees with the others to about 0.05 mag. C1's "0.03" is the scatter of each observer's single faintest point; the full range is 0.11.
- **Artifact / comparison stars** (K10, K78, K83, K101, K91, K92). ATE and DUBF observed both eclipses: 0.71-0.72 in 2014, and at least 1.35 / 1.44 in 2025. The 2025 baselines agree within 0.03 mag. Post-eclipse level minus pre-eclipse level is 0.01. B, V, I and visual data agree. **Not checkable here:** comparison-star IDs and transformed/untransformed flags, which the case data do not keep. The eclipse is grey, so a colour-term error is at most about 0.005 mag.
- **2014** (K55, K84, K87, K88). The minimum was not missed: it is flat-bottomed (0.65-0.71 over about 6 nights) with 1407 V points within ±3 d. Pienkowski et al. (2020) give 0.71 mag.
- **2020** (K102, K105, K106, K108). Flat at 0.45-0.5 mag for about 13 nights from three observers. A much deeper minimum would have to fit inside the −6..−2 d gap.
- **Colour** (K83, K85, K86, K89-K92). C5's ratios compare different nights. On the same nights the depths are B 1.49, V 1.44, I 1.23. Colour slopes dB/dV are 1.06 / 1.02 and dI/dV 0.84 / 0.91 for 2014 / 2025 (interstellar dust: 1.32 / 0.59). The eclipse is near-grey and behaves the same in both years.
- **Visual era** (K93-K99, K109). The faintest single estimate biases depth high: in 2014 the visual median is 0.70, but the faintest estimate is 1.0. Median depths over −7..+3 d: 1980 ≥0.6 (3 estimates), 1986 ~1.1 (3 estimates, one observer), 1992 ~1.15 (8), 1997 ~1.6 (22 estimates, 6 observers), 2003 ~0.55, 2009 ~0.45. Uncertainties are about ±0.2-0.3. A photometric V series from 1997 (observer CK) reaches 1.61-1.73 mag below the modern level. That level is stable to 0.01 across 2008-2025 (K110, K111).
- **Timing** (K102-K104, K108; bisectors from pandas). Because the eclipses are asymmetric, mid-eclipse moves by up to 4 d with the depth level used. 2014: 56889.9-56893.8. 2025: 60991.7-60993.2, matching the AAVSO prediction of JD 2460993. Two-cycle period: 2049-2052 d. **2020 was about 10 d early** (58929-58934 against about 58942 expected). The case does not mention this.
- **Shape and duration** (C19). Widths at 0.1 mag are 33 / 46 / 36 d for 2014 / 2020 / 2025, and 17 / 24 / 26 d at 0.3 mag. 2014 was flat-bottomed and 2025 V-shaped. C12's 1.5-2.1x ratio holds, peaking at the core.
- **TESS** (K107). No sector falls within about 380 d of any eclipse, so TESS is irrelevant.
- **Literature** (K82, plus a web search outside the tools). The tool returns only the titles of the 25 most recent SIMBAD references. Survey papers among them could cover EE Cep's recent eclipses. SIMBAD also lags, misses AAVSO alerts and forums, and only partly covers ATels and IBVS. The search found AAVSO Alert Notice 700 (2020, D. Kubicki, NCU Toruń, publication planned) and Campaign #894 (2025-26). Pienkowski et al. (2020) note depths of 0.5-2 mag, and that the published precession model predicted about 2.0 mag for 2014, which failed.

## Required wording changes

- **C1:** "1.44 mag at minimum (MJD 60991-60993): eight observers, each against their own baseline, range 1.35-1.47. ATE did not observe those nights." Drop the "838 points across the minimum" parenthetical.
- **C2 / summary:** "twice as deep in magnitudes; 73% vs 48% of the light blocked."
- **C3:** "≈0.5 mag, flat over 13 nights; a −6..−2 d gap leaves room for slightly deeper. 2020 came about 10 d early and was longer."
- **C4 / summary:** "similar outer duration (33 vs 36 d at 0.1 mag) but different shape: 2014 flat, 2025 V-shaped."
- **C5:** retract and replace with C15.
- **C6:** replace with C16's medians and their uncertainties.
- **C7:** "deep in 1992 and 1997 (1986 from one visual observer)". Note that this is previously reported.
- **C8 / summary "as expected for a precessing disk":** "qualitatively consistent with disk precession, an existing interpretation whose published model mispredicted 2014". Tilt alone is underdetermined, so downgrade to speculated.
- **C9 / summary "No refereed paper":** "No refereed paper on the 2020/2025 depths found in a SIMBAD title check and a brief web search. Both eclipses were professional-led AAVSO campaigns; this is an early independent measurement from public data, not a discovery."
- **H3:** keep it rejected, citing C13 and C21.

## Next checks for a professional

1. Get comparison-star and transformation metadata from AAVSO and redo the depth with transformed data only.
2. Ask the Toruń group (Campaign #894) whether a 2025 analysis is in press.
3. Fit the 2014 (flat) and 2025 (V-shaped) profiles together with a precessing inclined disk, including the early, long 2020 eclipse.
4. Replace the 1986 and 1992 visual depths with published photoelectric photometry.
5. Re-derive the ephemeris with timing errors, and test the 2031 P1 window against a −10 d shift.
