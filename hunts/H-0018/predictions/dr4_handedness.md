# Handedness of Gaia DR4 astrometric orbits: seven forecasts

Author: claude (H-0018), 2026-11-06; revised the same day after the referee (`../reviews/claude-referee-2026-11-06.md`). **A draft
for sealing. NOT sealed.** It would be sealed by the commit that merges it into `main` before Gaia DR4 is released (2026-12-02,
~11:00 UTC). After that nothing may change except the adaptations below. Grader:
[`dr4_handedness_grade.py`](dr4_handedness_grade.py) (`--self-test` on DR3 passes). Hunt: [H-0018](../README.md).

Definitions as in the hunt: `sense = sign(BF − AG) × sign(ecliptic latitude)`, +1 being the sense of Earth's orbit. The *ratio* is
the N-weighted mean, over unit G bins in 12 ≤ G < 16, of median `parallax_error` for sense +1 over sense −1, type `Orbital`. `A` is
the mean of `sense` for `Orbital` + `AstroSpectroSB1`.

## The forecasts

Model: `scripts/chiral_sim.py --dr4` in the grader's statistic (`scripts/forecast_table.py`, `work/forecast_table.txt`), for the
two parent populations. DR3 is the data, from the grader's self-test. Probabilities are my judgement.

| | statement, on DR4 | DR3 data | DR4 model | P(TRUE) |
|---|---|---|---|---|
| **F1** | ratio at 340–390 d > 1.05 | 1.163 | 1.15, 1.16 | 0.75 |
| **F2** | ratio at 700–800 d exceeds the mean of 600–700 and 800–900 d by > 0.05 | 0.100 | 0.21, 0.13 | 0.70 |
| **F3** | ratio at 600–700 d and at 800–900 d both < 1.10 | 1.212, 1.187 | 1.07, 1.04; 1.03, 1.01 | 0.75 |
| **F4** | ratio at 1100–1600 d < 1.08 | 1.181 | 1.02, 1.01 | 0.70 |
| **F5** | A(340–390 d) < 0 by more than 3σ | −0.282 ± 0.027 | −0.10, −0.13 | 0.85 |
| **F6** | ratio at 700–800 d, e < 0.2 minus e ≥ 0.4, > 0.10 | 0.38 | 0.37, 0.19 | 0.80 |
| **F7** | for e < 5×10⁻⁴ at 600–900 d, \|ratio − 1\| < 0.10 | 1.001 | not modelled | 0.60 |

## What they test

- **F3, F4 are the only ones DR3 fails**, so they carry the risk. A longer baseline should narrow the feature around two years and
  remove the excess where DR3's span did not cover the orbit. A cause unrelated to baseline would leave these near 1.2.
- **F2, F6, F7** ask for the two-year structure the explanation depends on: a peak at two years, which falls with eccentricity, and
  which vanishes when e and T are held fixed. The referee found the last in DR3 after the fact, so this is the first prospective test.
- **F1, F5** are persistence checks. Almost any account of DR3 predicts them. They are here so a failure would be noticed.
- These forecasts do not separate the explanation from every alternative: a sidelobe of the observing window would also scale with
  baseline. F6 and F7 are what tell those apart.

## Rules

- Graded once, by the grader, on the first DR4 table of astrometric orbit solutions. Resolve by 2027-03-31.
- Allowed adaptations: renamed columns; solution-type names that mean the same thing, stated with the grade.
- If DR4 publishes no parallax error for orbit solutions, F1–F4, F6 and F7 are `ungradeable`. If it publishes no Thiele-Innes
  constants or equivalent signed orbit orientation, all seven are. F7 is `ungradeable` if DR4 does not fix e and T for near-circular
  solutions, or if a G bin needed for it has fewer than ten orbits of each sense throughout.
- A sense-blind change in Gaia's cuts does not void them. If DR4 documents that it fits orbit and parallax differently from DR3,
  they are graded and that fact is printed next to them.

## Known weak points

- **Stand-in scan law.** The 66-month law is not public. `--dr4` repeats the real 34-month law three years later, keeping the solar
  phase but with the wrong spin-axis phase.
- **Reversed precession is omitted.** DR4's span includes about 188 d of reversed precession. One check by the referee (300 stars,
  own sense, all G) moves 340–390 d from 1.19 to 1.11 and 700–800 d from 1.23 to 1.15; it leaves F3 and F4 alone. F1 and F2 lose margin.
- **Scale.** Model and data differ at DR3 by up to 0.06 at 340–390 d and more at 700–800 d, depending on the parent.
- **It is a Fisher calculation.** A real non-linear fit on simulated epochs agrees at the periods tried, but no full pipeline with a
  period search and acceleration models has been run (`gaiamock` or similar would be better before sealing).
- **Final read owed.** Check this revised text before it is sealed.
