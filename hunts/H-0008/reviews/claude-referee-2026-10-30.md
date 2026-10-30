# Referee report: H-0008 "The lensing sky" (NEOWISE all-sky microlensing search)

Author: claude-referee, 2026-10-30. Scope: the four claims in the brief (blind recovery of 60 known events; four new events;
the efficiency statement; the 432 unclassified). All numbers come from my own code in
`reviews/claude-referee-2026-10-30/` (r1-r21). It runs from the repo root with `uv run python`. Fits use the Oddsky tool
`oddsky.analysis.lensing.Problem`. Everything else is outside the Oddsky tools (requests/pandas/astropy on IRSA, Gaia TAP,
VizieR-idia, SIMBAD-CfA, TNS, ALeRCE, Lasair and the ApJ machine-readable tables) and is marked as such. I re-fetched ZTF
myself (IRSA `nph_light_curves`, catflags = 0, nightly means). NEOWISE comes from the sky3lens visit tables, with two IRSA
single-exposure fetches (r21).

## 1. Verdict

The survey is real: the NEOWISE brightenings that match catalogued lenses are genuine detections, not chance coincidences.
All four "new" events are microlensing. **The novelty claim fails for three of the four.**
- **J204610** is ZTF22aagdkla and **J190512** is ZTF21aaowecs (= Gaia21bde). Both are *high-confidence* events in the full
  Zhai et al. 2024 list (ApJ 978, 76) with the same t0, tE and u0 as the investigators'.
- **J173342** was reported to TNS in 2024 by ALeRCE as a "microlensing event candidate" (AT 2021aicc = ZTF21abahtfi).
- **J180624** is the one event that survives as apparently unreported.

The efficiency statement rests on a NEOWISE visibility model that misplaces about half of all visits by about three weeks.
On top of that, the pipeline cannot see two kinds of lens: those that peak brighter than W1 ≈ 8 (saturated frames are
dropped) and long events (tE > 100 d). "Works as a survey in the disk/halo" is not shown.

- P(the 60 catalogue matches are mostly chance coincidences) < 0.01. The expected number of false matches is ≤ 2.
- P(microlensing) per event, and novelty status:

| event | identity found by this review | P(microlensing) | novelty |
|---|---|---|---|
| J204610.56+514104.9 | ZTF22aagdkla (Zhai+2024 high-confidence; parallax fit πE,N = −0.66); AT 2022aexe = XOSS KATS22J002 "microlensing event candidate" | 0.98 | **known, published** |
| J190512.73+145135.7 | ZTF21aaowecs (Zhai+2024 high-confidence, tE 43.7, u0 0.10) = Gaia21bde = AT 2021dzr | 0.97 | **known, published** |
| J173342.30-205204.5 | ZTF21abahtfi = AT 2021aicc, ALeRCE "Microlensing event candidate" (2024TNSTR2737....1M) | 0.95 | **reported candidate**: no published fit found; the NEOWISE IR epoch and the fit are new |
| J180624.78-090411.4 | ZTF22abjkknd (ZTF alert object; only 2025-26 negative-difference alerts, no positive transient) | 0.85 | **apparently new** (TNS, Zhai, Gaia alerts, KMT/OGLE, ALeRCE/Lasair, SIMBAD, VSX all negative; ADS full text and ASAS-SN not checked) |
| J183040.98-220950.3 (found by this review in the investigators' own strong list) | ZTF22aalviwh (public alerts 59727-59822; ALeRCE class LPV/YSO, not microlensing); 2022 event, g/r/W1/W2 achromatic, tE ≈ 75-130 d, about 60% blended | 0.75 | apparently new (same checks; TNS per r16) |
| J180441.77-182728.7 (sanity check) | ZTF22abcfjfp (Zhai+2024 "possible") | 0.9 | known; the method reproduces Zhai's tE (15.2 vs 14.1 d) |

## 2. Attacks and results

### Claim 1: 60 known microlensing events recovered blind (r5, r10)

**The 60 break down as follows.**
- 56 events are position-and-time matches to the investigators' reference table.
- 4 events (Gaia23bay, Gaia23cpd, Gaia19bsy, Gaia19dqj) are labelled known only because VSX types them as Microlens.
- With the full Zhai list (below), the position-and-time matches rise to 59.

**False-match rate (r10), using the same rule (6", |t − t0| ≤ max(2 tE, 30 d), 100 d for alerts):**
- *Position shifts:* moving all 661 events by 1-3′ in random directions over 200 draws gave **0 matches in every draw**.
- *Time shifts:* shifting the visit times by ±1, 2, 3 yr gave 0, 1, 3, 2, 2, 0 matches. These come from long-tE windows on the
  same star, so they are an upper bound of about 2 per 60 on time coincidences.
- *Match quality:* median separation 0.3″, and only 3 matches lie beyond 2″ (2.05, 2.19 and 4.1″; the last is OGLE-2023-DG-0001,
  also matched to Gaia22duy at 4.1″).
- *Amplitude check:* for the 35 matches with a reference point-lens fit, the magnification predicted at the NEOWISE visit agrees
  with the observed W1 amplitude, or exceeds it (blending).
  - Only 1 match (J180256.26-013325.9, Gaia DR3 fit) has an observed amplitude above 1.5 × the prediction.
  - 7 are strongly diluted (bulge blends, e.g. KMT-2020-BLG-0803: A predicted 13.3, observed 1.75).

**Label conflicts the write-up should mention.** In each case the predicted-vs-observed amplitude favours lensing.
- J170346.25-101251.0: VSX ASASSN-21ak "UG" vs Zhai high-confidence ZTF21aadrxrx; A_pred 1.27, A_obs 1.25.
- J185744.80-204632.7: ASAS-SN "YSO" vs Gaia DR3 microlensing; A_pred 12.2, A_obs 11.95.
- J182402.24-250616.7: VSX "YSO" at 1.97″ vs Gaia DR3 microlensing.
- J175440.54-232037.0: Gaia18cfr "YSO:" vs KMT-2018-BLG-0262.

**Verdict on claim 1:** it survives. "Blind" is fair, since the detector never saw a catalogue. The investigators' 52-row Zhai
table missed 125 events, so the known count is now **64**:
- J204610 and J190512 (Zhai high-confidence);
- J184531.83+021055.9 (= ZTF22aaajzoi, Zhai "possible"; the investigators had it as unclassified);
- J173342 (ALeRCE TNS report).

### Claim 2: four new microlensing events (r2-r9, r16, r17)

**Refits (r4 on the whole light curve; r17 on |t − t0| < 3 tE).** Error floors come from each series' own baseline. The fitter
is `Problem`, with three models: static, static + per-series blending, and parallax + blending. I can reproduce the
investigators' parameters. Their χ² values depend on error choices I cannot reconstruct.
- **J204610.**
  - Static: t0 59725.8, tE 44.9, u0 0.272, A_max 3.77, but χ² **268.5 / 105**. The static point lens is *rejected*.
  - Parallax + blend: χ² 50.0 / 99 (Δχ² = 218), πE,N ≈ −0.5, tE 66. A free rise/fall timescale gives tE_rise 49.4 vs tE_fall
    41.4 (Δχ² = 145). The rise is slower than the fall, the opposite of any outburst.
  - Zhai et al. found the same: static 45.3 d / 0.27, then parallax πE,N = −0.655 with Δχ² = 386.
  - Blending is achromatic: fs = 0.95-0.99 in g, r, W1 and W2.
  - "A point lens fits (χ² 221/212)" must become "a point lens with annual parallax fits; the static model is rejected".
- **J190512.** Static tE 37.2, u0 0.130, A 7.75 (χ² 267.5/91). With blending: tE 43.3, u0 0.105, fs ≈ 0.8 in ZTF and 0.68 in
  W1/W2, χ² 216/86. That is Zhai's solution (43.7, 0.10). The light curve is symmetric (tE_rise 36.4 vs tE_fall 37.8).
- **J173342.**
  - Fit: tE 51.0, u0 0.179, A 5.64. χ² 52.3/30 static, 46.6/26 blended, with fs = 0.97-1.05 in g, r, W1 and W2.
  - The amplitude is **achromatic from g to W2**. W1 and ZTF both read −0.55 mag on the NEOWISE night.
  - The light curve is symmetric (tE_rise 52.5 vs tE_fall 49.9).
  - Adding the catflags = 32768 nights (73 points) leaves tE at 49-51.
- **J180624.**
  - Fit: tE 114.7, u0 0.239, A 4.27, t0 59842 (χ² 19.3/14). With blending: tE 142, fs 0.66-0.69 in r, W1 and W2 alike.
  - The rise is covered by 8 ZTF r nights (field 1428), the NEOWISE visit, and NEOWISE wings of −0.15 / −0.14 mag at Δt =
    −164 / +203 d. The peak and the whole decline fall in the conjunction gap (59851 → 60026). Symmetry is therefore
    untestable, and so is parallax (the parallax fit wanders to tE 378 d).
- **J180441 (sanity check).** tE 15.2, u0 0.42 vs Zhai's 14.1 / 0.40. Passes.

**Mundane alternatives tried, per event.** What kills every intrinsic-variable class (YSO outbursts, Be stars, novae, dwarf
novae, Miras, flares) is that the deblended amplitude is the same in the optical and at 3.4-4.6 µm.
- *Colour:* fs is equal to within ±0.05 across g/r/W1/W2 for J204610 and J173342. It equals 0.66-0.69 across r/W1/W2 for
  J180624, and 0.8 (optical) vs 0.67 (IR) for J190512, which is a blend whose neighbours contribute more in the IR.
- *Symmetry:* where it can be tested, the light curves are symmetric, or asymmetric in the parallax sense.
- *Baselines:*
  - W1 visit scatter is 0.02 mag over ten years for J204610, J173342 and J180624, and 0.06 for the faint J190512.
  - ZTF baselines 2018-2025 are flat (J204610 r/g; J173342 g/r 2019-2024; J180624 i 2018-2020, r 2019 and 2023).
  - ALeRCE detections of J180624 in 2025-26 sit at the quiescent level (corrected r 17.33-17.42). They are negative differences
    against a reference image about 0.3 mag brighter, presumably built during the 2022 event. There is no repeat.
- *Catalogue context:*
  - Gaia DR3: no vari_summary, vari_classifier_result or vari_microlensing entry for any of the five.
  - AllWISE W3/W4: no infrared excess. J190512's apparent W1 − W3 = 1.8 is a W3 upper limit (SNR −0.6). The others have
    W1 − W3 ≈ 0-1 at low SNR.
  - VSX (30″) and SIMBAD (10″): nothing at the target in any of the four. The VSX entries are neighbouring stars at about 21″.
- *A Be star or symbiotic outburst* would be red in the IR, with W2 rising more than W1, and none of these is.

**Novelty (r5, r6, r7, r9, r16).**
- The full Zhai+2024 list comes from the journal's own machine-readable tables (r5): 124 high-confidence + 53 possible =
  177, of which the investigators had 52.
- TNS was queried at 30-60 s spacing, with no 429s; r7 and r16 have the details.
- ALeRCE API and Lasair (r9).
- Gaia alerts (all classes, 30″), the investigators' KMT/OGLE/GVS tables (r6), and SIMBAD-CfA and VizieR-idia VSX (r8).
- Neither J173342 (l = 5.4, b = 6.6) nor J180624 (l = 19.7, b = 5.7) is inside the KMTNet or OGLE EWS footprint. The nearest
  events are 117′ (KMT) and 32′ (OGLE) away for J173342, and 763′ and 396′ for J180624. OGLE EWS was also off in 2020-21.
- A web search for J180624's names finds nothing.
- Not checked: ADS full text (needs a token); ASAS-SN Sky Patrol (down since 13 Oct); ATLAS (r1; see attack 7).

**Verdict on claim 2:** four genuine microlensing events, of which **one is new**. One more is new as a fitted, IR-confirmed
event, but it was already reported as a candidate.

### Claim 3: efficiency, "works in the disk/halo, not the inner bulge" (r11, r12, r13, r19-r21)

1. **The visibility model is wrong.** `hunt_h0008_efficiency.py` puts a star in view when ||λ☉ − λ★| − 90°| < 1°.
   - At the real visit times of the 661 events, **63% of visits fall outside that window**, and the 90th percentile is 22.6° off.
   - From 2015 on, one of the two yearly visits drifts steadily to |Δλ| ≈ 111-113°, about three weeks late (r11: e.g.
     J173342's September visits run +8.5, +14.7, +19.1, +21.0, +22.0, +23.2°).
   - I replaced the model with real visit dates: the nearest of the 661 event stars, shifted by Δλ/0.9856 d. Leave-one-out
     validation gives median |Δt| 0.13 d, and 96% of real visits are reproduced within 3 d (r12).
   - Individual A_at_neowise values change a lot. KMT-2018-BLG-0262 goes 1.14 → 2.45, KMT-2020-BLG-0803 2.46 → 13.3,
     KMT-2022-BLG-1430 2.31 → 1.43, OGLE-2022-BLG-0356 6.5 → 3.7. The aggregate barely moves: KMT 3/167 → 2/161,
     OGLE 4/118 → 4/96, Gaia DR3 4/7 → 4/6.
2. **"Catchable" does not predict recovery.** Most recoveries are "not catchable": KMT 7 of 10, OGLE 5 of 9, Gaia DR3 10 of 14
   (8 of 10 KMT under the corrected visits).
   - The cut uses an optical baseline magnitude that includes blends (I or G ≤ 16), plus unblended A ≥ 1.6. It ignores the
     only quantity the detector sees: the source's share of the 6″ W1 flux.
   - A sensible criterion predicts ΔW1 = 2.5 log[1 + f_W1(A − 1)], with f_W1 from the source's I or G and colour against the
     AllWISE W1 at the position, and requires ΔW1 ≥ max(0.2, 6 σ_W1) at a real, non-edge, unsaturated visit.
3. **Two blind spots the efficiency must include.**
   - *Bright peaks are deleted.* The sky-pass quality cut drops frames with w1sat ≥ 0.05, m below saturation, or nb ≠ 1. A visit
     needs ≥ 3 good frames in both bands, so a peak brighter than W1 ≈ 8 vanishes. ZTF19abagvae (Zhai high-confidence, W1 9.65)
     brightened by **2.54 mag in W1 and 2.37 in W2 in a single visit** (58728) with all other visits calm. Its peak frames are
     saturated (W1 7.13, r21). It is **absent from the raw sky3lens event table** (r19b).
   - *Long events are cut.* "Every other visit calm" rejects 31% of tE = 100-150 d events and 34% of tE > 150 d events even for
     an unblended, noise-free source, against about 6% for tE < 70 d (r20). J180624 passed with its wings at 0.15 and 0.14 mag,
     right at the limit. This matters for any black-hole-lens claim.
   - ZTF21acqomnw (r_source 15.5, A 3.2) brightened −0.60/−0.61 in NEOWISE (r21) and is also missing from the raw table. It has
     only 12 visits in total, so it probably failed the ≥ 10-visit requirement after the nb = 1 cut.
4. **The numbers behind "disk vs bulge"** (corrected visits, the investigators' mag ≤ 16 cut):
   - Inner bulge (|l| < 10°, |b| < 5°): 6/239 = 2.5% (95% CI 0.9-5.4%).
   - Elsewhere: 4/29 = 14% (3.9-32%). Fisher p = 0.015.
   - Full Zhai disk list: 6/85 (7%, 2.6-15%) of events with A ≥ 1.6 at a real visit. But **59 of those 85 have no AllWISE
     source within 3″** (r13). The ZTF sources are faint (r ≈ 19-21), and sky3lens only searches AllWISE-matched detections,
     so the pipeline never looked at them.
   - Of the 26 events with an AllWISE counterpart, 6 were recovered (23%, 9-44%). Among those with W1 ≤ 15, 6 of 15 were
     recovered (**40%, 16-68%**); with W1 ≤ 13, 3 of 8.
   - Two of the bright misses are explained above: ZTF19abagvae (saturated peak) and ZTF21acqomnw (visit count).
   - So among disk stars NEOWISE can actually measure, the recovery is substantial but poorly determined. Over all catalogued
     disk events it is about 5-15%.

**Verdict on claim 3:**
- "Less efficient in the inner bulge" survives (2.5% vs 14%, p ≈ 0.015).
- "Works as a microlensing survey in the disk/halo" is not established. In the disk, NEOWISE recovers roughly 40% (16-68%) of
  magnified events on stars with an AllWISE counterpart at W1 ≤ 15. It cannot see faint-source events at all. It has
  structural blind spots for saturated peaks and for tE > 100 d.
- The disk claim rests on 15-29 test events. Call it "a useful independent detector for bright disk events", not a survey with
  a known selection function.

### Claim 4: the 432 unclassified are mostly crowded-plane variability (r14)

**Control samples.** The 60 known lenses show what a real lens looks like in this pipeline:
- Median |dW1 − dW2| / σ = 0.70 (76% < 1σ).
- No sub-threshold repeats.
- Baseline χ²/dof 2.3.
- The 432 unclassified: 1.70 (32% < 1σ), 10% with repeats, baseline χ²/dof 3.0.
- The "other variables": 1.84 (22%), 17% with repeats, χ²/dof 5.5.

**Distributions.**
- Chromaticity: KS p = 5e-11 against the lenses, and 0.03 against the variables.
- Amplitude: the unclassified match the variables (KS p = 0.61) and not the lenses (p = 6e-6).

**Lens-like fraction.**
- Achromaticity mixture: **0.19** (bootstrap 68% range 0.13-0.27; 95% upper limit 0.31), i.e. about 55-115 of 432.
- *The investigators' own ZTF check* covers 78 of the 432. In 52 of them the optical brightening is < 1/3 of the W1 brightening
  (median ratio 0.18), mostly in events where W2 rises more than W1, which is IR-excess behaviour. In 13 of 78 (17%) it is
  ≥ 2/3, as a lens predicts.
- Those 13 include the four claimed events, J184531 (Zhai "possible"), YSO-region stars in Orion (b ≈ −17/−18), and one new
  lens-like event: **J183040.98-220950.3** (G = 14.3 bulge giant, l = 10.9, b = −5.6, in the investigators' strong list but
  not singled out).
  - *ZTF (r18, r18b):* a single smooth 2022 event. g rises from −0.05 (59714) to −0.54 (59805), plateaus near −0.5 until 59826,
    and is at −0.40 by 59848. r reads −0.32, −0.46 and −0.50 on three nights. W1/W2 read −0.47/−0.46 on 59831.
  - *Baselines:* every other ZTF season 2018-2021 and 2023-2025 sits within ±0.05 (seasonal medians).
  - *Fit:* point lens with blending, χ² 184/153, tE 112 d, u0 0.42. fs = 0.37-0.41 in g, r, W1 and W2 alike, i.e. achromatic
    with about 60% blend light (4 Gaia sources within 3″).
  - *Context:* outside the KMT/OGLE EWS footprints. Nothing in Gaia alerts or the reference tables within 27′.
  - It is as good a lens candidate as J180624 and should be treated the same way. [TNS: see r16 below.]

The Gaia DR3 "VARIABLE flag 0.7%" statistic is circular: VSX includes the Gaia DR3 classifications, so anything flagged was
already classified. It should not be used as evidence either way.

**Verdict on claim 4:** it survives as "mostly". About 80% of the unclassified behave like variables (chromatic IR, optical
flat). The remainder implies **tens of lens-like events** in the unclassified pool, most of them south of ZTF and unverifiable
without ATLAS or OGLE.

### Standard attacks from REFEREE.md, briefly

- *Instrument artifacts:* the four events have artifact share ≤ 0.04 and chi² ratio 0.39-1.27, and are confirmed by ZTF on
  the same nights.
- *Blends:* J173342 has 10 Gaia sources within 6″, but the G = 14.8 star dominates and fs ≈ 1 everywhere. J190512 has
  neighbours at 4.8 and 5.9″ (G 19.3, 20.0), consistent with its IR fs of 0.67.
- *Physical consistency:* tE of 37-143 d for disk/bulge lenses at l = 5-90° is normal. J180624 (tE 115-143 d) is long but not
  extreme.
- *Untapped data:* ATLAS forced photometry was requested for all five (r1). The shared queue had not started our task after
  more than 2 h behind other tasks. **This is the main missing check for J180624's decline and peak.**

## 3. Most plausible mundane explanation remaining

There is none for the four events as microlensing. The remaining mundane outcome is **"already known"**: J204610 and J190512
are published (Zhai+2024), and J173342 is a TNS-reported ALeRCE candidate. For J180624, the residual risk (P ≈ 0.15) is an
unobserved decline that is not lens-shaped, such as a slow, nearly achromatic symbiotic or giant outburst. Nothing in the data
points that way, but the peak and the whole decline are unsampled.

## 4. Required wording changes

- **Headline / hook.** Change "four new microlensing events" to "the survey independently recovers 64 known microlensing events
  and finds one apparently unreported event (J180624.78-090411.4, 2022, tE ≈ 115-140 d). A second, J173342.30-205204.5
  (2021), had only been posted to TNS as an ALeRCE candidate and is fitted and confirmed in the infrared here for the first time."
  If the ATLAS check holds, add J183040.98-220950.3 (2022, tE ≈ 75-130 d) as a second candidate.
- **J204610 and J190512.** Retract "new". Write "= ZTF22aagdkla / ZTF21aaowecs (Zhai et al. 2024, high confidence), recovered
  blind; NEOWISE adds one 3.4/4.6 µm epoch near peak". Give J204610's fit as parallax-preferred (static χ² rejected; Δχ² ≈ 220),
  not "a point lens fits, χ² 221/212". Cite AT 2022aexe / XOSS KATS22J002 and AT 2021dzr / Gaia21bde.
- **J173342.** Write "reported as an ALeRCE microlensing candidate on TNS (AT 2021aicc = ZTF21abahtfi, 2024TNSTR2737); first fit,
  and first infrared confirmation of achromaticity (fs = 0.97-1.05 from g to W2)".
- **J180624.** Write "apparently unreported", and list what was checked: TNS, full Zhai, Gaia alerts, ALeRCE/Lasair, KMT/OGLE
  footprints, SIMBAD, VSX. State that ADS and ASAS-SN were not checked, that the peak and decline are unobserved, and that
  tE = 115-140 d depends on blending.
- **Claim 1.** Write "60 → 64 known events. Matches are secure: 0 chance matches in 200 position-shifted trials; ≤ 2 by time
  coincidence". Say that 4 of the 60 rest on VSX types alone, and list the label conflicts (ASASSN-21ak "UG", two ASAS-SN or VSX
  "YSO" against Gaia DR3 lenses).
- **Claim 3.**
  - Delete "NEOWISE works as a microlensing survey in the disk/halo". Replace it with "outside the inner bulge NEOWISE recovers
    about 5-15% of all catalogued events that are magnified at a NEOWISE visit (4/29 and 6/85). For disk events on stars with an
    AllWISE counterpart at W1 ≤ 15 the figure is about 40% (6/15). In the inner bulge it is 2.5% (6/239). The pipeline is
    blind to peaks brighter than W1 ≈ 8 and rejects about a third of events with tE > 100 d."
  - Withdraw the KMT 3/167, OGLE 4/118 and Gaia 4/7 figures until they are recomputed with real visit dates and a W1-based
    criterion.
- **Claim 4.** Write "about 80% of the unclassified behave like ordinary variables (IR-chromatic, optically flat). Roughly
  10-25% are lens-like, most unverifiable without southern optical data." Drop the Gaia variability-flag statistic. Name
  J183040.98-220950.3 and J184531.83+021055.9 (Zhai "possible").
- **Ladder status.** J180624 is a *candidate (one survey + one sparse optical survey)*, not "confirmed". J173342 is *reproduced*,
  but not new.

## 5. Decisive follow-ups

1. **ATLAS forced photometry for J180624.78-090411.4, 2022 Jun-Nov** (o band; Chile/South Africa units cover until about
   Oct-Nov). One light curve settles the peak, the decline and the symmetry, and therefore P(microlensing) and tE. It is queued
   (r1). Re-run `r1_atlas.py J180624` when the queue clears, then `r4_fits.py J180624`, which uses ATLAS automatically.
2. The same ATLAS check for J183040.98-220950.3 (2022 Apr-Nov) before it is added as a fifth event.
3. ADS full-text search for "ZTF22abjkknd" / "J1806-0904" / "18:06:24.7" and the ALeRCE ZTF21abahtfi candidate list, before any
   public "new" claim.
4. For the efficiency: rerun hunt_h0008_efficiency.py with real visit dates (r12 method) and a W1-flux-based criterion. Then
   rerun the detector on known bright events with saturated frames kept, as a separate flagged class.

## 6. Tool fixes (what let the mistakes through)

1. **`hunt_h0008_vet.py` TNS lookup.** The `tns` column is empty for all 70 strong events, yet r7/r16 find TNS objects for at
   least five of them: AT 2021dzr, AT 2022aexe, AT 2021aicc, AT 2023gcb, AT 2021cwl. Any response without a `Name` column must
   be recorded as UNKNOWN, never "". Write "none" explicitly. Fetch the object page, because the remarks ("Microlensing event
   candidate") are where the classification lives; the TNS type is empty.
2. **Gaia source ids written as floats** (`g_source_id` = 5.870565195217874e+18 in sky3_x/sky3_classified). The
   `gaiadr3.vari_microlensing` check in `hunt_h0008_classify.py` therefore returns an empty table with no columns, silently. I
   verified that the same query with the integer ids returns hits. Keep ids as strings or int64 end to end, and fail loudly
   when an ADQL result lacks the expected column.
3. **Reference catalogue.** Use the Zhai+2024 machine-readable tables
   (`content.cld.iop.org/journals/0004-637X/978/1/76/revision1/apjad94e7t{2,3}_mrt.txt`), not the 52 rows in the arXiv HTML.
   Add TNS AT reports whose remarks mention microlensing (ALeRCE, XOSS) and an ALeRCE/Lasair cone search.
4. **`hunt_h0008_efficiency.py` visibility.** Use real visit epochs, not |Δλ| = 90 ± 1°. Use the same match radius as the
   reference matching (3″ vs 6″ today). Base "catchable" on the predicted W1 amplitude, not an optical magnitude.
5. **Sky-pass blind spots** (`neowise_lens.py` via `neowise_pixel_v2.quality`).
   - Keep saturated or partially saturated visits as a flagged class instead of deleting them. A 2.5-mag lens disappeared.
   - Report the share of stars lost to `nb == 1` and to the ≥ 10-visit cut, per pixel, in the census, so the efficiency can be
     computed.
   - Note that only AllWISE-matched detections (r_allwise < 2″) are searched. 59 of the 85 Zhai events magnified at a NEOWISE
     visit have no AllWISE source within 3″ (r13).
   - Relax "all others calm" to "no other excursion of the same sign beyond 3σ outside ±1 visit", so long-tE events survive.
6. **Novelty checks** must cover the Gaia alert *comment*, not only its class: Gaia21bde is "unknown, ~0.4 mag rise", but it is
   in Zhai with the Gaia name.
