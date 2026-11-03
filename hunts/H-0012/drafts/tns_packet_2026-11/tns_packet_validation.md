# TNS filing packet 2026-11: H-0012 infrared-only outbursts, validation (2026-11-02/03)

**Nothing was filed, submitted or posted** to TNS (production or sandbox), to ATel, or anywhere else. No case was
edited or sealed. The packet holds validated drafts only.

**Files.**
- Draft reports: `tns_report_OS-0035.md`, `tns_report_NGC4945-obs3.md`.
- Form fill files: `fill_OS-0035.json`, `fill_NGC4945-obs3.json`.
- Figures: `M81_OS-0035_summary.png`, `NGC4945_obs3_summary.png`.
- Numbers: `numbers.json`. Scripts: `scripts/`.
- Raw query outputs are outside the repo, in `~/oddsky-runs/imaging/scratch/tns-packet-2026-11/` (`tns/`, `lc/`,
  `timing/`, `numbers_m81/`, `astrometry/`, `archives/`, `spitzer/`, `atlas_summary.json`).

**Precedent.** OS-0030 = AT 2020afkm (`../tns_OS-0030_validation.md`, `../tns_report_OS-0030.md`). Its conventions
are copied unchanged:
- discovery and last-non-detection times are the mean of the NEOWISE exposures at the source;
- AB = −2.5 log10(f/3631 Jy) from the unWISE Vega zero points;
- instrument "Other - Other" [0], with "Instrument=WISE (NEOWISE-R)" in the comments;
- filters 3.4-WISE [45] / 4.6-WISE [46]; ABMag [1];
- reporting group and data source None [0]; AT type "Other - Undefined" [0];
- reporter "Alan Shortz (Oddsky)";
- the Meisner credit line in the remarks; the remarks never call the work AI-run.

## Verdict

**Ready to file (2)** (NGC 4945 revised 2026-11-03: Spitzer discovery):
1. **M81 = OS-0035, the 2023-24 eruption.** First detected 2023-10-23; the 2009-10 Spitzer event goes in the
   remarks.
2. **NGC 4945 obscured #3**, a slow single outburst. **Discovery = Spitzer/IRAC [3.6] on 2018-06-02** (revised
   2026-11-03 on the coordinator's decision; expect AT 2018xxx). First WISE ≥ 5σ 2019-01-27, peak 2022-07, fading
   by 2024.

**Not ready (14):** NGC 55 #13, IC 342 #23, Holmberg II #17, M101 #20, NGC 1744 #29, UGCA 127 #27, NGC 300 #31,
NGC 4214 #32, NGC 253 #33, NGC 4656 #34, NGC 4656 #35, KKR 59 #36, NGC 925 #37, ESO 274-001 #39. None of them is a
clean, verified outburst; the reasons are in the table and in §3.

**Out of scope (repeating sources), not screened further:** OS-0031 (NGC 2403, P ≈ 5.3 yr), OS-0033 (NGC 4945, P ≈
5.4 yr), OS-0034 (NGC 3344, P ≈ 10 yr), §4.

## Validation table

Ranks are the h0012b obscured-transient ranking (`work/triage_h0012b.csv`, `rank_obs`). Times are UT. Magnitudes are
AB of the difference flux. "Prior reports" = TNS 60" cone with `unreal=all` and no date limit (2026-11-03), plus the
other public records named in §1-2. **"In De list?" is left blank on purpose**: fill it when K. De's group (Columbia)
sends its WISE-outburst list. Novelty is claimed only against public records.

| candidate | ready? | why | discovery date (UT) | mags (AB) | position (J2000) | prior reports | in De list? |
|---|---|---|---|---|---|---|---|
| **M81 = OS-0035** (rank 8) | **READY** | Flat in 18 epochs, 2014.8-2023.2. Eruption in both bands and both visit seasons, PSF-like, 351" from the nucleus. Both referees: real. Earlier Spitzer event 2009.9 (two eruptions, no period established). | **2023-10-23 05:41:33** (MJD 60240.237); last non-det. 2023-03-27 18:12:04 | disc. W1 18.18 ± 0.07, W2 18.05 ± 0.12; 2024-03-28 W1 16.71, W2 16.36 (still rising); last non-det. W1 > 19.57, W2 > 18.78 (5σ) | 09:54:57.378 +69:08:48.75 ± 0.5" (Gaia-tied WISE) | none. TNS: AT 2026dvq at 22.6" (ATLAS, 2026, unrelated). No ATel, ADS, SIMBAD-transient, VSX or Gaia-alert entry; no ZTF alert object within 35". | |
| **NGC 4945 obscured #3** (rank 3) | **READY** | Flat in 11 epochs, 2010-2017.5. Single slow outburst in both bands and both seasons, PSF-like and stationary. Confirmed independently by Spitzer/IRAC (SPIRITS), which agrees with WISE to 5% in 2019-07 and detects the rise first. Referee: real, unreported obscured outburst. | **2018-06-02 05:10:43** (MJD 58271.2158; IRAC [3.6], SPIRITS 13053); last non-det. 2017-10-03 09:08:01 (IRAC) | disc. [3.6] 20.09 ± 0.10 (10.7σ); last non-det. [3.6] > 20.55, [4.5] > 20.50 (5σ). WISE: first ≥ 5σ 2019-01-27 W1 18.97 ± 0.10, W2 18.80 ± 0.22; peak 2022-07-07 W1 16.52, W2 16.71; 2024-07-06 W1 18.20 | 13:05:52.700 −49:24:58.23 ± 0.3" (Spitzer centroid; WISE 0.79" away) | none. TNS: nothing within 60". No ATel, ADS, SIMBAD, VSX or Gaia-alert entry. | |
| NGC 55 obscured #13 (3.75579 −39.2033) | not ready | Secular brightening since 2010 (W1 ≈ +0.8 mJy over 14 yr, accelerating in 2023-24) of a source already present in Spitzer 2004-09. No discrete outburst; an obscured background AGN is not excluded (referee). TNS excludes long-term variables. | (first ≥ 5σ vs 2010: 2014.4) | — | 3.75579 −39.2033 | TNS none within 60" | |
| IC 342 obscured #23 (56.5658 +68.1491) | not ready | Steady rise 2014-2021, then a plateau, of a luminous star (Gaia G = 20.1). ZTF optical brightening 2020 (alerts ZTF20abxovha). An LRN-precursor-like variable, not a transient yet (referee). Monitor. | (2014.2 vs 2010) | — | 56.5658 +68.1491 | TNS none; ZTF alert object exists (not a TNS report) | |
| Holmberg II #17 (124.80276 +70.71872) | not ready | Brightening since 2016 by +0.9 / +1.1 mJy (W1/W2), a jump at 2019.8, then a variable high state still rising in 2024. On a bright compact HII knot (reference W1 1.8, W2 4.4 mJy; Gaia blue knot 0.04"). No outburst-and-decline; nature undetermined; never refereed beyond triage. **The best of the second tier**: worth a case, Spitzer and HST. | (2018.2 vs ≤ 2016) | — | 124.80276 +70.71872 | TNS none | |
| M101 #20 (210.854 +54.5073) | not ready | No ≥ 5σ epoch against a 2014-2018 reference. The "brightening" is a 2010-vs-NEOWISE offset of ~80 µJy. NVSS J140324+543023 (SIMBAD radio galaxy) at 0.5": background AGN. | — | — | 210.854 +54.5073 | TNS none | |
| NGC 1744 #29 (74.9977 −26.0432) | not ready | W1-only marginal rise (+50-66 µJy; first ≥ 5σ only in 2023.7). The h0012a referee (same source, #32) found a dipole: a moving foreground star. | (2023.7, W1 only) | — | 74.9977 −26.0432 | TNS none | |
| UGCA 127 #27 (95.2591 −8.4826) | not ready | W2-only hump 2016.7-2019.2 (+200 µJy; W1 ≤ +40). No difference stamps on disk (var_sig < 5) and the tile is not cached, so PSF shape cannot be checked without a NERSC fetch. b = −10.6°: a foreground dusty star is not excluded. Referee: low priority. | (2016.75, W2 only) | — | 95.2591 −8.4826 | TNS none | |
| NGC 300 #31 (13.57636 −37.58393) | not ready | IR brightening (W1 ×2 since 2019, a jump in 2023) of a catalogued red supergiant (SIMBAD s*r and Gaia G = 18.3, 0.43"). A variable star, out of TNS scope unless it erupts. Monitor. | (2020.5) | — | 13.57636 −37.58393 | TNS none | |
| NGC 4214 #32 (183.92217 +36.30241) | not ready | Up 2014-16, down 2018-21, up 2022-24. H-0013 lists it as a recurrent candidate (P ≈ 11 yr). A variable, not a single outburst. | (2022.4) | — | 183.92217 +36.30241 | TNS none | |
| NGC 253 #33 (11.9774 −25.2047) | not ready | Slow rise 2010-2021, then a plateau. Not an outburst. | (2014.0 vs 2010) | — | 11.9774 −25.2047 | TNS: AT 2022llt (Gaia22cbg) at 16.5", a different source | |
| NGC 4656 #34 (190.896 +32.1797) | not ready | A broad 10-yr hump (+0.4 mJy) on a bright source (reference W1 1.5 mJy). A long-term variable. | (2014.0 vs 2010) | — | 190.896 +32.1797 | TNS none | |
| NGC 4656 #35 (190.92204 +32.08198) | not ready | A rise-and-fall in 2019-2023 (peak 2021.4: W1 +129 ± 11, W2 +330 ± 27 µJy), both bands and both seasons. But 2010 is also elevated against 2014-18 (W1 +78, W2 +160 at 2010.96): a possible earlier episode (H-0013 "edge-cycle" P ≈ 12 yr). The X-ray source [RW2000] NGC 4656 X-1 is 1.4" away. Modest S/N, noisy W2 stamps, not refereed. **The nearest miss**: a referee pass and Spitzer 2004-19 would settle it. | (2019.4 W2 / 2020.0 W1) | — | 190.92204 +32.08198 | TNS none | |
| KKR 59 #36 (315.85568 +57.29008) | not ready | Empty-sky reference (reference flux −100 / −135 µJy, the referee's veto class). Slow +55 / +95 µJy rise since 2019. b = +7°: foreground. | (2022.5 W2) | — | 315.85568 +57.29008 | TNS none | |
| NGC 925 #37 (36.75536 +33.57473) | not ready | Late rise in the last three epochs; W2 8σ only in the final 2024.0 visit. Pre-existing HII/PAH source; referee undecided. Needs post-2024 IR (SPHEREx). | (2024.0) | — | 36.75536 +33.57473 | TNS none (AT 2023nzt is 78" away) | |
| ESO 274-001 #39 (228.52859 −46.82968) | not ready | W2-dominated and irregular: rise 2020.6, decline 2022, rise again 2024.1. b = +9.3°. Not a single outburst. | (2020.6 W2) | — | 228.52859 −46.82968 | TNS none | |

Not-ready "dates" are only the first ≥ 5σ epoch of the light-curve screen (`scripts/lc_screen.py`, quick-look
figures in `…/lc/quicklook_<rank>.png`), not discovery claims.

## Method and data limits (all candidates)

- **Data on disk.** Only M81's unWISE tile (1507p696, 23 epochs × 2 bands) is fully cached. For every other
  candidate, the h0012b run left only per-candidate products in `~/oddsky-runs/h0012b/<tile>/<galaxy>/`:
  - forced-photometry light curves;
  - 41 × 41-px reference and per-epoch difference cutouts, for var_sig > 5 only.
  NGC 4945's tile 1974m500 has one cached epoch (13, W1), which was used for the astrometric tie. **Nothing was
  downloaded from NERSC.** UGCA 127 #27 has no cutouts, and would need a tile fetch to check its stamps (§3).
- **Photometry (`lc_screen.py`).**
  - The pipeline's fluxes are differences against a full-run median that contains the event. They are
    re-referenced to the median of the pre-event epochs of the same visit season, leaving the epoch itself out
    (leave-one-out, as in OS-0030's `recompute_numbers.py`). Forced photometry is linear, so this equals
    differencing against a pre-event reference.
  - Errors are the larger of the propagated pipeline error and an empirical one: a Gaussian-PSF fit at 24 offset
    positions in the same re-referenced cutout, scaled to the pipeline flux scale.
- **Full-stack cross-check for M81 (`recompute_m81.py`).** This is `recompute_numbers.py` re-pointed at tile
  1507p696. Compared with the pipeline-product numbers:
  - 2023-10: W1 194.0 against 201.1 µJy, W2 218.1 against 200.6 µJy;
  - 2024-03: W1 753 against 739, W2 1036 against 1003;
  - so they agree to 4-9%.
  For M81 the full-stack flux is quoted, with the larger of its error and the empirical cutout error.
- **Timing (`timing_at_source.py`).** IRSA NEOWISE-R L1b frame index at each position (688 frames for NGC 4945, 824
  for M81). The mean is over qual_frame > 0 exposures in the epoch's visit. For M81 the visit was matched by header
  MJDMIN/MAX and n-m was read at the source; for NGC 4945 frames were matched within ±6 d of the tile midpoint, and
  n-m is known only for epoch 13 (W1: 25). The tile midpoints differ from the source means by 0.38 d (M81 discovery)
  and 0.85 d (NGC 4945 discovery).
- **Astrometry (`astrometry.py`).** The transient centroid is a Gaussian fit to the S/N-weighted sum of the
  event-epoch difference cutouts (W1+W2). The tile zero point is tied to Gaia DR3: 60 isolated G = 13-17.5 stars
  per tile, measured with the same fit on a cached W1 image. The WISE−Gaia offsets were +0.28"/−0.27" (M81) and
  −0.27"/+0.42" (NGC 4945), and were removed.
  - Formal errors are 0.23-0.32".
  - 0.5" is quoted, the WISE floor the referee measured on DS1. For NGC 4945, Spitzer shows the WISE centroid is
    off by 0.79", so 0.5" is if anything optimistic for WISE.
- **TNS (`tns_search_packet.py`).**
  - 22 requests: 16 cones at 60" with `unreal=all` and no date limit, plus 6 host-name searches, 61-65 s apart.
  - All returned HTTP 200 with CSV bodies, and none returned a 429 or HTML (`…/tns/tns_search_log.json`,
    2026-11-03 03:04-03:26 UTC).
  - The host searches return SN 2005af, SN 2011ja and SN 1993J, so they are not date-limited.
  - Proprietary reports by others cannot be seen. If one existed, TNS would attach our report to it.

## 1. M81 = OS-0035 (148.739074 +69.146874)

### M81.1 Real and astrophysical

- **Referee verdicts.**
  - Triage referee 2026-11-01 (§2.3): "Real, unreported, obscured outburst in a compact HII region … real in both
    bands (per-epoch cutouts), and in the final short 2024 visit."
  - H-0013 referee: "Real; recurrent eruptions; nature undecided."
- **My checks.**
  - **Both bands and both visit seasons**: 2023-10 (season 1) W1 15σ, W2 9σ; 2024-03 (season 0) 68σ/69σ.
  - **Flat baseline**: 18 epochs 2014.8-2023.2, rms 13 (W1) and 28 µJy (W2), with no epoch beyond 2.8σ (W1) or
    3.7σ (W2, negative).
  - **PSF-like** point source in every event difference stamp (figure).
  - **Stationary**: per-epoch centroids in 2023-10 and 2024-03 agree within 1.3" (2023-10 W2 is only 8.6σ). The
    2010 excess centroids within ~0.6" of the 2024 one.
  - **Not a moving object**: positive in consecutive visits from opposite sides of the Sun.
  - **Not a core residual or saturation artefact**: 351" NW of the nucleus, mask code 0, `low_confidence` False.
  - **No brighter neighbour residual**: the nearest SIMBAD neighbours are HII regions at 2.9" and 4.5" and an HXB
    at 6.2". The difference image shows a single PSF.
  - **Not an AGN**: the counterpart is a resolved HII region/cluster (Gaia DSC P(galaxy) = 1, referee), and an
    eruption from a nine-year flat baseline is not AGN-like.
  - **Not a known variable**: VSX has nothing within 30", and SIMBAD has no variable within 15".

### M81.2 Is it a TNS transient?

- **Yes, it is an eruption.** The source was flat for nine years. Within 6.5 months of the last non-detection it
  rose to 15σ, and 5 months later it was at 0.75 / 1.04 mJy (W1/W2), still rising when NEOWISE ended. At
  3.4-4.0 Mpc that is νLν ~ 3×10⁵ L☉ per band.
- **Caveat: it is recurrent.** Spitzer saw an earlier event (+0.22 mJy at 3.6 µm on 2009-11-25) after a flat
  2003-2005.
  - Two eruptions do not make a period. OS-0035's H2 ("~16-yr dust-forming binary", confidence 0.25) is the class
    that makes OS-0031/33/34 out of scope.
  - It is filed as a transient on the strength of the 2023-24 eruption itself, as recurrent LBV-type eruptions and
    SN impostors are on TNS.
  - If later data show strict periodicity, TNS can carry that as a comment.
  - **Alan should accept this framing explicitly**; the remarks state the earlier event plainly.

### M81.3 Not already reported

- **TNS**: 60" cone `unreal=all`: AT 2026dvq only (09:55:01.48 +69:08:42.56, 22.6", ATLAS26cer, 2026-02-20).
  Host searches "M81" and "NGC3031" return 32 objects, none within 60" other than AT 2026dvq. "NGC 3031" and "M 81"
  return 0 rows (TNS stores "NGC3031, M81").
- **ATel/ADS** (`archives_packet.py`, `ads_abstracts.py`; token read from file, never printed):
  - Position strings in astronomy full text: 3 hits, all unrelated (WALLABY, YSO flares, GW background).
  - ATel with M81 in the full text: 144 hits, almost all novae. Those that could matter were read and none is at this
    position: P60-M81-081203 (2008) at 09:55:16.9 +69:02:17; P60-M81OT-071213 (2007) at 09:55:25.98 +69:04:34.8;
    AT 2017dfw; AT 2018akh.
  - TNS bibstems: 1 (an ISSP 2017 report; its object is not within 60").
  - IR/transient terms 2019+: 191 hits, keyword-screened, none on this source. The October 2026 "Dancing Bonfire"
    X-ray paper (M81F4) is at 09:55:24.2 +69:09:57, a different position.
  - H-0013 / OS-0035 C4 had already checked ADS full text for the coordinates.
- **SIMBAD** (CfA TAP, 15"): [HAE2008] 7 (reg, 0.56"), [PR95] 50996 HII (2.9"), HK NGC 3031 652 HII (4.5"),
  [LET2019] NGC 3031 27 HXB (6.2"), [BKC98] C3 (9.6"), PSK 110 HII (14.5"). None is a transient or variable.
- **VSX** (idia): 0 within 30".
- **Gaia alerts** (alerts.csv, 27,076, to 2025-01): nearest 336".
- **ASAS-SN transients**: 0 within 60".
- **ALeRCE/ZTF**: nearest ZTF20acsuakt at 35.8" (2 detections).
- **SPIRITS catalogues** (referee; Jencson 2019, Karambelkar 2019): nothing within 10".
- **Not checked**: Fink (timed out for OS-0030; not retried), Lasair (needs a token). Both work from the same ZTF
  alert stream as ALeRCE.

### M81.4 Numbers

All in `numbers.json`; see the draft report.

**Discovery.** Epoch 21, mean 2023-10-23 05:41:33. 19 frames from 2023-10-22 16:22 to 10-23 21:51; n-m at the
source 17/16.
- W1 194.0 ± 12.6 µJy = 18.18 ± 0.07 AB (Vega 15.51).
- W2 218.1 ± 23.4 µJy = 18.05 ± 0.12 AB (Vega 14.74).

**Last non-detection.** Epoch 20, 2023-03-27 18:12:04 (22 frames).
- W1 +18.9 ± 10.8 µJy; 5σ > 19.57 AB.
- W2 +5.6 ± 22.3; 5σ > 18.78 AB.

**Later.** 2024-03-28 13:22:28: W1 16.71 ± 0.02, W2 16.36 ± 0.02 AB. There are no later WISE data (NEOWISE ended
2024-08-08).

**Earlier event.**
- WISE 2010-04: W1 +129 ± 10, W2 +285 ± 24 µJy over the 2014-2023 level.
- WISE 2010-10: W1 +77 ± 17, W2 +168 ± 17.
- Spitzer (H-0013): flat 2003.8-2005.0, then +0.22 mJy on 2009-11-25, falling to +0.13 by 2010-04/06.

**Optical.**
- ATLAS (referee job 5280889; `atlas_summary.py`): ±30 d around 2023-03-27, 2023-10-23 and 2024-03-28 gives 3σ
  c > 21.3 and o > 21.2 / 21.9 AB.
- At 2023-10 the o-band mean is −19 ± 4 µJy, a negative offset of the ATLAS difference flux on this HII region, so it
  is a systematic, not a measurement of the transient.
- The ZTF DR light curve of the knot is flat 2018-2025 (referee).

### M81.5 Position

Gaia-tied WISE centroid: 148.739074 +69.146874 = 09:54:57.378 +69:08:48.75, ±0.5" (formal 0.24"/0.32").
- Gaia DR3 1070474934439610752 (G 20.25, BP−RP 0.37, RUWE 1.89) at 0.28".
- AllWISE J095457.30+690848.1 (the HII region blend; W1 13.39, W2 13.03 Vega) at 0.75".
- H-0013's Spitzer bright-minus-faint centroid of the 2009 event is 0.26" from the triage WISE position, so it is
  consistent with the same source.
- No better position exists: HST has no data after 2010, and JWST none.

### M81.6 Host and distance

- NED: NGC 3031, preferred z = −0.00013 ± 0.00001 (2012ApJ...752...52S). NED's preferred-name field returns "SN 1993J
  HOST"; the position is M81's centre.
- NED redshift-independent distances: 99 values, 1.4-5.0 Mpc, median 3.63.
  - Cepheids: 33 values, median 3.63 (3.24-4.79).
  - TRGB: 14 values, median 3.62 (3.44-4.05).
  - Working range 3.4-4.0 Mpc.
- TNS has no distance field. The host redshift is left blank because it is negative (decision in the report).

### M81.7 HST/JWST/Spitzer counterpart or progenitor

**MAST (30").**
- HST WFPC/WFPC2 1991-1997.
- ACS/WFC F814W 2004-09-14 (10250, Huchra).
- F435W/F606W 2006-03-22 (10584, Zezas).
- F555W 2010-04-12 and 2010-06-15 (11731, Kochanek).
- No HST after 2010; no JWST.
- The 2010 ACS images were taken during the decline of the 2009.9 event. They are worth a look in the case
  follow-up (not done here). The remarks do not mention HST.

**Spitzer.** 1,302 IRAC rows, 2003.85-2019.64. They cover the 2009.9 event, and no Spitzer data cover 2023.

**Data rights.** All public (dataRights PUBLIC).

## 2. NGC 4945 obscured #3 (196.469582 −49.416175)

### NGC4945.1 Real and astrophysical

- **Referee verdict** (triage 2026-11-01, §1 #1 and §2.2): "Real, unreported, obscured slow IR outburst … The
  4-year rise rules out a supernova."
- **My checks.**
  - **Both bands and both seasons**: W1 ≥ 5σ in every epoch from 2019-01 to 2024-07 (12 epochs, alternating seasons);
    W2 ≥ 5σ in 9 of them (4.7-5.0σ in the other three).
  - **Flat baseline**: 11 epochs 2010-2017.5, rms 17 µJy, none beyond 2.3σ.
  - **PSF-like** in the difference stamps.
  - **Stationary**: per-epoch centroids scatter 0.23"/0.41" (rms, 19 epoch-bands), with no trend over 2019-2024.
  - **Independent confirmation by a second observatory**: Spitzer/IRAC (SPIRITS 13053/14089, public), measured
    here with the H-0013 tool (`spitzer_ngc4945.py`: 46 mosaics, 0 errors; final numbers from `spitzer_discovery.py`).
    - [3.6]: flat in 2013-2016 (rms 3.5 µJy); +15.5 (2.9σ) and +17.2 (3.9σ) in 2017; +33.3 ± 3.1 µJy on 2018-06-02
      (the discovery); then +182 / +203 / +322 µJy in 2019-05, -07 and -10.
    - [4.5]: +49.9 ± 5.0 µJy on 2018-11-23, +212 µJy in 2019-10.
    - [3.6] on 2019-07-02 (+203 µJy) against WISE W1 on 2019-07-07 (+213 ± 17 µJy): a 5% difference.
  - **Not a core residual**: 309" NE of the nucleus, mask code 0.
  - **Neighbour**: a second SEIP 4.5 µm source at 4.2" (47 µJy) is static in the reference. The variable's Spitzer
    centroid is 0.19" from the other SEIP source (below).
  - **Not an AGN**: no host in the reference, and a single smooth hump.
  - **Not a known variable**: nothing in SIMBAD within 15" or VSX within 30", no Gaia DR3 source within 6".
  - **Not a Galactic moving or foreground star**: b = +13.4°, but stationary for six years with no Gaia source. A
    Galactic YSO-type outburst cannot be strictly excluded, but nothing points to one (see below).

### NGC4945.2 Is it a TNS transient?

Yes: one outburst, with a slow rise from 2017/18 to a 2022-07 peak and a decline to 20% of peak by 2024-07, from a
flat 2010-2017 baseline. There is no earlier episode:
- WISE 2010-2017 is flat;
- Spitzer 2007.6 ([4.5] −10 ± 5) and 2013-2016 are flat;
- H-0013's recurrence scan does not list it (`candidates_h0013.csv`).

It is **not OS-0033** (the periodic source in NGC 4945, 140" away).

Peak νLν(W1) ≈ 3×10⁵ L☉ at 3.7 Mpc (referee). The remarks give no interpretation; the referee favours an obscured
LRN-like or ILRT-like eruption of a dusty progenitor.

### NGC4945.3 Not already reported

- **TNS**: 60" cone `unreal=all`: 0 rows. Host "NGC4945": SN 2011ja and SN 2005af only, both > 6' away. "NGC 4945":
  0 rows.
- **ATel/ADS**:
  - Position strings in astronomy full text: 4 hits, unrelated (catalogue papers).
  - ATel: 3 hits.
    - ATel 12638 (Denisenko 2019, "Peculiar Red Flaring Object in the field of NGC 4945") is at RA 13:05:14.57,
      6.2' from ours. It is a different object (an optical flare). Abstract read.
    - ATel 14380 (new ULX, 196.23359 −49.53283): a different object.
    - ATel 3820 (SN 2011ja): unrelated.
  - TNS bibstems: 0.
  - IR/transient terms 2019+: 103 hits, keyword-screened, none on this source.
  - The referee's 2026-11-01 checks (Gaia alerts, SPIRITS catalogues: no event within 5"; WTP papers) also stand.
- **SIMBAD** (15"): none.
- **VSX** (30"): none.
- **Gaia DR3** (6"): none.
- **AllWISE** (6"): none.
- **Gaia alerts**: nearest 2,486".
- **ASAS-SN**: 0 within 60".
- **ZTF**: outside the footprint (dec −49°).
- **SPIRITS**: SPIRITS observed this position through the rise, but no SPIRITS transient is published within 5"
  (referee). It may be on an internal SPIRITS or WTP list, which is why the De column matters most here.

### NGC4945.4 Numbers

**Revised 2026-11-03 (coordinator decision): the TNS discovery is the Spitzer detection.** A WISE discovery after
an earlier 8σ Spitzer detection was internally inconsistent: the WISE last non-detection came after that detection
and was shallower than the WISE discovery magnitude. Spitzer numbers are from `spitzer_discovery.py`:
- Exposure times are the mid-times of the IRAC BCD frames that contain the source (IRSA SIA, 0.36" circle; 207
  frames in 21 AORs). This is the analogue of the NEOWISE L1b frame index.
- Fluxes are 2.4" aperture-corrected differences at the reported position, against the median of the flat 2013-2016
  epochs (12 at [3.6], 4 at [4.5]), leaving the measured epoch out. 2017 is excluded from the reference because it
  is already marginally positive. The empirical error comes from 12 apertures 10" away; the [3.6] reference scatter
  is 3.5 µJy rms.
- These replace the first-pass Spitzer numbers (`spitzer_ngc4945.py`: all-epoch reference, no LOO, WISE-centroid
  aperture), which were 6-15% different.

**Discovery.** IRAC [3.6], 2018-06-02 05:10:43 (MJD 58271.2158).
- Mean mid-time of 7 BCD frames, 05:04:29-05:16:57; AOR 60808960, SPIRITS13 programme 13053, PI M. Kasliwal;
  public. Exposure 655.2 s.
- +33.3 ± 3.1 µJy (10.7σ) = 20.09 ± 0.10 AB.
- [4.5] does not cover the source in this AOR: no BCD frame, 0% mosaic coverage.

**Last non-detection.** IRAC, 2017-10-03 (AOR 60808704, SPIRITS13).
- [3.6] at 09:08:01 (9 frames): +17.2 ± 4.4 µJy (3.9σ), 5σ > 20.55 AB.
- [4.5] at 09:22:11 (7 frames): +7.8 ± 4.6 µJy (1.7σ), 5σ > 20.50 AB.
- It is the last epoch before discovery with no ≥ 5σ detection, though the rise had probably begun (2017-06-08 is
  +2.9σ). Its limit is fainter than the discovery magnitude, so the pair is consistent.
- The alternative strictly flat epoch is 2016-05-27 ([3.6] +2.3 ± 3.7 µJy, 5σ > 20.74).

**Later Spitzer.**
- [4.5] 2018-11-23: +49.9 ± 5.0 µJy = 19.65 ± 0.11 AB.
- [3.6] 2019-05-20 / 2019-07-02 / 2019-10-25: 18.25 / 18.13 / 17.63 AB.
- [3.6] on 2019-07-02 (+202.9 µJy) against WISE W1 on 2019-07-07 (+213 ± 17): a 5% difference.

**WISE (kept in the remarks).**
- First ≥ 5σ: epoch 13, 2019-01-27 17:43:39 (26 qual frames, 2019-01-25 16:11 to 01-29 15:59; n-m W1 25). W1 93.4 ±
  8.7 µJy = 18.97 ± 0.10 AB; W2 109.5 ± 22.0 = 18.80 ± 0.22 AB.
- Last WISE non-detection: 2018-07-07 14:37, W1 +46.6 ± 23.5 µJy, 5σ > 18.72. This is no longer a TNS field.

**Peak.** 2022-07-07 09:19: W1 897.7 ± 13.6 µJy = 16.52 ± 0.02 AB; W2 16.71 ± 0.04.

**Last.** 2024-07-06: W1 18.20 ± 0.09, W2 17.96 ± 0.17.

**Optical.**
- ATLAS (referee job 5280888): no valid ATLAS measurement before 2019-02-13. At the 2022-07 peak, 3σ c > 22.05 and
  o > 21.06 AB.
- o − W1 > 4.5 mag at peak.

### NGC4945.5 Position

**Spitzer/IRAC centroid of the 2019 brightening**: mean of [3.6] and [4.5], which agree to 0.13".
196.469582 −49.416175 = 13:05:52.700 −49:24:58.23, **±0.3"**.
- It lies 0.19" from SSTSL2 J130552.71−492458.3: [4.5] 40.5 ± 0.7 µJy and no [3.6], in the cryogenic-era SEIP
  catalogue, the probable progenitor.
- The Gaia-tied WISE centroid (13:05:52.761 −49:24:58.74, ±0.5") is 0.79" away.
- There are no HST or JWST data within 30" (MAST).

### NGC4945.6 Host and distance

- NED: NGC 4945, z = 0.001878 ± 0.00001 (2014MNRAS.440..696A), cz 563 km/s.
- Distances: 16 values, 3.36-7.04 Mpc, median 3.88.
  - TRGB: 4 values, 3.36-3.80, median 3.65.
  - Tully-Fisher: 10 values, median 3.91.
- Working range 3.4-3.9 Mpc.

### NGC4945.7 Counterpart or progenitor

- **Progenitor**: the SEIP 4.5 µm source (above). At 3.7 Mpc that is νLν(4.5) ≈ 1×10⁴ L☉ (referee), red (no 3.6 µm).
  It is mentioned factually in the remarks.
- No Gaia source, and no HST or JWST imaging.
- **Spitzer/IRAC**: 522 rows, 2007.6-2019.8 (SPIRITS 2014-2019 and SN 2011ja programmes). Used above.

## 3. Not-ready candidates: details

See the table. Additional notes:

- **NGC 55 #13 and IC 342 #23** are on the brief's start list. Both fail the transient test.
  - They are long-term brightenings of pre-existing sources: a Spitzer 2004-09 blend for NGC 55, and a G = 20.1 star
    with a ZTF optical rise for IC 342.
  - Neither has a quiescence-outburst-decline shape. TNS excludes variable stars, and filing either now would be a
    classification claim ("pre-merger", "eruption") that the data do not support.
  - Both should stay monitoring cases. Re-assess with SPHEREx 2025-26: an outburst on top of the rise would be
    reportable.
- **NGC 4656 #35** is the closest call. The 2019-2023 rise-and-fall is clean in W1. Against filing:
  - the elevated 2010 level could be either an earlier episode or a cryogenic-vs-NEOWISE offset (the same 2010
    offset is seen in M101 #20);
  - an X-ray source lies 1.4" away;
  - nobody has refereed it.
  Next step: Spitzer 2004-2019 with `oddsky.imaging.spitzer` (as done here for NGC 4945) and a referee pass.
- **Holmberg II #17**: luminous (+1 mJy at 3.4 Mpc ≈ 4×10⁵ L☉ in W2) and certainly real (strong PSF residual,
  both bands and seasons). But it is an eight-year brightening with no decline, in an HII knot whose own IR flux is
  larger. It needs a case: Spitzer to establish the pre-2010 state, and HST.
- **UGCA 127 #27**: checking its stamps needs one small tile fetch (0949m091). That is allowed only "if essential",
  and since the source fails on other grounds (W2-only, low latitude, referee low priority) it was not fetched.
- **NGC 1744 #29**: the h0012b cutout-dipole flag is False, while the h0012a referee saw a dipole. Either way it is a
  marginal W1-only rise.

## 4. Repeating sources: out of scope

TNS takes transients, not periodic or long-term variables: "NOT variable stars … or other such galactic/local
variable/moving sources" (Yaron 2024; `../tns_OS-0030_validation.md` §2). Oddsky's periodic dust makers are
therefore not filed:
- **OS-0031** (NGC 2403; four cycles 2007-2023, P ≈ 5.3 yr);
- **OS-0033** (NGC 4945, 196.41592 −49.42001; three cycles, P ≈ 5.4 yr);
- **OS-0034** (NGC 3344; P ≈ 10 yr, WR 140-like).

NGC 4214 #32 (an H-0013 recurrent candidate) is excluded for the same reason. M81 = OS-0035 is the exception argued
in §M81.2: two eruptions, no demonstrated period, and an eruption in 2023-24 large enough to be reportable on its own.

## 5. Service log (errors are errors, not nulls)

| service | status |
|---|---|
| TNS search (22 requests) | all HTTP 200 with CSV, ≥ 61 s apart; no 429 or HTML |
| IRSA L1b frame index | NGC 4945 OK (requests). M81 OK via the curl fallback after a Python ConnectionError. A second M81 call in `recompute_m81.py` was reset (curl exit 35), so the frame list saved minutes earlier was reused (same URL). |
| IRSA SIA (Spitzer) | OK, 46 mosaics; 0 download errors |
| IRSA TAP SEIP | OK |
| VizieR idia (Gaia DR3, AllWISE, VSX) | OK. The first attempt went to vizier.cds.unistra.fr and **timed out** (error). It was redone on idia. |
| SIMBAD CfA TAP | OK |
| NED ObjectLookup / nDistance | NGC 4945: **ConnectionReset** twice, then OK on retry (`ned_hosts.py`). NGC 3031 OK. |
| ADS API | OK, except one bibcode lookup that returned **HTTP 502** (2017TNSTR.250, the ISSP report; its object is not within 60" per TNS). |
| ALeRCE | OK (M81) |
| MAST | OK |
| Fink, Lasair | **not queried** (Fink unreachable for OS-0030; Lasair needs a token). They cover the same ZTF stream as ALeRCE; NGC 4945 is outside ZTF. |
| ATLAS | no new job. The referee's 2026-11-01 jobs 5280888/5280889 were reused. |

## 6. What Alan must decide before filing

1. Fill in the **De list** column. If either source is on it, talk to K. De first.
2. Accept the M81 framing (§M81.2) and the M81 host-redshift choice.
3. NGC 4945: the discovery is now Spitzer/IRAC 2018-06-02 (coordinator decision, 2026-11-03). Check that the live
   form lists "SST - IRAC" [193] and "3.6-Spitzer IRAC" [40]; these values come from the TNS values mirror, not from
   the live form. If they are missing, fall back to Other. Expect AT 2018xxx.
4. Re-run the two TNS cones on the filing day (`scripts/tns_search_packet.py` or by hand, 60 s apart).
5. Fill the form with the fill JSON, checking the option values against the live drop-downs, and upload the summary
   PNG. **Do not submit without Alan's go-ahead.**
6. After filing, record the TNS names (OS-0035 through the case tools; for NGC 4945, a new case if wanted).
