# Handedness of Gaia DR4 astrometric orbits: nine forecasts

Author: claude (H-0018), 2026-11-06; revised after the referee (`../reviews/claude-referee-2026-11-06.md`), an assumption audit
(`../ASSUMPTIONS.md`) and a blind pipeline run. Sealed by the merge that first brings this file into `main`, if that precedes Gaia DR4's release (2026-12-02); a final referee read it first
(`../reviews/claude-referee-final-2026-11-06.md`). After that nothing may change except the adaptations below. Grader:
[`dr4_handedness_grade.py`](dr4_handedness_grade.py) (`--self-test` on DR3 passes). Hunt: [H-0018](../README.md).

Definitions as in the hunt: `sense = sign(BF − AG) × sign(ecliptic latitude)`, +1 being the sense of Earth's orbit. The *ratio* is
the N-weighted mean, over unit G bins in 12 ≤ G < 16, of median `parallax_error` for sense +1 over sense −1, type `Orbital`. `A` is
the mean of `sense` for `Orbital` + `AstroSpectroSB1`. Period, eccentricity, `parallax_error` and Thiele-Innes constants come from the orbit table. G bins need ten orbits of each sense.

## The forecasts

Models, for a 66-month span: **Fisher** is `scripts/chiral_sim.py --dr4` in the grader's statistic, for two parents (`work/forecast_table.txt`).
**Cascade** is `gaiamock`'s blind pipeline with reversed precession included, under DR3's cuts and, in brackets, looser ones (a₀/σ > 15, ϖ/σ > 5,
`work/gm_dr4.txt`). DR4's real cuts are not published. Probabilities are my judgement, and P(TRUE) is conditional on the forecast being gradeable.

| | statement, on DR4 | DR3 data | Fisher | Cascade | P(TRUE) |
|---|---|---|---|---|---|
| **F1** | ratio at 340–390 d > 1.05 | 1.163 | 1.15, 1.16 | 1.14 (1.25) | 0.80 |
| **F2** | ratio at 700–800 d exceeds the mean of 600–700 and 800–900 d by > 0.05 | 0.101 | 0.21, 0.13 | 0.14 (0.16) | 0.75 |
| **F3** | ratio at 600–700 d and at 800–900 d both < 1.10 | 1.212, 1.187 | 1.07, 1.04; 1.03, 1.01 | 1.03, 1.01 (1.03, 1.02) | 0.75 |
| **F4** | ratio at 1100–1600 d < 1.08 | 1.181 | 1.02, 1.01 | 1.01 (1.01) | 0.75 |
| **F5** | A(340–390 d) < 0 by more than 3σ | −0.282 ± 0.027 | −0.10, −0.13 | −0.12 ± 0.03 (−0.04 ± 0.03) | 0.70 |
| **F6** | ratio at 700–800 d, e < 0.2 minus e ≥ 0.4, > 0.10 | 0.38 | 0.37, 0.19 | 0.17 | 0.75 |
| **F7** | for e < 5×10⁻⁴ at 600–900 d, \|ratio − 1\| < 0.10 | 1.001 | 1.01–1.03 (DR3 span, no selection) | not modelled | 0.90 |
| **F8** | A(600–900 d) > −0.05 | −0.122 | | −0.01 (−0.01) | 0.55 |
| **F9** | A(1100–3000 d) > −0.03 | −0.064 | | −0.00 (−0.01) | 0.55 |

In DR3 the cascade reached about 40% of the observed A overall and 53% at 600–900 d. Its DR4 run has 0.6% of 600–900 d orbits at margin < 1.5 (DR3 cascade 11%, DR3 data 21%), so −0.01 is unreliable if DR4 keeps the parallax cut: DR3's A ≈ −0.5 × (ratio − 1) with the model ratios gives −0.03 to −0.06, around F8's threshold.

## What they test

- **F3, F4, F8, F9 are the ones DR3 fails**, so they carry the risk. A longer baseline should narrow the features around one and two years and remove the excess
  where DR3's span did not cover the orbit. The cascade attributes about half the asymmetry above 1100 d to the choice between orbit and acceleration solutions, which matters less
  once the span covers the orbit. The other half is unexplained and alone would sit at F9's threshold. A cause unrelated to baseline would leave these near their DR3 values.
- **F2, F6, F7** ask for the two-year structure the explanation depends on: a peak at two years, which falls with eccentricity and vanishes with e and T fixed. F7 is close to
  an identity if DR4 conditions the covariance as DR3 did, so it mainly tests that the two-year term enters through those parameters.
- **F1, F5** are persistence checks, which almost any account of DR3 predicts. F5 could fail if DR4 relaxes the parallax cut: the cascade's value falls to −0.04 under looser cuts.
- These do not separate the explanation from every alternative: a sidelobe of the observing window would also scale with baseline. F6 and F7 are what tell those apart.

## Rules

- Graded once, by the grader, on the first DR4 table of astrometric orbit solutions. Resolve by 2027-03-31, or four months after release if later.
- Allowed adaptations, stated with the grade: renamed columns; joining `gaia_source` for G and ecliptic latitude; converting an equivalent signed orientation or a documented sign-convention change to this definition; solution-type names that mean the same thing.
- Any statistic that cannot be computed makes that forecast ungradeable.
- Only types `Orbital` and `AstroSpectroSB1` count; `OrbitalPoorlyConstrained`, new in DR4's data model, does not. If DR4 publishes no parallax error for orbit solutions, F1–F4, F6 and F7 are `ungradeable`. If it publishes no Thiele-Innes
  constants or equivalent signed orbit orientation, all nine are. F7 is `ungradeable` if DR4's documentation or null `eccentricity_error` does not show e and T fixed for e < 5×10⁻⁴, or if no G bin has ten orbits of each sense.
- A sense-blind change in Gaia's cuts does not void them. If DR4 documents that it fits orbit and parallax differently from DR3,
  they are graded and that fact is printed next to them.

## Known weak points

- **DR4's cuts are unknown.** The draft data model keeps `parallax_error`, the Thiele-Innes constants and pseudo-circular marking, and lists 5.9 M `nss_two_body_orbit` rows, far more than
  DR3's 443,205, so the cuts may have changed. The ratio forecasts depend less on them than F5, F8 and F9 do.
- **Stand-in scan law.** The 66-month law is not public. The real 34-month law repeated three years later keeps the solar phase but has the wrong spin-axis phase. On DR3, repeating the first
  year changes ratios by 0.03 or less, except 0.05 at half a year. Reversed precession is approximated by reflecting the last 188 d (the cascade includes it; the Fisher column does not).
- **Scale.** The two-year ratio depends on the eccentricity distribution (1.21–1.52 on DR3), and model and data differ at DR3 by up to about 0.1.
- **`gaiamock` is a model of Gaia's pipeline**, not the pipeline. DR4's may also differ from DR3's. My driver omits gaiamock's 10% transit rejection and its extra noise at G < 13, the stand-in has a 58 d gap, and I did not test its `skip_acceleration=True` option, which could move F9.
