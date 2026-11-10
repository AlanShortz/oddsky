# H-0019 second referee report: the real-light-curve reference and the note for the advisor (claude-referee, 2026-11-09)

Independent referee, no stake in the result. Scope: (A) `scripts/13_ogle_real.py`, `scripts/14_reference_real.py`,
`work/reference_real.csv` and the README text that rests on them; (B) `drafts/note_for_review.md` and its claims file.
Recomputed with my own pandas scripts (`/tmp/h19note/a.py` … `f.py`) from `~/oddsky-runs/h0019/ogle_pairs_{lmc,smc}.parquet`,
`work/{lmc,smc}_population.csv`, `work/galaxies.csv`, `~/oddsky-runs/h0019/hsc/*_det.parquet`. Downloads: eight single OGLE
light curves (about 100 kB in all) to look at observation times, which the pair files do not keep. No file other than this
one was changed.

## Verdict

1. The real-light-curve reference reproduces (LMC 0.0368, SMC 0.0242 with my own noise draws, against 0.0366 and 0.0244)
   and survives every artifact attack I ran: id join, zero points, outliers, noise double-counting, pair drawing. Its
   star-level bootstrap error is ±0.0013 (LMC) and ±0.0015 (SMC).
2. "The pooled Hubble galaxies match the LMC" is not a like-for-like comparison. The reference is noise-matched to the five
   clean fields, which score 4.4 ± 0.3% (2.3σ above the LMC's 3.7%); matched to the noise of all 13, the LMC gives 3.9%
   and the pool is 2.0σ below. "In the same range as the LMC" is supported. "Matches" is not.
3. The note is accurate in its numbers (paper-check: 11 recomputed, 0 failures) but five phrases would make a
   professional wince or mislead by omission: "blind", "so it is not photometric noise", "matches the LMC", "measured the
   same way", "easy to run for any cadence". Replacement wording is given. "Stops around 2017" is right.

## Findings

### A. The reference from real OGLE light curves

**A1. Reproduces (note).** Ran: my own merge of pairs and population, my own noise draws (seed 777), weights of one per
star per lag, same boxes (tip 14.60 / 15.00, mean of the two magnitudes, V−I > 1.2).

| | README | mine | per lag 150 / 400 / 1,000 / 2,500 d (from `reference_real.csv`) | bootstrap sd |
|---|---|---|---|---|
| LMC, noise 0.043 | 0.0366 | 0.0368 | 0.0365 / 0.0355 / 0.0370 / 0.0374 | 0.0013 |
| SMC, noise 0.043 | 0.0244 | 0.0242 | 0.0225 / 0.0255 / 0.0240 / 0.0254 | 0.0015 |

Bootstrap: 1,000 resamples of stars (variables and constants together), lags averaged within each resample; a single lag
alone gives 0.0016 / 0.0017. The scatter from the added-noise realisation is 0.0002. V−I > 1.6: LMC 0.0420 (mine 0.0422),
SMC 0.0294. The sinusoid values 0.0272 / 0.0138 are as in `tests.json`.

**A2. Star ids join correctly (note; attack failed).** All 22,564 LMC and 9,092 SMC variables of the population are in
the pair files and nothing else is; ids are 5 characters in the parquet, 4 or 5 in the SMC population before padding, no
duplicates. Mean pair magnitude minus catalogue I, per star: median +0.010 mag (LMC), 0.000 (SMC); 1st to 99th
percentile −0.005 to +0.095 (LMC). OSARGs +0.009 / 0.000, Miras +0.10 / +0.07 (a magnitude mean against the catalogue's
mean, as expected). A wrong join would give offsets of tenths of a magnitude for every type. The LMC's +0.010 is
equivalent to a 0.01 mag tip shift and does not matter.

**A3. Zero points within a light curve (note; attack failed).** The eight light curves I fetched (5 LMC, 3 SMC) hold
OGLE-III only: HJD 2452087 to 2454956, 437 to 738 points, no OGLE-II segment spliced in. For OSARGs with catalogue
amplitude under 0.02 mag the median signed difference m2 − m1 is 0.000 at every lag in both Clouds (−0.001 at one SMC
lag).

**A4. Outliers do not inflate the fraction (note; attack failed).** OSARGs with A1 < 0.02 mag: 0 of 680,890 pairs (LMC,
14,188 stars) and 0 of 309,621 (SMC, 6,455 stars) differ by more than 0.3 mag, or by more than 0.2; 0.012% and 0.009%
exceed 0.1. Their pair rms is 0.016 / 0.015 mag. All OSARGs: 0.17% / 0.11% exceed 0.3. Raw by type: Miras 68% / 74%,
semiregulars 8.4% / 10.0%. In the LMC box above the tip, semiregulars supply 66% of the exceedances, Miras 25% (from 1.8%
of the stars), OSARGs 9%, constants none.

**A5. Noise double-counting is negligible (note).** OGLE's own scatter is in the variables' pairs (about 0.011 mag per
point from the quiet OSARGs) and not in the constants'. In quadrature with 0.043 that is 0.0445 for variables. The
reference moves by 0.15 per mag of noise (0.0356, 0.0368, 0.0391 at 0.03, 0.043, 0.06), so the effect is about 0.0002.

**A6. Pair drawing: no bias found, one limit to state (should-fix, wording).** Ran: the script's draw re-implemented on
the eight light curves with 20,000 draws per lag, and a variant that takes a random observation inside the ±10% window
instead of the first after t + lag.
- Start indices are drawn at random with replacement, so "the first 12 accepted" are not the earliest epochs. Acceptance
  is about 40%, 75%, 60% and 10% at 150, 400, 1,000 and 2,500 d; realised mean lags 154, 403, 1,011, 2,503 d.
- First-after against random-in-window: identical on the seven low-amplitude stars. On the one large-amplitude star
  (LMC 28963, P = 341 d) they differ at single lags (0.82 against 0.45 at 2,500 d), in both directions across lags: one
  star's phase coherence, not a population bias. I could not test the population without the archive.
- The limit: OGLE-III spans about 2,780 d, so every 2,500-d pair starts in the first season (the first 3 to 4% of the
  span, 38 to 78 distinct starting points per star) and ends in the last. The 12 pairs of a star at that lag are close to
  one independent sample. That is harmless for the mean and is why the error must be a star-level bootstrap. It also
  means the reference says nothing beyond 7.5 years, while M33's median Hubble lag is 4,592 d.
- 33 LMC and 31 SMC star-lags have fewer than 12 pairs; 50 LMC and 21 SMC stars have none at 2,500 d. No star was
  dropped for having under 30 points.

**A7. "The same at every lag to 0.002" (should-fix).** True for the LMC (0.0355 to 0.0374). The SMC runs 0.0225 to
0.0255: 0.003.

**A8. Raw fractions are quoted at a different noise from the excess (should-fix).** "4.4% (LMC) and 3.0% (SMC) for
V−I > 1.2, and 5.1% in both for V−I > 1.6" are the noise-0.03 rows (4.39, 3.01, 5.07, 5.05). At 0.043, the noise of the
quoted 0.0366 / 0.0244, they are 4.5%, 3.1%, 5.2% and 5.2%. The conclusion (equal at matched colour) holds either way.

**A9. The error on the reference is borrowed (should-fix).** "Error 0.002 from the referee's bootstrap" was the sinusoid
reference's. Use ±0.0013 (LMC), ±0.0015 (SMC). `14_reference_real.py` still carries the old figure in a comment and
computes none.

**A10. The pooled comparison is not noise-matched (blocking for "looks like the LMC" / "matches the LMC").**
Ran: the reference at other noise levels, and at each Hubble galaxy's own control scatter (noise = 0.9 × `sd_long_rgb`,
the ratio the first referee found), weighted by `n_long_agb` as the pooled estimator is.

| LMC reference at noise | 0.043 | 0.06 | 0.08 | 0.09 | per-galaxy mix of the 13 |
|---|---|---|---|---|---|
| E₀.₃ | 0.0366 | 0.0390 | 0.0430 | 0.0453 | 0.0391 |

- 45% of the pooled stars are in fields with control scatter above 0.06 (NGC 2403, NGC 1313, Holmberg II and others at
  0.067 to 0.091). The 0.043 reference describes the five clean fields only.
- Clean fields against it: Hubble 0.0437 ± 0.0028 (480 of 8,185 above the tip, 5.9%; control 1.5%),
  LMC 0.0366 ± 0.0013: **2.3σ above** for V−I > 1.2, 0.5σ above the LMC's V−I > 1.6 value (0.0420).
- All 13 against the mix-matched reference: 0.0343 ± 0.0020 against 0.0391 ± 0.0013: **2.0σ below**. Gaussian noise is
  not a model of blending, which shrinks changes, so this direction is the expected one for crowded discs.
- So the "0.8σ below the LMC" is two offsets of about 2σ in opposite directions cancelling. Supported: the Hubble values
  (3.4% pooled, 4.4% in clean fields) lie in the range the LMC gives (3.7% for all red stars, 4.2% for its redder ones)
  and above the SMC's 2.4%. Not supported: "match", "look like the LMC" as a result.
- With the proper error the README's other figures become: pooled 1.0σ below, M33 1.4σ above, NGC 300 2.8σ above (README:
  0.8, 1.3, 2.6; with its own 0.002 NGC 300 is 2.7, not 2.6).

**A11. The reference is as sensitive to the tip as the sinusoid one was (should-fix).** Tip moved by −0.2, −0.1, +0.1,
+0.2 mag: LMC 0.0262, 0.0335, 0.0336, 0.0292; SMC 0.0204, 0.0238, 0.0222, 0.0198. The adopted tips sit at the maximum,
as they should if they are right (a wrong tip either lets giants into the box or variables into the control). Boxing on
the first visit alone gives LMC 0.0326, SMC 0.0233 (Hubble clean fields: 0.041). The statistical ±0.0013 is therefore
not the whole error: a 0.1 mag tip error costs 0.003, and four of the 13 Hubble tips are off their predictions by more
than that.

**A12. SMC box corner (note).** Fraction of Gaia members matched to an OGLE variable is 26 to 28% in RA 9 to 11,
Dec > −72.525 against 45 to 83% elsewhere: probably the edge of OGLE-III's coverage. 249 of about 12,000 members, so the
SMC value is diluted by 1 to 2% of itself at most.

**A13. Not attacked (note).** The Gaussian noise model, V−I > 1.2 against each Hubble field's own colour cut, I against
F814W aperture magnitudes, and the Cloud denominators (first report, B5) are unchanged from the first report and still
open. In the LMC control box Miras are 0.6% of the stars and 48% of the exceedances: the Cloud control is partly signal
too, as in M33.

### B. The note for the advisor

`uv run oddsky paper-check hunts/H-0019/drafts/note_for_review_claims.py`: 11 statements recomputed, 0 external, 0
failures, reviewed False. Every number in the note is right. The findings are about words.

**B1. "a number that matches the LMC" (blocking).** See A10. The note also leaves out the SMC (2.4%) and that the 13
galaxies disagree among themselves (χ² = 55.9 for 12; 0.6% to 4.9% among those with over 1,000 stars). An AGB specialist
will ask both at once. Replacement in the results list:
> The excess is 3.4 ± 0.2% pooled, and 4.4 ± 0.3% in the five least crowded fields. From real OGLE light curves, boxed
> as nearly the same way as I could, the LMC gives 3.7% and the SMC 2.4%.

and in the last paragraph: "It is a method that works and a number in the range the LMC gives, nothing more yet."

**B2. "Measured the same way" (should-fix).** The Cloud boxes use V−I > 1.2 and Cousins I; the Hubble boxes use each
field's own F555W or F606W colour and F814W aperture magnitudes, with noise added as a Gaussian. Use "as nearly the same
way as I could" (in B1's wording).

**B3. "As a blind check" (should-fix).** The pipeline never used the Mira list, which is what is meant. But the test was
exploratory, its first run was invalid (0.48" offset, about 30% chance matches) and it was redone after the first
referee's report. "Blind" promises more than that. Replacement:
> As a check against known variables: of the 91 published Miras in M33 (Yuan et al. 2017) that have such a pair, 65
> changed by more than 0.3 mag. For other stars of the same brightness it is 2.9%.

**B4. "so it is not photometric noise" (should-fix).** True of M33's short pairs. Left out: pooled over galaxies the
short-pair fraction is 0.36% (33 of 9,125, 32 of them in three crowded discs), the preregistered
short-lag control failed (T3, 2.3σ from zero), and short pairs share orientation and epoch, so they do not test what
changes over years. Replacement:
> In M33, none of the 3,195 stars above the tip changed that much between visits less than 10 days apart, so short-term
> photometric scatter is not producing it there. In the most crowded discs it is not zero (33 of 9,125 over all
> galaxies).

**B5. The failed tests (should-fix).** "I preregistered a test … and it failed" is right and reads well. Two of five
preregistered tests failed; naming only one is selective once B4 is fixed, and B4's replacement covers it. No further
change if B4 is applied.

**B6. "giant branches of different metallicity" (should-fix).** No metallicity is in the analysis and the README says
the colour mix follows age and metallicity both. Use "giant branches of different age and metallicity".

**B7. "the forecast is easy to run for any cadence" (should-fix).** What exists: a sinusoid simulator for any cadence,
shown here to be a third low, and real-light-curve pairs at four lags from 150 to 2,500 d in the I band. Roman's filters
are mostly redder than I, where these stars' amplitudes are smaller. Replacement:
> A few visits to many nearby galaxies is exactly this situation. I can run the forecast from the OGLE light curves for
> a given cadence up to about seven years, in the I band; Roman's redder filters would need near-infrared light curves.

**B8. "two clean ACS F814W visits" (should-fix).** 72% have exactly two; the rest have more and the first and last are
used. Only stars with a measured colour are counted. Use: "kept the red stars with a measured colour, up to 1 mag above
the red-giant tip, that have at least two clean ACS/WFC F814W visits 100 days or more apart (first and last used)".

**B9. "the newer automatic per-visit catalogues your team produces" (should-fix).** Nothing in the call notes says his
team produces them; he offered to send a link. Use: "If you meant the newer per-visit catalogues on MAST, send me the
link you mentioned and I will point the same tool at them."

**B10. "stops around 2017" (note; correct).** Latest `StartMJD` over all 55 `hsc/*_det.parquet` files: 2017-08-17 (M33).
NGC 300 ends 2014-09-05, NGC 6822 2016-09-15. In the claims file cite the HSC v3 release notes alone: Whitmore+2016
describes version 1.

**B11. "the full write-up follows the order you suggested" (note).** The README runs abstract, figures, introduction,
data, results, analysis, conclusions, which is the order in the call notes with figures up front. He described how he
reads papers; "suggested" is fair. The write-up is not attached and the repository is private, so say what he can get:
"the full write-up is in the order you described, figures first; I can send it."

**B12. Not checkable by me (note).** The paraphrases of what the advisor said agree with the README's quotations and the call
notes; I have not seen the transcript. "Nothing is public yet" agrees with the README status line.

## Required changes

### (A) README and reference

1. Abstract, section 3 and conclusion 2: stop saying the pooled galaxies "look like" or match the LMC. State: pooled
   0.0343 ± 0.0020 against an LMC reference of 0.039 at the pool's own noise (2.0σ below); five clean fields
   0.0437 ± 0.0028 against 0.0366 ± 0.0013 (2.3σ above; 0.5σ above the V−I > 1.6 value 0.042). "In the range of the LMC,
   above the SMC."
2. Replace "error 0.002 from the referee's bootstrap" with ±0.0013 (LMC) and ±0.0015 (SMC), star-level, from this
   report; the abstract's "3.7 ± 0.2%" becomes "3.7 ± 0.1%" with the tip sensitivity beside it (item 4). Redo the
   significances: M33 1.4σ, NGC 300 2.8σ.
3. Raw fractions at the same noise as the excess: 4.5% and 3.1% (V−I > 1.2), 5.2% in both (V−I > 1.6); or say they are
   at 0.03.
4. Add the reference's sensitivities: tip ±0.1 mag gives 0.034 (LMC), ±0.2 gives 0.026 to 0.029; noise 0.03 to 0.09
   gives 0.036 to 0.045; first-visit boxing 0.033.
5. "The same at every lag to 0.002": LMC yes, SMC 0.003. Add that OGLE-III spans 2,780 d, so the reference stops at
   7.5 years and M33's median lag (4,592 d) is beyond it.
6. Conclusion 1: drop "blind" (B3).
7. Status line: the reference has now been refereed (this file), with what was found.
8. `14_reference_real.py`: compute the bootstrap instead of quoting it in a comment (tool debt, not blocking).

### (B) The note

1. Results line 1 and the "matches the LMC" sentence: the replacement in B1 (blocking).
2. Mira line: the replacement in B3.
3. Noise line: the replacement in B4.
4. "of different age and metallicity" (B6).
5. Roman sentence: the replacement in B7.
6. Selection sentence: the wording in B8.
7. Question 1: the wording in B9.
8. Write-up sentence: the wording in B11 (optional).
9. Claims file: add receipts for the new numbers (4.4 ± 0.3% clean fields, SMC 2.4%, 33 of 9,125); cite the HSC v3
   release notes alone for 2017.

## Re-check of the revised text

Re-read `drafts/note_for_review.md`, its claims file and the changed README passages (`git diff hunts/H-0019/README.md`)
after the author applied the required changes. `uv run oddsky paper-check hunts/H-0019/drafts/note_for_review_claims.py`:
18 statements recomputed, 0 external, 0 failures.

**Numbers verified again from the work files.**
- Clean fields 0.0437 ± 0.0028 (`explore.json`: 8,185 stars above the tip, f = 5.86%; control 14,777, 1.50%; M33,
  NGC 300, IC 10, NGC 4163, Sagittarius dIrr): "4.4 ± 0.3%" is right.
- SMC 0.0244 ± 0.0015: "2.4%" (note) and "2.4 ± 0.2%" (README) are right. LMC 0.0366 ± 0.0013: "3.7 ± 0.1%".
- Short pairs: 33 of 9,125 from `measure.csv` (NGC 4449 22, NGC 253 7, NGC 2403 3, NGC 247 1). "Nearly all in crowded
  discs" is fair; all four are discs.
- Significances: clean fields 2.30σ above, pool 2.01σ below (against 0.0391), M33 1.41σ, NGC 300 2.84σ. As stated.
- Sensitivities in the README (tip ±0.1: 0.034; ±0.2: 0.026 to 0.029; noise 0.03 to 0.09: 0.036 to 0.045; first-visit
  boxing 0.033; V−I > 1.6: 0.042; lags steady to 0.002 / 0.003; OGLE-III 2,780 d against M33's 4,592 d; raw fractions
  4.5%, 3.1%, 5.2%) agree with findings A7, A8, A10 and A11.

**The note.** All of B1 to B9 are applied. No blocking or should-fix problem remains. The added sentence owning the
first, wrong Mira match is accurate (offset 0.47"). Two notes, neither required:
- "the five least crowded fields" was my wording; the cut is on photometric scatter below the tip, not on crowding.
  More exact: "the five fields with the cleanest photometry".
- "a number in the range the LMC gives" is said twice (results list and last paragraph); one could go.

**The README.** The changed passages are right and nothing from the "Required changes (A)" list is left over (no
remaining "0.8σ", "look like the LMC", "blind", "not yet refereed", or noise-0.03 raw fractions). Item 8 (bootstrap inside
`14_reference_real.py`) is still tool debt.

document-sha256: 6aae4e808d6558c268151eb5b7e79beae69cf88080eedbd85a5917c7da8fc1e3
