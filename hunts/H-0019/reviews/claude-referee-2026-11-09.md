# H-0019 referee report (claude-referee, 2026-11-09)

Independent referee, no stake in the result. Everything below was recomputed with pandas scripts outside the Oddsky
tools (`/tmp/h19ref/a.py` … `f.py`, reading `work/pairs/*.parquet`, `work/*.csv|json`, `~/oddsky-runs/h0019/hsc|cat`).
Nothing was re-downloaded. No file other than this one was changed.

## Verdict

1. The measurement (T1: pooled E₀.₃ = 0.0343 ± 0.0020 from 15,145 stars) reproduces exactly and survives the artifact
   attacks I could run (mismatches, close neighbours, single-epoch box selection). The tool works.
2. The M33 "rediscovery" is wrong as run: the Mira list is offset 0.48" from Hubble, so the 0.5" match is about 30% chance
   matches. Done properly, Miras change **more** often than the sinusoid predicts (65 of 91 against 55 ± 3), which
   reverses the README's use of that test and supports "the reference is low".
3. "M33 and NGC 300 above the LMC" and "dwarfs above the SMC" are not results about galaxies yet. Probability that both
   are mundane (reference model, colour mix, NGC 300's centre, IC 10's tip): about 80%.

## Findings

### A. Numbers

**A1. M33 Mira match is invalid (blocking).**
Ran: all Yuan+2017 / Hubble pairs within 2"; 2-D offset histogram; re-match after removing the offset; chance rate by
shifting the Mira positions 3, 5 and 8 arcsec in 8 directions (24 trials).
- Hubble minus Yuan: dRA = −0.45", dDec = −0.14" (scatter 0.07" per axis, 96 stars). `09_rediscover.py` matches at 0.5"
  with no offset, so 62 of its 90 matches sit at 0.4–0.5" separation, clipped by the cut.
- Chance rate of the README's match: 32 within 0.5" and 25.6 passing the |ΔI| < 1.5 cut per trial, against 90 and 83
  claimed. Chance matches change by > 0.3 mag 2% of the time (0.5 per trial).
- Offset removed:

| radius | Miras used | chance | > 0.3 obs / exp | > 0.5 obs / exp | > 1.0 obs / exp | dimmed / brightened |
|---|---|---|---|---|---|---|
| 0.15" | 91 | 2.6 | 65 / 55.3 ± 3.4 | 51 / 41.3 ± 3.5 | 22 / 18.9 ± 2.9 | 49 / 42 |
| 0.20" | 99 | 4.5 | 69 / 60.4 ± 3.6 | 55 / 44.9 ± 3.6 | 23 / 20.1 ± 2.9 | 55 / 44 |

- The README's "46 of 83 against 52 ± 3", "36 (38 ± 3)", "16 (17 ± 3)", "44 dimmed, 39 brightened" are all superseded.
  Median Hubble-minus-published magnitude drops from +0.44 to +0.10 mag once the right star is matched.
- Consequence: published Miras exceed the single-sinusoid prediction by 2.4–2.9σ at 0.3 and 0.5 mag (about 15–20% in
  count). "The M33 test shows the sinusoid model is not low for Miras" must be reversed.

**A2. Tip agreement (should-fix).** "Agree to 0.1 mag in 11 of 13" is 9 of 13 from `work/measure.csv` (edge minus
prediction: M33 +0.23, IC 10 +0.48, Sag dIrr +0.13, NGC 7793 −0.12; nine others within 0.08). 11 of 13 holds only at
0.13 mag. Sag dIrr's edge is not significant (2.1), so the prediction is used there.

**A3. Significances against the reference ignore the reference's own error (should-fix).** "3.5σ" and "5.3σ" reproduce
arithmetically (3.45, 5.31) with the LMC value taken as exact. Bootstrap over the LMC population gives ± 0.0022 on the
reference; matching the reference noise to these fields (control scatter 0.046–0.048 needs 0.043 mag, not 0.03) moves
it to 0.0285. Then M33 is 2.9σ and NGC 300 4.4σ, before any systematic on the reference (C1, D1). Same for the dwarfs:
0.7σ / 2.9σ become about 0.5σ / 2.8σ.

**A4. Short-pair outliers (should-fix).** 22 of 33 in NGC 4449 and 3 in NGC 2403 is correct, but the other 8 are 7 in
NGC 253 and 1 in NGC 247. "Two crowded discs" should be three: NGC 253 has more than NGC 2403.

**A5. Hubble Catalog of Variables (should-fix).** "Of 19 … HCV flags none" is true for the AGB box in IC 10 only.
`work/hcv_check.csv` also shows 1 of 4 in the bright box and 3 of 10 in the control flagged, so 4 of 33 overall. "HCV
cannot see this sampling" overstates it. The IC 10 epochs are confirmed (2002-10-13; four between 2005-01-08 and 01-13).

**A6. "Never at short lag" (note).** Control stars exceed 0.3 mag in 26 of 13,681 short pairs (0.19%); in M33 1 of
5,694. "Never" is true only for the clean fields, approximately.

**A7. Lag statement is selective (should-fix).** NGC 300 at 400–6,000 d is 0.049, 0.050, 0.053 as stated, but
`work/lag_within.csv` also has NGC 300 at 10–100 d: 0.108 ± 0.024 (one image pair), higher than every long bin, and
`explore.json` pooled `by_lag` rises 0.017 → 0.026 → 0.048 → 0.041. Neither is mentioned.

**A8. Reproduced as stated (note).** 262 probed, 46 with ≥ 300, 10 tiled, 394 MB; 15,145; 0.0343 ± 0.0020 (17.5σ);
T2 0.36% (33/9,125) and 1.49% (75/5,037); T3 0.0017 ± 0.0007 (2.35σ, rounds to 2.3 not 2.4); T5 0.0341 ± 0.0022 vs
0.0338 ± 0.0040, ρ = −0.50, p = 0.08; χ² = 55.9/12 and 7.5/4, mean 0.043; LMC 0.0272, SMC 0.0138, control 0.6%;
M33 4.35 ± 0.47%, NGC 300 4.88 ± 0.41%, three dwarfs 3.16 ± 0.61%; tip ±0.1 and redder-cut numbers; 282 candidates
(138/144); control 2.6/0.9/0.2%; "0 of about 600" (625 in 21 dwarfs excluding IC 10). M33 short pairs are 3,195 in
`measure.csv`, 3,194 in `lag_within.csv`.

**A9. Not checkable (note).** "With the first ten, T2 failed at 0.56% and T3 passed": no file records it.

### B. Code

**B1. Mean-magnitude selection (note; attack failed).** Re-boxed on first-visit and last-visit magnitude alone: M33
0.0436 / 0.0471 (mean: 0.0432); NGC 300 0.0428 / 0.0401 (0.0493); five clean fields 0.041 / 0.041 (0.044). The LMC
reference boxed on one visit: 0.0236 (mean: 0.0272). The excess is not an Eddington artifact, but NGC 300 loses 0.006–
0.009 and the reference does not move the same way.

**B2. Mismatched stars between visits (note; attack failed).** M33: stars that change by > 0.3 mag have the same
detection-to-match offsets (median 7.0 vs 6.9 mas) and the same change in concentration index as the rest; restricting
to offsets < 20 mas leaves f_AGB = 6.7%, f_control = 2.2%. Stars with a neighbour inside 0.3" score lower, not higher.

**B3. The control is not a noise control in M33 (should-fix).** Control stars 0–0.25 mag below the tip change by
> 0.3 mag 3.3% of the time, 0.25–0.5 below 1.2%, 0.5–0.75 below 0.6%. By colour, the reddest third of M33's control box
scores 5.0% and the rest 0.25%. That is astrophysical (red variables below the placed tip), so E subtracts signal and
how much depends on the galaxy's colour distribution. It biases M33 low, not high.

**B4. Stars without a colour (should-fix, wording).** Hubble stars with no second filter are classed "mid" and dropped:
1,770 of 6,139 stars 0–1 mag above the tip in NGC 300 (29%), 27% in NGC 2403, 39% in NGC 1313, 2% in M33. In the
Clouds, OGLE stars with no V are forced red (one star in either box, so harmless there). "Every star 0 to 1 mag above
the tip" in the abstract is not what is counted.

**B5. Cloud denominator (should-fix).** `gaia_*_box.csv` has no query in the repo; the file is already cut at
BP−RP > 1.4, RP < 15.3 (LMC) and > 1.3, < 15.8 (SMC). OGLE variables that fail the Gaia match are added back regardless
of membership; constants are not, which can only raise the reference. Membership radius 0.6 / 1.2 / 2.0 mas/yr gives
18,361 / 19,708 / 20,048 LMC members, so the cut itself is not a lever. Only 15% of the LMC box is non-OGLE stars.

**B6. OGLE amplitudes (note).** Mira minimum A1 is 0.81 in both Clouds, matching OGLE's 0.8 mag peak-to-peak
definition. The convention is right. They are amplitudes of the fitted period, not the full range.

**B7. IC 10 tip (should-fix).** The edge is 0.48 mag from the prediction, at the boundary of the ±0.5 search window,
and the luminosity function has no clear step. E₀.₃ is 0.005 ± 0.014 with the predicted tip, 0.022 ± 0.010 at 22.5,
0.033 ± 0.008 as used. The pooled ±0.1 test hides this. IC 10 is 68% of the three-dwarf pool.

**B8. Errors are binomial only (note).** NGC 300's nine image pairs give χ² = 16.7 for 8; M33's eleven give 9.1 for 10.

### C. Preregistration

**C1. Intact (note).** `PREREGISTRATION.md` matches `prereg.sha256` and commit `3cc2f73` (21:00:43). `04_measure.py`
changed since only by reading several probe files. T1–T5 are evaluated as written; T3 and T5 are reported as failures.

**C2. The headline galaxies entered after preregistration (should-fix).** M33, NGC 300 and NGC 7793 all come from
`03b_fetch_tiled.py` (files written 21:34–21:47), a different footprint from the preregistered cone. They are 46% of
the sample and both "above the LMC" results. The README discloses the tiling but not that these are the tiled ones.

**C3. T2 is a knife-edge pass and the sample grew while the tests were watched (should-fix).** 75 of 5,037; one more
star fails it. The README says T2 and T3 changed sides as galaxies were added. Say plainly that the stopping point was
not preregistered.

**C4. Clean-field cut is post hoc (should-fix).** Scatter < 0.05 was chosen after seeing the data (M33 0.048 and
NGC 4163 0.047 are in; KKH37 0.052 and IC 2574 0.056 are out). It is labelled exploratory in §3, but the abstract and
conclusions 2–4 rest on it without the label.

**C5. "Refereed (`reviews/`)" (should-fix).** Before this report the folder held only a literature read.

### D. Mundane explanations tested

**D1. SMC half the LMC is colour mix (should-fix).** Rebuilt the reference by colour. Stars with V−I 1.2–1.6 never
change by 0.3 mag (E = 0.0006 LMC, 0.0001 SMC); they are 13% of the LMC box and 40% of the SMC box. Raw fraction above
the tip at matched colour:

| V−I > | LMC | SMC |
|---|---|---|
| 1.2 (as used) | 3.3% | 1.8% |
| 1.6 | 3.8% | 3.1% |
| 1.8 | 4.0% | 4.2% |
| 2.0 | 4.4% | 5.8% |

Red SMC stars vary as often as red LMC stars. A fixed colour cut on a bluer giant branch produces the factor of two.
T5's prediction was derived from this artifact, and "2.9σ above the SMC" compares against it.

**D2. The LMC reference is soft at the level of the claim (blocking for conclusion 4).** Scaling amplitudes by 1.2
gives 0.039; by 1.4, 0.052. Tip ±0.2 mag gives 0.021–0.023. Noise 0.09 gives 0.035. With A1 showing real Miras exceed
the sinusoid model, a reference near 0.04 is as likely as 0.027.

**D3. NGC 300's excess is concentrated in its centre (should-fix).** Inside 1.37': 0.074 ± 0.009 (990 stars). Outside:
0.040 ± 0.004, which is 2.3σ above the noise-matched reference. M33 is flat with radius (0.038–0.054) and with density.

**D4. Colour inside the Hubble box (note).** Bluest third of the red stars: 0.016 (M33), 0.010 (NGC 300). Reddest
third: raw 8.2% and 7.7%. E tracks the colour mix as strongly as it differs between galaxies.

**D5. Three dwarfs (should-fix).** No metallicity is in any work file. Without IC 10 the pool is 0.026 ± 0.009, 1.3σ
above the SMC reference. I believe IC 10 is not more metal-poor than the SMC (from memory; check before reuse).

### E. Wording

- Abstract and conclusion 1: "stars Hubble measured only twice" and "the stars the variable-star catalogue leaves out".
  72% of the 15,145 have exactly two clean F814W images; in the five clean fields 59%; in IC 10, 85% have five or more.
- Conclusion 3, "agrees with Goldman et al. 2019 … at 2.9σ": not supported (D1, D5, B7).
- Conclusion 4, "Unexplained": explained candidates exist and two were confirmed (A1, D3).
- "The noise control is essentially perfect": true at short lag in clean fields; at long lag the control is 1.5–2.1%
  and partly astrophysical (B3).

## Required changes to README.md

1. Replace every M33 rediscovery number (abstract, §3, Figure 3) with the offset-corrected match, state the 0.48" offset
   and the chance rate, and say Miras exceed the sinusoid prediction. Fix `09_rediscover.py` and regenerate.
2. In §4 reverse "the sinusoid model is not low for Miras"; add that amplitude ×1.2 moves the LMC reference to 0.039.
3. Quote M33 and NGC 300 against a noise-matched reference with its error (2.9σ, 4.4σ), and NGC 300 inside and outside
   1.37'. Conclusion 4: "above the sinusoid reference; the reference is probably low".
4. Add the colour-matched Cloud table; say the SMC value is a colour-mix effect and that T5's premise came from it.
5. Withdraw or rewrite conclusion 3: drop "more metal-poor than the SMC" and the Goldman agreement; give the IC 10 tip
   sensitivity and the value without IC 10.
6. Tips: "9 of 13 within 0.1 mag"; name M33 (+0.23) and IC 10 (+0.48).
7. Short-pair outliers: add NGC 253 (7). HCV: 4 of 33 across boxes. Lag: add the 10–100 d bin and the pooled trend.
8. Say M33, NGC 300 and NGC 7793 came from the post-preregistration tiled fetch, that T2 passes by one star, and that
   the clean-field cut was chosen after the data; label it exploratory in the abstract.
9. Abstract: "red stars with a measured colour", not "every star"; give the share with exactly two visits.
10. Status line: say what the referee found.

## Decisive follow-up

Run the two-visit estimator on real OGLE-III I-band light curves of the LMC box (the README's own next step), boxed by
the same colour as each Hubble field. Nothing about M33, NGC 300 or the SMC should be claimed before that.

## Tool fixes

- Positional matches: fit and remove the bulk offset first, then report a shifted-position chance rate with the match.
- `tip_edge`: flag an edge that lands in the outermost bin of the search window.
- Reference builder: carry a bootstrap error and a colour-matched option; commit the Gaia query with the data.
