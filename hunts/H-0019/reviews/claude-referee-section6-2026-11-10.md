# H-0019 referee report on section 6, "Follow-ups" (claude-referee, 2026-11-10)

Independent referee, no stake in the result. Scope: README section 6 only (PSF photometry, M31, the "adds up to"
paragraph, the Librarian tally). Everything was recomputed with my own pandas scripts outside the Oddsky tools
(`/tmp/h19s6/a.py` … `n.py`), from `work/pairs/*.parquet`, `work/psf*.{csv,parquet}`, `work/m31.json`,
`work/candidates_librarian.csv`, `work/{lmc,smc}_population.csv`, and the raw files in `~/oddsky-runs/h0019`
(`hsc/MESSIER031_{det,sum}.parquet`, `angst/*.parquet`, `ogle_pairs_{lmc,smc}.parquet`). `16_psf.py` was re-run from a copy
with its outputs redirected to `/tmp`. Nothing was downloaded. No file other than this one was changed.
**Literature values (M31 tip, metallicities) are quoted from memory and were not re-fetched; check each before it is
quoted anywhere.**

## Verdict

1. Every number in section 6 reproduces from the files (two small exceptions: "30 in published Mira lists" is 28, and
   "245 or so" is 249). The variability in M31 is real: I could not make it an artifact (chip position, programme,
   PHAT vs not, short-lag control, colour-matched control slices all clean).
2. But **"E₀.₃ = 0.068 vs the LMC's 0.037" is not a like-for-like number and must not be the headline.** 21.65 is not
   M31's tip: the published tip is 21.2 in this system, the data's own variability drops there, and 83% of the "above
   the tip" box is below it. E runs from −0.07 to +0.094 as the tip moves over 20.6 to 22.0, and at the published tip
   from 0.16 (inside 0.25°) to 0.01 (beyond 1°).
3. "PSF photometry raises the excess" is not supported (paired, same epochs: +0.000 ± 0.004). The ordering paragraph
   rests on seven hand-picked values from four measurement systems; with the three it sets aside, ρ = 0.16. The caveats
   in it are right, the first two sentences are too strong.

## Findings

### A. M31

**A1. The tip is misplaced by 0.47 mag; the registered box is mostly red giants (blocking).**
Ran: luminosity function of red summary stars in 0.05 mag bins, split by colour; fraction of long pairs with |Δ| > 0.3
in 0.25 mag bins by colour slice.
- Published: I_TRGB ≈ 20.54 Vega, observed (McConnachie et al. 2005, MNRAS 356, 979, from memory). Plus 0.43 (AB) plus
  0.25 (aperture) = **21.2**, which is the README's own prediction (21.18). The prediction was right.
- The luminosity function has no edge at 21.65. It rises smoothly by a factor 1.15 per 0.05 mag from 21.1 to 21.9. The
  Sobel statistic, which is weighted by √N, has a broad maximum there (63.1 at 21.63, 61.3 at 21.73) and the ±0.5 mag
  window ends in that bin. It is the steepest part of a smooth curve, not a tip.
- The data place the tip themselves. Fraction changing by > 0.3 mag, long pairs, colour (AB, dereddened) 1.9 to 2.8:

| F814W (AB, aperture) | 20.65–20.90 | 20.90–21.15 | 21.15–21.40 | 21.40–21.65 | 21.65–21.90 | 21.90–22.15 |
|---|---|---|---|---|---|---|
| colour 1.9–2.2 | 10.0% | 10.7% | 3.8% | 1.3% | 0.3% | 0.2% |
| colour 2.2–2.5 | 15.8% | 9.2% | 3.6% | 1.4% | 0.5% | 0.3% |
| colour 2.5–2.8 | 15.7% | 12.4% | 5.6% | 2.4% | 0.9% | 0.5% |
| colour > 3.8 | 30.1% | 28.2% | 26.6% | 25.3% | 22.6% | 14.0% |

  The step is at 21.15 to 21.2 for ordinary giant colours. Only the reddest stars keep varying fainter (their tip in I
  is fainter, and some are dusty).
- Of the 55,598 stars in the registered box (20.65 to 21.65), 46,400 (83%) are fainter than 21.15.
- E against tip placement, all red stars (the README gives 21.18 to 21.65 only):

| tip | 20.6 | 20.8 | 20.9 | 21.0 | 21.1 | 21.2 | 21.3 | 21.4 | 21.5 | 21.65 | 21.8 | 22.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E₀.₃ | −0.071 | −0.020 | 0.021 | 0.047 | 0.070 | 0.089 | 0.094 | 0.088 | 0.081 | 0.068 | 0.055 | 0.040 |
| f above | 0.100 | 0.134 | 0.149 | 0.156 | 0.160 | 0.162 | 0.153 | 0.137 | 0.121 | 0.096 | 0.075 | 0.052 |
| f control | 0.170 | 0.153 | 0.129 | 0.109 | 0.090 | 0.073 | 0.059 | 0.049 | 0.039 | 0.028 | 0.020 | 0.012 |

  "None of those is near the LMC's 0.037" is true only inside the range the README tried. 0.1 mag brighter than the
  prediction E is 0.047; 0.2 mag brighter it is 0.021; at 22.0 it is 0.040.
- The control is not a control in M31. At the published tip it holds 7.7% large changes (the LMC's: 0.9%), nearly all
  from stars redder than 2.8 (14% there). E subtracts real variables.

**A2. At the published tip the statistic is a strong function of position, and E is the wrong summary (blocking).**
Ran: boxes at 21.18, by radius, errors from a bootstrap over image pairs.

| radius | 0–0.25° | 0.25–0.6° | 0.6–1.0° | 1.0–2.0° |
|---|---|---|---|---|
| f above tip (20.18–21.18), all red | 0.234 | 0.163 | 0.098 | 0.092 |
| f control (21.18–21.68) | 0.075 | 0.076 | 0.080 | 0.081 |
| E₀.₃ at tip 21.18 | 0.159 ± 0.011 | 0.087 ± 0.007 | 0.018 ± 0.006 | 0.011 ± 0.009 |
| E₀.₃ at tip 21.65 (README) | 0.075 ± 0.003 | 0.069 ± 0.002 | 0.059 ± 0.003 | 0.058 ± 0.005 |
| f above tip, colour 1.9–2.8 only | 0.174 (1,436) | 0.103 (1,015) | 0.036 (742) | 0.037 (295) |

- The registered box hides a factor of 2.5 to 5 between M31's centre and its outer disc; it looks flat because the box
  is mostly sub-tip stars whose 8% does not change with radius.
- Beyond 0.6°, E at the published tip is 0.01 to 0.02, **below** the LMC's 0.037. The raw fraction there (9 to 10%) is
  still above the LMC's (4.5 to 4.7%), but in the colour slice 1.9 to 2.8 it is 3.6%, about the LMC's.
- In finer rings the raw fraction peaks at 0.26 to 0.28 between 0.05° and 0.15° (bulge) and falls to 0.08 at 0.8 to 1.0°.
- So M31 has no single value. The honest statement is a profile, and its inner part is bulge.

**A3. Artifact attacks, all failed (note).**
- Chip position. Ran: XImage/YImage from the detection table, distance from each image's footprint centre, normalised.
  E by quintile of the larger of the two distances: 0.064, 0.070, 0.065, 0.076, 0.065 (each ± 0.003); by the smaller:
  0.061, 0.069, 0.069, 0.070, 0.071. f_control 0.026 to 0.031 throughout. No edge effect.
- Programme. PHAT with PHAT (75% of the stars): 0.067 ± 0.002; any other combination: 0.070 ± 0.003. 56 programme pairs
  with ≥ 300 stars range 0.021 to 0.099, tracking lag (A5), not programme.
- Short lag, same pixels: 0.07% above the tip; by radius and colour never above 0.25%, including inside 0.25°.
- Colour-matched control at long lag: red stars of colour 1.9 to 2.8 at 21.65 to 22.15 change by > 0.3 mag 0.8% (inner)
  to 0.1% (outer) of the time. Photometric or matching errors cannot be larger above the tip than 0.5 mag below it.
- Dimmed/brightened above the published tip, by radius: 456/504, 342/338, 148/167, 56/63.
- Caveat the README should carry: short pairs share a roll angle, long pairs mostly do not (PHAT half-bricks are
  rotated 180°). The faint colour-matched slice is the control for that, and it is clean.

**A4. Radial trend: survives image-pair errors, but only at long lag, and A2 supersedes it (should-fix).**
Ran: bootstrap over the 632 image pairs holding box stars; weighted regression on the 112 large pairs with the
intrinsic scatter (0.0135) that makes χ² equal its degrees of freedom.
- README bins with cluster errors: 0.075 ± 0.003, 0.069 ± 0.002, 0.059 ± 0.003, 0.058 ± 0.005. Inner minus outer
  (> 0.6°): 0.016 ± 0.004. Whole sample: 0.0679 ± 0.0016 (binomial 0.0013).
- Split by lag: at 100 to 250 d the trend is absent (0.062, 0.048, 0.056, 0.054; inner minus outer 0.006 ± 0.005, 1.1σ);
  at ≥ 250 d it is there (0.077, 0.078, 0.062, 0.061; 0.015 ± 0.004, 3.4σ).
- Image-pair regression: radius alone −0.023 ± 0.009 per degree (2.5σ); with a short-lag term −0.015 ± 0.010 (1.5σ).
- It is not colour mix: the box gets redder outward (median 2.59, 2.82, 2.97, 3.00), which should raise E.
- "Crowding would push the inner fields down, not up" is fair. "Falls outward as metallicity does" omits that the inner
  bin is bulge, that age falls outward too, and that the fraction of the box above the true tip changes with radius
  (16%, 18%, 21%, 23%).

**A5. Lag (should-fix).** 0.054 ± 0.002 at 100 to 250 d against 0.074 ± 0.002 later is 6.8σ with image-pair errors, and
it holds inside every radial bin, so it is not the inner fields. Finer: 0.077 ± 0.008 (100–140 d, 1,653 stars), 0.054,
0.051, 0.048 (140–250 d), 0.080 (250–400 d), 0.076, 0.071, 0.072, 0.072. The LMC reference is flat from 150 d
(0.0365) to 2,500 d (0.0374). That is a real difference from the LMC in time structure and deserves a sentence; long
periods (half a cycle near a year) would do it, so would a roll-angle term in f_control (0.030 to 0.033 at 140–250 d
against 0.026 after), which is too small to explain it. Radius and lag are confounded (outer pairs are mostly short):
any radial statement must be made within lag bins.

**A6. Colour (should-fix).**
- By colour cut (registered tip): > 1.07 0.068; > 1.9 0.072; > 2.3 0.081; > 2.8 0.101; > 3.2 0.113. In slices: 0.029,
  0.018, 0.026, 0.025, 0.038, 0.056, 0.100, 0.086 for 1.07–1.5, –1.9, –2.2, –2.5, –2.8, –3.2, –3.8, > 3.8.
- The cut (AB 1.07, Vega 1.60 in F475W−F814W) is roughly V−I ≈ 1.05 as intended, but the M31 box's median colour is
  AB 2.7 (Vega 3.2, V−I near 2), far redder than the LMC box. No transformation is in the analysis.
- **11.6% of long pairs above the registered tip have no F475W and are dropped; they vary more** (12 to 23% by
  magnitude, against 7 to 17% for the red stars). Stars too red for F475W are the dustiest variables. The README does
  not give this number for M31; it does for NGC 300 and NGC 1313.

**A7. Noise- and colour-matched LMC (note).** Ran: my own draw from `ogle_pairs_lmc.parquet`, weights of one per star
per lag, three noise realisations.

| LMC, noise | V−I > 1.2 | > 1.6 | > 1.8 | > 2.0 | raw f above tip (> 1.2 / > 2.0) |
|---|---|---|---|---|---|
| 0.043 | 0.037 | 0.042 | 0.040 | 0.022 | 0.045 / 0.061 |
| 0.056 (M31's long-pair control scatter) | 0.038 | 0.044 | 0.042 | 0.023 | 0.047 / 0.063 |
| 0.080 | 0.043 | 0.050 | 0.047 | 0.028 | 0.053 / 0.071 |

No colour cut or noise level brings the LMC's E to 0.068, and its raw fraction reaches 12% only for V−I > 3.0. M31's raw
fraction above the published tip is 16% overall. So the difference is not noise and not a simple colour cut. But see
A2: the outer disc at ordinary colours matches the LMC.

**A8. Foreground and young stars (note).** Red summary stars 2 to 3 mag above the box (18.65–19.65), mostly Milky Way
dwarfs, are 0.6%, 1.4%, 2.1%, 2.8% of the box count in the four radial bins; with a flat dwarf luminosity function the
box is at most 2 to 6% foreground, largest outside. That dilutes the outer bins by a few per cent of their value and
cannot make the trend. Red helium-burning stars sit in the slices bluer than 1.9 (9% of the box), which score 0.02 to
0.03; they dilute too.

**A9. Three tiles were probably truncated (note).** `m31.log` shows tiles 14, 180 and 188 with exactly 50,000
detections, the page size of `oddsky.data.hsc`. Rows are sorted by MatchID, so whole stars are missing, not epochs; no
bias, but "all were fetched" is not quite true. Also: 489 images are in the download, 457 enter a pair, 632 image pairs
hold box stars (647 hold any).

### B. PSF photometry

**B1. Reproduces (note).** My re-run of `16_psf.py` gives `work/psf.csv` byte for byte. Fit rms 6 to 17 mas; chance
matches 0.2% to 3.1% per field pair, 2.1% pooled; 89 of 119; χ² = 28.2 for 5 (19.4 for 4 without NGC 300).

**B2. "It raises it" is not supported (should-fix).** Same-star values are correlated, so the table's two columns
cannot be compared with their own errors. Paired (discordant stars only):

| | above tip: catalogue only / PSF only | control: catalogue only / PSF only | E_PSF − E_cat |
|---|---|---|---|
| NGC 300 | 28 / 33 | 11 / 8 | +0.005 ± 0.007 |
| Garland | 0 / 3 | 2 / 2 | +0.019 ± 0.012 |
| KKH 37 | 0 / 1 | 1 / 0 | +0.019 ± 0.016 |
| NGC 4163 | 2 / 1 | 0 / 2 | −0.006 ± 0.006 |
| IC 2574 | 0 / 1 | 0 / 0 | +0.010 ± 0.010 |
| all | 30 / 39 | 14 / 12 | +0.005 ± 0.005 (1.1σ) |

None is beyond 1.6σ. And B3 removes NGC 300's rise.

**B3. In NGC 300 a third of the "same stars" are not the same epochs (should-fix).** The catalogue pair is first and
last detection of any programme; ANGST has 2002 and 2006 only. 1,122 of the 3,565 matched NGC 300 stars have a
catalogue pair ending in 2012 or 2014. For those the two columns compare different time baselines, not different
photometry (correlation of the two changes 0.53, against 0.90).

| NGC 300 above tip | stars | catalogue large changes | confirmed by PSF | E cat | E PSF | paired difference |
|---|---|---|---|---|---|---|
| same epochs | 851 | 60 | 49 (82%) | 0.062 | 0.058 | −0.004 ± 0.005 |
| different epochs | 362 | 29 | 12 | 0.066 | 0.093 | +0.027 ± 0.019 |

Same epochs, all five galaxies: **77 of 90 confirmed (86%)**; discordant above the tip 13 catalogue-only, 14 PSF-only;
E 0.0529 (catalogue) and 0.0530 (PSF), paired difference +0.000 ± 0.004. Of NGC 300's 11 same-epoch misses most sit just under the threshold (overall, 12 of the
28 unconfirmed have a PSF change of 0.2 to 0.3 mag, 21 of 28 the same sign; 8 are under 0.1 mag). So "61 of 89" is
neither good nor bad news as written: it mixes a fair 82% with an unfair comparison. The fair reading is good news:
PSF photometry reproduces the catalogue's excess to within 0.4 percentage points.

**B4. Code (note).**
- `ebv = 0.0` is set and never used: PSF colours are not dereddened, the catalogue's are. Shift of the cut: 0.07 to
  0.11 mag in Garland and M81, under 0.04 elsewhere. Small, and it lets slightly bluer stars in.
- The tip is searched among stars with colour > 0.8 whatever the filter pair (the box uses 1.05 for F555W−F814W).
- Vega cuts 0.79, 1.05, 1.60 are the AB cuts 0.45, 0.62, 1.07 correctly moved (AB − Vega: +0.09, 0.00, −0.10; F814W
  +0.43).
- Colour from epoch 1 only: harmless for the box, but a Mira's colour changes with phase; mean of both would be better
  where both epochs share a filter (NGC 4163, IC 2574).
- Catalogue-to-ANGST offset grid: IC 2574's best offset is at the grid's limit (+1.0"). Extending to ±2" gives 197
  matches at +1.1" against 196: no harm, but widen the grid. No chance rate is recorded for this second match; over the
  grid the chance level is 3 to 19 matches (185 in NGC 300, 5%).
- `uncrowded_*` columns equal the main ones: the gst lists already cut on crowding. Drop them or say so.

**B5. M81 (should-fix).** The edge is in the last bin of the ±0.3 window (0.275 from the prediction): the same failure
as IC 10 and M31, in the same direction (fainter), and section 5 already says `tip_edge` should flag this. With A1 in
hand, a tip 0.28 mag too faint means a box that is partly red giants. 164 stars, one outer field, colours not
dereddened by 0.09. Not worth a row in the table; one sentence saying it was tried and the tip was not located.

### C. The ordering paragraph

**C1. The seven values are not one measurement (blocking for the first two sentences).**

| | value used | photometry | colour of the cut | tip | noise |
|---|---|---|---|---|---|
| SMC, LMC | 0.024, 0.037 | OGLE light curves + added noise | V−I > 1.2 | adopted 15.00, 14.60 | 0.043 added |
| NGC 4163 | 0.025 | DOLPHOT (catalogue: 0.028) | F606W−F814W | edge | 0.043 |
| M33 | 0.044 | catalogue aperture | F606W−F814W | edge, 0.23 from prediction | 0.048 |
| IC 2574 | 0.046 | DOLPHOT own box (catalogue 0.027 ± 0.015; same stars by PSF 0.029 ± 0.017) | F555W−F814W | edge | 0.040 |
| NGC 300 | 0.049 to 0.064 | catalogue, whole / DOLPHOT, inner fields | F606W / F555W | edge | 0.046 / 0.055 |
| M31 | 0.068 | catalogue aperture | F475W−F814W | 0.47 mag too faint (A1) | 0.056 |

IC 2574's place depends on which of three numbers is taken (0.027, 0.029 or 0.046). M31's value is anywhere from 0.01
to 0.16 (A2). NGC 300's is a range that spans M33 and M31.

**C2. Rank correlation with literature metallicities.** Values (from memory, to be checked): SMC [Fe/H] −1.0 (Dobbie+
2014); NGC 4163 12+log(O/H) 7.56, so −1.1 (Berg+ 2012); IC 2574 7.93, so −0.8 (Croxall+ 2009); M33 inner disc about
−0.45 (Rosolowsky & Simon 2008); LMC −0.4 (Cole+ 2005); NGC 300 inner disc about −0.25 (Bresolin+ 2009); M31 disc
about −0.05 (Gregersen+ 2015). Gas-phase oxygen and stellar iron are mixed here, and AGB stars are older than the gas;
I take ± 0.15 to 0.2 dex. Monte Carlo over both sets of errors (M31's E given ± 0.02 for its tip):

| sample | n | Spearman ρ | p | with errors: median, 95% range |
|---|---|---|---|---|
| the paragraph's seven | 7 | 0.82 | 0.023 | 0.75, 0.21 to 0.96 |
| without M31 | 6 | 0.71 | 0.11 | 0.66, 0.14 to 0.94 |
| plus Garland, KKH 37, M81 field (set aside in the paragraph) | 10 | 0.16 | 0.66 | 0.22, −0.24 to 0.72 |
| plus Holmberg II, IC 10, Sagittarius dIrr (catalogue values) | 13 | 0.37 | 0.21 | 0.34, −0.07 to 0.73 |

(Metallicities assumed for the extras: KKH 37 −1.5, Garland −0.6 ± 0.4, M81 field −0.6, Holmberg II −1.0, IC 10 −0.5,
Sagittarius dIrr −1.3.) A weighted line through the seven has slope 0.023 per dex with χ² = 10.3 for 5.

**C3. What a professional would conclude.** A suggestive ordering in a subset chosen after the fact, p ≈ 0.02 before
any penalty for the choice, gone when the three high metal-poor values are kept. With A2 (the statistic changes by a
factor of several inside one galaxy with radius) and section 4 (it follows colour), the working hypothesis should be
that E tracks the make-up of the box (how many stars are late-M, oxygen-rich, long-period, and how far above their own
tip), which correlates with metallicity and with age. The paragraph's caveats say most of this. "The values now line
up" and "that is the direction the failed registered test predicted" are too strong; "it is not yet evidence" is about
right. M31's internal trend should not be offered as support (A4).

### D. Librarian tally

**D1. Counts (note).** 282 rows, 282 distinct stars: 173 unlisted, 75 catalogued, 30 mentioned, 4 studied. 115
incomplete, 70 of them NGC 300 (then Holmberg II 13, IC 10 11, Garland 10, NGC 2403 6, IC 2574 2, one each in M33,
NGC 4163, Sagittarius dIrr). All correct.

**D2. "30 in published Mira lists" is 28 (should-fix).** The 30 "mentioned" in M33 are 28 Yuan et al. 2017 Miras and 2
DIRECT variables (Macri et al. 2001, field M33B), whose type the Librarian does not give. The 31st is the Cepheid, which
the README counts both as "known variable re-found" and as "contaminant".

**D3. "The other 245 or so" is 249 (note).** 282 − 31 (M33) − 1 (Sagittarius dIrr) − 1 (NGC 300 Cepheid). 63 of the 75
"catalogued" are infrared or ultraviolet source-list entries (Spitzer SSTSL2 56, WISE 6, GALEX 1); the other 12 are
entries in cluster, nebula, X-ray or star lists. None carries variability content, so they belong with the unlisted. One is worth a look: NGC 2403 MatchID 36164999 lies within 1" of
the Chandra source CXOU J073649.2+653633.

**D4. The gap (should-fix).** For 112 of the 249 (45%) the variable-star index was never consulted (115 incomplete rows, 3 of them among the known); for NGC 300 that
is 70 of 83, and NGC 300 has published Cepheid and long-period-variable lists. A second NGC 300 candidate (MatchID
97135192) is 3.6" from Cepheid cep011. The sentence is honest as a search result, but the number that is checked
against a variable-star index is 137, not 249.

## Required changes to README section 6

1. **M31, first bullet and tip bullet.** Replace with: "With the registered code the edge finder returns 21.65, which
   is not the tip: the published tip (I ≈ 20.54) is 21.2 in this system, the prediction was 21.18, and the fraction of
   stars changing by more than 0.3 mag drops at 21.15 to 21.2. 83% of the registered box is below the true tip. The
   registered number (0.068 ± 0.002, image-pair errors) is therefore not comparable with any other galaxy's. With the
   tip at 21.18, 16% of red stars above it change by more than 0.3 mag (LMC: 4.5%), and 7.7% just below it (LMC: 0.9%),
   so the control is contaminated and E (0.085) is not a clean statistic here. E runs from −0.07 to +0.094 for tips
   from 20.6 to 22.0."
2. **Add the radial profile at the published tip** (table in A2) and say: "M31 has no single value. The fraction above
   the tip falls from 23% inside 0.25° (bulge) to 9% beyond 0.6°; among stars of ordinary giant colour from 17% to
   under 4%, which is the LMC's level."
3. **Radius bullet.** Give image-pair errors, state that the trend is absent at 100 to 250 d and 3.4σ at longer lags,
   and delete it as support for a metallicity reading.
4. **Lag bullet.** Add "6.8σ with image-pair errors, present at every radius; the LMC reference is flat with lag".
5. **Add:** "11.6% of stars above the registered tip have no F475W and are dropped; they change more often than the
   stars kept." And the artifact checks of A3 in one sentence, with the roll-angle caveat.
6. **PSF bullets 1 and 2.** Replace with: "Where the two measurements cover the same epochs, PSF photometry confirms 77
   of 90 large changes (86%) and changes the excess by 0.000 ± 0.004 (paired). In NGC 300 a third of the matched stars
   have a later last epoch in the catalogue than ANGST reduced; those are excluded from this comparison (with them: 89
   of 119). PSF photometry neither lowers nor raises the excess." Add an epochs note to the table's NGC 300 row.
7. **M81.** Remove the table row; keep one sentence (tip not located, 164 stars).
8. **Ordering paragraph, first two sentences.** Replace with: "Seven of the values, taken from four different
   measurements, can be put in an order that resembles metallicity (Spearman ρ = 0.82, n = 7, p = 0.02, chosen after the
   fact); adding the three values set aside here gives ρ = 0.16. M31's value is not comparable (its tip), IC 2574's is
   0.027, 0.029 or 0.046 depending on the measurement, and inside M31 the statistic changes by a factor of several
   between bulge and outer disc." Keep the rest. Delete "and inside M31 the value falls outward as metallicity does".
9. **Librarian.** "30 in published Mira lists, 28 of them matched…" becomes "28 Miras of Yuan et al. 2017 and 2 DIRECT
   variables of unstated type"; "245 or so" becomes "249, of which 112 were never checked against a variable-star
   index"; count the Cepheid once.
10. **Status line and abstract** need no change, provided M31 stays out of them.

## Probability that the M31 excess over the LMC is astrophysical

**About 65%** that red stars above M31's tip really change by more than 0.3 mag in F814W more often than the LMC's, for
reasons belonging to the stars and not to the photometry, the box or the selection.

- For (pushing towards 90% that the variability itself is real): the step at the published tip, which no artifact
  knows about; 0.07% at short lag in the same pixels; clean colour-matched faint slices; no dependence on chip
  position or programme; equal numbers dimming and brightening; a factor of 3 to 5 over the LMC in the inner galaxy,
  too large for any box effect I can construct.
- Against: the published number is from a misplaced box; colours are in different systems with no transformation and
  M31's box is a magnitude redder; the redder, dustier 12% are dropped; the LMC denominator is Gaia members while M31's
  is catalogue stars passing shape cuts; a fixed 0.3 mag threshold in I favours late-M oxygen-rich stars, whose I-band
  amplitude is inflated by TiO, over the LMC's carbon stars; and the outer disc at ordinary colours matches the LMC.
- That it is an effect of metallicity on pulsation, as opposed to bulge age, spectral type or box make-up: no more
  than 20 to 25%, and this dataset cannot raise it.

## Decisive follow-ups

1. Redo M31 with the tip fixed at the published value per colour (the tip in F814W as a function of colour is
   published for PHAT), and report the raw fraction above the tip by radius and colour, not E.
2. One LMC reference in F475W−F814W-equivalent colour (synthetic from V and I), split into oxygen-rich and carbon
   stars using the OGLE spectral-type flag already in `lmc_population.csv`.
3. M32 and the M31 bulge against Galactic-bulge OGLE: an old metal-rich reference would test whether 25% is what such
   a population gives.

## Tool fixes

- `tip_edge`: refuse an edge in the outermost bin (already owed), and normalise the Sobel response so that a smooth
  rising function has no maximum; report the published tip beside the found one when the catalogue has it.
- `04_measure.py`: report the fraction of above-tip stars dropped for lack of colour, per galaxy, in the output row.
- `16_psf.py`: restrict "same stars" to pairs whose catalogue epochs match the ANGST epochs; use `ebv`; record a chance
  rate for the catalogue match; widen the offset grid.
- `oddsky.data.hsc._pages`: a page of exactly `PAGE` rows followed by an empty reply should raise or retry, not end.
- `17_m31.py`: errors from image pairs by default once χ² per degree of freedom exceeds 1.
