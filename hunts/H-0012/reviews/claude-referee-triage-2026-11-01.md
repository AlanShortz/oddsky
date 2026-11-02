## 1. Verdict

Referee: Claude (adversarial pass on the full run's triage), 2026-11-01. Scope: `README.md` (full-run section),
`work/triage_h0012a*.{csv,json}`, `figures/triage_h0012a_top.png`, `scripts/merge_triage.py`, the run outputs in
`~/oddsky-runs/h0012a/`, and the archives listed under each lead. Scripts and small outputs are in
`reviews/claude-referee-triage-2026-11-01/`. Nothing else in the repo was edited, and nothing was posted. Two
unWISE tiles were fetched for the mask test: 2029p469 (M51) and 1507p696 (M82). Also fetched: the 332 bitmasks
(about 150 kB each) and 15 single-epoch W1 images.

**Headline.**

- **None of the briefed leads is a credible failed supernova.** Every one is an AGB or long-period variable, a
  background AGN, a slow fade with no catalogued progenitor, or a fade too luminous for any star.
- **One source not on the brief list is a credible unreported obscured transient: NGC 3239 156.2910 +17.1639.**
  - WISE: a W1/W2 transient peaking on 2020-11-21 that decays over about 1.5 years.
  - There is no TNS entry and no ZTF alert, and ZTF and ATLAS saw nothing at the WISE peak.
  - HST imaged the field by chance 85 days after the WISE peak. That image holds a faint point source,
    F606W ≈ 25.8 AB, 0.87" from the WISE position. It is absent in 2022-12 and in 2025-01.
  - So the optical counterpart is about 7.5 mag fainter than W1: a dust-obscured transient.
- **Three briefed leads are real, unreported obscured outbursts with no optical counterpart, and are worth cases:**
  NGC 4945 (196.4697 −49.4162), M81 (148.739 +69.147) and NGC 55 (3.7558 −39.2033). IC 342 56.5658 +68.1491 is a
  slowly brightening luminous star, a possible pre-merger (LRN precursor).
- **The SN 2014J miss is the bitmask.** The unWISE "bright star" bits fire on M82's nucleus and blank 92% of the
  galaxy's W1 light. Forced photometry at the SN gives W1 = 11.4 mJy at S/N 116 on 2014-04-19.
- **SN 2011dh is not masked.** It was simply below threshold by the first NEOWISE epoch, 937 days after explosion.
- **The ranking fix is a luminosity floor on the lost light, plus a roughness test.** With both, BH1 moves from
  #65 to #9 and DS1 to #1. M31/M33 drop from 28 of the top 30 to 4.

| # | Item | Verdict |
|---|---|---|
| 1 | NGC 4945 196.4697 −49.4162 (obs #3) | **Real, unreported, obscured slow IR outburst.** Flat 2010-2017; rises 2018 → mid-2022 to +0.9 mJy (3.3×10⁵ L☉ in W1); falls by 2024. The progenitor was a dusty IR source in Spitzer (4.5 µm 40 µJy ≈ 1.2×10⁴ L☉ νLν). No Gaia source; no ATLAS signal at peak (o ≳ 21.9 AB; o − W1 ≳ 6 mag AB). The 4-year rise rules out a supernova. Most likely an obscured luminous red nova or merger, or a slow ILRT-like eruption of a dust-enshrouded star. **Worth a case: yes.** |
| 2 | M81 148.739 +69.147 (obs #9) | **Real, unreported, obscured outburst in a compact HII region** ([HAE2008] 7; Gaia/DSC calls the counterpart extended). The 2010 level is +150/+250 µJy above a flat 2014-2023 level; then +0.8/+1.0 mJy in 2023.8-2024.2 (about 3×10⁵ L☉). No ZTF alert; ATLAS flat (o − W1 ≳ 4.5 mag AB). An eruptive massive star (LBV-like or pre-SN outburst) or an obscured SN in early 2024. **Worth a case: yes** (needs post-2024 IR: SPHEREx, JWST). |
| 3 | NGC 55 3.7558 −39.2033 (obs #14) | **Real, unreported, decade-long monotonic IR brightening that accelerated in 2023-24.** W1 roughly 0.3 → 1.1 mJy (+10⁵ L☉), 0.1 R25 from the centre. ATLAS shows no optical change (Δo ≲ 10 µJy). Candidates: a dust-forming massive star, a common-envelope pre-merger (LRN precursor), or an obscured background AGN (W1−W2 of the rise is 0.62, below the AGN cut). **Worth a case: yes** (monitoring; it would matter if an LRN followed). |
| 4 | M101 210.729 +54.374 (obs #19) | **Real fading IR point source inside a young cluster / HII complex** ([HBS84] 29; NED *Cl at z = 0.00076; a Wolf-Rayet candidate and a Chandra HMXB within 1.2"). Bright in 2010, then faded by 0.2 mJy in W1 and 0.45 mJy in W2 (4×10⁵ L☉ in W2) to 2019, with the faded light very red. Not an AGN; not a failed SN (a cluster blend, and far too luminous). Most likely the fading dust of a pre-2010 obscured transient or a dusty massive-star eruption. **Case: low priority** (Spitzer 2004-2008 and SPIRITS archives first). |
| 5 | IC 342 56.2762 +68.0725 (fsn #1) | **Real, very luminous fade that began before WISE; not a failed SN.** Spitzer (cryogenic, 2004-08) shows 2.6 mJy at 3.6-5.8 µm (a flat Fν, about 900 K dust; νLν ≈ 7×10⁵ L☉), 0.93 mJy in AllWISE 2010, and about 0.1-0.2 mJy by 2024: at least a 15× fade over 15-20 years. No Gaia, SIMBAD or TNS object; NED only the WISE source. A 15× monotonic mid-IR fade with hot, flat-to-falling dust argues against an AGN (W1−W2 = 1.03 notwithstanding). Most likely the cooling IR remnant of an unrecorded pre-2004 luminous transient in IC 342; a Galactic embedded YSO is the alternative. **Case: moderate** (Spitzer epochs 2004-2019 would settle it). |
| 6 | NGC 2976 146.7650 +67.9350 (fsn #5) | **Probable background AGN.** The Spitzer 2004 SED rises to 8 µm with IRAC colours inside the Stern et al. 2005 AGN wedge ([3.6]−[4.5] = 0.69, [5.8]−[8.0] = 1.19). The light curve is flat 2010-16, then a wiggly decline with a partial recovery in 2021-22, which is stochastic, not a fade-and-stay. There is no AllWISE or Gaia entry because of blending with the disk. "L ≈ 10⁶ L☉" is the photospheric bolometric correction applied to an AGN. **No case.** |
| 7 | M31 10.0712 +40.4525 (fsn #4) | **A dusty (extreme) AGB star, or less likely an AGN.** AllWISE W1−W2 = 1.36; Spitzer [3.6]−[4.5] = 1.28 mag, with 8 and 24 µm detected. Optically almost invisible (one PS1 z = 21.3 detection). It faded in 2014-19, then **W2 recovered by 30%**. L_fade = 4×10³ L☉, an AGB amplitude. **No case.** |
| 8 | M33 ranked 10, 12, 13, 14 | **AGB / long-period variables.** #10 zig-zags (roughness 2.5-2.9) with W1−W2 = 1.05. #12-14 are slow 25-40% fades with season zig-zag. Their Spitzer SEDs fall with λ (cool photospheres plus modest dust). PS1 gives r ≈ 21.2-21.7 and r − z ≈ 1.5; #13 has Gaia BP−RP = 4.26, a carbon star or dusty AGB. L_fade is 1.7-2.6×10³ L☉. **No case.** |
| 9 | Other top-20 failed-SN unknowns in M31 | **#3** (11.4583 +40.0859): 2.4 R25 out; PS1 extended (i_PSF − i_Kron = 0.76); KLG2007 lists it as a galaxy, so it is a background galaxy or AGN. **#7** (11.2730 +42.7306): 1.4 R25, a point-like PS1 counterpart at r = 20.2, W1−W2 = 0.77; probably a background QSO. **#9** (9.7195 +40.3182): cyclic with a period of about 6.5 yr, W1−W2 = 1.87, Spitzer very red; an OH/IR or extreme AGB star. **#11** (11.9763 +42.0834): W1−W2 = 1.69, a red power-law Spitzer SED, a 1×10³ L☉ fade; a dusty AGB star or AGN. **No case for any of them.** |
| 10 | Other obscured-transient unknowns | **NGC 3239 156.2910 +17.1639 (obs #33): the best new object in the run** (§2.1). **IC 342 56.5658 +68.1491 (#26):** slow optical and IR brightening of an M_r ≈ −9 star, the textbook LRN-precursor signature; worth monitoring. **UGCA 127 95.2591 −8.4826 (#30):** a W2-only 3-yr hump (W1−W2 > 2) with no counterpart anywhere; a possible SPRITE-like event or a foreground dusty LPV, low priority. **Holmberg II 124.803 +70.719 (#21):** a steady 2016-2024 brightening (about 3×10⁵ L☉) of a compact HII knot. SIMBAD's nearest "UZC galaxy" is almost certainly Ho II itself, since Gaia shows a blue knot (BP−RP = −0.2) and NED an HII region. Not an AGN; low-moderate priority. **NGC 4945 #22:** two humps about 5 yr apart (3×10⁵ L☉ amplitude, too luminous for an AGB star in NGC 4945); probably a foreground long-period variable. **NGC 1744 #32:** a dipole in the late−early image, so a moving foreground star the triage missed. |
| 11 | SN 2014J (M82) miss | **Masked.** The pixel carries unWISE bits 0-3 (W1/W2 bright star, both scans) and 27-28 (PSF spikes), because the bitmask treats M82's nucleus as a bright star. 20.7% of M82's search area and **92% of its W1 light** are masked. Forced photometry at the SN: **W1 = 11.4 mJy at S/N 116 (2014-04-19)**; 1.1 mJy in 2014-10. |
| 12 | SN 2011dh (M51) miss | **Not masked (bit 9 only); too faint by the first NEOWISE epoch.** WISE has no data from 2011-02 to 2013-12. At day 937 the change since 2010 is W1 +11 ± 11 and W2 +41 ± 21 µJy, below both channels' thresholds. Separately, **the runner's NGC 5194 centre is 141" from M51's nucleus** (UNGC position), so its nucleus circle sits on the disk. The real nucleus happens to be masked by bits 0, 1 and 21. |
| 13 | Ranking (BH1 #65) | **The 64 sources above BH1 are AGB-luminosity faders.** 56 are in M31/M33; 48 lost less than 4×10³ L☉ in W1 (median 1.75×10³ L☉, against BH1's 6.6×10⁴); 40 zig-zag about any smooth curve. The score has no floor on the lost luminosity, rewards redness (up to ×2), and its photospheric bolometric correction puts dusty AGB stars in the RSG window. Proposed fix (§4): BH1 lands #6-#12 and DS1 #1 under every threshold variant tried. |
| 14 | Novelty | **None of the surviving objects is reported.** Checked: TNS (cached galaxy cones, 60" around each lead), Gaia alerts, SIMBAD/NED, the SPIRITS transient and variable catalogues, Jencson et al. 2019, the WTP papers, ADS/arXiv. NGC 3239, NGC 55 and UGCA 127 were never in SPIRITS. NGC 4945, M81 and IC 342 were, but no SPIRITS event lies within 5" of any lead. ATel was only partly searchable (§5). |

## 2. The leads

All light curves below are the runner's forced photometry (`leads.py` → `leads_*.png`, `leads_lc.csv`). Each is a
change since 2010-11 in µJy, season-aligned. Per-epoch difference cutouts are in `epochs_*.png`. Cross-matches are
in `xmatch.json`: Gaia DR3 within 5" (source_id as a string), AllWISE within 6", SIMBAD (Harvard) within 10", NED
within 10", Milliquas. Spitzer SEIP cryogenic-era fluxes are in `spitzer_seip.json`. ZTF and NEOWISE are in
`ztf_neowise.json` and `ztf_*.csv`, ZTF alerts in `alerce.txt`, ATLAS in `atlas_*.txt` and `atlas_vs_wise.png`,
HST in `hst_*.{png,json}`.

### 2.1 NGC 3239 156.2910 +17.1639: a credible unreported obscured transient (not on the brief list; obs #33)

| date (MJD) | W1 change (µJy) | W2 change (µJy) |
|---|---|---|
| 2010-2020 May (58967) | within ±30 of 0 | within ±45 of 0 |
| **2020-11-21 (59176)** | **+250 ± 8** | **+302 ± 17** |
| 2021-04-28 (59334) | +101 ± 8 | +103 ± 16 |
| 2021-11-22 (59542) | +51 ± 8 | +41 ± 19 |
| 2022-04 onward | ≤ +30 | ≈ 0 |

- **The WISE event.**
  - It is a compact PSF in both bands at the peak epoch. It is positive in both visit seasons (2020-11 and
    2021-04), so it cannot be an asteroid.
  - No quiescent source: the reference flux is −3 µJy. No AllWISE, Gaia or SIMBAD counterpart within 5".
  - At 7.9 Mpc the peak is W1 = 15.2 Vega, M_W1 ≈ −14.3, νLν ≈ 1.6×10⁵ L☉. The decay e-folds in about 175 days.
  - W1−W2 of the transient light is 0.84.
- **Timing and optical limits.**
  - The onset lies between 2020-05-02 and 2020-11-21. NGC 3239 was in solar conjunction around late August.
  - ZTF DR photometry at the position stays at its quiescent r ≈ 20.2-20.5 through 2020 Oct-2021 Mar, including
    on the WISE peak day: r = 20.17 on MJD 59176.6.
  - ALeRCE has **no ZTF alert object** within 4", so nothing reached 5σ in ZTF difference imaging, 2018-2025.
  - TNS has nothing within 60" except SN 2012A (49.9").
  - Any unobscured SN (IIP plateau, Ia or Ib/c tail) at 7.9 Mpc would have been r ≈ 15-17 when the field emerged
    from conjunction in October.
- **HST, by chance.** Three epochs cover the position:
  - WFC3/UVIS F606W/F814W on 2021-02-15 (programme 16179, a SN 2012A follow-up), 85 days after the WISE peak, when
    W1 was still about +170 µJy;
  - ACS/WFC F606W on 2022-12-11 (15446);
  - WFC3/UVIS F555W/F814W/UV on 2025-01-07 (17502).
- **What the difference shows** (`hst_ngc3239_peak.png`, `.json`). I differenced F606W 2021 minus the scaled ACS
  F606W 2022 on the common HAP skycell grid.
  - A point source sits **0.87" from the WISE centroid**. The WISE astrometric floor measured on DS1 is about
    0.5"; this is a 2.75"-pixel instrument at S/N about 30.
  - It has F606W ≈ 25.8 AB, and is the most significant residual within 1.2" (S/N 8.4). Only 0.03% of control
    apertures 2-3.8" away exceed it.
  - It is absent in ACS F606W 2022 and in F555W 2025.
  - It also appears in the 2021+2025 F814W stack, at 25.3 AB diluted. Since that is a different filter from the same
    2021 visit, it is not a cosmic ray.
- **What it is.**
  - At 2021-02-15 the source had F606W − W1 ≈ 25.8 − 18.3 ≈ 7.5 mag (AB), and M_F606W ≈ −3.7.
  - A supernova 3-6 months after explosion has V − [3.6] of about 1-2 mag. This one therefore implies A_V ≳ 6
    along the line of sight, unless it is an intrinsically very red, faint transient.
  - **Most likely a heavily obscured core-collapse SN in NGC 3239. An obscured LRN or ILRT is the alternative.**
- **Caveats.**
  - The HST counterpart could be an unrelated faint variable star that happened to be brighter in 2021. The odds are
    low at 0.9" and at the WISE event's epoch.
  - The ATLAS task (queued, not finished at writing) should show no optical light in 2020-21 if this is right.
- **Novelty.** Not in TNS, ATel (as far as searchable), Gaia alerts, the WTP papers or SPIRITS. SPIRITS ended in
  January 2020 and never observed NGC 3239.
- **Worth a case: yes, the strongest object in the run.** Next steps:
  - PSF photometry on the HST SVM exposures, not the skycell stack, for an exact 2021-only F814W magnitude.
  - Check whether HST 2025 UV/Hα shows a host cluster.
  - Read the ATLAS result.
  - Report to TNS once the owner decides. The referee posted nothing.

### 2.2 NGC 4945 196.4697 −49.4162 (obs #3)

- **Light curve.** Flat within ±50 µJy from 2010 to 2017.5. Then it rises smoothly in both bands and both seasons:
  +106 µJy (2019.1), +429 (2021.1), +913 (2022.5, peak), +627 (2023.1), +288 (2023.5), +206 (2024.5). W2 tracks
  W1, with W1−W2 of the rising light 0.47.
- **Progenitor.**
  - Spitzer SEIP (2004-09) has a 4.5 µm source of 40 µJy (SSTSL2 J130552.71−492458.3, 0.8"), with no 3.6 µm
    detection. At 3.8 Mpc that is νLν(4.5) ≈ 1.2×10⁴ L☉: a dust-enshrouded luminous star.
  - The pipeline's reference W1 is 38 µJy.
- **Optical.**
  - Gaia: none within 5". Gaia alerts: none within 2'.
  - ATLAS difference photometry, 2016-2025 (job 5280888): c and o flat, robust SD 2-4 µJy per 60-day bin. Peak-epoch
    bins are consistent with 0, so o ≳ 21.9 AB while W1 ≈ 16.0 AB.
  - NGC 4945 is an edge-on, dusty galaxy at b = +13°.
- **Interpretation.**
  - A 4-year rise to 3×10⁵ L☉ (W1 alone) and a roughly 2-year decline, from a dusty IR progenitor, invisible in the
    optical.
  - Not a SN (too slow to rise), not an AGB star (too luminous by 10×), and not a background AGN (no host in the
    reference; a smooth single hump).
  - It resembles an obscured LRN with a long IR pre-merger rise, or a slow ILRT-like eruption of a SN 2008S-type
    dust-enshrouded progenitor.
  - SPIRITS imaged the position on 18 days from 2014 to 2019, so the onset in 2018-19 is in the public Spitzer data.
    Its nearest events (17ar, 16rz) are about 2.6' away.
- **Worth a case: yes.**

### 2.3 M81 148.739 +69.1468 (obs #9)

- **Light curve.**
  - 2010: +45 / −45 µJy (W1) about the 2010 mean.
  - 2014-2023.3: flat at −100 (W1) and −210 µJy (W2) relative to 2010.
  - 2023.8: W1 −10, W2 −6, i.e. +100 / +200 above the flat level.
  - **2024.2: W1 +645, W2 +783**, i.e. about +750 / +1000 above the flat level, about 3×10⁵ L☉ in W2.
  - Real in both bands (per-epoch cutouts), and in the final short 2024 visit.
- **Counterpart.** Gaia DR3 1070474934439610752 at 0.1" (G = 20.25, BP−RP = 0.37). It is not a quasar: DSC gives
  P(quasar) ≈ 0 and P(galaxy) = 1.0 because it is resolved, a compact HII region or cluster (SIMBAD [HAE2008] 7;
  NED HII region; AllWISE W3 = 8.7, W4 = 6.1).
- **Optical.** ZTF has no alert object, and its DR light curve of the HII knot is flat from 2018 to 2025 (slope
  < 0.01 mag/yr in g and r; `optical_faders.json`). ATLAS (job 5280889) is flat through 2023-24 (o robust SD
  11 µJy), so the outburst is IR-only to o − W1 ≳ 4.5 mag AB.
- **Nearest known objects.** Nova M81 2025-01c? is 24" away. No SPIRITS event lies within 5'.
- **Interpretation.** Two IR-bright episodes (≤ 2010 and 2023-24) from a source in a young star-forming knot,
  with the second about 3×10⁵ L☉: an eruptive massive star (LBV-like, possibly a pre-SN outburst), or an obscured SN
  in early 2024. NEOWISE ended in 2024-08, so the next IR data must come from SPHEREx (2025+) or JWST.
- **Worth a case: yes.**

### 2.4 NGC 55 3.7558 −39.2033 (obs #14)

- **Light curve.** Zero in 2010-11. +150 to +200 µJy in 2014-16, +300 to +480 in 2017-22, +580 in 2023.5 and
  **+800 in 2024.5** (W1 and W2 together, W1−W2 of the rise 0.62). The rise is accelerating.
- **Earlier IR.** Spitzer SEIP (2004-09) holds two blended sources within 3": 315/416/477/700 µJy at 3.6-8.0 µm,
  and 123 µJy at 3.6 µm. That is consistent with the 2010 WISE level of about 0.2-0.3 mJy. A Gaia DR3 two-parameter
  source of G = 21.1 lies at 0.42". The position is 0.09 R25 from the centre, just outside the runner's 89" nucleus
  circle.
- **ATLAS** (job 5280890): no trend, robust SD 9-13 µJy per bin, against a +600 µJy W1 rise.
- **Not in SPIRITS.**
- **Interpretation.** An IR-only, decade-long, accelerating brightening of about 10⁵ L☉. Candidates:
  - a common-envelope pre-merger: LRN precursors brighten for years, and their dust can hide the optical;
  - a dust-forming massive star;
  - an obscured background AGN seen through the edge-on disk. The rise colour (0.62) is below the AGN cut but
    proves nothing.
- **Worth a case: yes, as a monitoring target.**

### 2.5 M101 210.729 +54.374 (obs #19)

- **Light curve.** Bright in 2010. By 2014 W1 is −110 and W2 −220 µJy. W2 keeps falling to −450 by 2019, then is
  flat. The faded light has W1−W2 = 1.53.
- **What sits there.** The position is in the giant HII complex [HBS84] 29 / NGC 5457 knot. NED lists
  2MASS J14025498+5422264 as a star cluster (*Cl, cz = 228 km/s). There are two Gaia sources (G = 18.7 and 18.8)
  within 1". [BKD2008] WR 258 is at 0.7", and 2CXO J140254.9+542227 (an HMXB in Chandar et al. 2020) at 1.2".
- **Optical.** ZTF has 6 alerts in 2018-2020 (ZTF18aajytik). ZTF shows a steady r ≈ 17.0 cluster.
- **Novelty.** No SPIRITS event within 30" (16kp is 35" away).
- **Interpretation.** A red mid-IR point source of about 4×10⁵ L☉ (W2) that faded after ≤ 2010 inside a young
  cluster. Not an AGN; not a failed SN. Probably the dust of a pre-2010 obscured transient or eruption. Spitzer
  2004/2007 IRAC images and SPIRITS 2014-19 would give the earlier history (SEIP has no IRAC match because of
  crowding).
- **Low priority.**

### 2.6 IC 342 56.2762 +68.0725 (fsn #1)

- **Light curve.** A monotonic decline in both bands from 2010 to 2024: W1 about −700 µJy, W2 about −1100 µJy. The
  W2 zig-zag between seasons (blending under the flipped PSF) gives a high roughness, but every season declines.
- **Earlier and later IR.**

  | epoch | 3.6 µm / W1 | 4.5 µm / W2 | 5.8 / 8.0 µm |
  |---|---|---|---|
  | Spitzer cryogenic (2004-08) | 2583 µJy | 2685 µJy | 2614 / 2266 µJy |
  | AllWISE 2010 | 0.93 mJy | 1.75 mJy | — |
  | 2024 (pipeline) | about 0.1-0.2 mJy | — | — |

  AllWISE also gives W1−W2 = 1.03, W2−W3 = 3.0, W3 = 9.7, W4 = 7.8.
- **Interpretation.**
  - The fade started before WISE, and is at least 15× in W1 over 15-20 years.
  - The cryogenic-era SED is flat in Fν from 3.6 to 8 µm: about 900 K dust with νLν(3.6) ≈ 7×10⁵ L☉.
  - Not a failed SN: no RSG-like progenitor phase is seen, and the luminosity is ≥ 10× a red supergiant's mid-IR.
  - Not typical of an AGN: AGN mid-IR fades are factors of 2-5, with Fν rising to longer λ.
  - Galactic dust-shell stars at kpc distances would be far too faint (νLν ~ 10 L☉ at 10 kpc), except a nearby
    embedded YSO.
  - Favoured: the cooling IR remnant of a luminous pre-2004 transient in IC 342, which is behind A_V ≈ 2 and had
    poor 1990s-2000s optical coverage.
- **Case: moderate.** The Spitzer 2004-19 epochs would give the decline curve. The literature check found the
  position outside the SPIRITS field, but other Spitzer programmes cover it.

### 2.7 NGC 2976 146.7650 +67.9350 (fsn #5)

- **Light curve.** Flat from 2010 to 2016. Fades about 300 µJy to 2020.8, recovers to −50 in 2021.8-22.3, then
  fades again to −300/−350 in 2024. A stochastic red-noise curve, not a vanishing star.
- **Spitzer** 2004: 501/607/1001/1674 µJy at 3.6-8.0 µm, in the Stern AGN wedge.
- **ZTF:** a faint (r ≈ 19.5) variable optical source.
- **Probable background AGN.**

### 2.8 M31 10.0712 +40.4525 (fsn #4), and the M33 #10 and #12-14 faders

These are AGB stars (or, for some, AGN). Evidence:

- **Spitzer** (`spitzer_seip.json`): #4 is extremely red. M33 #12-14 have photosphere-plus-modest-excess SEDs, with
  W1 300-400 µJy, i.e. νLν(3.6) ≈ 6-8×10³ L☉.
- **Optical** (`optical_faders.json`): M33 #12-14 are faint and red in PS1 (r ≈ 21.2-21.7, z ≈ 19.8-20.5;
  M_z ≈ −4.8). M33 #13 has Gaia BP−RP = 4.26.
- **Lost light** of 1.7-4.4×10³ L☉, typical AGB amplitudes.
- **Roughness:** M33 #10 2.5-2.9; #12 4.5; #14 2.7.

### 2.9 IC 342 56.5658 +68.1491 (obs #26): an LRN-precursor candidate

- **IR.** A steady rise from 2014 to 2021 (W1 +300, W2 +250 µJy, about 10⁵ L☉), then a plateau.
- **Optical.**
  - Gaia DR3 493491093772440704 at 0.18": G = 20.1, BP−RP = 2.0, no significant parallax or proper motion (an
    extragalactic distance).
  - ZTF r brightened from about 20.5 (2018-19) to 19.8 (2020.7-2021). ZTF issued alerts in 2020-08/09
    (ZTF20abxovha, 5 detections). By 2023.7 it had faded back to about 21.
  - At 3.28 Mpc with A_r ≈ 1.4, the star is M_r ≈ −9: a luminous yellow or red supergiant.
- **Interpretation.** A years-long optical brightening with a growing IR excess, followed by optical dimming as the
  IR plateaus. This is the pre-outburst pattern of LRN progenitors (M31-LRN-2015, M101 OT2015-1, AT 2018bwo), or a
  dusty eruption.
- **No paper or ATel** mentions the ZTF name. The nearest SPIRITS event (15agl) is 16" away.
- **Worth a case: yes, monitoring** (ATLAS queued).

### 2.10 Is any of them a credible failed supernova?

**No.** A failed-SN candidate needs three things: an RSG-luminosity progenitor of 10⁴·⁵-10⁶ L☉ with a photospheric
SED; a fade of most of its light; and a fade that stays down. Checked against that:

- Among the briefed leads, only the M33 faders have photosphere-like SEDs. Their fades are 25-40% of AGB-level
  stars, still declining slowly with zig-zags.
- IC 342 #1 and NGC 2976 #5 fail on the SED (dust and AGN respectively).
- M31 #4 recovers.

The best candidate the *revised* score surfaces is **M31 10.1448 +40.7498**, the catalogued red supergiant
GAPO 209 (Gaia G = 17.9; reference W1 = 2.2 mJy, about 2-3×10⁵ L☉ bolometric). It has lost about 25% of its mid-IR
flux in steps between 2015 and 2023 (`leads_6.png`). That is semi-regular RSG behaviour unless the optical has
collapsed. I could not get its ZTF light curve: IRSA timed out repeatedly. **It is worth a 30-minute optical check (LGGS → PS1 → Gaia → ZTF) before anything else in the failed-SN
list.**

## 3. The two benchmark misses, and what the masks hide

`mask_check.py` rebuilds the runner's masks and difference stacks for NGC5194 (2029p469) and MESSIER082
(1507p696). It uses `galaxy_from_row` and the default `Config`, exactly as `infra/gcp/imaging_tile.py` does, then
reads every mask component and the forced photometry at the SN positions (`mask_check.json`, `mask_check_*.png`,
`sn_forced_*.csv`).

### 3.1 SN 2014J (M82): masked by the unWISE bright-star bits

| | |
|---|---|
| bits at the SN pixel | 0, 1, 2, 3 (W1/W2 bright star, both scans), 9, 23, 24, 27, 28 (PSF-based spikes) |
| masked by | `ARTIFACT_BITS` (dilated). Not the nucleus circle: 27.6" against a 67" separation. Not the bright-peak circles. |
| distance to the nearest unmasked pixel | 22 px (60") |
| M82 search area masked | 20.7% |
| **M82 W1 light masked** | **91.6%** (W2 93.8%) |
| forced photometry at the SN (W1) | **+11.42 ± 0.10 mJy on 2014-04-19 (S/N 116)**; +1.06 mJy on 2014-10; baseline elsewhere |
| forced photometry at the SN (W2) | +1.58 ± 0.09 mJy on 2014-04-19 |

M82's nucleus is in the unWISE bright-star list, so bits 0-3 and 27-30 draw a bright-star core-and-wings footprint
of about 1' radius over the galaxy. One caution about unmasking: the W2 forced flux at the SN position in 2010-12
reads +446 ± 64 µJy (7σ), before the SN. The noise model is not trustworthy on the starburst core, so unmasking
must come with a local empirical noise floor (see below).

### 3.2 SN 2011dh (M51): not masked, below threshold by 2013-12

- **The pixel.** Only bit 9 (resolved galaxy) is set. It is not in the nucleus circle and not in a bright-peak
  circle; in short, unmasked.
- **WISE coverage.** None between 2011-02 and 2013-12-24 (the 2011-13 gap); the SN exploded on 2011-05-31.
- **Forced photometry.** Change since 2010:

  | epoch | W1 | W2 |
  |---|---|---|
  | first NEOWISE epoch (day 937) | +11 ± 11 µJy | +41 ± 21 µJy |
  | day ~1100 | about +15 | about +20 |
  | after that | consistent with 0 (largest +15 W1 / +53 W2, at S/N ≤ 3.3) | |

- **Comparison with Spitzer.** By about day 625, Spitzer 4.5 µm had fallen to a few tens of µJy (Helou et al.
  2013; Tinyanont et al. 2016, arXiv 1601.03440). The NEOWISE level is consistent with that and sits below both
  channels' 50% completeness (35-90 µJy).
- **Expected miss.**

**Separate bug found on the way.** UNGC gives NGC 5194 at (202.4696, +47.2344). That is **141" north of M51's
nucleus** (202.4696, +47.1953), roughly between M51a and M51b. The runner's 38" nucleus circle therefore blanks a
patch of disk, while the real nucleus is unmasked by the circle. It is blanked only because bits 0, 1 and 21 happen
to fire there.

The runner also ignores `oddsky.imaging.galaxies`:

- the M32 and NGC 205 masks;
- the acceptance-test nucleus radii. The full run used 150" for M33 (acceptance test: 40"), 68" for NGC 2403 (15")
  and 62" for NGC 300 (10").

### 3.3 Masked area per galaxy

From the 332 bitmasks and the runner's geometry (`mask_census.py` → `mask_census.csv`; `mask_benchmarks.py` →
`mask_benchmarks.csv`; `mask_light.py` → `mask_light.csv`):

- **Area.** The median galaxy has 3.4% of its search area masked. 42 of 310 have more than 10% masked.
- **Centres.** 36 galaxy centres carry the unWISE "bright star" bits, so their cores are blanked.
- **Light.** The masked fraction of W1 light inside the search circle (one epoch, tile of the centre) is in the
  table. Low-latitude fields (IC 342, NGC 6946) include masked foreground stars, so their light fractions are upper
  bounds.

  | galaxy | M82 | NGC 5102 | NGC 4736 | NGC 2403 | NGC 4945 | NGC 253 | NGC 6946 | M81 | NGC 5128 | IC 342 | NGC 5055 | M51 | NGC 4258 | M83 | M101 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | W1 light masked | 92% | 78% | 66% | 52% | 48% | 46% | 45% | 44% | 44% | 42% | 39% | 34% | 33% | 26% | 13% |

- **Benchmarks.** Of the 33 non-nova benchmarks, **6 sit on masked pixels**: SN 2014J, SN 2020ukx (NGC 2784,
  bits 0-3), SN 2012A (bit 27), SN 2014bc (NGC 4258 nucleus, bits 0-3 and the circle), AT 2020nqq (geometric
  spikes 29-30) and SN 2016adj (Cen A, bits 0-3 and the circle). 14 of 72 novae are masked.
- **So yes, the mask setting is hiding real events in bright galaxy regions.** It hides close to half of the
  stellar light of the big spirals and almost all of M82. This matters most for obscured SNe, which concentrate in
  nuclear starbursts: M82, NGC 253 and NGC 4945 are the three best places within 4 Mpc to find one.

**Recommended mask changes:**

1. **Drop bits 0-5 and 27-30 wherever the "bright star" is the galaxy's own nucleus or bulge.** Either compare the
   bitmask star centroid with the galaxy centre and extended-source catalogues, or restrict `ARTIFACT_BITS` to
   pixels where the reference shows a stellar PSF.
2. Keep detection honest in those regions with an empirical local noise floor. The existing 64-px scatter
   calibration is too coarse on a starburst core: use 16 px, plus a "both seasons" requirement that is already in
   place.
3. **Add a known-position channel.** Force-photometer every TNS position in every galaxy whatever the mask, and
   report it.
4. Use the `galaxies.py` centres, nucleus radii and companion masks where they exist. Fix UNGC centres more than
   10" off (M51).
5. Report the masked area and light fraction per galaxy in the summary JSON, as part of the completeness statement.

## 4. The ranking: why BH1 is #65, and a fix

`ranking.py` re-scores all 738 failed-SN-like rows from the merged table and the run's light curves (`ranking.csv`,
`ranking.json`).

**What sits above BH1.** 64 rows, of which:

- 56 are in M31/M33;
- **48 lost less than 4×10³ L☉ in W1** (median 1,750 L☉; BH1 lost 6.6×10⁴, DS1 1.4×10⁴);
- 40 have roughness above 1.5. Roughness is √χ²ν about their own 5-point running median, so above 1.5 means
  zig-zag LPV behaviour;
- 16 have AllWISE W1−W2 ≥ 0.8;
- none is a SIMBAD-catalogued AGB star (the existing 0.3 penalty only reaches catalogued ones).

The score demotes none of these, because:

- (a) `f_L` uses a photospheric bolometric correction (×7.1) that puts any dusty AGB star at M31's distance into
  the 10⁴-10⁶ L☉ window;
- (b) `f_IR` multiplies by up to 2 for red faded light, which AGB stars and AGN have;
- (c) nothing asks how much light was lost. At 0.8 Mpc a 2×10³ L☉ wobble is a 7σ "fade".

**Proposed changes, each with a physical reason:**

1. **A floor on the lost luminosity:** × logistic(log L_fade,W1; 4×10³ L☉, 0.25 dex). A ≥ 3×10⁴ L☉ RSG photosphere
   emits about 0.14 of its light in W1, so a vanishing failed-SN progenitor loses at least about 4×10³ L☉ there.
   This is the distance-dependent luminosity window, in the band that is measured.
2. **Roughness (the LPV test):** × min(1, (1.5 / max roughness)²). A pre-fade-only χ² test, run only where at least
   6 pre-onset epochs exist, does almost nothing (BH1 #52). Most fades start in the 2011-13 gap, and DS1's
   "pre-fade" segment is its rise. Roughness during and after the fade is what separates LPVs.
3. **Colour:** drop the f_IR redness bonus, and × 0.3 for static AllWISE W1−W2 ≥ 0.8 (an AGN or dusty AGB colour)
   anywhere, not only outside D25.
4. **Proper motion:** × 0.02 when SIMBAD has a PM* within 3". This catches the top-ranked LP 826-62 in NGC 253
   (fsn #38), which the 2" Gaia match missed. NGC 3109 #143 and NGC 1744 #32 show dipoles the dipole flag missed;
   a cutout-level dipole test (correlate late−early with the PSF gradient) is the general fix.

**Ranks under each variant:**

| variant | DS1 | BH1 | M31+M33 in top 30 |
|---|---|---|---|
| current | 2 | 65 | 28 |
| roughness only | 1 | 34 | 27 |
| pre-fade χ² only (onset ≥ 2015) | 2 | 52 | 26 |
| L_fade floor only | 2 | 15 | 10 |
| colour only | 1 | 61 | 25 |
| roughness + L_fade | 1 | 9 | 5 |
| **all four (proposed)** | **1** | **9** | **4** |
| all four, L floor 2×10³ / 1×10⁴ | 1 / 1 | 12 / 6 | 11 / 4 |
| all four, roughness reference 1.2 / 2.0 | 1 / 1 | 8 / 10 | 5 / 7 |

**Cautions:**

- This was designed after seeing BH1 at #65. The 4×10³ L☉ floor is physically motivated, and BH1 lands in the top
  12 for floors from 2×10³ to 10⁴, but two benchmarks cannot validate a score. The honest test is
  injection-recovery of synthetic DS1/BH1 light curves at random positions and distances through the same scorer,
  with SIMBAD and Gaia-flagged LPVs as the negative set.
- The proposed top 30 is not clean. It surfaces:
  - the RSG GAPO 209 (#2; §2.10);
  - SPIRITS14akj (#3, a known M83 transient);
  - several slow 30-40% faders in NGC 3109, IC 342 and Cen A;
  - two NGC 3109/NGC 1744-type moving stars (until the dipole test lands);
  - duplicated rows (ESO 274-001 at 228.50 −46.92 appears twice: the within-tile grouping split one source).
  It is a much better review list, not a candidate list.
- Separately, `Lbol_pre_est` should use a colour-dependent bolometric correction (W1+W2 dust-dominated for
  W1−W2 > 0.5). The "IC 342 #1 1.4×10⁶ L☉" and "NGC 2976 1.1×10⁶ L☉" figures in the brief are artefacts of the
  photospheric correction.

## 5. Novelty and literature

- **TNS.** I queried the run's cached per-galaxy cones (all status ok) for objects within 60" of every lead.
  - Only SN 2012A (49.9" from NGC 3239 #33), AT 2026dvq (22.8" from M81 #9), AT 2022gyw (55" from M101 #19) and a
    2024 M33 nova turned up. None is a match.
  - No new TNS requests were made.
- **Gaia alerts.** The full alerts.csv (27,077 alerts) has nothing within 2' of any lead.
- **SPIRITS** (Kasliwal et al. 2017; Jencson et al. 2017-2019; Karambelkar et al. 2019 variables; Oskinova et al.
  2018 list of 85 transients): no event within 5" of any lead. NGC 55, NGC 3239 and UGCA 127 were never observed;
  NGC 2976 only 2014-16.
- **WISE transient papers by De et al.**
  - The WTP pipeline paper is still "in prep."
  - The published WTP objects (WTP19aalnxx, WTP14adbjsh, WTP20aabowt, and Galactic novae) are elsewhere.
  - The 17 delayed-IR SNe in arXiv 2405.14663 are ZTF Bright Transient Survey objects at z ≈ 0.01-0.07.
  - No WTP name or paper covers any lead.
- **ATel.** astronomerstelegram.org blocked the literature agent's IP after a few requests, so ATel coverage rests
  on web-search excerpts and the ATels cited in SPIRITS papers. **A manual ATel search for NGC 3239, NGC 4945, M81
  and NGC 55 is still owed before any announcement.**

## 6. Corrections owed to the README's full-run section

1. Replace "SN 2011dh (M51) and SN 2014J (M82) … are under investigation (masking)" with: 2014J is masked by the
   unWISE bright-star bits around M82's nucleus (92% of M82's W1 light is masked; the SN is at S/N 116 in forced
   photometry); 2011dh is unmasked but below threshold after the 2011-13 gap.
2. State the masked area and light fractions (§3.3), and that 6 of 33 non-nova benchmarks fall on masked pixels.
3. The leads paragraph:
   - NGC 4945, M81 and NGC 55 are real, IR-only, unreported events (cases).
   - IC 342 #1 is a pre-2004 luminous fade, not a failed-SN candidate.
   - NGC 2976 #5 is a probable AGN.
   - The M31/M33 faders are AGB stars or AGN.
   - **Add NGC 3239 156.2910 +17.1639** as an obscured transient with an HST counterpart.
4. Note the runner differences from the acceptance tests (UNGC centres, M51's offset, nucleus radii, no companion
   masks) and that `Lbol_pre_est` is photospheric.
5. "N6946-BH1 #65 (behind unidentified M31 and M33 faders)" should say that those faders lose about 2×10³ L☉,
   AGB-level, and that a lost-luminosity floor puts BH1 in the top 10.

## 7. ATLAS tasks queued (difference-image forced photometry, from MJD 57200; not waited on)

| lead | task URL | state at writing |
|---|---|---|
| NGC 4945 196.4697 −49.4162 | https://fallingstar-data.com/forcedphot/queue/5280888/ | done: no optical signal (o ≳ 21.9 at the IR peak) |
| M81 148.7390 +69.1468 | https://fallingstar-data.com/forcedphot/queue/5280889/ | done: flat through 2023-24 |
| NGC 55 3.75575 −39.2033 | https://fallingstar-data.com/forcedphot/queue/5280890/ | done: flat, no trend |
| NGC 3239 156.2910 +17.1639 | https://fallingstar-data.com/forcedphot/queue/5280891/ | running |
| UGCA 127 95.2591 −8.4826 | https://fallingstar-data.com/forcedphot/queue/5280892/ | queued |
| IC 342 56.5658 +68.1491 | https://fallingstar-data.com/forcedphot/queue/5280893/ | queued |

`atlas_fetch.py` picks up finished tasks (it needs `~/.config/oddsky/atlas.env`).

## 8. Files (`reviews/claude-referee-triage-2026-11-01/`)

**Leads**

| file | contents |
|---|---|
| `leads.py` | `leads_*.png`, `leads_lc.csv`, `leads.json` |
| `event_cutouts.py` | `epochs_*.png` (per-epoch difference cutouts) |
| `xmatch.py` | `xmatch.json`: Gaia (ESA, ARI fallback), AllWISE, SIMBAD-Harvard, NED, Milliquas |
| `spitzer_seip.py` | `spitzer_seip.json` |
| `ztf_neowise.py`, `ztf_plot.py` | `ztf_*.csv`, `neowise_*.csv`, `ztf_vs_wise.png` |
| `alerce.sh` | `alerce.txt` (ZTF alert objects) |
| `optical_faders.py` | `optical_faders.json` (LGGS, PS1, ZTF; IRSA timed out on several) |
| `hst_coverage.py` | `hst_coverage.json` |
| `hst_ngc3239.py`, `hst_ngc3239_peak.py` | `hst_ngc3239*.{png,json}`; HAP MVM cutouts from `astroquery.mast.Hapcut`, downloaded to a scratch directory |
| `atlas_submit.py`, `atlas_fetch.py` | `atlas_tasks.json`, `atlas_*.txt`, `atlas_vs_wise.png` |

**Masks**

| file | contents |
|---|---|
| `mask_check.py` | `mask_check.json`, `mask_check_*.png`, `sn_forced_*.csv` |
| `mask_census.py` | `mask_census.csv` |
| `mask_benchmarks.py` | `mask_benchmarks.csv` |
| `mask_light.py` | `mask_light.csv` |

**Ranking**

| file | contents |
|---|---|
| `ranking.py` | `ranking.csv`, `ranking.json` |

**Caveats on services.** The ESA Gaia TAP returned 503 errors intermittently. The ARI fallback rejects `CAST`, so
two M31 positions have Gaia from the pipeline's own 2" match only. IRSA's ZTF service timed out or returned 400s
for several M31/M33 positions. NED reset some connections; those positions are marked ERR in `xmatch.json`.
