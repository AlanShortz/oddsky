VERDICT: SEAL AFTER CHANGES

Forecasts, numbers and driver hold. The grader and several sealed sentences do not.

## Required changes

**Forecast and grader (permanent)**

1. **Grader.** NaN silently gives FALSE: one null `parallax_error` per period bin makes F1–F4, F6, F7 FALSE (tested). Line 29: add `& o.parallax_error.notna()`. In `grade`, print `UNGRADEABLE` for any NaN statistic. Rules: "Any statistic that cannot be computed makes that forecast ungradeable."
2. **Lines 4–5.** Sealed text would say "NOT sealed" forever. Replace "**A draft" through "UTC)." with: "Sealed by the commit that first adds this file to `main`, if that precedes Gaia DR4's release (2026-12-02)."
3. **Line 9.** `gaia_source.parallax_error` is a different solution. Append: "Period, eccentricity, `parallax_error` and Thiele-Innes constants come from the orbit table. G bins need ten orbits of each sense."
4. **Lines 44–45.** Delay is unhandled; a Thiele-Innes sign flip inverts eight verdicts (tested) with no permitted fix. Append to 44: "or four months after release if later." Line 45: "Allowed adaptations, stated with the grade: renamed columns; joining `gaia_source` for G and ecliptic latitude; converting an equivalent signed orientation or a documented sign-convention change to this definition; solution-type names that mean the same thing."
5. **Lines 47–48.** Replace with: "F7 is `ungradeable` if DR4's documentation or null `eccentricity_error` does not show e and T fixed for e < 5×10⁻⁴, or if no G bin has ten orbits of each sense."
6. **F7 row, line 16.** Fisher cell: "1.01–1.03 (DR3 span, no selection)". `sim_ko_Te`: 57 median transits, zero accepted orbits, no G bins, no script. P: 0.90; the rules remove the main failure path, and DR3 is 1.002 ± 0.025 (bootstrap). Line 16, append: "P(TRUE) is conditional on the forecast being gradeable."
7. **Line 30.** −0.05 is not "about twice" −0.01. Replace with: "In DR3 the cascade reached about 40% of the observed A overall and 53% at 600–900 d. Its DR4 run has 0.6% of 600–900 d orbits at margin < 1.5 (DR3 cascade 11%, DR3 data 21%), so −0.01 is unreliable if DR4 keeps the parallax cut: DR3's A ≈ −0.5 × (ratio − 1) with the model ratios gives −0.03 to −0.06, around F8's threshold."
8. **Line 35.** Contradicts the README's "about half". Replace that sentence with: "The cascade attributes about half the asymmetry above 1100 d to the choice between orbit and acceleration solutions, which matters less once the span covers the orbit. The other half is unexplained and alone would sit at F9's threshold."

**README and ASSUMPTIONS (same merge)**

9. **"35–75%" (README 14, 221; ASSUMPTIONS 28).** Replace with: "about 40% overall and 35–75% in the tabulated bins; other bins run from about 0 (450–500 d) to 120% (800–900 d), and the main run detects none above 1100 d".
10. **README 175; ASSUMPTIONS 31.** Replace with: "At ϖ 1–1.5 mas, −0.095 without the cut, −0.139 with it; over all 600–900 d, −0.053 and −0.065. The referee's observed-margin estimate gives the cut 80–90% of this zone; the cascade, with half the data's near-cut share, about 20%. Unresolved."
11. **README 179; ASSUMPTIONS 32.** Replace "symmetric (−0.006 ± 0.003)" with "nearly symmetric (−0.0059 ± 0.0012 by star bootstrap; −0.0080 ± 0.0010 past RUWE)".
12. **README 172; ASSUMPTIONS 34:** add "at 600–900 d". **README 5:** "listed, and tested where marked". **README 246, 303:** "No commit" is false (e162015).

## Other findings

- **Validity.** Prospective. Table and grader agree on bins, types, G range, e cuts, sign. F7 is near-identity; F1, F5 are persistence checks.
- **Driver correct.** Sign, parallax factor, column order, units match gaiamock. Midpoint tref, unsorted t and reflection's 180° scan flip are harmless. Mirrors share noise; fits get no truth. Current code reproduces stored rows for six stars.
- **Undisclosed, small.** No 10% transit rejection or G < 13 extra noise; 58 d gap.
- **Probabilities.** F1–F6 defensible; F5 fair (at N near 5000, −0.04 is borderline at 3σ). F8's 0.70 needs change 7. F9's 0.65 is high-side.
- **Recommended.** Publish the hash before 2 December; a private repo gives no third-party date.
- **First referee.** Applied, except 70–77% (see 10).

## Numbers checked

Self-test; all DR3, Fisher and cascade cells (F8 −0.010, F9 −0.004; looser −0.012, −0.005). README cascade, channel, long-period, e tables; variants; `knockout_Te`; literature credits.
