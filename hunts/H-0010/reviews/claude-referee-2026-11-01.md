## 1. Verdict

Author: claude-referee (H-0010 pass), 2026-11-01. Scripts, logs and data are in `reviews/claude-referee-2026-11-01/`. Run them from the
repo root with `uv run python -I <script>`. I re-fetched every input myself and did not import the investigators' code, with one
exception: r3e reads their `lib.epoch()` to audit its clip. The inputs I fetched:

- Gaia DR3 epoch photometry through `gaia_epoch.fetch_report(ids, releases=("Gaia DR3",))`, plus the raw datalink CSV.
- The Gaia TAP: neighbours, blend diagnostics, astrophysical parameters.
- GOST scan geometry.
- IRSA NEOWISE-R single exposures within 8″ (25″ for J174618), AllWISE and 2MASS.
- OGLE EWS `lenses.par` 2014-17, the KMTNet 2015 public page, MOA, the Gaia alerts live CSV, TNS (paced), the ASAS-SN transients
  page, VizieR on the idia mirror (CDS was unreachable all day), SIMBAD (CfA), APOGEE DR17, OGLE's GVS light curve, and the
  literature (arXiv, plus the Rimoldini+2023, Eyer+2023 and Mróz+2020 papers).

Column definitions for the table:

- **lens vs shape**: ΔBIC of the best non-lens shape minus the best physical lens (fs ≤ 1 in every band; static or parallax).
  Positive favours the lens.
- **colour**: Δ(BP−RP) at the transits where G is brightened by ≥ 5σ, with BP/RP not clipped against G, and the excess ratio
  k = (F_BP − 1)/(F_RP − 1). An unblended lens gives Δ = 0 and k = 1.

| candidate | H-0010 P | my P | verdict | main reasons |
|---|---|---|---|---|
| **J174618.09-253631.3** | 0.85 | **0.75** | **keep** (claim corrected) | Real, smooth ×4.4 G event on an APOGEE red giant (Teff 3960 K, log g 1.8, [M/H] +0.47). G/RP equal (RP/G excess 0.97). NEOWISE frames clean, event centroid on the star. Scan angles and FoV pairs clean. **But** "×7.3 observed vs ×7.1 predicted" is spurious: the ×7.1 needs fs_G = 1.5 (at the fit bound, a negative blend). Physical lens fits predict ×4.3-10.6. The ×7.3 baseline is a 6″ neighbour's blend, and the star's true W1 ratio is ×7.6-11.4. A Gaussian beats the lens by ΔBIC 14 (4 Gaia points) |
| **J173332.42-421445.1** | 0.75 | **0.75** | **keep** | Achromatic to 2%: Δ(BP−RP) +0.002 ± 0.017, k 1.003 ± 0.037. A physical parallax lens (fs ≈ 1, t0 2014 Aug 4, tE ≈ 135-140 d, u0 0.33, πE ≈ 0.2) beats every shape by ΔBIC 45, and by Δχ² 61 when NEOWISE is included. NEOWISE (clean frames, on the star) agrees at all three visits. The investigators' static model (t0 2014 Jul 11) predicts ×2.5 for 2014 Mar 17, **excluded** by NEOWISE (W2 ×1.03, star barely detected) |
| **J072830.43-204112.5** | 0.65 | **0.60** | **keep** | Achromatic: Δ(BP−RP) −0.005 ± 0.020, k 1.006 ± 0.071. NEOWISE ×1.34/×1.34 in 13 clean frames on the star, against a model ×1.30. Be star disfavoured: ESP-HS types the XP spectrum K; XP Hα pEW −0.12 ± 0.11 nm and VPHAS+ r−Hα at the field locus (no emission); no K or W1 excess; IR amplitude equals optical. **tE is not 188-456 d**: that range is the fs = 0.07 static solution. The physical parallax lens has tE ≈ 47 d, u0 0.68, fs ≈ 1 (Δχ² 39 over the best shape). The investigators' "ΔBIC 330" is a failed shape fit |
| **J144905.72-545455.6** | 0.65 | **0.45** | **downgrade** | ×14 over 6 dates, FoV pairs agree, scan angles clean, BP/RP consistent with achromatic at peak (Δ +0.15 ± 0.17; "untested" is wrong). But with fs ≤ 1 the parallax lens is **not** preferred (ΔBIC +1.2 over FRED). The investigators' "χ² 46 vs ≥ 53" used fs_G = 1.5. Gaia only; G 20; a YSO (EXor-type) burst is not excluded |
| **J200958.93+321427.9** | 0.55 | **0.40** | **downgrade** | ×1.44, u0 ≈ 0.8. A fair asymmetric Pearson VII fits better than the lens (ΔBIC −4.6). The investigators' "ΔBIC 78" is a failed shape fit (their pv7 χ² 2330 against a lens 302). NEOWISE ×1.28/×1.32 is real and on the star (the centroid shift matches). Be outburst disfavoured but not excluded: IPHAS r−Hα 0.56 against 0.70 ± 0.15 for field stars of the same r−i (no emission, pre-event epoch); no XP spectrum |
| J174656.42-190909.2 | 0.50 | 0.45 | keep | Achromatic (Δ +0.025 ± 0.061). Lens ≈ shape (ΔBIC −5.5). VVV VIVACE classifies the source as an LPV (unexplained; Gaia baseline scatter is only 0.009 mag) |
| J171847.68-300609.5 | 0.50 | 0.35 | downgrade | Shape better by ΔBIC 9.3. Δ +0.21 ± 0.13, k 0.54 ± 0.30. Crowded: 12 Gaia sources within 6″, two within 2.5″; C* 3.4σ |
| J184922.92-000203.9 | 0.50 | **0.15** | downgrade (likely emission-line star) | A static lens fails (Δχ² 137). Parallax needs tE ≈ 890 d, u0 ≈ 0, fs_G 0.11. Colour untestable (1 transit). **Hα excess in two surveys**: IPHAS r−Hα 1.13 against 0.65 ± 0.10 for the field (4.6σ); VPHAS+ 0.92 against 0.62 ± 0.14 (2.1σ). Points to a YSO, Be star or CV |
| J172020.30-381044.3 | 0.50 | 0.20 | downgrade (inconclusive) | **Bluer when brighter, 4.9σ**: Δ(BP−RP) −0.51 ± 0.10, k 1.43 ± 0.24. The faint-BP bias would push the other way |
| J182124.77-190909.7 | 0.50 | 0.60 | **keep as a lens, but NOT new** | **Published** as OGLE-IV GVS "possible microlensing event" BLG783.17.33659 (Mróz et al. 2020, Table B2; 0.14″). OGLE's public I light curve shows the same single 2015 event (Gaia ×1.42 and OGLE ×1.42 on the same night). The NEOWISE centroid moves onto the Gaia star |
| J175414.32-275241.8 | 0.50 | 0.40 | keep (marginal) | 2 dates, 4 transits. Shape better by 5.8. In an OGLE/KMT field (9 OGLE events within 15′ in 2014-17; KMT 2016) at a late-season peak |
| J174036.98-223251.4 | 0.50 | 0.30 | downgrade | Shape better by 14.7. Bluer when brighter at 2σ (Δ −0.49 ± 0.25, k 1.9 ± 0.7). C* 7.4σ (BP/RP contaminated). "Achromatic yes" was not justified |
| J174029.07-331407.7 | 0.50 | 0.30 | downgrade | BP barely follows: k 0.23 ± 0.12. A lens needs fs_G 0.09-0.21. Lens ≈ shape |
| J171234.40-353502.0 | 0.45 | 0.30 | downgrade | Redder when brighter: k 0.52 ± 0.14, Δ +0.37 ± 0.19. Shape better by 5.9 |
| J182656.25-264645.9 | 0.45 | 0.30 | downgrade | 3 transits on 2 dates; 5 similar-brightness Gaia sources within 4″ (3 with RUWE 2-4); k 1.47 ± 0.28 |
| J190032.43-004939.8 | 0.45 | 0.25 | downgrade | **Two single transits**, both FOV2, 31 d apart, never confirmed by the other FoV. G 16.4 neighbour at 3.1″ (2.75 mag brighter); C* 4.8σ |
| J151331.38-523733.2 | 0.45 | 0.45 | keep | Achromatic (k 1.10 ± 0.16). Lens ≈ shape (−4.1). Neighbour at 1.5″ (ΔG 1.4) |
| J171838.94-334129.2 | 0.45 | 0.40 | keep (marginal) | Lens ≈ shape (−0.5). Colour weak (Δ −0.32 ± 0.21) |
| J182811.16-082538.6 | 0.45 | 0.30 | downgrade | BP does not follow G at the ×9 peak (the investigators' clip removed that BP point). 2 dates. Baseline scatter 0.10 mag, with a 0.17 spread between scan-angle bins. AEN significance 6.1 |
| J180313.03-150702.0 | 0.40 | **0.10** | **kill** (→ not a lens / chromatic transient) | **Bluer when brighter, 4.3σ** (Δ −0.66 ± 0.15, k 2.2 ± 0.4). An asymmetric non-lens shape beats every physical lens by ΔBIC 33 |
| J184837.12-051620.2 | 0.40 | 0.30 | downgrade | ×1.38, u0 0.5-0.7. Bluer at 2σ (Δ −0.11 ± 0.05). Lens ≈ shape |

**Totals.**

- Of the 21:
  - 9 remain new candidates at P ≥ 0.4: J174618, J173332, J072830, J144905, J200958, J174656, J175414, J151331, J171838.
  - 1 is a lens candidate already in print (J182124).
  - 10 fall to inconclusive (P 0.15-0.35).
  - 1 is killed (J180313).
- ΣP over the 20 that are actually unpublished is **7.5**, not 11 (§7).

**What the investigators got wrong.**

1. **The J174618 "×7.3 vs ×7.1" agreement is not a test** (§3.1).
   - The ×7.1 comes from a static fit with fs_G pinned at the upper bound 1.5.
   - The ×7.3 divides by a "baseline" that is a different star 6″ away, blended with the target.
2. **Blending at bounds again** (the H-0008 pitfall).
   - `lensing.Problem` allows 0.02 ≤ fs ≤ 1.5. In `gaia_ml_unpub.csv`, 20 of the 21 candidates have at least one fitted fs (static or parallax) at 1.5 or 0.02, and 10 have fs_G itself at a bound.
   - The tE ranges quoted for J072830 and J182124 (190-460 d) are fs ≈ 0.04-0.07 solutions.
   - J144905's parallax preference rests on fs_G = 1.5.
3. **Broken non-lens fits** inflate "lens beats every shape" claims.
   - J200958 (78), J072830 (330), J174656 (12 633) and J184837 (1303): their best shape χ² is 1.7-28× the lens χ² (e.g. J174656 13 102 against 469), i.e. the optimiser failed.
   - With a working shape fit, only J173332 (+45), J072830 (+34) and J172020 (+10, but chromatic) prefer a lens.
4. **Colour labels.**
   - Two "untested" candidates are chromatic: J172020 and J180313, bluer when brighter at 4-5σ.
   - Two labelled "achromatic yes" are not shown to be: J174036 (bluer at 2σ, C* 7.4σ) and J184837 (2σ).
   - J144905's colour is testable at peak and passes.
   - The BP/RP clip in `lib.epoch()` (drop BP/RP points that disagree with G by more than max(1 mag, 5σ)) is conditioned on the answer. In these data it removed one informative event point (J182811's BP at peak) besides gross spikes (r3e).
5. **Novelty.**
   - J182124 is published (Mróz et al. 2020, Table B2).
   - The list of 67 itself is published: Rimoldini et al. 2023, §4.13 and Appendix D, give the count and the ADQL (§6).
6. **The "28 known lenses, 21 pass Sample B's entry cuts" claim is wrong.**
   - Sample B was drawn from Mróz et al. 2019 and 2020b, not from the OGLE EWS.
   - Only 3 of the 28 are in Mróz 2019 and none is in Mróz 2020b. Only 1 (OGLE-2015-BLG-2080) passes the published entry cuts (§8).

## 2. Data re-derived (r1, r1b, r2, r3b)

**Epoch photometry (r1).**

- My re-fetch through `fetch_report(..., releases=("Gaia DR3",))` returns, for all 21, exactly the investigators' transits and
  magnitudes (max |Δmag| = 0).
- The raw datalink CSV adds transit_id, flux_over_error and the flag words.

**g_other_flags (r1b).**

- Bright transits carry g_other_flags bits 2-10, which the historical ESA help describes as "AF1-AF9 rejected by photometric
  processing". Quiet transits carry 1.
- The same holds for the bright transits of 6 catalogued lenses among the 67: 35 of 42 are flagged. So this is a generic response
  to a large brightening, not an artifact marker.

**Neighbours and blending (r2, Gaia TAP, 6″).**

| | G | RUWE | ipd_frac_multi_peak | C* (σ) | BP/RP blended transits | nearest neighbours |
|---|---|---|---|---|---|---|
| J174618 | 17.54 | 1.01 | 0 | 2.5 | 1/39, 0/34 | 3.4″ (ΔG +1.26), 5.0″ (+0.77) |
| J173332 | 16.79 | 1.06 | 0 | 1.0 | 23/23, 19/19 | 4.9″ (+2.35) |
| J144905 | 19.85 | 0.97 | 0 | −0.6 | 0/24, 0/24 | 3.2″ (+0.58), 4.9″ (−0.66), 5.7″ (−0.24) |
| J072830 | 17.10 | 1.03 | 0 | 0.8 | 0/67, 1/59 | 3.0″ (+3.37) |
| J200958 | 17.74 | 0.97 | 1 | 1.4 | 21/50, 19/49 | **1.9″ (+1.98)**, 4.6″ (+0.86) |

- None of the five has a Gaia neighbour that could enter the G PSF fit.
- J200958's 1.9″ neighbour (16% of the flux) enters the BP/RP window at some scan angles. That explains its noisy BP and k < 1.
- Full list for all 21: `r2_neighbours_gost.log`.

**Scan-angle test (r3b).** Every G transit was matched to GOST (FoV, scan angle; 1-4 unmatched per star). For each event transit I
took the baseline transits within ±20° (mod 180°) of the same scan angle.

| | event transits (dates) | event scan angles (mod 180°) | baseline transits at the same angles: max excess | same-day FOV1/FOV2 pairs |
|---|---|---|---|---|
| J174618 | 4 (3) | 38, 41, 137, 137 | +0.6%, +1.7% | ×4.396 / ×4.415 (−0.4σ) |
| J173332 | 7 (4) | 48, 135, 143, 151 | ≤ +2.0% | 3 pairs, all < 1σ |
| J144905 | 10 (6) | 26-32, 72-76, 145 | ≤ +17% (baseline scatter 6%) | 3 pairs < 0.6σ |
| J072830 | 17 (9) | 9-22, 74-84, 120, 145 | ≤ +1.4% | 5 pairs, ≤ 2.0σ |
| J200958 | 10 (6) | 47, 73, 112, 167-170 | ≤ +1.4% | 2 pairs < 1σ |

- None of the 21 brightens at a scan angle where baseline transits do not. The impostor class "blended pair measured differently
  along scan" is excluded for all 21.
- Weakest:
  - J190032: 2 transits, both FOV2, no pair.
  - J182656 and J175414: 2 dates.
  - J182811: baseline scatter 0.10 mag and a 0.17 spread between scan-angle bins (`r3b_scan_angle.log`).

## 3. The five best

### 3.1 J174618.09-253631.3 (r3, r3c, r5, r5b, r5c)

**The star.**
- APOGEE DR17 2M17461809-2536313 (1 visit, 2018-05): Teff 3964 K, log g 1.79, [M/H] +0.47, RV 63 km/s. A metal-rich bulge red giant.
- Gaia XP Hα pEW +0.41 ± 0.25 nm (absorption side); ESP-HS type M.
- An ideal source star, and it removes Be stars, YSOs and CVs as hosts.

**Gaia light curve.** Four transits on three dates:

| date | G | RP | BP |
|---|---|---|---|
| Feb 25 | ×1.82 | ×1.79 | ×1.48 ± 0.39 |
| Mar 25 (two FoVs) | ×4.40 / ×4.42 | ×4.29 / ×4.24 | ×3.8 ± 0.9 |
| Apr 17 | ×1.40 | ×1.34 | – |

- Achromatic within Gaia: Δ(BP−RP) +0.15 ± 0.14, k 0.80 ± 0.18; RP/G excess 0.97.
- Only two transits before the event (2014 Oct).

**Fits** (fs ≤ 1 unless stated):

| model | χ² (n 125) | BIC | t0, tE, u0, fs_G | G-model at the NEOWISE visit (2015-03-19) |
|---|---|---|---|---|
| static lens | 928.3 | 957.3 | Mar 18, 33 d, 0.091, 1.00 | **×10.6** |
| parallax lens | 918.9 | 957.5 | Mar 29, 83 d, −0.13, 0.55 | ×4.3 (source ×7.1) |
| static lens, fs ≤ 1.5 (the investigators' bound) | 925.7 | 954.6 | Mar 18, 27 d, 0.20, **1.50** | **×7.06** (the investigators' ×7.07) |
| Gaussian | 919.1 | **943.2** | | |
| pv7 / FRED | 919.1 | 948 | | |

- 830 of the χ² is three single-transit RP spikes in the baseline. They are common to all models (r3c).
- With four event points, the lens is not preferred; a Gaussian is better by 14 in BIC.
- The "prediction" for the NEOWISE epoch spans ×4.3-10.6 across acceptable physical fits.

**NEOWISE exposures.**
- In every quiet visit, the only detection within 8″ sits 4.5-5.5″ SE of the star (nb = 2). This is the 2MASS K = 11.66 neighbour
  at 6.3″, blended with the target. The target itself is never extracted on its own.
- Only 4% of quiet frames have a detection within 3″. Those frames supplied the survey's "7 visits of 21 exposures" baseline of
  W1 10.92.
- In the event visit all 11 frames show a single nb = 1 detection 0.19″ from the Gaia star: W1 8.76, W2 8.96, 7 frames clean,
  frame scatter 0.03 mag. The SE detection is gone, i.e. merged into the event detection.
- So the event is on the Gaia star and is not an artifact, but the baseline is not the star.
- Star-only baselines:
  - AllWISE (deblended, nb = 3) gives W1 11.06 and W2 11.40.
  - 2MASS K 11.63 implies W1 ≈ 11.3-11.4.
  - These give A_W1 = 7.6-11.4, depending on how much of the neighbour went into the event detection, and A_W2 ≈ 9.5 (r5c).

**Verdict.**
- The event is real, on a red giant, achromatic in G/RP, and its peak fell between Gaia transits. NEOWISE shows the peak reached
  ≳ ×8.
- Single in Gaia 2014-17, NEOWISE 2014-24 (total flux within 8″ flat to 0.05 mag) and ZTF.
- No alternative I can name makes a ×8, one-month, 0.6-4.6 µm achromatic brightening of a metal-rich bulge giant.
- But "the Gaia-only lens model predicted the NEOWISE ratio" must be withdrawn. P 0.75.
- **Safe wording:** "a smooth, achromatic ×4.4 (G) brightening of an APOGEE bulge giant in 2015 March; NEOWISE caught the peak at
  ×8-11 in W1/W2 between Gaia transits. A point lens fits, but four Gaia points do not distinguish it from a symmetric bump."

### 3.2 J173332.42-421445.1 (r3, r5)

**Gaia.**
- ×2.47/×2.48 on 2014 Sep 7, ×1.87 on Oct 12, ×1.20 on 2015 Mar 28, ×1.14/×1.16 on Apr 20. BP and RP are identical to 1-3%.
- Excess ratio k = 1.003 ± 0.037.

**Fits.**
- A static lens wants u0 → 0 and t0 2014 Jun 11, which predicts ×2.5 for the NEOWISE visit of 2014 Mar 17.
- The physical parallax lens (χ² 297.9 against 338.1 static; n 79):
  - t0 2014 Aug 4, tE 135 d, u0 −0.35, πE (0.12, −0.16), fs 0.99-1.00 in all bands;
  - predicts ×1.17 for 2014 Mar 17, ×2.31 for Sep 15 and ×1.22 for 2015 Mar 17;
  - all shapes are worse: pv7 χ² 351, FRED 399, Gaussian 532.
- The fast-then-slow decline is what a Paczyński curve gives and a bump does not.

**NEOWISE** (on the star, all frames, centroid within 0.1″):

| date | W1 | W2 | detected frames |
|---|---|---|---|
| 2014-03-17 | ×1.30 | ×1.03 | 2, as in quiet visits; a ×2.3 star would be detected in all |
| 2014-09-15 | ×2.45 | ×2.39 | 10 of 10 |
| 2015-03-17 | ×1.26 | ×1.16 | |

- A joint fit with NEOWISE (parallax lens) gives χ² 309, against 370 for the best shape.

**Verdict.**
- Achromatic, one-sided but Paczyński-shaped, confirmed in the IR. P 0.75.
- Correct the README:
  - t0 is in 2014 Jul-Aug (parallax fit Aug 4), not "before 2014-09-07, fit 2014-07-11";
  - tE ≈ 140 d in the parallax fit, not "unconstrained";
  - the NEOWISE 2014-03 visit is a constraint the README omits.
- Alternatives: no IR excess (K−W1 0.12), G 16.8 with BP−RP 1.69. Any intrinsic variable would show some colour change over
  ×2.5 → ×1.1, and none is seen to 2%.

### 3.3 J072830.43-204112.5 (r3, r5, r6)

**Gaia.**
- First transit (2014 Oct 28) already ×1.06. Then ×1.09-1.11 (Dec 4), ×1.16 (Dec 21), ×1.70-1.71 (2015 Feb 19), ×1.58-1.59 (Mar 11),
  ×1.27 (Apr 16), ×1.15 (May 23-Jun 8), ×1.03 (Nov).
- Achromatic over 16 transits: Δ(BP−RP) −0.005 ± 0.020, k 1.006 ± 0.071.
- The rise is faster than the decline.

**Fits** (n 222; χ² dominated by baseline BP/RP spikes):
- The static lens runs to fs = 0.066 (tE 240 d, u0 0.08). That is the investigators' 188-456 d.
- The physical parallax lens has fs 0.98, tE 47 d, u0 0.68, πE (0.28, −0.54), χ² 1771.1.
- The best shape (asymmetric PV7) has χ² 1810.5.
- So **tE is 47-240 d depending on blending**, and the README's "188-456 d" must go. Their ΔBIC 330 compares with a failed shape fit
  (pv7 χ² 13 321).

**NEOWISE.** W1 ×1.34 and W2 ×1.34 on 2015 Apr 10, in 13 clean frames. The centroid does not move (isolated). The model gives ×1.30.

**Be-star test.**
- GSP-Phot gives Teff 8144 K, but:
  - ESP-HS classifies the XP spectrum as **K**;
  - Gaia XP Hα pEW is −0.12 ± 0.11 nm, no emission (Be stars in XP typically show ≲ −1 nm), averaged over 2014-17 including the event;
  - VPHAS+ r−Hα is 0.60, against 0.58 ± 0.09 for 17 field stars of the same r−i;
  - J−H 0.81, H−K 0.32, K−W1 0.15, W1−W2 −0.04 lie on the reddening line of a K giant (E(BP−RP) ≈ 1.1), with no K or W1 excess;
  - the IR brightening equals the optical one, whereas disc build-up brightens the IR 2-3× more.
- Be is disfavoured.

**Verdict.** P 0.60. The rise/decline asymmetry, reproduced by parallax, is the remaining reason for caution.

### 3.4 J144905.72-545455.6 (r3)

**Gaia.**
- ×1.17 (2014 Oct 4), ×11.3 (2015 Jan 6), ×14.0/×13.6 (Jan 23, two FoVs), ×3.9 (Feb 26), ×1.64-1.75 (Apr 8, four transits),
  ×1.47-1.68 (Apr 19), ×1.0 from Jul.
- At peak BP ×13.7 and RP ×14.3 track G: Δ(BP−RP) +0.15 ± 0.17, k 0.71 ± 0.19.

**Fits.**

| model | χ² | BIC |
|---|---|---|
| static lens, fs ≤ 1 | 127.0 | |
| parallax lens, fs ≤ 1 (tE 140 d, u0 0.05, πE 0.66) | 79.8 | 115.6 |
| FRED | 90.0 | 116.8 |
| pv7 | 91.8 | 118.7 |
| pv7_asym | 87.6 | 119.0 |

- The investigators' parallax χ² 45.9 used fs_G = 1.5.

**Verdict.**
- A real, smooth event with no second instrument (no WISE source, south of ZTF, outside OGLE).
- A long, roughly symmetric outburst of an unknown faint source (EXor-like) is not excluded.
- P 0.45.

### 3.5 J200958.93+321427.9 (r3, r5)

**Gaia and the fits.**
- ×1.09 (2015 Sep 19), ×1.16, ×1.41, ×1.44 (Dec 15), ×1.22 (2016 Jan 8), ×1.04 (Feb 28).
- Lens: tE 41-44 d, u0 0.79-0.80, fs_G 0.95, χ² 337.2. pv7_asym: χ² 337.7, BIC 373.1 against the lens's 377.7.
- No preference.

**NEOWISE.**
- ×1.28 (W1) and ×1.32 (W2) on Oct 31 in 14 clean frames.
- The quiet centroid is 0.48″ off the Gaia star (the 1.9″ neighbour). In the event it shifts by (+0.09, −0.11)″, against a
  predicted (+0.03, −0.10)″ if the Gaia star brightened. So the brightening is on the star.

**Verdict.**
- Low amplitude on a hot, reddened star (GSP-Phot 9240 K, A_G 5.9 mag, BP−RP 3.3).
- K−W1 0.43 is about 0.2 mag above a reddened photosphere, so a mild W1 excess is possible.
- IPHAS (pre-event, 2003-12): r−Hα 0.56 against 0.70 ± 0.15 for 10 field stars at the same r−i, so no Hα emission. That weakens
  the Be alternative, though Be discs come and go.
- P 0.40.

## 4. NEOWISE exposure-level checks (H-0009 pitfalls) (r4, r5)

| | event visit | frames | clean-only ratio | merged / unextracted neighbour | centroid | verdict |
|---|---|---|---|---|---|---|
| J174618 | 2015-03-19 | 11 | W1 ×7.2 (7 clean) against the survey baseline | **yes**: the 6.3″ K = 11.66 neighbour is extracted in quiet frames and merged in the event | on the Gaia star (0.19″) | event real; survey baseline invalid (§3.1) |
| J173332 | 2014-09-15 | 10 | ×2.37 | no | +0.10″ (predicted +0.06″) | clean |
| J072830 | 2015-04-10 | 13 | ×1.34 | no | no shift (isolated) | clean |
| J200958 | 2015-10-31 | 14 | ×1.28 | no | moves to the star as predicted | clean |
| J182124 | 2015-09-19 | 13 (against 43% of quiet frames within 3″) | no clean frames (all nb = 2) | AllWISE source 2.9″ off | shift (+0.33, −0.13)″, predicted (+0.34, −0.06)″ | the ×1.14 is on the Gaia star |
| J175414 | 2016-09-06 (−52 d) | 5 | ×1.04 | – | – | flat, uninformative (tE ≈ 16 d) |

## 5. Alternatives (r6)

| class | how it would look | excluded for | not excluded for |
|---|---|---|---|
| Be-star outburst | fast rise, slow decline; redder when brighter in IR (IR amplitude > optical); Hα emission; NIR excess | J174618 (APOGEE giant), J072830 (K-type XP, no Hα, no excess, IR = optical), J173332 (achromatic to 2%, no excess) | J200958 (hot, reddened, mild W1 excess possible, no XP); most G > 19 candidates (no data) |
| YSO burst (EXor/FUor/UXor) | colour change (bluer, or redder for UXor dips), IR excess, star-forming field | J174618, J173332, J072830 | J144905, J184922, J190032 (faint, no IR, no colour) |
| CV / dwarf nova | fast rise (days), bluer, ×10-100, 1-3 weeks (superoutburst ≲ 3 weeks) | all with a ≥ 2-month achromatic event | **J180313 and J172020 (bluer when brighter, 4-5σ); J184922 (Hα emitter)** |
| Classical nova | ×10⁴, fast rise, years of decline | all (amplitudes ×1.4-14; quiescent sources detected) | – |
| Flare | minutes to hours, very blue | all (multi-week, several dates) | – |
| R CrB | fades | all | – |
| LPV / Mira / SR | periodic, chromatic, red | all with a flat 2014-17 baseline; J174656 has a VVV VIVACE "LPV" label but Gaia baseline scatter is 0.009 mag | – |

- **H-alpha photometry** (VPHAS+/IPHAS, r6; field stars within 60″ at the same r−i as the reference):
  - J072830: VPHAS+ r−Hα 0.60 against 0.58 ± 0.09 (17 stars). No emission.
  - J200958: IPHAS r−Hα 0.56 against 0.70 ± 0.15 (10 stars). No emission.
  - J174618: no VPHAS+ source within 1.5″. J173332 and J144905: no VPHAS+/IPHAS coverage returned.
  - **J184922: emission.** IPHAS r−Hα 1.13 against 0.65 ± 0.10 (+0.48, 4.6σ). VPHAS+ 0.92 against 0.62 ± 0.14 (+0.30, 2.1σ).
    Its brightening is most likely intrinsic (YSO, Be star or CV).
  - J175414: VPHAS+ 0.89 against 0.90 ± 0.13 (no emission).
  - The remaining 14 have no VPHAS+/IPHAS source within 1.5″ or no coverage returned (`data/halpha.csv`).
- 2MASS/AllWISE colours for the other 16 could not be retrieved: IRSA reset the connections. The investigators' J, K, W1-W4 columns
  stand unverified for those.

## 6. Novelty: has anyone published this list? (r7, r7a, r7b; literature search)

**The list: yes, its existence and size.**
- Rimoldini et al. 2023 (A&A 674, A14; arXiv:2211.17238), §4.13: "Among the microlensing candidates, 187 are in common with the
  SOS module and 67 are unique to classification."
- Their Appendix D gives the ADQL to extract them (a LEFT JOIN of the classifier table against `vari_microlensing`). It returns 67.
- Eyer et al. 2023 (arXiv:2206.06416), Table 2, lists "MICROLENSING 254 (67)".
- So "67 classifier-only sources" is Rimoldini's number. H-0010 must cite it, and must not present the list as something it found.

**Vetting: no.**
- I found no paper, catalogue, VizieR table or thesis that goes through the 67 one by one.
- Checked: Wyrzykowski 2023 (which says nothing about the classifier), Kruszyńska et al. 2024 (arXiv:2401.13759), Howil et al. 2025
  (arXiv:2403.09006), Pylypenko et al. 2025 (arXiv:2504.11546), Eyer et al. 2024 (arXiv:2412.02744).
- The search was title/abstract level: the arXiv API plus Semantic Scholar and OpenAlex citation lists of Rimoldini and Wyrzykowski.
  ADS full text was not searched (no token).

**Per object, for all 21.**

| check | result |
|---|---|
| OGLE EWS `lenses.par` 2014-17 (7955 events) | none within 3″ |
| Mróz+2019 bulge (J/ApJS/244/29) | none |
| **Mróz+2020 GVS disc, main table and Table B2 "possible events"** | **J182124 = BLG783.17.33659 (0.14″, Table B2)**. The investigators' local GVS copy has only the 460-event main table |
| KMTNet 2015 public page (857 events, RA 267.5-272.3°, Dec −32 to −27°) | none within 15′ of any candidate. J174618 lies outside the 2015 fields (the README said 2015 was unchecked) |
| KMTNet 2016-24 (local) | none within 3″ |
| MOA alert index 2014-17 | HTTP 200 but **empty tables**: MOA's public alerts are not served. Unchecked; the agent also checked the MOA catalogues of Sumi 2013/2016, none |
| Gaia alerts live CSV (27 076) | none within 60″ |
| TNS (60″, 50 s pacing, header-validated, no 429) | none for all 21 |
| ASAS-SN transients page (1226 positions) | none within 60″ |
| ASAS-SN variables (II/366) | none |
| VSX (B/vsx, idia mirror; CDS unreachable) | only neighbours 8-9″ away (Gaia LPVs) for J175414 and J174029 |
| SIMBAD (CfA, 10″) | J174618 = a bare 2MASS entry (APOGEE target); J175414, J174029: LPV? neighbours at 8″ |
| VVV: Navarro+2020 microlensing; VIVACE variables | VIVACE labels J174656 LPV; no microlensing match. Agent: Navarro 2020 (two tables), Husseiniova 2021, UKIRT (Wen 2023), OGLE-III, MACHO: none |
| Whole-VizieR cone | **not run** (CDS down; the idia mirror does not support it) |

**J182124 is not unreported.**
- Mróz et al. 2020 list it among 170 "possible microlensing events" (light curves noisy or poorly sampled, or with tE poorly
  measured).
- OGLE's public I-band light curve (r7b) shows one brightening: ×1.13 on 2015 Jun 1 rising to ×1.76 on Aug 1, then a gap, then
  ×1.54 on Aug 25 → ×1.15 on Oct 29.
- On 2015 Sep 22, Gaia measured ×1.42 and OGLE ×1.42 the next night.
- **Safe wording:** "independent Gaia and NEOWISE confirmation of OGLE-IV possible event BLG783.17.33659".

## 7. The population claim "about 11 of 21 expected real" (r3, r3d)

**It is not justified as stated.**

1. **The sum is a sum of judgements.** The README says so itself, and the judgements were made with three flawed inputs:
   - fits with fs at the 1.5/0.02 bounds;
   - failed shape fits;
   - "achromatic" or "untested" labels that do not survive (§1).
2. **The anchor does not transfer.**
   - "18 of 19 single events are catalogued lenses where OGLE/KMT were looking" measures the classifier's precision in the
     high-event-rate bulge fields.
   - The 21 lie mostly where the lens rate per star is lower and the impostor mix differs. All 7 not-lenses among the 67 are
     outside the bulge survey footprints, and so are most of the 8 inconclusive.
   - Among the 36 non-catalogued, non-case sources, at least 7 are definite non-lenses. My checks add two chromatic events
     (J172020, J180313) and one Hα emitter (J184922), so the impostor rate outside survey coverage is ≥ 28%, not ~5%.
   - Rimoldini et al. 2023 give only a contamination lower limit for the class (> 7.2%).
   - I did not re-verify the 18/19 number.
3. **The light curves cannot carry it.** With a working shape fit and fs ≤ 1, only 2 of the 21 prefer a lens over a generic bump
   by ΔBIC > 10 without being chromatic (J173332, J072830). 16 are within ±10. For those, P reflects the classifier label and the
   prior.

**My numbers.**
- Revised P: ΣP = 8.1 over the 21; 7.5 over the 20 that are unpublished.
- I would quote "several (roughly 5-10) of the 20 are expected to be lenses; three (J174618, J173332, J072830) are strong."

## 8. The 28 catalogued lenses and Sample B (r8)

**What Wyrzykowski et al. 2023 actually did** (arXiv:2206.06121, §4.2, read from the paper).

- Inputs to Sample B:
  - OGLE-IV events "published separately for the bulge region (Mróz et al. 2019) and the southern Galactic disc (Mróz et al.
    2020b)": 1527 with tE > 20 d and a maximum in JD 2456863.9375-2457901.86389;
  - 2 ASAS-SN events;
  - 7 Gaia alerts, **including Gaia16aye**.
- Procedure: 1074 DR3 matches within 0.5″ → 404 recovered by Extractor/MSOS → 233 after visual inspection ("at least two points
  within the brightening").
- Sample A (Table C.1 cuts plus inspection) ran independently.

**Membership of the 28** (VizieR, all tables, 3″):

| group | n |
|---|---|
| in Mróz 2019 | **3** |
| – of which tE ≤ 20 d (OGLE-2016-BLG-1902, 13.5 d; OGLE-2016-BLG-0235, 18.2 d) | 2 |
| – of which pass the Sample B entry cuts (OGLE-2015-BLG-2080, tE 69 d) | 1 |
| in Mróz 2020b | 0 |
| Gaia16aye (a Sample B input; lost later, plausibly as a binary lens) | 1 |
| EWS or KMT events absent from Mróz 2019/2020b, so never in Sample B's input | **24** |

- The investigators' own `data/mroz2019.csv` shows the same 3 matches. The "21 lost at pipeline recovery or visual inspection"
  should read: "**1** (OGLE-2015-BLG-2080) entered Sample B and was lost at recovery or inspection; Gaia16aye entered and was lost
  (binary); 24 were never Sample B inputs because they are not in Mróz et al. 2019/2020b."
- These 24 could only have entered through Sample A. Its cuts (G0 < 19, 20 < tE < 300 d, |u0| < 1, 1 < BP−RP < 4, duration > 135 d,
  Extractor > 3 points, parallax χ²/dof < 1.9, …) were not evaluated per event; they need the unpublished Level-2 and Extractor
  parameters.
- One ambiguity in the paper: it calls the OGLE input "the most numerous OGLE-IV sample (6251 events)", a number I could not
  reconcile with either catalogue's size.

## 9. Corrections the investigators must make

1. **J174618.**
   - Delete "the Gaia-only lens fit predicts ×7.1"; it needs fs_G = 1.5.
   - Report NEOWISE as W1 ×7.6-11.4 and W2 ≈ ×9.5 against AllWISE/2MASS star-only baselines. The survey baseline is a 6.3″ neighbour
     blend.
   - Add APOGEE: a K giant, [M/H] +0.47.
   - Say that a symmetric bump fits the four Gaia points as well as a lens. P 0.75.
2. **J173332.** Replace "before 2014-09-07; fit t0 2014-07-11; tE unconstrained" with "parallax lens t0 2014 Aug 4, tE ≈ 140 d,
   fs ≈ 1; NEOWISE 2014 Mar 17 at baseline excludes the static solution."
3. **J072830.** Replace tE "188-456 d" with "47 d (parallax, fs ≈ 1) to 240 d (static, fs 0.07): not determined". Add the
   Be-star evidence of §3.3. Drop "ΔBIC 330".
4. **J144905.** Drop "parallax model preferred". With fs ≤ 1 lens and FRED are equal. Colour is testable at peak and consistent. P 0.45.
5. **J200958.** Drop "a lens beats every non-lens shape by ΔBIC 78" (failed fit). Add the IPHAS no-emission result. P 0.40.
6. **J182124.** Move it out of "new": Mróz et al. 2020 Table B2, BLG783.17.33659, with OGLE's 2015 light curve.
7. **J180313** (kill) **and J172020** (inconclusive). Bluer when brighter at 4-5σ.
8. **Downgrades.** J184922 to 0.15 (Hα emitter in IPHAS and VPHAS+). J171847, J174036, J174029, J171234, J182656, J190032, J182811 and J184837 drop to inconclusive (§1).
9. **Headline.**
   - "21 apparently unreported candidates, ~11 real" becomes "9 apparently unreported candidates at P ≥ 0.4 (3 strong: J174618,
     J173332, J072830), 1 previously listed OGLE possible event, 10 inconclusive, 1 not a lens; expected real among the 20
     unpublished ~5-10".
   - Cite Rimoldini et al. 2023 §4.13/App. D for the 67 and Eyer et al. 2023 Table 2.
10. **Sample B paragraph.** Rewrite as in §8.
11. **Code.**
    - Bound fs ≤ 1 (or derive it from neighbour shares) in `lensing.Problem` fits used for claims.
    - Fix `shape_fit`: start from the G-band peak, and check convergence against the lens χ².
    - Remove the G-conditioned BP/RP clip; drop only gross (> 3 mag) spikes or Gaia-flagged points.
    - Use the NEOWISE association with every detection of the source (H-0009 rule J).
12. **README "not checked against" list.**
    - KMTNet 2015 is now checked: no events near any candidate.
    - MOA is still unchecked (the public index is empty).
    - ADS full text is still unchecked.

## 10. What remains unchecked

- **MOA** alerts 2014-17 (the index serves empty tables). Only the published MOA catalogues were checked.
- **ADS full-text** search for the 20 positions and source ids. Title/abstract searches and the citations of Rimoldini and
  Wyrzykowski were screened.
- **Whole-VizieR cone** around each candidate (CDS unreachable all day).
- **OGLE-IV photometry** at J174618 in 2015, a low-cadence field with 2 EWS events within 15′. KMTNet 2015 did not cover it.
- **VVV/VIRAC2 Ks light curves** for the bulge and disc candidates. They would test J174656's "LPV" label and add a second
  instrument for many of the faint ones.
- **2MASS/AllWISE colours** for the 16 beyond the five best (IRSA connection resets). 14 of the 21 have no usable VPHAS+/IPHAS photometry.
- **The "18 of 19" calibration** and the investigators' tE calibration (s13) were not re-derived.
- **Sample A cuts** for the 24 known lenses outside Sample B's input (needs unpublished Gaia Level-2 parameters).
- **Spectra.** Only J174618 has one (APOGEE). A current Hα spectrum of J200958 (and of J072830) is the decisive Be test.
- **ATLAS and ASAS-SN light curves** of the candidates were not examined.
- **Gaia DR4** (Dec 2026) will add the missing side of J173332 and test all of them.

## Files

| script | what it does |
|---|---|
| `r1_gaia_epoch` | Gaia DR3 epoch photometry via `fetch_report` and the raw datalink; compared with the investigators' files |
| `r1b_other_flags` | g_other_flags in candidates against catalogued lenses |
| `r2_neighbours_gost` | Gaia TAP neighbours within 6″ with blend diagnostics (C*, blended transits, RUWE, IPD); GOST scan geometry |
| `fitlib.py`, `r3_fits` (`--all`), `r3c_chi2_budget`, `r3d_parallax_rest`, `r3e_clip_audit` | lens (fs ≤ 1, parallax, fs ≤ 1.5) and shape fits; colour test without clipping; NEOWISE joint fits; χ² budget; audit of the investigators' clip |
| `r3b_scan_angle` | scan-angle and FoV-pair test for all 21 |
| `r4_neowise_fetch`, `nwlib.py`, `r5_neowise_frames`, `r5b_irsa_catalogs`, `r5c_j174618_w1` | NEOWISE exposures within 8″ (25″ for J174618); per-visit near-star and blend-total ratios, clean frames, merged frames, centroid test; AllWISE/2MASS neighbours; J174618 W1 baselines |
| `r6_alternatives` | Gaia AP (GSP-Phot, ESP-HS, ESP-ELS Hα), IR colours, VPHAS+/IPHAS Hα |
| `r7_novelty`, `r7a_tns`, `r7b_j182124_ogle` | OGLE EWS, KMTNet 2015/2016-24, MOA, Gaia alerts, Mróz 2019/2020, VSX, ASAS-SN, VVV, SIMBAD; TNS; OGLE light curve of BLG783.17.33659 |
| `r8_sampleB` | Mróz 2019/2020 membership of the 28 catalogued lenses |
