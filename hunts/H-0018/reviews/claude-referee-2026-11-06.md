# H-0018 referee report, 2026-11-06

Scratch scripts and outputs are in `/tmp/ref_h18/`. These are my own scripts (pandas on the hunt's data), not Oddsky tools. `final.py --heldout` rerun from a scratch copy matches `work/final_heldout.txt` byte for byte. `controls.py` reproduces every control number in the README.

## 1. Verdict

No headline falls: the signs are right, the handedness is real and instrumental, and Gaia's own pseudo-circular solutions support the two-year explanation better than anything in the dossier. Several supporting statements are wrong or overclaimed, the parallax-cut explanation stops working above about 1100 d, and F1 in the forecast rests on the wrong model number, so neither the dossier nor the forecast should leave or be sealed as written.

| headline | P(materially wrong) |
|---|---|
| Limit, \|⟨L̂_Z⟩\| < 1.9% | 10% |
| DR3 handedness is real and instrumental | 3% |
| The explanation (free P, T, e plus the parallax cut) | 20% overall: about 10% at 1 and 2 yr; for P > 1100 d the cut is already shown not to be the cause |

## 2. Attacks and results

### Attack 1. Sign conventions: survives, now tested against outside data

- **Algebra.** With Gaia's definitions (Δα* = BX + GY, Δδ = AX + FY), (r × v)·n_out = BF − AG = −a₀² cos i. E × N is outward, so `sign(BF − AG)` is L·n.
- **Known orbits (new).** I cross-matched the Sixth Orbit Catalog to the NSS table. i > 90° should give y = +1.
  - Gaia period 0.7–1.4× the ORB6 period: 131 of 143 agree.
  - ORB6 period differing from Gaia's by more than 1%, and |i − 90°| > 10°: **61 of 63 agree** (p = 4e-16).
- **Earth sense.** The apparent parallactic offset is −ϖ r_E⊥, which turns with Earth, so L is along +NEP. Earth-sense maps to sense = +1 and a deficit to A < 0. This is correct.
- **Simulator.** `sense` is defined identically in `chiral_sim` and `nss_rv_test`. The parallax factors are standard. T0 is right: t runs 1666.44–2704.37, which is 2014-07-25 onward.
- **ψ.** The heading computed from successive scan points minus `scan_angle` has median 6e-5° and 1–99% range ±0.64°. The mirrored convention spreads over ±174°. So north-through-east is right, and along-scan = Δα* sin ψ + Δδ cos ψ.
- **Empirical sign.** The Oort control validates the wide-pair pipeline: D_Z < 0 with B < 0.

**Bug found: C and H are in au, not mas.** P·Q orthogonality has median |cos| 0.227 with raw C, H and 0.057 with C, H × ϖ. `final.py` line 180 and `nss_dev.py` mix the units.
- Published ⟨L̂⟩ = (−0.11, −1.43, −0.84)%.
- Corrected ⟨L̂⟩ = **(+0.11 ± 0.38, −1.50 ± 0.37, −0.51 ± 0.38)%**, with predicted Z −0.87%.
- The conclusion in the dossier stands, but the numbers must change.

### Attack 2. Forward model: correct; T1 has no discriminating power and uses the wrong selection

- **Derivatives.** Analytic T, ν and e columns match finite differences to 1e-9 (40 stars × 40 orbits). Normal-equation and QR ratios agree to 6e-11. **The ratio ≠ 1 is not a numerical artefact.**
- **"All three fixed gives ratio 1" is an identity.** The columns cpX, spX, cpY, spY contain no F or G. It is not a finding and should not be presented as one.
- **Knockout wording is partly wrong.**
  - 340–390 d: all free 1.408; P fixed still 1.209; T fixed 1.261; e fixed 1.285.
  - 700–745 d: T fixed (1.09–1.10) kills the peak as much as e fixed (1.09–1.10).
  - "One-year needs P" holds on the shoulders, not at the peak. "Two-year needs e" should be "needs e and T".
- **T1 is uninformative.**
  - A plain step at P > 300 d gives r = 0.822, higher than the model's 0.809.
  - Dev gave r = 0.792, a fail. Adding noise from the quoted ratio errors gives P(r ≥ 0.8) = 0.45. The pass is a coin flip.
  - Binnings give r = 0.695–0.857.
  - Leave-one-out: dropping 340–390 d gives 0.909.
- **T1 compares different selections.** `freeze_prediction.py` takes medians over "accepted in either sense". The data accept each sense on its own. With own-sense selection and G binning (not frozen, so exploratory):
  - r = 0.934 (0.78–0.98 across binnings).
  - **Model at 340–390 d = 1.226, not 1.468.**
  - The listed unexplained "overshoot, 1.47 against 1.15" is mostly this artefact: 1.226 against 1.154 ± 0.060 is 1.2σ.
- **A_model is noisy.** N_model is 108 at 340–390 d (se 0.10) and 167 at 50–100 d (se 0.08). With `sim_field2`, T2 gives ρ = 0.899.
- **Freezing.**
  - Hashes match for `final.py`, `handedness.py`, `wb.py`, `nss_rv_test.py`, `freeze_prediction.py` and `sim_prediction.csv`.
  - **`chiral_sim.py` does not match** (recorded 4e287a, now 3d403f, edited 01:45:57 after the opening; undisclosed). The change looks like `--fix`/`--dr4` only, but without a commit that cannot be shown.
  - Held-out and dev are random splits of one catalogue: dev-held correlation is 0.876 for the ratio and 0.935 for A. Held-out replication shows the pattern is not noise. It does not make a model built while viewing dev "predictive" in any strong sense.
  - PREREGISTRATION line 3 ("no row had been read") conflicts with the README's admission of a printed partial row.

**The natural experiment, new and the strongest result in the hunt.** Halbwachs+ 2023 §5.2: orbits with e < 0.0005 were "pseudo-circularised". "e and T0 are fixed", with the covariance "recalculated for the 10 selected unknowns". Gaia's own published errors therefore contain a knockout of e and T. Orbital, 12 ≤ G < 16:

| period (d) | ratio, e < 5e-4 | ratio, 6e-3 ≤ e < 0.05 |
|---|---|---|
| 600–700 | 1.034 ± 0.040 | 1.336 ± 0.049 |
| 700–800 | **1.008 ± 0.045** | **1.652 ± 0.096** |
| 800–900 | 1.020 ± 0.076 | 1.397 ± 0.071 |
| 900–1100 | 0.917 ± 0.083 | 1.256 ± 0.047 |

- Median σ_ϖ at 700–800 d: sense +1 falls from 0.0322 to 0.0205; sense −1 only from 0.0211 to 0.0199.
- A follows: **600–900 d A = −0.01 ± 0.04 (N = 682) against −0.30 (N = 1113).** A narrower cut, 650–850 d, gives −0.08 ± 0.05, with dev and held-out differing (+0.19, −0.17).
- Controls at 450–600 d show no such step (1.08 against 1.07), as the model's knockout predicts (1.08–1.12 all free, 1.07–1.08 e fixed).
- This is post hoc and fit-selected (e < 0.0005 is an outcome of the fit), but neither the model nor the investigators used it.

### Attack 3. The channel: holds below about 1000 d, fails above

- **Halbwachs cuts are stated correctly:** Eq. 16 ϖ/σ = 20000/P, s > max(5, 158/√P), σ_e < 0.079 ln P − 0.244. Table 1 also has F2 < 25, which the model omits.
- **`Orbital`:** hard edges. Min margin 1.000 for both cuts; RUWE ≥ 1.400.
- **`AstroSpectroSB1` is not alike.** Table 1's footnote says these conditions "do not apply" to main-processing solutions confirmed by SB1. In the data 0.30% fall below the parallax line and 1.49% below the a₀ line. T5 by type is the same anyway (−0.314 ± 0.030 against −0.330 ± 0.009 at margin < 1.5).
- **T5's trivial reading fails, which is good for T5.**
  - Low margin means low parallax, but at 200–300 d, where the ratio is 1, A is −0.001 ± 0.014 at margin < 1.5.
  - At fixed m_ref, A does not fall with a₀ margin (−0.20, −0.31, −0.37, −0.30). At fixed a₀ margin it does fall with m_ref. So the parallax cut, not the a₀ cut.
- **Mechanism against ecliptic latitude.** The 600–900 d ratio rises 1.01 to 1.35 from |sin β| < 0.1 to > 0.85, and A goes from +0.03 ± 0.02 to −0.15. A stays flat above |sin β| = 0.25 because the low-margin share falls (0.41 to 0.30).
- **Channel size (exploratory).** Identity: N₊(1 − L₊) = N₋(1 − L₋), where L is the fraction lost when an observed orbit's margin is mirrored with the model's own-sense r distribution. It needs no parent population. Share of the observed `Orbital` deficit reproduced, without and with conditioning on e and |sin β|:

| zone | share reproduced |
|---|---|
| 300–450 d | 86–91% (340–390 d: −0.315 against −0.333) |
| 450–600 d | 53–56% |
| 600–900 d | 80–90% |
| 900–1100 d | 56–61% |
| > 1100 d | 10% |
| all > 300 d | 70–77% |

  So "the model explains about half at 600–900 d" reflects the model's parent margins, not the mechanism. The model has 9.5% of orbits at margin < 1.5, the data 20.8%. Its σ_ϖ is low by a factor of 1.0–1.43, and it has 57 transits against 46 matched.

  Caveat: the estimator uses the observed margins. It shows the asymmetry is confined to within r of the cut. A false population piled up at the cut would pass it too.

- **Above 1100 d the parallax cut is not the channel.**
  - Observed minimum ϖ/σ exceeds the cut: 15.7 against 12.5 at 1300–1600 d, 14.9 against 10 at 1600–2000 d, 26.5 against 6.7 at 2000–3000 d.
  - A does not fade with margin: m_ref 5–10 gives −0.092 ± 0.025.
  - Orbital A at P > 1100 d is about −0.08 (N = 6285). Adding the a₀ route reaches only about 20% of it.
  - Likely a pipeline step the model lacks, such as the acceleration-orbit cascade. Untested.
  - Also unexplained: 450–600 d about half, and A = +0.11 ± 0.03 at 600–900 d, e 0.7–0.8 (channel −0.01 to +0.03).
- **A rises strongly with circularity.** 600–900 d: A = −0.26 at e < 0.1, −0.11 at 0.3–0.4, 0.00 at 0.6–0.7. The channel predicts −0.19, −0.12, −0.03. The dossier does not use this.

### Attack 4. Are they fake? No evidence of it; G > 13 is still not settled by RV

- **T3 reach.** It covers 14.5% of the zone's orbits and **8.8% of the 600–900 d excess**, with G 95th percentile 12.9. Its A is −0.08 against −0.12 overall.
- **New, T3 at low margin.** Margin < 1.5: A = −0.245, RV-variable 0.803 ± 0.023 and 0.802 ± 0.018. The full-fake prediction is 0.49.
- **New, independent of T3: RV-confirmed orbits show the same effect.** `AstroSpectroSB1` has an SB1 orbit behind it:
  - 300–450 d A = −0.121 ± 0.017
  - 600–900 d −0.077 ± 0.011
  - margin < 1.5 −0.314 ± 0.030
  - 50–100 d +0.118 ± 0.041 and 150–200 d +0.080 ± 0.023 (so these too are real)
  - Median G is 11.6, so this is also a bright-star result.
- **Spurious proxies, 600–900 d.**
  - A does not concentrate at high mass function, where fakes live. At margin < 1.5, f_M 0.3–0.5 gives −0.23 against −0.33 at 0.03–0.1.
  - A falls with `ipd_gof_harmonic_amplitude` (−0.35, −0.30, −0.15), the opposite of partial-resolution fakes.
  - G ≥ 15, margin < 1.5 (N = 2417, A = −0.43): f_M > 0.3 is 1.0% for sense + and 0.6% for sense −; RUWE KS p = 0.98; f_M medians 0.061 and 0.069 (KS p = 2e-4), but KS p = 0.5 at fixed e < 0.3.
  - AEN/a₀ differs by sense at faint G (0.465, 0.507), but also at G < 13, where RV is good (0.509, 0.541). So it is not a fake signature.
- **The pseudo-circular result** (Attack 2) reaches G 16 and removes the asymmetry when e and T are fixed.
- **Caution the dossier omits.** Halbwachs introduced the parallax cut to remove false solutions, so near-cut faint orbits are where fakes would be. The evidence above is indirect at G > 13.
- **Amplitude does not prove "sizes are right".** amp/2K_pred by K_pred: 1.98 (2–5 km/s), 1.45 (5–10), 1.10 (10–20), 0.67 (> 20). Spearman 0.42–0.44. It shows the same by sense, nothing more. K_pred is also a photocentre lower limit.

**No mundane explanation of the handedness remains.** Ecliptic longitude is flat (−0.11 to −0.14) and the ecliptic hemispheres mirror each other (y = −0.123, +0.121).

**The 20° offset is mostly explained, by something other than what the README implies.** A pure ecliptic pattern on the real sky gives only 5.5–6.2°. Letting A vary with |b| gives **19.7°**. Most of this is through margin: the share at margin < 1.5 is 0.29, 0.21, 0.12 for |b| < 10, 10–30, > 30, and at fixed margin A barely changes. A residual in Galactic X remains, −1.9 ± 0.5%.

**T4 did not remove the ecliptic pattern.** Its full fit is D = (−1.14 ± 0.54, **−5.97 ± 1.03**, −0.11 ± 0.83)%. With period × |sin β| nuisance terms, D_Z = −1.2 ± 3.4%. With period, margin, |sin β| and |b| terms fixed from the data, the residual Z is −0.5 ± 0.65%. The null stands; the ±0.83 and the phrase "pattern removed" do not.

### Attack 5. Wide-pair limit: stands; "conservative" is not earned

- **Arithmetic.** D = (3/2)⟨L̂⟩ for a dipole is correct (Funk-Hecke, l = 1). All limits reproduce. The prograde sign is correct: L = r × v = (−R₀x̂) × (Vŷ) is along −Z.
- **The "Kepler mock" is not one.** `controls.py` lines 40–54 use z = (L·n) × a lognormal, with noise 0.25, no orbit and no catalogue errors. This breaches prereg control 2.
- **My mock** (real pairs, real errors, thermal e, projected separation matched): gain **1.87–1.90**, 1.69–2.05 by bin. Real pairs pass the cut 1.09–1.23× as often as Kepler pairs. 13% of selected pairs exceed √2 v_c. That dilution gives an effective gain of about 1.5–1.75, so the (2/3) factor is roughly right, not clearly conservative. The 1.9% stands.
- **Frame spin is real and much larger than the test implies (new).** Regressing y on the bright-to-faint separation vector gives S = (+6.35 ± 0.56, +8.31 ± 0.60, +0.36 ± 0.62)% in ICRS, and (+16.7, +31.2, −1.4)% for pairs straddling G = 13. The random-order control gives (−0.37, +0.71, −0.39)%. **D_Z moves only from −1.56 to −1.55**, because ŝ ⟂ n. So the systematic dilutes but does not fake a dipole. The README's row (−2.4 ± 1.5 against −1.4 ± 0.8) has no power and should be replaced.
- **The hint.** chi²(3) for D = 0 has **p = 0.115**. Dev is −0.41 ± 1.05. Z is one of three components, and the 15 cells are a further look-elsewhere. The latitude bands look more like a step than sin b. The |z|/σ ≥ 5 bins give −0.55 and −0.92. Near −0.7 ± 0.9, far −2.8 ± 1.1. "Hint" overstates it.
- **Oort.** Sign as expected.
  - The factor 0.80 is close: empirical 2f(0), n_Z²-weighted, is 0.0209 against 0.0222 per km/s. Kurtosis after the ±100 km/s clip is about 0. It moves B by 6%.
  - A constant term exists from solar reflex. D_Z = a + b r gives a = −1.70 ± 0.73% raw, −0.30 ± 0.73% after subtracting the fitted solar motion.
  - The slope then gives B = −11.2 ± 1.6 km/s/kpc.
  - ±0.4 is far too small. A new random draw moves the top bin from −5.90 to −6.24.
  - A D_Y of about −1% remains, not growing with r and unexplained. It affects only this control.
  - Published: Bovy 2017 B = −11.9 ± 0.4; Li+ 2019 B = −13.4 ± 0.1. "About −12" is fair.
- **Injection.** The 5% run is a linearity check by label flipping, on dev, not the registered 0.5%. The README's blanket "fixed in the preregistration" does not cover this substitution.

### Attack 6. Novelty: search result stands; one attribution is wrong

- **Searched:** ADS, about 45 title, abstract and full-text queries, 2018–2026 (sense, clockwise, prograde, ecliptic, cos i, hemisphere, parallax, Thiele-Innes, orbital pole, Galactic dipole); the 7 papers citing Butkevich 2018; web searches. **No measurement of A, of sense-dependent parallax errors, or of a percent-level Galactic dipole in binaries was found.** Arenou+ 2023 full text mentions the ecliptic only for sky excess at high latitude.
- **Not read:** Perryman 2026 (Phys. Rep. 1150) and Lammers+ 2026 (uses `gaiamock`, mentions the ecliptic) matched full-text queries and should be read. Yahalomi+ 2026 (arXiv 2611.06915): abstract only, no mention.
- **Add to the note:** Makarov 2025 (ApJL 981, L23), face-on deficit from Thiele-Innes mathematics.
- **Butkevich 2018 quotes are verbatim.** The published sentence begins "However, for iE > 90°". The second quote is "the host star and Earth revolve in the same direction, if iE < π/2".
- **Attribution problem.** His "χ² statistic for parallax estimation" is a parallax-only fit with no orbit fit. It concerns detectability and parallax bias, not σ_ϖ in a 12-parameter fit. A linear orbit fit cannot carry the sense, as the README itself says. So the README's mechanism is **not** Butkevich's. His is closer to the model's RUWE channel.
- **His abstract says no effect on detectability for e ≳ 0.5.** The data at 340–390 d give A = −0.31 at e 0.4–0.6 and −0.15 at e ≥ 0.6.
- **Consequence:** the two-year finding and the pseudo-circular result appear more original than the README states.

### Attack 7. Numbers, labels, forecast

**All other README numbers I checked agree with `work/` or my rerun.** Those include 77,470/90,595, A values, the wide-pair table, T1–T5, D, 20°, 79°, 24σ, 1,817,594, the 2.7 factor and 26 days.

**Mismatches:**

| line | README | finding |
|---|---|---|
| 110–111 | ⟨L̂⟩ values | wrong units (see Attack 1) |
| 143 | e table 1.42, 1.37, 1.14, 1.08 | no script or output in `work/`. Registered definition, all data: 1.51, 1.41, 1.15, 1.10. Without G bins: 1.42, 1.37, 1.14, 1.06. "1.08" not reproduced. The model's first bin is 1.92, so "as in the model" holds only in shape |
| 158 | +0.20 at 72–100 d | +0.21 (0.2106). Model +0.006 has se 0.08 (`sim_field2` +0.02), so about 2σ |
| 156–157 | one-year overshoot listed as unexplained | definitional (see Attack 2) |
| 197 | margin ≥ 5 "nearly free" | true at 600–900 d. 300–450 d gives about −0.1, and 1100–3000 d gives −0.092 |
| 198 | "up to about 30%" | subsets reach 46–65% (\|sin β\| > 0.85: 1.46; low e: 1.65) |

**Reproduce block:** omits `sim_field2`, knockout, explore and the e table. `controls.py` has no output in `work/`.

**Labels:** exploratory marks are correct where present. Unmarked: the injection substitution, the mock, the Oort factor derivation.

**Forecast.** Its DR3 column is correct to all digits, and the self-test passes. The `--dr3` path also runs, though the self-test does not cover it.

- **Wrong statistic in the "model" column.** It uses either-sense selection without G bins, while the grader uses own-sense selection with G bins. With the grader's statistic:

| | cited | NSS parent | field parent | DR3 model/data for scale |
|---|---|---|---|---|
| F1 | 1.31 | **1.152** | **1.159** | 1.226–1.255 / 1.163 |
| F2 | 1.23 | 1.261 | 1.146 | 1.238–1.370 / 1.300 |
| F3 | 1.05, 1.03 | 1.069, 1.037 | 1.028, 1.012 | |
| F4 | 1.02 | 1.024 | 1.009 | 1.170–1.190 / 1.181 |

  **F1 at threshold 1.10 with P = 0.85 is not defensible.** Applying the DR3 model-data offset gives about 1.08–1.10. The note "F1 is therefore set well below the model" rests on the artefact. I would give it about 0.45.

- **The stand-in omits a real change.** The DR4 span (25 Jul 2014 to 20 Jan 2020, per ESA) includes **about 188 d of reversed precession** (2019.536–2020.576, Lindegren+ 2021). I ran one check with `--stars 300`, reflecting the last 188 d in the ecliptic plane (own-sense, all G; my run against `sim_dr4_nss`):
  - 340–390 d: 1.106 against 1.191
  - 700–800 d: 1.149 against 1.228 (se about 0.04, my estimate from N = 864)
  - 600–700, 800–900, 1100–1600 d: 1.03, 1.02, 1.01 (against 1.05, 1.03, 1.01)

  It does not invalidate F3 or F4. It erodes F1 and F2. F2 has thin margin (field parent × reversal lands near 1.10), so "decisive pair" is too strong.

- **Low-value statements.** F1, F2 and F5 are persistence: almost any account of DR3 predicts them. "F5: the sign should survive any plausible change in cuts" overclaims. Without a parallax cut, the model's non-parallax channels give about −0.05.

- **F2 + F3 do not separate the explanations as claimed.** "Any cause tied to Gaia's instrument or sky ... would keep the shoulders" is false for the rejected sidelobe reading, whose width also scales with baseline.

- **F6 is confounded in both directions.** Sense −1 has more low-margin orbits (27.5% against 18.3%), which lowers its retention with no fakes. A persisting DR4 cut lowers sense +1 retention near two years. The all-fake effect is 0.231 × retention, about 0.15, so a 0.03 threshold can fail with zero fakes.

## 3. Required wording changes

**README**

1. **Lines 11–13.** Replace "A no-free-parameter model predicted that pattern by period before the held-out data were opened" with: "A model with no fit to orbit data, built while dev was in view, matches the pattern on held-out data. The registered r test passes narrowly but cannot discriminate: a step at 300 d scores higher."
2. **Line 13.** Replace "explains about half" with: "The model reproduces about half the amplitude at 600–900 d with its own parent population. Applied to the observed margins (exploratory), it reproduces about 70–77% of the deficit above 300 d, and about 10% above 1100 d, where the parallax cut does not bind."
3. **Line 8.** Replace with: "The negative sign is prograde, but D = 0 is not rejected (p = 0.115) and dev gives −0.41 ± 1.05." Remove "hint" from lines 8, 108 and 152.
4. **Line 15.** Replace "The mechanism at one year was published as theory" with: "Butkevich 2018 published the sense dependence of orbit-parallax correlation near one year for a parallax-only fit. The error inflation through free P, T and e reported here is a different route."
5. **Line 78.** Rename and rerun the mock with real errors. Report gain 1.87–1.90 and effective 1.5–1.75. Delete "conservative" in line 78 and line 173.
6. **Line 76.** Report B from the slope, −11.2 ± 1.6 km/s/kpc, and state the constant term.
7. **Line 110.** Replace "ecliptic pattern removed" with "step-function ecliptic term removed". Report the full D with D_Y = −5.97 ± 1.03%. Fix the 3D values and the units bug.
8. **Line 120.** Replace with: "The 20° offset follows from A varying with |b|, through the parallax margin (19.7° when A(P, |b|) is imposed). A residual in X, −1.9 ± 0.5%, remains."
9. **Lines 133–134.** Replace "These binaries are real, and the astrometric sizes are right" with: "At these bright magnitudes the stars are RV-variable at the same rate in both senses, and amplitudes scale the same in both. This does not confirm individual orbits."
10. **Line 140.** Mark as a mathematical identity.
11. **Lines 141–142.** Change to "needs P, T and e in part at the peak, P on its shoulders" and "needs e and T". Add the pseudo-circular result as the main evidence.
12. **Line 143.** Give the source script and the registered definition, or remove the numbers.
13. **Lines 155–158.** Remove the one-year overshoot. Add P > 1100 d (A about −0.08, cut not binding), and 450–600 d. Give the 50–100 d model se.
14. **Line 166.** Quantify: "T3 reaches 8.8% of the 600–900 d excess. `AstroSpectroSB1` shows the same deficit in RV-confirmed orbits (median G 11.6). Nothing direct above G 13."
15. **Line 172.** Replace with the spin regression result.
16. **Line 197.** Limit to 600–900 d. **Line 198.** Say "up to about 30% overall, more at low e or high |β|".
17. **Disclose:** the `chiral_sim.py` hash change; the injection substitution; the PREREGISTRATION line 3 conflict.

**Forecast**

1. Replace the model column with the grader's statistic, for both parents, and give the reversal check.
2. Reset F1's probability. Lower it to about 0.45, or move the threshold in view of the DR3 offset (for instance 1.05).
3. Replace F2 with a contrast: ratio(700–800) minus the mean of ratio(600–700) and ratio(800–900) > 0.05. DR3 0.10; DR4 model 0.13–0.21. This is robust to global scale and grows with baseline.
4. Add two sharper forecasts, if the DR4 pipeline keeps these solutions and the e split:
   - The 700–800 d ratio falls with e.
   - For e < 5e-4 solutions at 600–900 d, |ratio − 1| < 0.1.
5. Rewrite F6 as margin- and significance-matched, one-sided, with a threshold set between the zero-fake and all-fake cases (about 0.06–0.08), or drop it.
6. Delete "Any cause tied to Gaia's instrument..."; state reversed precession as a known omission, not an untested possibility of a different phase; correct the "1.47 against 1.15" weak point.

## 4. Decisive follow-ups

1. **Real fit test, before sealing:** run `gaiamock` split by sense, or a true non-linear 12-parameter fit on simulated epochs, including pseudo-circularisation. Should give the pseudo-circular step and the P > 1100 d residual if the cascade is modelled.
2. **Faint RV:** LAMOST, APOGEE or GALAH epochs for G > 13, P 600–900 d, margin < 1.5, by sense, phase-folded on the Gaia orbit rather than a variability flag. This is the one direct test left of the spurious reading.
3. **P > 1100 d:** add the acceleration-orbit cascade to the model, or test whether A depends on `goodness_of_fit` and model choice there.
4. **DR4 on 2 Dec:** `epoch_astrometry` gives the real scan law including reversal. Rerun the model on it with the sealed forecast unchanged.
5. **DR4 wide pairs:** include a spin term in the fit by default.
