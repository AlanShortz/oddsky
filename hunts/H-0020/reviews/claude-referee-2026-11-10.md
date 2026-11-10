# Referee report: H-0020 twice-seen (tool, HSC quality card, AGB atlas v0, H-0019 correction)

Referee: claude-referee, 2026-11-10. Everything below was recomputed with my own scripts (pandas/numpy/scipy on the
parquet files plus calls into `oddsky.analysis.twiceseen`; scratch code in `/tmp/ref/`, not part of the repo). No file
other than this one was changed. Nothing was downloaded.

## Verdict

1. The tool runs, its arithmetic reproduces (every number in `work/*.csv` came back exactly), and the paging fix is sound;
   but four of the README's readings of the numbers are wrong: the "physical check" is circular, the IC 2574 explanation
   points the wrong way, a chip gap sits inside the "common sky" of two fields, and "lower bounds on depth" is not a bound.
2. The HSC quality card is real and its sign is right (HSC too bright next to neighbours), but its "isolated" class below
   the tip is 29% crowded stars by a truncation bug, "recovered" mostly measures centroid displacement, and the atlas
   attaches the *all-sources* card to stars that were selected with a concentration-index cut (the right rows say 54 to 84%
   recovered, not 89 to 99%).
3. Not ready to show an astronomer as written. Fixable in a day: nothing found here kills the idea, and two of the
   findings (the chip gap, the colour dependence of loss) are things the tool should be reporting as results.

## Findings

Severity: **blocking** = a stated result or reading is wrong; **should-fix** = misleading or fragile; **note** = for the record.

### A. The numbers (priority 1)

**A1 (note). Reproduction.** Re-ran part A (five pairs) and part B (seven fields): `n_truth`, horizon, m50, S/N at m50,
recovered isolated/crowded, zero points, tie rms all reproduce to the last digit. `tests/test_twiceseen.py`: 6 passed.
Atlas: 76,986 stars, 42 galaxies, 55,183 with a pair more than 100 days apart (minimum lag 105 d), 138 Yuan Miras, three
`tip_soft` galaxies: all correct.

**A2 (should-fix). Wrong or loose numbers in `hunts/H-0020/README.md`.**

| README says | From the files | Fix |
|---|---|---|
| "own card for four galaxies" | five (NGC 300, NGC 4163, KKH 37, Garland, IC 2574) | "five" |
| "Pooling it onto 38 other galaxies" | 42 − 5 = 37 | "37" |
| "89,354 truth stars" | 91,519 truth stars in the common sky; 89,514 within 2 mag above to 1 mag below the tip; 89,354 is the sum of the isolated and crowded bins that had 20 or more stars | "91,519 truth stars (89,514 in the range tabulated)" |
| "returns a planted half-recovery magnitude to 0.08 mag" | 0.08 is the test's tolerance; the error over five seeds is −0.009 to +0.011 | "to 0.01 mag (five seeds)" |
| "5.3% of isolated stars above the tip ... against 4.5% of crowded" | true only for 0 to 1 mag above the tip (619/11,774 = 5.26 ± 0.21% against 446/9,847 = 4.53 ± 0.21%; difference 0.7 ± 0.3, 2.4σ). For all stars above the tip it is 4.6% against 4.2% | say "0 to 1 mag above the tip" and give the errors; "separates" is too strong for 2.4σ |
| "offset −0.001" (isolated, above tip) | −0.0015 | "−0.002" or "0.00" |
| "(IC 2574: 73,982 stored of 91,270)" | not verifiable: the complete file has 98,113 summary rows; `hsc.py`'s docstring says "98,000 ... returned 87,245". Three different pairs of numbers for one event | state one pair and where it comes from, or drop it |
| "losing a fifth of its rows" | detail-table rows lost per galaxy, from `measure.csv` before/after: 15% (M33, NGC 7793) to 32% (NGC 1313, NGC 4244); IC 2574 30% | "15 to 32% of rows, galaxy by galaxy" |
| "In NGC 4163 recovery rises from 77% in the central 10 arcsec to 93% beyond 80" | all stars in the valid range: 75% to 90%; bright isolated: 78% to 96%; **with the chip gap removed (B3): 83% to 92%, and 87% to 96%** | see B3 |

**A3 (should-fix). H-0019 correction block.** 21,494 stars / 14 galaxies / 0.0341 ± 0.0017 (20.7σ) / T3 0.0012 ± 0.0007 /
T5 0.0338 ± 0.0019 against 0.0338 ± 0.0035 / five clean fields 0.0466 ± 0.0025 (was 0.0437 ± 0.0028) / 76 of 107 Miras /
399 candidates (was 282): all correct. Two statements are not:

- "No galaxy moved by more than its error." NGC 300 moved from 0.0488 ± 0.0041 to 0.0535 ± 0.0038: 0.0047, which is 1.15
  to 1.24 of its error (and the two samples share most of their stars, so the errors are not independent).
- The block does not say the tips were measured again and moved: NGC 3077 from 24.29 to 24.64 (that, not only the extra
  rows, is why it "now qualifies") and NGC 300 from 23.24 to 23.19 (probably why its excess moved).

"Conclusions are unchanged" is fair for the pooled number. It should be qualified: one preregistered test (T3) changed its
verdict from fail to pass, and one galaxy entered because its tip moved by 0.35 mag. Replacement wording:
"The pooled result is unchanged. T3 changed from fail to pass. Tips were re-measured on the complete catalogues: NGC 3077's
moved by 0.35 mag (which is why it now qualifies) and NGC 300's by 0.05; NGC 300's excess moved by 1.2 of its error, no
other galaxy by more than one."

### B. The tool (priority 2)

**B1 (note). `tie()` does not over-fit, and the cubic term does nothing on any real pair.** I ran every real tie (five
short/long pairs, seven HSC fields) with `order=1` and `order=3`: matched counts differ by 0 to 3 stars out of thousands
(e.g. Garland 24,472 against 24,474; NGC 300 wide3 34,728 against 34,731), rms identical. Fed unrelated sky (truth mirrored
in x, rotated 180 degrees, shifted 5 arcsec), the cubic produces no more matches than the affine fit and no more than the
chance count (e.g. KKH 37: 713 affine, 723 cubic, 705 chance). So: no manufactured matches. But the comment in the code
("enough to lose a fifth of the stars at a 0.07 arcsec radius") is not reproduced by any data on disk, and README section
4 lists the polynomial as something "fixed on the way". Either show the pair where it matters or say it is a precaution.

**B2 (should-fix). `tie()`/`quality()` do not refuse overlapping but untied catalogues.** In all those unrelated-sky
trials `tie()` returned a fit whose matches equal the chance count, and `quality()` went on to print a table (mirrored
test field: 359 "matched" of 27,487, `n_chance` 347, no error). "Catalogues of different fields refused" is true only when
the two do not overlap on the sky at all. `n_chance` is computed and never used. Refuse when matches < 3 × chance.

**B3 (blocking). The convex-hull footprint keeps the short visit's chip gap inside the "common sky".** The two snapshot
visits (programme 9771) are not dithered across the ACS gap. Projecting the test catalogue along the detector axis finds
an empty strip 2.5 arcsec wide in NGC 4163 (position angle 173.8 degrees, 8 arcsec from the galaxy's centre) and 2.75
arcsec wide in KKH 37 (128.0 degrees, 9 arcsec from the centre). It holds 3.6% and 6.0% of the common truth stars, of
which 2% are "recovered".

| | README | gap removed |
|---|---|---|
| NGC 4163, bright isolated stars recovered | 90% | 93.5% |
| KKH 37, bright isolated stars recovered | 84% (85.1% for the stars 1 mag above the horizon) | 89.3% |
| NGC 4163, all stars in the valid range | 83.6% | 87.6% |
| KKH 37, all stars in the valid range | 81.1% | 85.8% |
| share of the missed bright isolated stars that lie in the gap | | 141 of 421; 51 of 161 |

The radial trend in NGC 4163 survives (bright isolated stars, gap removed: 87% inside 10 arcsec, 96% beyond 80), so the
README's reading "real loss in the good-star list" is right for two thirds of the loss and wrong for one third. A tool
whose first job is completeness must find a 2.5 arcsec hole on its own: `footprint="cells"` with small cells would have,
`"hull"` cannot. Also: KKH 37 beyond 80 arcsec recovers 49% of 76 stars, an edge the 0.97 hull shrink does not remove.

**B4 (note). Chance correction: adequate.** (a) Direction and size of the shift: with shifts of 0.5, 1, 3 arcsec in four
directions and two diagonals the chance rate varies by ±6% of itself (Garland 0.090 to 0.103; NGC 4163 0.079 to 0.085;
KKH 37 0.042 to 0.049; IC 2574 0.118 to 0.129); a 10 arcsec shift is worse (Garland 0.078 to 0.108) because it leaves the
local density. An estimate from the test-star density in a 0.3 to 1 arcsec ring around each truth star agrees (0.0915,
0.0777, 0.0443, 0.0211, 0.1192). Effect on completeness: under one point. Use the ring; it has no direction. (b) One-to-one
is not enforced: test stars claimed by two truth stars are 69, 5, 126, 6, 93 (0.33%, 0.06%, 0.21%, 0.07%, 0.54% of the
matches). Negligible here. (c) The formula (raw − p)/(1 − p) is right for "found = real or chance". What it does not do
is clean the magnitude statistics: offset, scatter and the gross-error rate are computed on all matches including the
chance ones. With p = 0.10 to 0.12 (Garland, IC 2574) and completeness 0.5, a sixth of the "found" stars in that bin are
chance matches, and they dominate the gross-error rate there. Either subtract the chance population's Δm distribution or
blank those three columns when chance matches exceed, say, 5% of the matches in the bin.

**B5 (should-fix). Matching has no magnitude tolerance, so a blend's fainter member counts as "found".** Adversarial
simulation (`/tmp/ref/s1.py`): 74,000 stars with a dense core, luminosity function rising to 28; the test catalogue merges
every friends-of-friends group at a resolution r (flux summed, flux-weighted centroid), then detects on the merged
magnitude. Ground truth per star: it is the dominant member of a detected object ("strict"), or anything is there within
0.75 mag (the artificial-star convention).

r = 0.10 arcsec (PSF photometry; 31% of truth stars in a blend):

| class, mag | tool completeness | true (strict / AST) | tool gross | true gross | found only as a blend's secondary |
|---|---|---|---|---|---|
| isolated, 24 to 25 | 0.969 | 0.970 / 0.970 | 0.009 | 0.010 | 0.000 |
| isolated, 25 to 25.5 | 0.736 | 0.745 / 0.745 | 0.026 | 0.026 | 0.000 |
| crowded, 23 to 24 | 0.977 | 0.938 / 0.925 | 0.137 | 0.101 | 0.046 |
| crowded, 24 to 25 | 0.925 | 0.862 / 0.850 | 0.181 | 0.116 | 0.072 |
| crowded, 25 to 25.5 | 0.708 | 0.640 / 0.625 | 0.246 | 0.147 | 0.090 |

r = 0.20 arcsec (aperture-like; 69% in a blend): the error reverses. Crowded 20 to 23: tool 0.504, true 0.684 / 0.553; tool
gross 0.256, true 0.427. The bright member of a blend is in the catalogue but its centroid has moved by more than the
0.07 arcsec radius (18% of that class), so it is counted lost and its gross error is never counted.

So: isolated stars come back right. For crowded stars the tool overstates completeness by 4 to 7 points when the test
catalogue resolves about as well as the truth, understates it by up to 18 when it does not, and the gross-error rate is
wrong in the opposite sense each time. Completeness and gross-error rate are not separate measurements; they trade
against each other through the match radius. Fix: add a magnitude tolerance (found = within the radius *and* within
0.75 mag, the DOLPHOT convention), and report a third state, "displaced" (no match within the radius, a source of
comparable or greater flux within three radii).

**B6 (should-fix). `covered()` is biased upward by construction, but not measurably on these data.** A truth star in a cell
with no test star is always a miss, and the cell is dropped. Simulation (uniform field, test = random subset with
completeness c, 8 arcsec cells): with 1 test star per cell the tool returns 0.63 / 0.80 / 0.93 for c = 0.5 / 0.7 / 0.9; with
2 per cell 0.55 / 0.74 / 0.91; with 4 or more it is right to 0.01. (It also discards 8% of a 400 arcsec field at the
edges.) On the seven real fields, cells and hull differ by 0.3 points or less in every class (e.g. crowded below the tip
0.8917 cells, 0.8930 hull), and the 712 stars the cells drop inside both hulls are 97.8% found: no upward bias, because
HSC is built from the same images and has no holes there. The function should refuse, or warn, below about 4 test stars
per cell, and it cannot detect a region where the test catalogue lost everything, which is the case it was written for.

**B7 (blocking for the wording). `horizon()` and "lower bounds, not measurements".**

- The M81 pair is the test case. The truth catalogue's signal-to-noise at the tool's horizon (26.83) is 34, and at the
  short visit's half-recovery (27.07) it is 28. The short visit's completeness goes 0.93 (25.4) → 0.86 (26.4) → 0.81 (26.6)
  → 0.68 (26.9) → 0.45 (27.1) → 0.19 (27.4) → 0.05 (27.6) → 0.00 (27.9) entirely where the truth has S/N above 14. That curve
  is a measurement. The rule discards it. Same for Garland (truth S/N 17 at half-recovery). For KKH 37, NGC 4163 and IC 2574
  the truth's S/N at half-recovery is 8.6, 7.1 and 10.
- The reason the rule fires in M81: the peak of the truth luminosity function there (27.83) is the red clump of M81, not
  the completeness turnover, which is a magnitude fainter (second peak at 28.9; the catalogue runs to 29.4). The peak of a
  luminosity function is an astrophysical feature as often as an instrumental one. Here it errs on the safe side by luck.
- "Lower bounds on depth" is the wrong phrase in both directions. Beyond the horizon, shared crowding makes recovery look
  too high (true half-recovery brighter than measured), while noise in the truth magnitudes makes it look too low (stars
  scattered bright in the truth are really fainter). In a pure-noise simulation with catalogues of equal depth
  (`/tmp/ref/s2.py`) the tool's completeness at the truth's peak is 0.53 against a true 0.68, i.e. *under*stated; with
  shared blending it is overstated. It is not a bound.
- In the same simulation the rule is safe: with the truth 1 mag or more deeper the last valid bin agrees with the true
  value to 0.02, and the planted half-recovery comes back to 0.04 mag although it lies 0.1 to 0.7 mag *beyond* the horizon. One magnitude is
  roughly twice the margin this toy needs; it is not derived, as the README says.

Replacement for the first bullet under the table: "Every half-recovery magnitude is fainter than the horizon the tool
allows itself, so the tool marks them unverified. For M81 and Garland the rule is far too cautious: the deep visit has
signal-to-noise 28 and 17 at those magnitudes, and the roll-off is measured. For KKH 37, NGC 4163 and IC 2574 (truth
signal-to-noise 7 to 10 there) the values are uncertain in both directions, not bounds." The tool should take the truth's
signal-to-noise or error column when there is one (trust the truth where its S/N is 10 or more), and fall back to the
luminosity function only when there is not.

**B8 (blocking for the wording). The equal-depth bias is an equal-*resolution* bias, and its size.** Simulation: both
catalogues blend the same groups at 0.10 arcsec (same telescope), each with independent photon noise and an S/N cut at 4;
the truth is 0 to 3 mag deeper. Against the true fraction of real stars that are the dominant member of a detected
object:

| truth deeper by | tool, 22 to 24 mag | true | tool, 24 to 24.75 | true | tool, 24.75 to 25.25 (1 mag above the test's limit) | true |
|---|---|---|---|---|---|---|
| 0.16 mag | 1.000 | 0.975 | 1.000 | 0.943 | 1.000 | 0.921 |
| 1 mag | 1.000 | 0.975 | 1.000 | 0.943 | 1.000 | 0.921 |
| 3 mag | 1.000 | 0.975 | 1.000 | 0.943 | 1.000 | 0.921 |

(`/tmp/ref/s3.py`; 60,000 stars, a dense core, about a fifth of stars in a blend.) The overstatement (2.5 points for bright
stars, 6 to 8 a magnitude above the limit, at this density) is identical whether the truth is 0.16 or 3 mag deeper. A deeper image from the same telescope does not unblend anything. So all five rows of part A
measure "of the stars the long ACS visit separated, how many did the short ACS visit keep", and the stars both visits lose
to blending are invisible at any exposure ratio. The docstring and README section 1 say "two catalogues of equal depth
overstate completeness"; that should read "two catalogues of equal resolution, whatever their depths". With noise alone
and no blending, equal depth costs only 0.07 mag in half-recovery (and in the *brighter* direction).

**B9 (note). Zero point.** Taking it from bright isolated found stars is fine in simulation and in part B. But it hides a
result: the Garland pair has a zero point of −0.104 mag between two ANGST catalogues of the same stars in the same band
(M81 +0.045, KKH 37 +0.023, others under 0.02). The short visit's S/N is 3 to 6% above the √t prediction there, consistent
with a real 10% flux difference. A tenth of a magnitude between two DOLPHOT reductions of bright isolated stars deserves
a line in the README; it is larger than anything the card attributes to HSC for isolated stars.

**B10 (note). Float32 coordinates.** Every RA and Dec in the ANGST files is exactly representable in float32: positions are
quantised at 0.014 to 0.027 arcsec in Dec and 0.027 to 0.055 arcsec in RA (0.005 to 0.02 on the sky at these declinations).
That is most of the 18 to 21 mas tie rms. It does not cost matches at 0.07 arcsec (see C2) but it sets a floor: do not
shrink the radius below about 0.05.

### C. The physical check and the bright-star plateau (priorities 3 and 4)

**C1 (blocking). "Half-recovery lands at S/N 4.5 to 5.2, just above the cut at 4" is circular.** The number is the median
S/N of the short catalogue's stars near m50. Every star in that catalogue has S/N of 4 or more by construction (minimum
4.0 in all five; 10th percentile 4.1 to 4.6 near m50), so the median of survivors near the faint end is 4.5 to 5 almost
whatever m50 is. The selection is visible in the data: for recovered stars, short-visit S/N divided by the value predicted
from the deep visit is 1.00 ± 0.05 down to S/N 6, then 1.08 to 1.19 at m50 and 1.3 to 2 below it.

The non-circular check, done with the files on disk: take the *deep* visit's S/N for each truth star, scale it to the short
exposure (I used the ratio measured from stars with short-visit S/N above 15; it agrees with √(exposure ratio) to 5%
except in IC 2574, 0.78 against 0.87), and ask where the predicted short-visit S/N crosses 4.

| field | m50 | predicted S/N = 4 at | m50 is brighter by | predicted short S/N at m50 | README's (circular) S/N |
|---|---|---|---|---|---|
| NGC 4163 | 26.96 | 27.09 | 0.13 | 4.5 | 4.5 |
| KKH 37 | 26.90 | 27.19 | 0.29 | 5.0 | 4.9 |
| Garland | 27.28 | 27.59 | 0.31 | 5.2 | 4.5 |
| M81 outer | 27.07 | 27.69 | 0.62 | 6.7 | 5.2 |
| IC 2574 | 27.27 | 28.08 | 0.81 | 7.9 | 7.7 |

So the check holds for three fields (half-recovery 0.1 to 0.3 mag brighter than the predicted S/N = 4 point, which is where
a two-filter cut with a plateau of 0.85 to 0.93 should put it), and fails for two, not one.

**C2 (blocking). IC 2574's 7.7 is not the equal-depth bias; it and M81 are the other filter.** The equal-depth bias
overstates completeness, which would push m50 *fainter* and the S/N there *down*. IC 2574 is off in the opposite direction
by 0.8 mag. What the data show instead: the good-star list requires S/N of 4 in both filters, and the loss near m50
depends on colour. Recovery in the half magnitude above m50, bluest to reddest quartile of truth colour: IC 2574 0.78,
0.74, 0.69, 0.59; M81 0.76, 0.73, 0.72, 0.63; Garland 0.77, 0.76, 0.76, 0.71. And in M81 the *bright* isolated stars
(brighter than 25.8) are recovered at 95 to 98% in four colour quintiles and 78% in the reddest (F606W−F814W above 2.1):
those stars are below S/N 4 in the short F606W exposure. A completeness table in one band hides this, and the stars it
hides are the reddest giants, which are the subject of the atlas. The tool needs a colour axis (or a second magnitude
column) whenever the test catalogue was cut in two bands.

**C3 (should-fix). The bright-star plateau: real, minus the chip gap.** Tested on isolated truth stars at least 1 mag
brighter than the horizon:

- *Match radius, float32, proper motion*: no. Looking for a test star of similar magnitude (within 0.75 mag) around each
  missed star: 0.0 to 0.5% lie at 0.07 to 0.15 arcsec and 0.1% at 0.15 to 0.3 arcsec. The missed stars have no counterpart
  nearby; they are absent from the short visit's good-star list.
- *Chip gap*: yes, in NGC 4163 and KKH 37, a third of the misses (B3). No strip in Garland, M81 or IC 2574 (strongest
  3 arcsec strip deficit 4 to 6σ over 180 trial angles, against 46σ and 18σ).
- *Truth catalogue's own crowding measure*: strong. Recovery for `crowd2` under 0.02 / 0.02 to 0.05 / 0.05 to 0.1: Garland
  0.96 / 0.91 / 0.75; KKH 37 0.87 / 0.75 / 0.46; NGC 4163 0.92 / 0.82 / 0.55; IC 2574 0.97 / 0.78 / 0.53. These are stars the
  tool calls "isolated": its neighbour count within 0.5 arcsec misses what DOLPHOT's own crowding parameter sees.
- *Second filter*: yes for the reddest stars in M81 (C2); weak elsewhere.
- *Footprint edge*: KKH 37 beyond 80 arcsec, 63% of 27.

Corrected plateau for bright isolated stars: Garland 94.8%, KKH 37 89.3% (gap removed), NGC 4163 93.5% (gap removed), M81
92.6% (96% without the reddest fifth), IC 2574 93.7%. Replacement for the README bullet: "Bright isolated stars are 89 to
95% recovered in the short visits once the chip gap of the two snapshot visits is removed (it accounts for a third of the
loss there and the tool did not see it). The rest follows the deep catalogue's own crowding parameter and, in M81, the
star's colour: the reddest fifth is 78% recovered because the short F606W exposure does not reach S/N 4. Not yet checked
against ANGST's artificial stars."

### D. The HSC quality card (priority 5)

**D1 (blocking). The crowding class is computed after the truth catalogue is cut at 1 mag below the tip.**
`01_twice_seen.py` truncates `truth` to `mag < tip + 1.0` and `quality()` then counts neighbours "no more than a magnitude
fainter" in that truncated list. A star 0.9 mag below the tip can only see neighbours up to 0.1 mag fainter than itself.
Counting neighbours in the full-depth catalogue, 28.9% of the "isolated, up to 1 mag below" class is crowded (6.8% in the
first quarter magnitude, 44% in the last). Above the tip nothing changes. Corrected rows (star-pooled, same footprint and
radius):

| stars | recovered | offset | scatter | off by more than 0.3 |
|---|---|---|---|---|
| up to 1 mag below, isolated (was 97.2%, −0.027, 0.084, 4.4%) | 98.0% | −0.016 | 0.070 | 2.3% |
| up to 1 mag below, crowded (was 89.3%, −0.073, 0.124, 12.7%) | 91.2% | −0.064 | 0.118 | 10.7% |

Fix: pass the full truth catalogue and restrict the magnitude range in the tabulation, not before the neighbour count.

**D2 (blocking for the wording). "Recovered" in the card is mostly "not displaced".** Of the 2,810 crowded truth stars
below the tip with no HSC source within 0.10 arcsec, 55% have one within 0.15 and 89% within 0.25 (a random position
would have one within 0.25 about a quarter of the time); 4% have nothing within 0.5. With a radius of 0.15 the same class
is 95.4% "recovered", with 0.25, 98.9%. For isolated stars above the tip the radius hardly matters (99.0%, 99.4%, 99.4%)
and 44% of the 139 missing ones really have nothing within 0.5 arcsec. So HSC does not lose 11% of crowded stars below
the tip; it has them inside blends whose centroid moved by more than 0.10 arcsec, and those are exactly the stars whose
photometry is worst, so the 13% gross-error rate is an underestimate for the class (the simulation in B5 shows the same
trade). Replacement wording for the abstract: "crowded stars just below the tip: 9% have no catalogue source within 0.10
arcsec (nearly all are inside a blend displaced by 0.10 to 0.25 arcsec, not absent), and of those matched, 11% are more
than 0.3 mag too bright."

**D3 (note). Whose error is the −0.07 mag? The data favour HSC.** Three tests. (i) Stars with no DOLPHOT neighbour of any
brightness within 0.6 arcsec show no offset at any magnitude: −0.006, −0.009, −0.005, −0.004 from 2 mag above to 1 mag
below the tip. So there is no magnitude-dependent term in either catalogue; the offset exists only next to neighbours.
(ii) Where DOLPHOT resolves a neighbour *inside* HSC's 0.15 arcsec aperture, HSC is brighter by about the neighbour's
flux: predicted −0.65, −0.31, −0.15 mag against observed −0.54, −0.24, −0.08. That is aperture blending, not DOLPHOT
over-subtraction, which has no reason to scale that way. (iii) The gross errors of crowded stars are one-sided: 12.4% too
bright, 0.2% too faint. But only 2.5% of matched stars have a resolved neighbour inside the aperture; most of the class
median comes from neighbours at 0.15 to 0.5 arcsec, where the two explanations (PSF wings in the aperture, DOLPHOT
giving flux to the neighbour) predict the same sign and these two catalogues cannot separate them. A third measurement
would (the short and long DOLPHOT visits of part A compared for the same crowded stars is the cheap one). Wording: "HSC is
brighter than DOLPHOT next to neighbours, by the neighbour's flux where the neighbour falls in the aperture" is supported;
"DOLPHOT is truth for crowded stars" is assumed.

**D4 (should-fix). Above the tip, part of the "gross error" is the stars varying.** For isolated stars above the tip the
1.8% beyond 0.3 mag is symmetric (0.97% too bright, 0.81% too faint), unlike the blending signature. The truth is one
epoch; the HSC magnitude is a median over visits at other epochs; and stars above the tip are long-period variables at the
3 to 5% level by H-0019's own measurement. The card cannot tell a photometric error from a real change there. The README's
"same phenomenon as the 1.5% of control stars" holds for the stars below the tip. Say so.

**D5 (should-fix). Field to field the card is not stable, and the pooled card is mostly one field.** Gross-error rate,
crowded stars below the tip: 0.9% (NGC 300 wide1), 3.8% (wide2), 13.7% (wide3), 12.8% (NGC 4163), 11.0% (Garland), 9.1%
(IC 2574), 5.8% (KKH 37). Isolated above the tip: 0.6% to 3.4%. Offset for crowded stars below the tip: −0.034 to −0.082.
The three NGC 300 fields differ by a factor of fifteen from each other, so even "the galaxy's own card" is the wrong
unit; and 57% of the pooled crowded-below-tip stars come from NGC 300 wide3 alone. The controlling variable is local
surface density, not galaxy. The README's ranges for recovered fraction are honest; give the same ranges for the gross
rate, where the spread is.

**D6 (blocking for the atlas). `02_atlas.py` attaches the wrong card.** Four problems, in order of size:

1. The atlas stars come from H-0019's pairs, which were selected with concentration index 0.85 to 1.30 and Flags = 0
   (`04_measure.py` lines 73 and 107). The atlas attaches the card for *all sources*. `hsc_quality.csv` already holds the
   right rows ("point-like"):

   | stars | all sources (attached) | point-like (applies) |
   |---|---|---|
   | above tip, isolated: recovered / gross | 99.0% / 1.8% | 83.5% (75.7 to 94.6) / 0.9% |
   | above tip, crowded | 96.8% / 5.6% | 60.9% (44.0 to 80.4) / 1.8% |
   | below tip, isolated | 97.2% / 4.4% | 72.8% (63.9 to 89.3) / 0.6% |
   | below tip, crowded | 89.3% / 12.7% | 54.5% (49.0 to 82.1) / 1.2% |

   Every `q_completeness` in the atlas is too high by 15 to 35 points and every `q_gross` too high by a factor of 2 to 10.
   Conclusion 2 of the README ("the numbers are now attached to every star in the atlas") is not true of the right numbers.
2. The two "crowded" definitions are different things. The card counts DOLPHOT neighbours; the atlas counts HSC
   neighbours. For matched stars, of those the atlas rule calls crowded only 68% (above the tip) and 61% (below) are
   crowded in the card's sense; of the card's isolated stars below the tip, 34% are crowded by the atlas rule. Tabulated
   by the atlas's own rule, the all-sources card would read: above/crowded −0.016 mag, 3.7% gross (attached: −0.029,
   5.6%); below/crowded −0.057, 8.9% (attached: −0.073, 12.7%); below/isolated −0.019, 5.4% (attached: −0.027, 4.4%). The
   card must be built with the classification the atlas can compute, i.e. from HSC neighbours.
3. The HSC list stops 1.3 mag below the tip, so for the 17,497 atlas stars (23%) more than 0.3 mag below the tip the
   neighbour count "no more than 1 mag fainter" is truncated, as in D1.
4. KKH 37 has no "crowded, above tip" row of its own (16 stars); those atlas stars silently get the pooled values while
   `q_source` says "this galaxy".

**D7 (should-fix). Pooling onto 37 galaxies as "version 0".** Defensible only as a column labelled as a placeholder, and
not as it stands: 18 of the 37 are closer than 1.5 Mpc and hold 22,283 of the 76,986 stars (M33 and IC 10 alone 20,856),
where a star at the tip is 3 mag brighter in the frame and the crowding regime is different from anything in the five
calibrating galaxies (2.2 to 4.0 Mpc). Given D5, a card indexed by local HSC source density would transfer; one indexed
by galaxy does not. Until then set `q_*` to missing outside the calibrated range of distance and density.

### E. The paging fix (priority 6)

**E1 (note). `_pages` is correct for this sample.** Slices are half-open [lo, hi) with the same float used for `lt` and
`gte` at each split, so a row at exactly `mid` goes right once and only once; a full page forces a split; a slice that
cannot be split raises `Truncated`. On disk: all 52 summary files have zero duplicate `MatchID`, zero duplicate positions
and zero null `MatchRA`; all detail files have zero duplicate (`MatchID`, `SourceID`, `ImageID`). Independent evidence of
completeness: isolated stars above the tip are 98.4 to 100% present in all seven DOLPHOT fields, so no slab is missing
there. Galaxies fetched in one page before and after (Garland, KKH 37, NGC 4163, Sag dIr) have identical numbers in
`refetch_comparison.csv`, as they should.

**E2 (should-fix). Remaining ways to lose rows silently.**
- *RA wrap.* `_ra_span` returns `ra ± half` with no wrap; a cone crossing 0/360 would send a negative or >360 bound and
  lose the far side without error. Not triggered: I evaluated every cone in `probe.csv` (minimum lower bound 0.39 degrees,
  WLM) and NGC 7793's tiles end at 359.70. Raise if the span leaves [0, 360), or split it.
- *Poles.* The cosine is clipped at |dec| + radius = 89.9; beyond that the span is too narrow. Not triggered (maximum
  |dec| 70.7). Raise.
- *A short page that is not the end.* Completeness rests on "fewer than 50,000 rows means all of them". A server-side
  cap below 50,000, or a truncated body that still parses as CSV, would be accepted. There is no independent row count.
  Add one cross-check per query (the count endpoint if the service has one; otherwise re-ask one random sub-slice and
  compare).
- *Rows with a null `MatchRA`* would be dropped by the range filter. None is expected in this table; say so in the
  docstring.
- `drop_duplicates` after the fact would mask an overlap bug; assert there are none instead.
- The three row counts quoted for IC 2574 (README 73,982 of 91,270; docstring 87,245 of 98,000; disk 98,113) need
  reconciling (A2).

### F. Prior art (priority 7)

**F1 (should-fix). The framing is nearly fair and needs two sentences more.** "Completeness measured against a deeper
catalogue is an old idea in survey work" is true and is the right thing to say; the README does not claim the idea. What
a professional will expect to see named:

- Artificial-star tests themselves: Stetson 1987 (DAOPHOT, ADDSTAR); Stetson & Harris 1988; Aparicio & Gallart 1995 and
  Gallart et al. 1996 (crowding tests, and the point that recovered magnitudes are biased bright); Dolphin 2000 (HSTphot)
  and the DOLPHOT documentation; Dalcanton et al. 2009 (ANGST: the completeness limits this hunt wants to compare with)
  and Williams et al. 2014 (PHAT: artificial stars as a function of local stellar density, which is finding D5).
- Crowding-limited photometry predicted from the luminosity function: Olsen, Blum & Rigaut 2003.
- External completeness from a deeper or sharper catalogue: routine for ground-based surveys against HST (e.g. Bellazzini
  et al. 2002 for star counts in clusters); Gaia's completeness in crowded fields against HST and OGLE (Arenou et al. 2018)
  and against DECaPS (Cantat-Gaudin et al. 2023); the selection-function programme of Boubert & Everall 2020 and Rix et
  al. 2021; the DES deep-field and Balrog injection work (Suchyta et al. 2016; Everett et al. 2022), which states the
  trade-off between "inject" and "compare with deep" that this README is rediscovering.
- The catalogue itself: Whitmore et al. 2016 (HSC; its own comparisons of photometric repeatability and its warnings on
  crowded fields) and Bonanos et al. 2019 (Hubble Catalog of Variables, which had to model HSC's photometric noise).

I did not search the literature today for an existing HSC-against-DOLPHOT quality comparison; the claim "a catalogue that
ships with no quality model at all" should be checked against Whitmore et al. 2016 section 5 and the HCV papers before it
is repeated outside. What is plausibly new here is small and concrete: a per-class card for HSC v3 near the tip against
ANGST. Say that, not "a general, tested routine": after this report the routine is tested and found to need a magnitude
tolerance, a gap-aware footprint and a colour axis.

## Required changes

### (a) README

1. Abstract and section 3: replace the S/N sentence with the non-circular table of C1 ("predicted from the deep visit,
   half-recovery falls at S/N 4.5, 5.0 and 5.2 in three fields, 6.7 and 7.9 in M81 and IC 2574, where red stars are lost
   to the second filter's cut").
2. Remove "IC 2574 gives 7.7, the equal-depth bias the docstring warns of" (C2).
3. Replace "lower bounds on depth, not measurements" with the wording in B7.
4. Replace the bright-star bullet with the wording in C3; add the chip gap as a finding and as a failure of the tool.
5. Section 1 "What it cannot do": "two catalogues of equal *resolution* overstate completeness whatever their depths: in
   a simulation with a fifth of the stars blended, by 2.5 points for bright stars and 6 to 8 points a magnitude above
   the limit" (B8).
   Add: "for crowded stars the recovered fraction and the gross-error rate depend on the match radius and trade against
   each other" (B5, D2).
6. Card table: recompute after D1; add the point-like rows; add the range of the gross rate across fields (D5); reword
   "recovered" per D2; add D4's caveat on variable stars above the tip; soften "PSF photometry as truth" per D3.
7. Atlas paragraph: "five", "37"; state that `q_*` is being rebuilt (D6) or withdraw conclusion 2; restate the 5.3% against
   4.5% with its range and errors (A2).
8. Fix the numbers in A2. Reconcile the IC 2574 row counts.
9. Section 4: delete or substantiate "the polynomial distortion term" (B1); add the Garland zero point of −0.10 mag (B9).
10. H-0019 correction block: wording in A3.
11. Prior art: two sentences and the references in F1.

### (b) Tool

1. `quality()`: magnitude tolerance on a match (default 0.75 mag after the zero point); a "displaced" state; chance rate
   from a ring around each star instead of one shift; blank offset/scatter/gross where chance matches exceed 5% of matches.
2. Footprint: detect empty strips and holes in the test catalogue at the scale of a chip gap (occupancy on cells of about
   2 arcsec along the detector axes, or a Delaunay-based alpha shape); warn when `cells` has under 4 test stars per cell.
3. `tie()`/`quality()`: refuse when matches < 3 × `n_chance`; test with a mirrored field.
4. `horizon()`: accept a truth S/N or error column and trust the truth where S/N is 10 or more; keep the
   luminosity-function rule as fallback and look for the *faintest* significant peak, not the highest.
5. Optional second column (colour or second-band magnitude) in the table; at minimum a warning that a catalogue cut in two
   bands has colour-dependent completeness.
6. Crowding: count neighbours in the full truth catalogue; let the caller restrict the tabulated range separately (D1).
   Offer the truth catalogue's own crowding column as the class variable when it has one (C3).
7. Tests to add: blended field (B5), chip gap, mirrored field, equal-resolution pair with shared blends (the tool must at
   least print the warning), truncated truth catalogue.
8. `hsc.py`: raise on RA wrap and near the poles; assert no duplicates instead of dropping them; one count cross-check per
   query (E2). `02_atlas.py`: point-like card, HSC-side crowding class, no silent fallback (D6).

## Would someone who runs artificial-star tests find this useful, misleading, or trivial?

Useful as a cheap cross-check, misleading as written, and not trivial. Such a person will see at once that the method
cannot replace artificial stars: it measures conditional recovery among stars another catalogue already separated, so
when both catalogues come from the same telescope the stars lost to blending are invisible at any exposure ratio, and it
has no control over where the test stars sit in magnitude, colour or position. They would also catch within minutes what
this report caught: a chip gap inside the footprint, a self-fulfilling S/N check, a one-band table for a two-band
selection, and a "recovered" fraction that is really a centroid tolerance. But two things here would interest them. The
first is the direction of use that artificial stars cannot serve: grading a catalogue whose images and pipeline you do
not control (HSC) against PSF photometry of the same frames, by class, including the demonstration that the offset
scales with the neighbour's flux in the aperture. The second is that the tool found three real defects in a day (the
paging loss, the chip gap once pointed at it, a 0.10 mag zero-point disagreement between two ANGST reductions), which is
what an end-to-end external check is for. Show it to the advisor as "a sanity check that runs in a second and caught
these three things, with these stated blind spots", after the fixes above, and next to one real artificial-star
completeness curve for the same field; not as "the part of an artificial-star test the sky has already run".
