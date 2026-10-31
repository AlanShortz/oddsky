## 1. Verdict

Author: claude-referee (H-0009 ATLAS pass), 2026-10-31. Scripts, logs, data and the figure are in
`reviews/claude-referee-atlas-2026-10-31/` (r0-r14, run from the repo root with `uv run python -I`). I reduced the ten ATLAS files
myself from the raw forced photometry (`oddsky.data.atlas.parse`) and did not import the investigators' scripts. The fits use
`fitlib.py`, copied unchanged from the H-0008 atlas10b referee pass. I downloaded every NEOWISE-R single exposure within 6″ of all
122 strong events and 117 of the 118 known-lens recoveries (IRSA TAP, `neowiser_p1bs_psd`). Outside services used: Gaia DR3 epoch
photometry (datalink), the Gaia TAP, VizieR (idia mirror), SIMBAD (CfA), TNS (paced), the Gaia alerts list and GOST.

In the table, "ATLAS ±10 / ±30 d" counts the nightly bins (per unit and band) within 10 and 30 days of the NEOWISE peak visit. The
optical ratio is flux over baseline at the visit, PSF-corrected. "Lens on the star" is the optical ratio a lens on the matched Gaia
star would give, using Gaia-neighbour shares of the ATLAS PSF and WISE beam (r3). "Where it brightened" comes from the
exposure-level centroid test (r8b).

| star | ATLAS ±10 / ±30 d | optical ratio at the visit | NEOWISE (W1, W2) | lens on the star predicts | where it brightened | verdict | P(lens) |
|---|---|---|---|---|---|---|---|
| **J174401.99-382512.2** | 6 / 14 | o ×2.44 ± 0.08, c ×2.57 ± 0.14 | ×2.33, ×2.49 | ×2.0-2.5 | on the Gaia star | **lens candidate, parallax-dependent (inconclusive)**. Real, achromatic, six-month event; a lens fits no better than an asymmetric bump | 0.40 |
| **J180402.28-181847.5** | 2 / 7 (2015, PSF 4 px) | ATLAS o ×1.6 ± 1.0 (unconstrained); **Gaia DR3 G ×2.60 (−9 d), ×2.57 (+20 d), RP the same** | ×2.69, ×2.75 | ×2.1 | on the Gaia star | **lens candidate**. Achromatic from G to W2; the Gaia DR3 classifier labels it MICROLENSING | 0.60 |
| **J025145.03+602012.5** | 9 / 18 | o ×0.91 ± 0.03 (a dip, not flat) | ×2.53, ×2.55 | ×2.5 | on the star | **optical counterpart, not a lens**. SIMBAD lists a B8 young star in W5 (TYC 4048-993-1); IR rising since 2019; the optical dims at the IR peak | < 0.02 |
| **J185035.91-014014.4** | 4 / 16 | o ×0.92 ± 0.08 (×0.88 ± 0.04 at ±30 d) | ×3.39, ×3.45 (peak saturated) | ×2.3-2.6 | at the 2MASS/Gaia position | **no optical counterpart (IR-only)**. The IR source (J−K 4.6) cannot be the BP−RP 2.5 Gaia star; smooth two-year IR event, not an artifact; ATLAS cannot test a lens on it | 0.10 |
| **J182621.38-175812.7** | 0 / 9 (nearest −15.5, +12.5 d) | o ×1.03 ± 0.07 at ±12-16 d | ×2.81, ×2.89 | ×2.0 | **on a neighbour**: Gaia 4096281151213072384 (G 18.8), 2.5″ S | **unconstrained / mis-associated**. Rose 0.75 mag within the 1-day visit; only 4 of 11 frames kept | 0.10 |
| **J184240.11-052241.7** | 4 / 13 | o ×1.08 ± 0.05, c ×1.15 ± 0.10 | ×1.81, ×1.81 | ×1.8 | **on a neighbour**: 2MASS J18424008-0522407 (K 9.4, J−K 2.8), 1.1″ NW | **no optical counterpart on the Gaia star**. The event sits on a reddened IR source that ATLAS does not test | 0.10 |
| **J064439.73+011503.3** | 4 / 16 | o ×1.16 ± 0.03 (two weeks), c ×1.04 | ×1.72, ×1.78 | ×1.72 | on the star (all frames clean) | **optical counterpart, not a lens**. Chromatic (the optical excess is 0.2-0.3 of W1's); W2 > W1 across a two-year block | 0.03 |
| **J172057.02-414201.2** | 0 / 0 (ATLAS starts +193 d) | **Gaia DR3 G ×5.87 (−7 d), ×2.71 (+25 d), ×1.76 (+44 d), BP = RP** | ×4.50, ×4.77 | – | **on Gaia 5959812622743175552** (G 17.9, 0.59″), not the star matched at 2.2″ | **lens candidate**. The Gaia DR3 classifier labels it MICROLENSING (score 0.60) | 0.65 |
| **J170153.51-425620.0** | 1 / 2 (+8.8, +20.8 d) | o ×1.04 ± 0.04 | ×2.19, ×2.33 (×1.34 six months earlier) | ×2.1 | on the star (7 of 8 frames clean) | **no optical counterpart (IR-only)**. Star-forming surroundings (submm source 16″, nebular W3/W4) | 0.03 |
| **J173349.59-264330.5** | 0 / 0 (nearest −45 d) | – | ×1.72, ×1.81 | ×1.7 | on the star (every frame halo-flagged, as on every visit) | **unconstrained**. It lies in a dense OGLE/KMT field during OGLE's 2015 season and no alert was issued; that argues against a lens on this I ≈ 14-15 star | 0.15 |

Two strong events outside the ten follow from the checks:

- **J180839.93-151910.5** (new in H-0009, no ATLAS request yet) is a further lens candidate (P ≈ 0.5). Gaia DR3 epoch photometry
  shows G ×1.52 at −16 d, ×1.39 at +15 d and ×1.14 at +35 d, with BP and RP the same; W1 is ×1.62. Gaia's classifier labels it
  MICROLENSING (0.21). 91% of its event frames are deblended.
- **J194519.88+274002.7**, one of the README's three highlighted examples, is an artifact.

**What the first read got wrong.**

1. **J174401 is ×2.4-2.6, not ×5.** The ×5 is the ratio to the 01a unit's baseline. That baseline was taken in 2016-19 with a wide
   PSF (3.2-3.4 px) and reads ~100 uJy, against 366 uJy for 01a in 2020 and 355-415 uJy for 02a-04a. The event lasts six months,
   not "a months-long ×5": the rise starts in 2021 March (×1.15 in ATLAS and W1 alike) and the event is over by 2022 March.
2. **J180402's "×3" is a single wide-PSF night** (2015 02a, PSF 4 px; the next night reads ×0.86). After the PSF correction ATLAS
   alone is not significant. Gaia DR3 epoch photometry is what makes the event real.
3. **J025145 is not flat.** ATLAS o drops by 7-17% (5-13σ per night) from 2021 Aug 20 to Sep 13, at the NEOWISE peak, and by about
   4% at the 2021 Jan block visit. The star is a catalogued young B8 star in W5. A caveat: at o = 12.2 AB the star is close to
   ATLAS saturation, and frames inside the dip depend on PSF width differently from baseline frames (3σ). So the size of the dip is
   uncertain. The NEOWISE event is on this star and is astrophysical.
4. **J064439 has a clear optical counterpart** (×1.16-1.21, 14σ). It is chromatic, so it is not a lens.
5. **J170153 is not uncovered.** Two ATLAS nights at +9 and +21 d read ×1.04 ± 0.04, where a lens on the star needs about ×2.
6. **For J182621 and J184240 the brightening is not on the matched Gaia star**, and for J172057 it is on a different Gaia star from
   the one matched. The survey's position match (brightest Gaia star within 3″) chose the wrong star in all three.
7. **The first-pass fits (`work/atlas10.json`) are uninformative.**
   - Several peak guesses sit on unrelated ATLAS maxima: J185035 2018-07-13 against the NEOWISE visit on 2018-09-13; J182621
     2019-11-08 against 2020-03-27; J184240 2020-11-01 against 2021-03-30.
   - Nearly every blend fraction is at a bound (0.02 or 1.5). That includes J174401's 03a/04a series, which have no data within
     160 d of the peak.

## 2. Do the relaxed rules let artifacts in? (r0, r8, r8b, r9, r9b)

**Data.** I downloaded every NEOWISE-R exposure within 6″ of each event (239 of 240 analysable). I applied the survey's own relaxed
selection: detections associated with the AllWISE source within 2″, the W1 quality cuts, and h/d, nb ≤ 3 and saturated frames
allowed. My visit medians reproduce the survey's dW1 to within 0.3 mag for **all** 239 events.

**Diagnostics.** For each event visit (`framelib.py`):

- the share of frames that are h/d-flagged, deblended (nb > 1) or saturated;
- the brightening measured in clean frames only;
- aperture against profile-fit flux;
- frames in which a neighbour inside 6″ was not extracted ("merged");
- the share of the star's detections that pass the 2″ association;
- frame-to-frame scatter;
- the centroid test.

**The centroid test.** If the matched Gaia star brightened, the event-frame centroid must move toward it by
f_ex × (Gaia position − quiet centroid), where f_ex is the excess's share of the event flux. It identified the source correctly in
every case I could check against another instrument (J172057, J180402, J174401).

### 2.1 Results

| | known lenses, all (117) | known, new in H-0009 (58) | strong, all (122) | strong, new in H-0009 (56) | strong, also in H-0008 (66) |
|---|---|---|---|---|---|
| event frames ≥ 50% h/d | 29 (25%) | 27 (47%) | 30 (25%) | 24 (43%) | 6 (9%) |
| event frames ≥ 50% nb > 1 | 16 (14%) | 16 (28%) | 18 (15%) | 17 (30%) | 1 (2%) |
| event frames ≥ 50% saturated | 4 (3%) | 4 (7%) | 6 (5%) | 5 (9%) | 1 (2%) |
| **any of the three ("flag-dominated")** | 43 (37%) | **41 (71%)** | 47 (39%) | **39 (70%)** | 8 (12%) |
| hdfrac_event > hdfrac_other + 0.3 | 3 | 3 | 2 | 2 | 0 |
| nbfrac_event > nbfrac_other + 0.3 | 4 | 4 | 4 | 3 | 1 |
| merged neighbour in ≥ 30% of event frames | 0 | 0 | 6 | 6 | 0 |
| share passing the 2″ association drops by > 0.25 | 1 | 0 | 4 | 4 | 0 |
| clean frames show < ½ of the brightening | 1 | 1 | 2 | 2 | 0 |
| **any exposure-level artifact (previous three rows)** | **2 (2%)** | 1 | **10 (8%)** | **10 (18%)** | 0 |
| **off-target** (centroid misses the matched star by > 0.3″ and > 5σ) | 13 (11%) | 8 (14%) | **31 (25%)** | 20 (36%) | 11 (17%) |

What the table shows:

1. **Event frames dominated by flags are not the mark of an artifact.** Among events new to H-0009, they are as common in the known
   lenses (71%) as in the strong unexplained events (70%). The flags belong to the star (a bright neighbour, a crowded field), not
   to the event. Comparing the event visit with the star's own quiet visits does not help either: the hd and nb excess cuts flag 3-4
   known lenses and 2-4 strong events.
2. **The artifacts the relaxed rules let in are exposure-level, and almost all are among the new events.** There are 10 among the
   56 new strong events (18%), against 1 of the 58 new known lenses and none of the 66 strong events also found by H-0008. The
   mechanism is association, not the flags themselves. A brighter neighbour 2-5″ away goes unextracted in some frames, and the
   survey's "detection within 2″ of the AllWISE position" rule then keeps exactly those frames.
   - **J194519** (README example, "×3.5"). The star's detections normally sit 2.3-3″ from the AllWISE position and fail the 2″ cut.
     In two frames a W1 = 10.9 neighbour 3.8″ away was not extracted, and its flux landed in a detection 1.4-1.8″ from the position.
     The visit median comes from three frames, two of them merged. Artifact.
   - **J093200** (×1.9): the same mechanism with a W1 = 12.8 neighbour 4″ away. Artifact.
   - **J042956, J172600, J181418, J031935**: merged frames with frame-to-frame scatter of 2.8-18× normal. In J172600 and J031935 the
     clean frames show no brightening (d_clean −0.07 and +0.01 mag against −0.58 and −0.42). Artifacts.
   - **J153348, J172925** (2″-association share drops to 0.42-0.59, centroid 1.5-1.7″ off): position wobble. Probable artifacts.
   - **J182621** (above) and **J101348**, the SN 2022ffg host. These two are real transients offset from the catalogued star or the
     nucleus, and are caught by the same test.
3. **A quarter of the strong events (31; 20 of the 56 new) brightened on something other than the matched Gaia star**, against 11%
   of known lenses. These are not artifacts, but the Gaia star, the "lens on the star" expectation and the ATLAS and Gaia comparisons
   then refer to the wrong object. 7 of the 31 have no Gaia star within 3″ at all. Examples are J172057 (correct source confirmed by
   Gaia DR3), J182621, J184240, J185846 (H-0008 referee: "the Gaia star matched is not the variable"), J161946 (the strongest event,
   ×8, 100% halo-flagged and saturated, centroid off by 0.6″) and J123522.
4. **The flags do not predict the optical outcome.** 14 events have a second instrument (the ten above plus J180839, and the Gaia
   DR3 cases):

   | optical result | events | flag-dominated | off-target |
   |---|---|---|---|
   | achromatic optical counterpart | J174401, J180402, J172057, J180839 | 2 (J174401 h/d + nb; J180839 nb) | 1 (J172057, but the right Gaia star is the variable) |
   | chromatic counterpart (not a lens) | J025145, J064439 | 1 | 0 |
   | no counterpart on the matched star | J170153, J185035, J184240, J182621 | 3 | 2 |
   | unconstrained | J173349 | 1 | 0 |

   - With these numbers the flags are not over-represented in events without an optical counterpart in any significant way (3/4
     against 3/6).
   - The off-target test is what separates them: 2 of the 4 events without a counterpart brightened on a neighbour.
   - Two real, achromatic optical events (J174401 and J180839) were found only because the relaxed rules kept their h/d and nb
     frames.

### 2.2 Recommended cuts and their cost (r9b)

| rule | known lenses lost (of 117) | of the 58 new known lenses | strong rejected (of 122) | of the 56 new strong |
|---|---|---|---|---|
| A: hdfrac_event > hdfrac_other + 0.3 | 3 (3%) | 3 | 2 | 2 |
| B: nbfrac_event > nbfrac_other + 0.3 | 4 (3%) | 4 | 4 | 3 |
| A or B | 7 (6%) | 7 | 6 (5%) | 5 |
| D: event frames ≥ 50% flagged | 43 (37%) | 41 | 47 (39%) | 39 |
| **J: exposure-level artifact (merged / association drop / clean frames contradict / dW1 not reproduced)** | **2 (2%)** | **1** | **10 (8%)** | **10 (18%)** |
| E: off-target centroid | 13 (11%) | 8 | 31 (25%) | 20 (36%) |
| **L: J, or (E and flag-dominated)** | **7 (6%)** | 6 | **20 (16%)** | **19 (34%)** |

Recommendations:

- **Do not cut on hdfrac or nbfrac, in absolute terms or relative to the star's other visits.**
  - The relative cuts (A, B) remove as many known lenses as strong events.
  - Rule D would throw away 41 of the 58 known lenses the relaxed pass gained, and with them J174401 and J180839.
- **Adopt J as a hard cut.** It costs 1 of the 58 new known lenses (2 of 117 overall) and removes 10 of the 56 new strong events.
  - It needs the exposures. In the pipeline it can be computed in the same pass.
  - Its three parts: (i) keep the share of a visit's associated detections that fall within 2″, and reject a visit where that share
    drops by more than 0.25; (ii) count the detections within 6″ per frame and reject a visit where ≥ 30% of frames have fewer than
    usual; (iii) require the clean frames, where there are at least 2, to show at least half of the brightening.
  - The cleaner fix is (i): compute visit medians from every detection associated with the source, not only those within 2″.
- **Use the centroid test to re-associate events, not to reject them.**
  - Record the event-frame centroid shift. Take the Gaia star toward which it points as the source, and draw the ATLAS and Gaia
    expectations and blend fractions from that star.
  - If a cut is wanted, L (J, or off-target and flag-dominated) costs 6% of known lenses and removes 34% of the new strong events.
- **Saturation.** Among strong events only 6 have saturated event frames, and the clearest (J185035) is a real two-year IR event
  whose unsaturated visits carry the shape. No saturation cut is needed beyond J.

## 3. J174401, J180402, J172057 in detail

### 3.1 J174401.99-382512.2 (r1, r1b, r5, r11)

**The star.**
- G 17.55, BP−RP 2.39, J−K 1.06, K−W1 0.45; no IR excess. l 351.7°, b −4.7°.
- Gaia ϖ 0.71 ± 0.12 mas (RUWE 1.04, IPD multi-peak 4%). That parallax would put the star at ~1.4 kpc, which does not fit a giant;
  it may be biased by crowding.
- Gaia share of the ATLAS PSF 0.75. Share of the WISE beam 0.69 (RP proxy) to 0.98 (Ks proxy).

**Light curve.**
- ATLAS o rises steadily from ×1.1-1.2 in 2021 March to ×2.4-2.6 on Aug 7-Sep 12. It falls to ×1.6 by Oct 16 (+49 d).
- In 2022 Feb-Mar (+165 d onward) it is at ×1.0-1.1. The decline after Oct 16 falls in the solar gap.
- NEOWISE: ×1.15 at −164 d, ×2.33 at the visit, ×1.00 at +200 d.

**Achromatic.** At matched PSF the ratios are o ×2.44 ± 0.08 and c ×2.57 ± 0.14, against W1 ×2.33 and W2 ×2.49. The excess ratios
are equal within the blending uncertainty, which rules out accretion bursts (bluer) and dust events (redder).

**Exposure level.**
- 8 of the 9 event frames are flagged: 78% h/d, as on every visit of this star, and 56% deblended against 2% on quiet visits.
- Aperture and profile fit agree (R_ap 1.09). The centroid is consistent with the Gaia star.
- So this is a real event that the strict pass could not have found.

**Fits** (r5; series with nights within 150 d of the peak, 2020+ baseline; 11 variants):

| model | result |
|---|---|
| static lens, free blending | runs to unphysical fs ≈ 10 (u0 ≈ 1.5) |
| static lens, fs ≤ 1 | χ² 190.9 (n 191); tE 141 d, u0 0.38 |
| **parallax lens, fs ≤ 1** | **χ² 177.3; t0 2021 Sep 2 (MJD 59456.6), tE 107-121 d, u0 −0.31 to −0.36, πE (N −0.20, E +0.40-0.45), fs: o 0.8-1.0, c 0.84, W1 0.70, W2 0.83** |
| asymmetric Pearson VII | χ² 179.2; rise width 196 d, fall width 69 d |
| lens with separate rise and fall tE | tE_rise / tE_fall = 1.6-2.5 |
| across variants | parallax lens − best bump: −3 to +10 (only "with 03a/04a" gives +9.9). PSF-corrected variants give 0 and push fs to 1.6-3 (unphysical) |

- The event rises about twice as slowly as it falls.
- Only annual parallax lets a physical lens fit, and it then fits exactly as well as an asymmetric bump. This is the same position as
  J174744 in the H-0008 pass.
- The alternatives fail on other grounds:
  - LPV, semi-regular or R CrB: one event in 11 years, achromatic, a brightening.
  - Nova or YSO: a five-month achromatic rise; no IR excess.
  - Be star: colours.
- An unknown slow achromatic brightening is the main competitor.

**Novelty (r6, r11).**
- OGLE was not observing (2020 Mar 18-2022 Aug 12), which explains the absence of an OGLE alert. The nearest OGLE event of any year
  is 12′ away, so the star is in the OGLE-IV footprint.
- KMTNet: no event of any year within 30′. The nearest 2021 event is 128′ away; the star is outside the KMT fields.
- No Gaia alert within 60″. GOST puts Gaia transits on 2021 Aug 22 and Sep 18, when ATLAS gives ×2.58 and ×2.43 (ΔG ≈ −1.0), at
  Gaia's alert threshold. DR4 ends in 2020 January, so only DR5 can test this.
- TNS: none within 60″. SIMBAD: only an eclipsing binary 10.6″ away. VSX: an EB at 10.6″ and LPVs at ≥ 37″.
- ASAS-SN would not reach V ≈ 18.
- "Apparently unreported" is the strongest wording allowed (MOA unchecked).

**Safe wording.** "A six-month, achromatic ×2.5 brightening of a G 17.5 bulge-direction star peaking in 2021 Aug-Sep (ATLAS c, o and
NEOWISE W1, W2 equal). A point lens fits only with annual parallax (tE ≈ 110-120 d) and no better than an asymmetric non-lens shape.
Not classified."

### 3.2 J180402.28-181847.5 (r4, r5)

**The star.**
- G 18.66, BP−RP 4.25, J−K 2.23: a heavily reddened giant.
- Gaia DR3 VARIABLE, so epoch photometry exists. The 2MASS source and the Gaia star coincide (0.07″), and the centroid shift points
  at them.

**Light curve.**
- Gaia G ×2.60 (−9.4 d), ×2.57 (+19.6 d), ×1.76-1.79 (+42 d). RP gives the same factors (−1.07, −1.08, −0.66 mag).
- BP is too faint to use (median 21.1).
- W1 ×2.69 and W2 ×2.75 at the visit. Every other NEOWISE visit is flat to 2%.

**Fits** (Gaia G/RP + NEOWISE ± ATLAS o 02a):
- Static lens: tE 98-104 d, u0 0.20-0.23. fs is the same in every band: G 0.49-0.57, RP 0.54-0.63, W1 0.43-0.51, W2 0.44-0.53.
- A symmetric Pearson VII fits better than the static lens by Δχ² ≈ 10. Parallax improves on it by about 30, but drives fs to 0.1
  (the blending degeneracy).
- With 4 Gaia transits and one NEOWISE visit in the event, the shape is not determined.

**Gaia classification.** The DR3 general classifier labels the star MICROLENSING (score 0.26). It is not in the DR3 microlensing
catalogue (Wyrzykowski+2023; Gaia TAP `vari_microlensing` and VizieR J/A+A/674/A23 both empty).

**Novelty.**
- 2015, so OGLE was observing. Only 3 OGLE events of any year lie within 30′, which points to a sparse, low-cadence field. No OGLE
  alert.
- KMTNet 2015 is not in the reference list (KMT's 2015 season covered only central fields).
- No Gaia alert, no TNS entry.
- Already in H-0008's clean list.

### 3.3 J172057.02-414201.2 (r3, r4, r5, r8b)

**Which star.**
- The survey matched the G 17.21 star 2.21″ away.
- Gaia DR3 5959812622743175552 (G 17.87, BP−RP 2.57, VARIABLE) is 0.59″ from the AllWISE position. The event-frame centroid moves
  0.42″ toward it, which matches the predicted shift to within 0.02″.

**Light curve.** That source shows G ×5.87 at −7 d, ×2.71 at +25 d and ×1.76 at +44 d, with BP and RP equal (−1.94/−1.92 and
−1.18/−1.15 mag). W1 is ×4.50 at the visit.

**Fit.** Static lens with fs ≤ 1: tE 78 d, u0 0.15, fs_G 0.99, RP 1.00, W1 0.62, W2 0.66. The W1 blending fits the 0.43-0.66 WISE
share. Shapes are not distinguished: the asymmetric PV7 is 9 lower in χ², with χ²/dof ≈ 1.9.

**Gaia classification.** The DR3 classifier labels it MICROLENSING (0.60). It is not in the DR3 microlensing catalogue.

**Novelty.**
- No OGLE or OGLE-GVS event within 30′: outside the EWS footprint.
- No Gaia alert within 60″, although Gaia saw ΔG = −1.9 on 2015 Aug 30. Gaia alerts were still in their first year.
- No TNS entry.

## 4. Per-star notes (r1, r2, r3, r7, r8, r13)

- **J025145.**
  - W1 rises slowly: ×1.04 (2019-08), 1.06, 1.12, 1.21 (2021-01), 2.53 (2021-08), then 1.13, 1.07, 0.98 by 2023. W2 follows.
  - SED: W1−W2 0.42, K−W3 1.97, W1−W4 3.1.
  - SIMBAD Y*O, B8 (Koenig+2011; [KAG2008] 5977). Gaia DR3 has no parallax and IPD multi-peak 79%: probably a close double.
  - The ATLAS dip coincides with the IR peak. This is UX Ori-style dust behaviour, not lensing.
- **J064439.**
  - NEOWISE block: ×1.13 / ×1.20 (2019-10, W1/W2), ×1.16 / ×1.29 (2020-03), ×1.72 / ×1.78 (2020-10), ×1.11 / ×1.16 (2021-03).
    W2 is above W1 throughout.
  - ATLAS is ×1.02-1.04 at the first two visits and ×1.16-1.21 for about two weeks at the third, plus a ×1.07 bump at +110 d (10σ).
  - W1−W4 3.4 and Gaia RUWE 1.96. A YSO or Be-like IR variable.
- **J185035.**
  - IR light curve: ×1.03 (2017-09), ×1.50 (2018-04, unsaturated), ×3.39 (2018-09, all frames saturated at W1 7.9), ×1.08
    (2019-04), ×1.04 (2019-09).
  - NEOWISE-only: a lens with fs ≈ 1 fits the unsaturated visits as well as a bump does (χ² 32.4 against 34.0 and 28.4, n 38;
    tE ≈ 140-220 d).
  - Gaia G − Ks = 8.8 against BP−RP 2.5: the IR source is not an ordinary star seen in the optical. It is either an obscured object
    behind the Gaia star or a dusty object whose optical light is scattered.
  - The ATLAS o PSF-corrected ratio of 0.88 ± 0.04 over ±30 d hints at an optical dip, as in J025145.
  - Verdict: IR-only. An IR lens on an invisible source cannot be excluded by ATLAS.
- **J184240.**
  - Survey visits have W1 rchi² ≈ 58: badly fitted blends, near W1 = 6.1 and 6.9 stars 39-44″ away.
  - The brightening is in clean frames too (d_clean −0.64) and sits on the J−K 2.8 source.
  - Two visits six months apart at ×1.81 and ×1.71, then ×1.11 a further six months on.
  - A lens on that source fits NEOWISE (fs ≤ 1: tE ≈ 170 d, u0 0.39) as well as a bump. ATLAS's ≤ 10% does not test it.
- **J182621.**
  - Event-visit W1 runs 11.38 → 11.22 → 11.05 → 11.05 → 10.77 → 10.63 over 0.98 d, and W2 does the same.
  - Positions are 1.5-1.9″ south and steady to 0.5″, so not an asteroid.
  - ATLAS saw nothing at −15.5 and +12.5 d (≤ 100 uJy at the neighbour's position).
  - A lens on the G 18.8 neighbour would need tE ≲ 15 d. A dwarf-nova-like outburst is equally possible.
- **J170153.** ATLAS's +8.8 d night is in the 2016 wide-PSF era (4.0 px). The 02a PSF slope there is small (+4%/px), so the
  correction is minor, and both nights read ≤ ×1.10 raw.
- **J173349.** No ATLAS frame within 45 d (2016 02a nights at the second visit read ×0.2-0.4: wide PSF in a dense field). The event
  is in all frames with consistent aperture photometry, so it is not a halo artifact at the exposure level.
- **J160706 (OS-0023; r14).** Carried by clean frames (7 of 10, d_clean −2.29). The centroid is consistent with the matched star
  (miss 0.18″). Not an artifact.

## 5. Corrections the investigators must make

1. **J174401.** Replace "×5" with "×2.4-2.6 (o), ×2.6 (c), ×2.3-2.5 (W1, W2); six months, 2021 Mar-2022 Feb". Do not quote the
   first-pass fits. Wording: "parallax-dependent, not preferred over a non-lens shape" (§3.1).
2. **J180402 and J172057.** Cite the Gaia DR3 epoch photometry as the optical evidence. Give J172057 the correct Gaia source
   (5959812622743175552). Note that the DR3 classifier already labels both MICROLENSING (not in the DR3 microlensing catalogue).
   Add J180839 on the same footing and queue ATLAS for it.
3. **J025145.** Change "flat" to "dims by 7-17% at the IR peak (saturation caveat). Catalogued young B8 star; not a lens".
4. **J064439, J170153, J185035, J184240, J182621.** Use the verdicts in §1. Two of these events are on neighbours.
5. **README.**
   - Remove J194519.88+274002.7 from the examples: it is a merged-neighbour artifact (§2.1).
   - Note that 31 of 122 strong events brightened on something other than the matched Gaia star.
   - Add rule J and centroid re-association before any further follow-up is chosen (§2.2).
6. **`hunt_h0008_atlas10.py`.**
   - Choose the peak at the NEOWISE visit, not an ATLAS maximum elsewhere.
   - Use per-unit baselines at a matched PSF; 01a before 2020 must not set the scale.
   - Drop series with no nights near the event.
   - Bin southern units by local night.

## 6. What remains unchecked

- **MOA** (2015, 2016, 2021) and the **KMTNet 2015** season for J180402, J172057, J173349 and J180839.
- **OGLE-IV photometry** of J173349 (2015) and J180402 (a low-cadence field). Only the EWS lists were checked.
- **ASAS-SN light curves**. J025145 (V ≈ 12) would test the optical dip, free of ATLAS saturation. J172057 at peak (V ≈ 16.8) is
  marginal.
- **ZTF** for J025145 (Dec +60, 2021); it is probably saturated.
- **VVV/VIRAC2 Ks** for J182621 and J173349, which lie in the VVV area. They would identify which star brightened and whether
  J182621 was a short event or an outburst.
- **Gaia DR5** at the 2021 transits of J174401 (ΔG ≈ −1.0 predicted on Aug 22 and Sep 18).
- **The other 112 strong events have no optical check.** The exposure-level diagnostics (r9) cover them, but ATLAS does not. The
  centroid re-association has not been propagated to their Gaia matches.
- **Exposure-level diagnostics for the strong-event candidates selected by H-0008's strict pass**, beyond those in sky4_strong. One
  known lens (J053305, LMC) had too few frames.
- **Spectra** of J174401, J180402, J172057 and J180839.

## Files

| script | what it does |
|---|---|
| `r0_fetch_frames` (+ `_one`) | NEOWISE-R exposures within 6″ of 240 events (IRSA TAP) → `data/frames/` |
| `r1_reduce`, `r1b_j174401_ratio` | ATLAS re-reduction: baselines, PSF slopes, coverage and ratios at ±10/±30 d; J174401 at matched PSF |
| `r2_neowise_visits` | survey visit light curves and flags of the ten |
| `r3_catalogs` | Gaia/2MASS/AllWISE neighbours, beam shares, VSX |
| `r4_gaia_epoch`, `r10_gaia_dr3_window`, `r10b_j180839` | Gaia DR3 epoch photometry for the strong events inside the DR3 span |
| `r5_fits` | lens/non-lens fits for J174401, J180402, J172057 |
| `r6_novelty` | reference lists, Gaia alerts, TNS, SIMBAD |
| `r7_atlas_frames` | ATLAS frames on event nights; saturation tests |
| `framelib`, `r8_frames_ten`, `r8b_centroid` | exposure-level diagnostics; which source brightened |
| `r9_bulk`, `r9b_stats` | diagnostics for 239 events; flag statistics; cuts and costs (`data/r9b_flags.csv`) |
| `r11_gost` | Gaia transits during J174401's event |
| `r12_figure` (`r12_figure.png`) | light curves and flag histograms |
| `r13_neowise_only` | NEOWISE-only shape fits (J185035, J184240) |
| `r14_j160706` | exposure-level check of OS-0023 |
