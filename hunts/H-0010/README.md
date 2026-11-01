# Hunt H-0010: Gaia's unpublished lenses

**Question.** The Gaia DR3 variability classifier (`gaiadr3.vari_classifier_result`) labels 254 sources MICROLENSING. 67 of them
are not in the DR3 microlensing catalogue (`gaiadr3.vari_microlensing`, Wyrzykowski et al. 2023). Oddsky's blind NEOWISE searches
(H-0008, H-0009) found three of the 67 independently: cases OS-0026, OS-0027 and OS-0029. What are the other 64?

The 67 themselves are not a new list: Rimoldini et al. (2023, §4.13 and Appendix D) report "67 unique to classification" and the
query that returns them, and Eyer et al. (2023, table 2) list "MICROLENSING 254 (67)". What no paper we found has done is vet them
one by one (title/abstract search; ADS full text not searched).

**Status: done and refereed (2026-11-01)** ([referee](reviews/claude-referee-2026-11-01.md)). ATLAS queued for 8 candidates
(`work/atlas/queue.csv`).

**Answer in one line, after the referee.** Of the 67: 28 are catalogued lenses the DR3 catalogue left out, 3 are Oddsky's cases, 1
(J182124) is a lens candidate already published by Mróz et al. (2020, table B2, as OGLE BLG783.17.33659), and of the remaining 20
first-pass candidates **9 hold up as apparently unreported lens candidates (P ≥ 0.4), 3 of them strong** (J174618.09-253631.3,
J173332.42-421445.1, J072830.43-204112.5), 10 are inconclusive and 1 is not a lens; 8 more are inconclusive and 7 are not lenses as in
the first pass. About 5-10 real lenses are expected among the 20 (the referee's sum is 7.5); the first pass said about 11.

## After the referee

| candidate | first pass P | referee P | what changed |
|---|---|---|---|
| J174618.09-253631.3 | 0.85 | 0.75 | real and on the star (APOGEE: a metal-rich bulge giant, a good lens source), but the "NEOWISE ×7.3 against ×7.1 predicted" agreement is withdrawn: the ×7.1 came from a fit with the blend fraction pinned at its bound (physical fits predict ×4.3-10.6), and the ×7.3 used a neighbour 6" away as baseline (against the star's own AllWISE/2MASS baseline W1 rose ×7.6-11.4). A Gaussian fits Gaia's four points better than a lens (ΔBIC 14) |
| J173332.42-421445.1 | 0.75 | 0.75 | a parallax lens (t0 2014 Aug 4, tE ~140 d, fs ≈ 1) fits Gaia and all three NEOWISE visits; the static model failed the 2014 Mar visit |
| J072830.43-204112.5 | 0.65 | 0.60 | Be star disfavoured (K-type Gaia spectrum, no Hα in VPHAS+, no infrared excess, infrared rose as much as the optical); tE undetermined (the 188-456 d came from blend fractions at the bounds) |
| J144905.72-545455.6 | 0.65 | 0.45 | colour testable at the peak and passes; its parallax "preference" came from a blend fraction at the bound |
| J200958.93+321427.9 | 0.55 | 0.40 | the non-lens comparison fit had not converged; IPHAS shows no Hα emission before the event, but Be not excluded |
| J174656, J151331, J175414, J171838 | 0.45-0.50 | 0.40-0.45 | kept, marginal |
| J182124.77-190909.7 | 0.50 | 0.60 | a real lens candidate but published (Mróz et al. 2020); Gaia and OGLE both read ×1.42 on consecutive nights |
| J172020.30-381044.3 | 0.50 | 0.20 | bluer when brighter (4.9σ) |
| J180313.03-150702.0 | 0.40 | 0.10 | not a lens: bluer when brighter (4.3σ), a non-lens shape fits better by ΔBIC 33 |
| J184922.92-000203.9 | 0.50 | 0.15 | Hα excess in IPHAS (4.6σ) and VPHAS+: an emission-line star |
| J171847, J174036, J174029, J171234, J182656, J190032, J182811, J184837 | 0.40-0.50 | 0.25-0.35 | inconclusive |

Other corrections: 20 of the 21 first-pass fits had a blend fraction at a bound (1.5 or 0.02), so their timescales are not
constrained; four non-lens comparison fits had not converged; scan-angle impostors are ruled out for all 21, and the NEOWISE frames of
J173332, J072830, J200958 and J182124 are clean and on the Gaia star. The tables below are the first pass; the referee's verdicts
above supersede them where they differ.

## Data

| | |
|---|---|
| list | re-derived with the ESA Gaia TAP (`s1_select.py`): 254 classifier MICROLENSING, 187 in `vari_microlensing`, **67 not**. Identical to the 67 handed over. The 363-event catalogue holds 187 classifier-MICROLENSING sources, 10 LPV, 1 YSO and 165 unclassified (`data/vari_microlensing_classes.csv`) |
| Gaia DR3 | epoch photometry (G, BP, RP per transit, 2014-07-25 to 2017-05-28) for all 67 and for the 3 neighbours within 6" that have it (`gaia_epoch.fetch_report`, `releases=("Gaia DR3",)`). Transits rejected by photometry dropped; variability-flagged ones kept and marked. `gaia_source`, `astrophysical_parameters`, `vari_summary` and classifier rows; every Gaia neighbour within 6" (VizieR mirror) |
| NEOWISE | IRSA single exposures within 3" of all 67, matched to the AllWISE source; visit medians with H-0009's long-mode cuts. The sky4long pixel light curves only hold H-0008/H-0009 event stars, so their brighten tables were matched by AllWISE cntr |
| ZTF | 2018-2025 light curves of the 26 unmatched sources north of -31°, as a repeat test only (all events predate ZTF) |
| novelty | `H-0008/ext/reference_lenses.csv` (KMTNet 2016-22, OGLE EWS 2011-26, OGLE GVS, Gaia DR3, Gaia alerts, ZTF lists), Mróz et al. 2019 (OGLE-IV bulge events, alerted or not; VizieR), the Gaia Science Alerts index (from Gaia14aaa), TNS (60", 45 s pacing, all 67 answered, no HTTP 429 left), SIMBAD (CfA mirror, 5"), VSX (VizieR mirror, 10") |

## Method

Scripts in `scripts/`, run from the repo root with `uv run python -I hunts/H-0010/scripts/<name>.py`, in this order:
`s1_select`, `s1b_neighbours`, `s2_epoch` (and `--neighbours`), `s3_lightcurves`, `s4_neowise`, `s5_xmatch`, `s5b_tns`,
`s5c_mroz2019`, `s6_diag`/`s6b_zoom` (diagnostic sheets in `data/`), `s7_neighbours`, `s8_neowise_event`, `s11_ztf_repeats`,
`s12_verdicts`, `s9_table`, `s13_calibrate`, `s14_dr3_cuts`, `s10_figure`.

1. **Light curves** (`s3`). Quiet baseline per band; brightening episodes in G (≥ 2 transits brighter than max(4σ, 0.08 mag),
   separated by a quiet transit); fading episodes; the number of distinct scan dates per episode (a one-date "event" can be a
   scan-angle artifact). Joint fits to the G, BP and RP flux ratios: point lens with blending per band, static and with annual
   parallax (`oddsky.analysis.lensing.Problem`, five t0 starts), against symmetric and asymmetric Pearson VII and FRED shapes
   (`shape_fit` from `hunt_h0008_atlas_fit.py`), compared by BIC.
2. **Colour** (`s3`, `s7`). At transits where G is ≥ 5σ brighter, the change in BP−RP and the excess-flux ratio
   k = (f_BP − 1)/(f_RP − 1); a lens on an unblended star gives k = 1. Neighbours within 2" (19 in total around the 67) and the
   corrected BP/RP excess C* (Riello et al. 2021) flag window contamination. Not tested where the BP baseline is fainter than 20.5,
   where Gaia BP is unreliable.
3. **Second instrument** (`s8`, `s11`). NEOWISE visits within max(2 tE, 100 d) of the Gaia event against the Gaia lens model's
   prediction for that moment, and NEOWISE brightenings elsewhere in 2014-2024. ZTF 2018-2025 for repeats.
4. **Known?** (`s5`, `s5b`, `s5c`). 6" and |Δt| < max(2 tE, 60 d), plus any-time matches inspected by hand (this is how Gaia16aye,
   alerted 3.5 months before the Gaia DR3 peak, was recovered).
5. **Context** (`s9`). The Sun's elongation at the peak (ground surveys cannot observe the bulge from about November to January;
   Gaia, scanning at 45° from the Sun, can), and survey coverage: OGLE EWS events (2014-17) and KMTNet events (2016-17) within 15'.
6. **Calibration** (`s13`). On the 27 catalogued lenses with OGLE/KMTNet parameters, this pipeline's Gaia-only t0 lies within
   6 d (median) and 17 d (80%) of the survey value, better than the brightest transit (10 d, 33 d). The static tE is
   0.59-1.43 × the survey tE (16-84%, median 0.80). The 95% profile ranges are almost always open, so the reported tE range is the
   static fit scaled by that calibration (computed).
7. **Verdicts** (`s12`), by hand after inspecting every light curve, with P(microlensing) and robust parameters only.

## Funnel

| step | n |
|---|---|
| classifier MICROLENSING, not in `vari_microlensing` | **67** |
| catalogued lenses (OGLE, KMTNet, Gaia alerts) | **28** |
| Oddsky cases found blind by H-0009 (OS-0026, OS-0027, OS-0029) | **3** |
| **new lens candidates** (P ≥ 0.4, apparently unreported) | **21** (ΣP ≈ 11.0) |
| inconclusive (0.15 ≤ P < 0.4) | **8** |
| not lenses | **7**: 2 artifacts, 5 chromatic or repeating variables |

Apart from the artifact 508920918409038464, every one of the 67 is a single brightening in 2014-2017 (computed): no other source
has a second G episode brighter than 0.3 mag, and only J201826 has one above 0.2 mag (a 0.28-mag precursor, which counts against
it). The classifier was not fooled by periodic variables; it was fooled by artifacts and by one-off events of other kinds.

## The classifier is clean where someone was looking (computed)

Where OGLE or KMTNet were monitoring (≥ 5 of their events within 15') and the Sun was more than 60° away, **18 of 19** of these
sources are catalogued lenses. The exception is J174618 below, in a KMTNet field but in 2015, before KMTNet's full survey. Of the
21 new candidates, 16 lie where OGLE's EWS reported no event within 15' in 2014-2017. Four of the other five peaked with the Sun
47-56° away (Oct-Feb), outside the ground bulge season; that applies to 8 of the 21 in all. Only J174618 needs neither excuse. The
candidates are unreported because nobody else was looking, not because they look less like lenses (inferred).

## New lens candidates (`work/gaia_ml_unpub.csv`, `figures/candidates.png`)

t0 ± 3 weeks; tE is the 68% calibrated range; "peak" is the largest observed G ratio (a lower limit). "Achromatic" is the Gaia
BP/RP test.

| | Gaia DR3 | l, b | G | t0 | tE | peak | achromatic | P |
|---|---|---|---|---|---|---|---|---|
| **J174618.09-253631.3** | 4067152339419332992 | 2.9, +1.6 | 17.5 | 2015-03-18 | 19-46 d | ×4.42 | yes | **0.85** |
| **J173332.42-421445.1** | 5958944416543307648 | 347.4, −5.0 | 16.8 | before 2014-09-07 | unconstrained | ×2.48 | yes | **0.75** |
| **J072830.43-204112.5** | 5620272814897694848 | 235.5, −1.5 | 17.1 | 2015-02-26 | 188-456 d | ×1.71 | yes | **0.65** |
| **J144905.72-545455.6** | 5893807634053861120 | 319.4, +4.2 | 19.9 | 2015-01-17 | 64-156 d | ×13.97 | untested | **0.65** |
| **J200958.93+321427.9** | 2054828730840779520 | 70.1, −0.6 | 17.7 | 2015-12-11 | 27-65 d | ×1.44 | yes | **0.55** |
| J174656.42-190909.2 | 4119926316171065984 | 8.5, +4.8 | 17.6 | 2014-12-23 | 74-178 d | ×2.13 | yes | 0.50 |
| J171847.68-300609.5 | 4059204107239408512 | 355.8, +4.3 | 17.9 | 2017-01-02 | 26-63 d | ×1.92 | yes | 0.50 |
| J184922.92-000203.9 | 4266365704324232576 | 32.7, +0.4 | 20.2 | 2016-11-21 | 83-202 d | ×7.43 | untested | 0.50 |
| J172020.30-381044.3 | 5972789089004520192 | 349.4, −0.6 | 19.2 | 2016-11-13 | 93-225 d | ×3.08 | untested | 0.50 |
| J182124.77-190909.7 | 4096047127002546560 | 12.5, −2.3 | 17.7 | 2015-09-03 | 188-457 d | ×1.44 | yes | 0.50 |
| J175414.32-275241.8 | 4063479523864717184 | 1.9, −1.1 | 19.0 | 2016-10-28 | 10-25 d | ×2.37 | untested | 0.50 |
| J174036.98-223251.4 | 4117136992643758080 | 4.9, +4.3 | 19.3 | 2017-02-10 | 11-27 d | ×3.15 | yes | 0.50 |
| J174029.07-331407.7 | 4054091653004081408 | 355.8, −1.3 | 19.6 | 2017-02-14 | 23-56 d | ×3.63 | untested | 0.50 |
| J171234.40-353502.0 | 5977088149415668736 | 350.6, +2.1 | 20.1 | 2015-04-10 | 27-64 d | ×5.85 | untested | 0.45 |
| J182656.25-264645.9 | 4052046905029445376 | 6.3, −6.9 | 18.9 | 2015-04-26 | 34-82 d | ×3.03 | yes | 0.45 |
| J190032.43-004939.8 | 4265542994777483776 | 33.2, −2.4 | 19.2 | 2015-05-13 | 34-83 d | ×2.62 | yes | 0.45 |
| J151331.38-523733.2 | 5888321552071879552 | 323.6, +4.4 | 19.2 | 2014-09-12 | 37-91 d | ×3.56 | yes | 0.45 |
| J171838.94-334129.2 | 5979167630832540032 | 352.9, +2.2 | 19.0 | 2016-11-17 | 35-84 d | ×2.34 | untested | 0.45 |
| J182811.16-082538.6 | 4156259162525506816 | 22.8, +1.3 | 19.5 | 2015-10-09 | 52-125 d | ×9.14 | untested | 0.45 |
| J180313.03-150702.0 | 4146782166880069632 | 14.0, +3.5 | 19.7 | 2015-10-30 | 76-185 d | ×5.78 | untested | 0.40 |
| J184837.12-051620.2 | 4254872092666139264 | 27.9, −1.8 | 17.9 | 2017-03-21 | 74-181 d | ×1.56 | yes | 0.40 |

The five with P ≥ 0.55:

- **J174618.09-253631.3 (P 0.85).** NEOWISE measured ×7.3 in W1 and ×8.2 in W2 on 2015 Mar 19 (observed). The Gaia-only lens fit
  predicts ×7.1 for that moment (computed): Gaia saw ×1.8 eleven days before and ×4.4 six days after, so NEOWISE caught the peak
  between Gaia's transits. Single in Gaia 2014-17, NEOWISE 2014-24 and ZTF 2018-25. It lies in a KMTNet field (22 KMTNet events
  within 15' in 2016-17) but peaked in 2015; OGLE's EWS has only 2 events within 15'. Not in OGLE EWS, Mróz et al. 2019, the Gaia
  alerts, TNS, SIMBAD (a bare 2MASS entry) or VSX. Only 7 NEOWISE visits of 21 exposures pass the cuts (crowded field), so the
  NEOWISE baseline scatters by 0.2 mag; the ×7 is ten times that.
- **J173332.42-421445.1 (P 0.75).** Already ×2.5 and fading at Gaia's first transits (2014 Sep 7). NEOWISE eight days later reads
  ×2.43/×2.33, against the model's ×2.29 (observed/computed). Achromatic in Gaia: k 0.96 ± 0.04. The peak fell before Gaia's
  science operations, so t0 and tE are bounded on one side only. A single W2-only ×7 visit in 2017 with W1 flat is an exposure
  artifact, not a repeat.
- **J072830.43-204112.5 (P 0.65)**, in the Galactic anticentre (l 235°). A six-month ×1.7 brightening, achromatic in Gaia
  (k 0.94 ± 0.07). NEOWISE ×1.33/×1.35 on 2015 Apr 10 against the model's ×1.27 (H-0008/H-0009 had seen it as a clean but
  sub-threshold brightening). GSP-Phot makes it a hot star (Teff ~8100 K), so the main alternative is a Be-star outburst. But Be
  disks brighten more in the infrared than in the optical, and here G, BP, RP, W1 and W2 rise alike. It shows no infrared excess
  (W1−W2 −0.04) and no other brightening in NEOWISE 2014-24 or ZTF 2018-25 (inferred).
- **J144905.72-545455.6 (P 0.65).** ×14 in G with a smooth rise and fall over five scan dates; the parallax model is preferred
  (χ² 46 against 76 static and ≥ 53 for any shape). Faint (G 19.9), no NEOWISE source, south of ZTF, outside OGLE coverage.
- **J200958.93+321427.9 (P 0.55)**, in Cygnus (l 70°). ×1.44 for about two months; NEOWISE ×1.27/×1.31 on 2015 Oct 31 against
  the model's ×1.32. A lens beats every non-lens shape by ΔBIC 78. No other brightening in NEOWISE or ZTF. A hot, reddened star
  (Teff ~9200 K, BP−RP 3.3) whose BP/RP are noisy (k 0.70 ± 0.37), so a Be-star outburst remains the alternative.

Four candidates have a second instrument: J174618, J173332, J072830 and J200958. For J182124 the AllWISE source 3" away, a blend
containing the star, rose ×1.2 at +25 d. The other 16 rest on Gaia alone. J201826.29+292422.1 (Gaia DR3 1861208444041823360;
×4.1 in 2016 Mar, NEOWISE ×1.22/×1.18 at +47 d against the model's ×1.33) was a candidate until the checks for repeats. Gaia shows
a 0.28-mag precursor on two transits in 2015 Feb, and ZTF has three bright points (to r 17.9) on 2024 Jan 3-5. Those were taken in
evening twilight 20° from the Sun, at ZTF's limit. It is now inconclusive (P 0.3).

## Not lenses and inconclusive

| Gaia DR3 | verdict | what it is (evidence) |
|---|---|---|
| 508920918409038464 | not a lens, P 0.01 | artifact: 8 one-scan G spikes, absent in BP/RP, on a near-equal pair (neighbour 0.1 mag fainter within 2", C* 30σ); ZTF flat |
| 5939477464424988544 | not a lens, 0.03 | artifact: one scan date, two neighbours within 2", RUWE 3.6, C* 27σ |
| 2030258876550898816 | not a lens, 0.01 | repeating infrared brightener: Gaia ×1.46 while NEOWISE ×2.95/×3.54 (2015); NEOWISE again ×3.3/×4.1 in 2019 with ZTF flat; redder when brighter (k 0.57 ± 0.06); hot star. A Be star or young star |
| 5861862148375056384 | not a lens, 0.03 | NEOWISE swings by 0.7-1.1 mag across 2014-24 and was fainter during the Gaia "event"; a dusty variable |
| 4266315436092309504 | not a lens, 0.05 | infrared excess (W1−W2 +0.23); NEOWISE ×1.7/×2.0 against Gaia ×1.2; redder when brighter |
| 5593963735024586240 | not a lens, 0.12 | a slow, symmetric 0.33-mag bump over a year, redder when brighter at 7σ (k 0.60 ± 0.04) with no neighbour within 2" |
| 4069070918399108992 | not a lens, 0.08 | SIMBAD YSO candidate; redder when brighter (k 0.48 ± 0.11); hot star; cut by the window start |
| 1861208444041823360 | inconclusive, 0.30 | a lens-like ×4.1 event with NEOWISE support, but two hints of repeats (above) |
| 4152593734345648000, 4097904476963000576, 4103794114069593216, 4040204305809966848, 4120472262420519296, 4143778198039891712, 5884091589077519616 | inconclusive, 0.30-0.35 | rising at DR3's end with no decline (3), declining from the first transits at G 20.2 (1), small amplitude (×1.35), shapes fit better than a lens (ΔBIC 45), or a flat top with a contaminated BP/RP window |

All seven non-lenses lie outside the bulge survey footprints, and four are hot or infrared-excess stars. The classifier's impostors
are Be-star/young-star brightenings and blended-pair artifacts, not cataclysmic variables (computed for this sample; inferred as a
pattern).

## The 28 catalogued lenses, and why DR3 left them out (`s14`, `data/dr3_cuts.csv`)

Of the 28, 26 are OGLE and/or KMTNet events, one is KMTNet only, and one is **Gaia16aye** (AT 2016eta), the binary-lens event with
caustic crossings that no point lens can fit (χ² 5 × 10⁵). Wyrzykowski et al. (2023, §4 and table 2) built the catalogue from:

- **Sample A:** automated cuts (G0 < 19, 20 < tE < 300 d, |u0| < 1, 1 < BP−RP < 4, at least one tE inside the data, an event
  longer than 135 d, …) plus visual inspection, 324 → 163.
- **Sample B:** OGLE-IV events with tE > 20 d and a maximum inside the DR3 span, recovered by their pipeline (404 of 1074 matched
  sources), then visual inspection (233). Gaia16aye was among the alerts they considered.

Against those published criteria (computed):

| reason | n |
|---|---|
| OGLE tE ≤ 20 d (Sample B entry cut) | 3 |
| OGLE maximum after DR3 ends | 2 |
| not an OGLE-IV event (KMTNet only) | 1 |
| binary lens (Gaia16aye) | 1 |
| ~~passes Sample B's entry cuts~~ (withdrawn, see below) | 21 |

**Corrected by the referee:** Sample B's input list was Mróz et al. 2019/2020b, not the OGLE alerts. Only 3 of the 28 are in Mróz
2019, and only OGLE-2015-BLG-2080 passes the entry cuts; Gaia16aye was an input and was lost later. The other 24 were never in Sample
B's input list, so "lost at pipeline recovery or visual inspection" does not apply to them; Sample A's cuts need unpublished Gaia
parameters and could not be checked. The classifier, which ran separately, recovered them.
Two of the 28 were also found blind by H-0008/H-0009 (OGLE-2015-BLG-0102 and OGLE-2016-BLG-0086).

## What is new

- **The first one-by-one vetting of the 67 classifier-only MICROLENSING sources** (the list itself is Rimoldini et al. 2023's).
- **9 apparently unreported microlensing candidates** in Gaia DR3 data after the referee, 3 strong; about 5-10 real lenses are
  expected among the 20 unpublished first-pass candidates.
- **An explanation for why they were missed:** 20 of the 21 fell where the ground surveys were not looking, either in fields
  without EWS coverage or near solar conjunction. Where the surveys were looking, the classifier's single events are 95% (18/19)
  catalogued lenses.
- **A calibration of Gaia-DR3-only lens fits:** t0 to ±17 d (80%) and tE to a factor of ~1.5 on 27 OGLE/KMTNet events.
- **The DR3 catalogue's losses:** 28 catalogued OGLE/KMTNet lenses, including Gaia16aye, are absent from it although Gaia's own
  classifier found them; most were never in its Sample B input list.

## Caveats

- **"Apparently unreported" was not checked against:** MOA (its alert pages are empty, as in H-0008; SIMBAD lists some MOA events),
  KMTNet's 2015 season (not in the reference list; its fields lie at negative b near l 0-2°, none of the candidates), or ADS full
  text.
- **Sixteen of the 21 rest on Gaia alone**, typically 3-5 bright transits. Twelve have G > 19, where crowding errors grow; the
  one-scan-date test removed two artifacts, but fainter artifacts that span two scan dates would survive it.
- **Colour is untested for nine candidates**, where the BP baseline is fainter than 20.5.
- **tE is an order-of-magnitude statement** for long, low-amplitude events (J072830, J182124: 190-460 d), where blending, u0 and tE
  trade off. No lens masses or parallaxes are claimed; parallax "preferences" are Δχ² of 10-30 on sparse data.
- **GSP-Phot temperatures in the plane are unreliable** (extinction degeneracy); they were used only as a flag for Be-star risk.
- **P values are judgements**, anchored on the 18/19 calibration and on the second-instrument tests, not on a model. They have not
  been refereed.
- `s1_select.py` originally queried neighbours through the ESA TAP. Those cone queries stalled after an hour, so neighbours come
  from the VizieR mirror (`s1b`). The TNS run was interrupted and resumed; every one of the 67 has an answer.

## Next

- Cases for the three strong candidates once ATLAS and a spectrum-level Be test (J072830) allow; an Hα spectrum of J200958 is
  the decisive Be test.
- **ATLAS** (queued 2026-11-01, `work/atlas/queue.csv`) for 8 candidates: peak after 2015 Aug, dec > −45, peak G < 19, Sun > 50° (`atlas_testable`
  column). They are J200958, J184837, J174036, J182124, J180313, J184922, J182811 and J174029. It could also test 5 inconclusive
  events (J201826 among them) and the 3 cases.
- **Gaia DR4** (2 Dec 2026) re-measures every transit through 2020 with improved crowding treatment. For the events cut by the DR3
  window (J173332 and the three rising at DR3's end) it adds the missing side. A sealed sample prediction in the style of H-0009 is
  possible before then.
- Mróz-style and MOA cross-checks for the bulge candidates; then a TNS report for anything that survives the referee (needs the
  project's TNS account).

Files: `work/gaia_ml_unpub.csv` (one row per source, every measurement and the verdict), `work/gaia_ml_unpub_list.csv` (the
re-derived list), `work/verdicts.csv`, `figures/candidates.png`, `data/` (inputs, fits, diagnostic sheets `diag_*.png`,
`zoom_*.png`), `scripts/`.
