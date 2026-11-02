# H-0012 v2 (h0012b): referee of the new leads (2026-11-02)

Referee: Claude. Scope: the 37 survivors in `work/new_in_h0012b.csv` (in the v2 run, not in h0012a_v2), with the
briefed leads first. Inputs: `work/triage_h0012b*.{csv,json}`, the run outputs in `~/oddsky-runs/h0012b/`, and
public archives (below). Scripts, figures and small outputs are in `reviews/h0012b-referee/`. Downloads (Spitzer and
HST images) are in `~/oddsky-runs/imaging/scratch/h0012b-referee/`. Nothing in the repo was edited, nothing was
committed, and nothing was posted or submitted anywhere (no TNS requests; the cached TNS galaxy cones were used; no
ATLAS jobs were queued).

## Verdicts

| Lead | Verdict | Most likely nature / reason |
|---|---|---|
| **NGC 2403 obs#50** (114.228 +65.598) | **Real. The best new object.** | **Periodic, dust-obscured mid-IR outbursts, P ≈ 5.3 yr.** Peaks in 2007.3 and 2012.4 (Spitzer, found here) and 2017.8 and 2023.2 (WISE; 2017-18 also in Spitzer). The Spitzer variable lies 0.25" from the WISE position. No optical counterpart: HST shows a dust lane, there are no ZTF alerts. Hump amplitude about 5-7×10⁴ L☉ per band at about 700 K. Most likely a periodic dust-forming massive binary (colliding-wind WC or LBV binary). **Case: yes.** |
| **NGC 55 fsn#7** (3.80788 −39.2148) | **Real. Not a failed SN.** | A luminous dusty source that faded ×2.9 (W1) and ×3.5 (W2) from 2010 to 2024, smoothly, with no recovery. Spitzer 2005 is at the 2010 level. The probable counterpart is a blue, luminous star (Gaia G = 20.2, BP−RP = 0.14, M_V ≈ −6.7) that is **still there, unchanged in HST F814W from 2007 to 2024**. Most likely a dusty massive star (sgB[e]/LBV/WR dust-maker) whose circumstellar dust is clearing. A background AGN is not excluded (IRAC colours are in the AGN wedge). **Case: yes, moderate.** |
| NGC 925 obs#37 (36.7552 +33.5748) | **Undecided, leaning real** | Flat for 2010-2022. Then a compact source rises in the last three epochs: W1 at 4-6σ from 2023.0, W2 at 8σ in the final visit (2024.0). The NEOWISE single-exposure catalogue independently shows the brightest W2 of the mission in 2023.6-2024.0 (0.7 mag up). The rise is red (W1−W2 ≈ 1.8) at about 1-3×10⁵ L☉ (9.3 Mpc). It sits in an HII region and is not AT 2023nzt (78" away). A possible onset of an obscured transient at the end of the data; it needs post-2024 IR. |
| NGC 55 fsn#13 (3.7601 −39.2179) | Real, ordinary | Semi-regular variability of a red supergiant (Gaia G = 19.25, BP−RP = 2.9, 1.3" away). W1 is about 30% lower since 2010, with a 2017 bump; W2 is nearly flat. No case. |
| M81 fsn#24 (148.924 +69.0145) | **Artefact / noise** | No source in the reference (negative reference flux). No PSF-shaped residual in any epoch. A small 2010-vs-NEOWISE background step between two bright stars. |
| NGC 2903 obs#75 (143.051 +21.4919) | **Artefact** | A W1-only "step" set by one low 2010 epoch on the bright bulge (HSB pixel; AllWISE halo flags `hhhH`). No compact residual. |
| Circinus fsn#72 (213.312 −65.3369) | **Artefact** | 31" from the saturated Circinus AGN nucleus, in its PSF wings (reference flux −2.3 mJy), with ring residuals. Released-core pixel. The same holds for Circinus fsn#364 and #482. |
| AT 2020nqq (NGC 5128, obs#22) | **Correct recovery** | The WISE peak epoch is 2020-07-08, 11 days after the 2020-06-27 discovery. The previous epoch (2020-01-28) and the whole 2010-2020 baseline are flat. The source is 0.29" from the TNS position. |
| NGC 55 obs#184 (3.79288 −39.2126) | Real, ordinary | A red, dusty variable star: W2 humps in 2014.5 and 2019.3, and Spitzer 4.5 µm fell ×2.9 from 2003 to 2005. The counterpart is red in HST (F814W ≈ 20.4, F160W ≈ 19.8 AB). Dusty AGB star or RSG. No case. |
| NGC 55 obs#299 (3.79834 −39.2132) | Real, ordinary | A red supergiant (Gaia G = 19.8; HST F814W 19.6-19.7 in both 2007 and 2024, F160W 18.6 AB, M_I ≈ −7) with irregular 25% mid-IR variability. No case. |
| Other 27 new survivors | Noise, artefacts, or ordinary stars | See §6. Five NGC 55/M33 "step" sources at var_sig ≈ 2 are noise-level. Three are empty-sky steps like M81 #24 (ESO 274-001 #51, NGC 6946 #71). Two are linear streaks (HIZSS 012 #123, IC 3104 #259). M31 obs#302 and M33 #304/#754 are AGB/RSG-like. The 14 already flagged as moving stars, foreground stars or AGN were spot-checked: the NGC 55 #318/#421 and M33 #516/#698 pairs are opposite-sign partners about 9" apart, so they are moving stars as flagged. |

**Bottom line.** As the brief suspected, most of the new survivors (var_sig ≈ 2) are noise or artefacts. Two are worth cases:

- NGC 2403 obs#50, a periodic dust-obscured outburster with four cycles recovered;
- NGC 55 fsn#7, a fading dusty luminous star.

Neither is a failed-supernova candidate. NGC 925 obs#37 (a late rise, independently seen in NEOWISE single exposures)
needs post-2024 infrared data.

## 1. NGC 2403 obs#50: a periodic, dust-obscured infrared outburster

Figures: `lead_NGC2403_obs50.png`, `epochs_NGC2403_obs50.png`, `spitzer_ngc2403.png`, `hst_ngc2403.png`.

**WISE.** The light curve shows two humps, in both bands and both visit seasons:

- 2017.2-2018.8, peaking at 2017.8: W1 +170, W2 +355 µJy;
- 2022.8-2023.8, peaking at 2023.2: W2 +300 µJy;
- plus a +115 µJy W2 tail in 2014.3.

Between the humps the source sits at a flat minimum. The per-epoch difference stamps show a compact PSF at the position at 8-9σ against local empirical noise (`stamps.json`). Other numbers:

- W1−W2 of the hump light ≈ 1.4 (about 700 K dust).
- Peak νLν ≈ 4.8×10⁴ L☉ (W1) and 7.4×10⁴ L☉ (W2) at 3.2 Mpc.
- The position is 21" from the nucleus. The source was inside h0012a's 68" nucleus circle and is new only because v2 restored the 15" acceptance-test radius.

**Spitzer: two earlier cycles (`spitzer_ngc2403.py`).** NGC 2403 has IRAC imaging at about 40 epochs from 2004 to 2019 (SINGS, SN 2004dj monitoring, SEEDS, the Kochanek and Thompson dusty-star programmes, SPIRITS). I resampled every post-BCD mosaic onto a common grid and took differences against the median, measured in a 2.4" aperture. The 4.5 µm change against the median, in µJy:

| epoch | [4.5] change (µJy) | | epoch | [4.5] change (µJy) |
|---|---|---|---|---|
| 2004.8-2005.8 | −68 to −85 (minimum) | | 2014.4-2016.1 | −24 to −87 (minimum) |
| 2006.22 | −2 | | 2017.03 | +86 |
| 2006.82 | +158 | | **2018.03** | **+243** |
| **2007.25** | **+235** | | 2018.47 | +148 |
| 2007.88 | +177 to +193 | | 2019.18 | +32 |
| 2008.27 | +88 to +94 | | 2019.5 | −17 to −22 |
| 2011.90 | +95 ± 31 | | | |
| **2012.45** | **+232** | | | |
| 2014.0 | +13 to +18 | | | |

[3.6] tracks [4.5] at about 60% of the amplitude (peaks +148, +163, +127 µJy). Errors are 5-12 µJy, from the same aperture
at 12 positions 10" away.

- **Peaks fall at 2007.25, 2012.45, 2017.5-2018.0 and 2023.2 (WISE).** That is a period of 5.3 ± 0.1 yr (about 1,940 d). The 2017-18 peak is seen by both observatories.
- The rise is fast: 2006.2 → 2006.8 goes from −2 to +158 µJy. The decline is slower, over about 1-1.5 yr, to a flat minimum.
- The variable's centroid in the bright-minus-faint Spitzer image is 0.23" (3.6 µm) and 0.25" (4.5 µm) from the WISE position. It is a clean, isolated point source in that image (`spitzer_ngc2403.png`).

**No optical counterpart.**
- HST (ACS 2004/2005/2019, WFC3 2018, WFC3/IR 2010): the 1" circle falls on a dark dust lane. The two near-IR-brightest sources within 1.5" are faint.
  - Source 0 (0.96" away): F814W = 23.08 / 23.13 / 23.12 / 23.12 AB in 2004 / 2005 / 2018 / 2019, i.e. constant.
  - Source 1 (0.68" away): F814W = 23.82 / 23.97 / 24.21 / 23.99. It is faintest in 2018.4, which is on the IR hump (Spitzer [4.5] +148 µJy). That is a 0.3-0.4 mag dip, but it comes from a different camera (WFC3 against ACS), so it is only suggestive of dust obscuration at the IR maximum.
  - So any optical counterpart is fainter than about M_I ≈ −4.5 to −5.
- No ZTF alert object within 5" (ALeRCE, `alerce.txt`). Gaia: nothing within 4.6".
- SIMBAD: star clusters at 3.2" and beyond. TNS: nothing within 50" (AT 2019aabm is 51" away; 1954J/V12 is 120" away).
- The SPIRITS long-period-variable catalogue (Karambelkar et al. 2019) has nothing within 10". It only fits periods below about 1,000 d.

**What it is.** A strictly periodic (four cycles), fast-rise / slow-decline, about 700 K dust outburst of about 10⁵ L☉, from a source that is optically invisible. Candidates:

- **Periodic dust formation in a colliding-wind massive binary** (WR 140-like, WC + O, dust forming at each periastron). The shape and period fit, but the amplitude is about 10× WR 140's, so the system is very luminous or is an LBV binary (an η Car-like 5.5-yr cycle is a tempting comparison, but no more than that).
- **An extreme AGB / OH-IR star** is less likely. Periods above 1,900 d are extremely rare, Mira curves are not fast-rise/flat-minimum, and 7×10⁴ L☉ in one band exceeds an AGB star's total output.
- **Not a foreground star:** b = +29°, and nothing appears in HST or Gaia.

**Caveats.**
- The Spitzer light curve is aperture photometry on resampled mosaics. It has not been PSF-fitted, and the cryogenic and warm-mission calibrations are mixed. The timing is robust; the amplitudes are approximate (±20%).
- Kochanek's group targeted dusty luminous stars in NGC 2403 with Spitzer (Khan et al.). This source may already be catalogued there as a variable, so **a literature check (ADS full text) is owed before any novelty claim.**

**Follow-up.**
- Fit PSFs to the SPIRITS/IRAC data for a precise period and colour.
- Optical and near-IR spectroscopy is impossible if A_V is very large, so try JWST/NIRSpec, or MIRI for the dust features (WC dust shows a featureless continuum; AGB dust shows silicate or SiC).
- SPHEREx monitoring.
- The ephemeris predicts the next peak at about **2028.5**.

## 2. NGC 55 fsn#7: a fading dusty luminous star, not a failed supernova

Figures: `lead_NGC55_fsn7.png`, `epochs_NGC55_fsn7.png`, `hst_ngc55.png`, `spitzer_ngc55.png`.

**WISE.**
- A smooth, decelerating decline in both bands and both seasons. W1 goes from 740 to 251 µJy (absolute PSF flux, 2010.4 → 2024.4) and W2 from 1,675 to 456 µJy.
- No recovery and no zig-zag (roughness 0.81). var_sig 14.4; delta_neo −35σ (W1) and −53σ (W2).
- The per-epoch stamps show a clean PSF: positive against the median reference before 2018, negative after. The neighbours (obs#184, #299) are 28-43" away.
- The faded light has W1−W2 ≈ 1.6, i.e. about 650-700 K dust. The W1 and W2 fractions lost are similar (66% and 73%), so the dust's colour hardly changed while it faded.
- νLν in 2010: 9×10⁴ L☉ (W1) and 1.6×10⁵ L☉ (W2) at 2.13 Mpc.
- The source lay inside h0012a's misplaced 89" nucleus circle (UNGC centre 193" off), so it is new in v2 because of the centre correction, not the core unmasking.

**Spitzer 2005-12 (cryogenic; the 2003 mosaic does not cover it).**
- 2.4"-aperture photometry gives [3.6] = 965 and [4.5] = 1,727 µJy.
- SEIP (3.8" aperture) gives 4.5 / 5.8 / 8.0 µm = 1,813 / 3,031 / 5,346 µJy.
- [4.5] in 2005 equals W2 in mid-2010 (1,675 µJy) to within 3%. **The source was steady at its 2010 level for 4.5 years, then faded.**
- The SED rises to 8 µm (cool dust, plus some PAH from the surroundings), so L_IR ≳ 3×10⁵ L☉ in 2005-10.
- IRAC colours: [3.6]−[4.5] = 1.12 and [5.8]−[8.0] = 1.25. That is inside the Stern et al. (2005) AGN wedge, where dust-enshrouded stars also fall.

**Optical counterpart (HST, `hst_ngc55.py`).**
- Gaia DR3 4997972666905659392 is 0.20" from the WISE position: G = 20.18, BP−RP = 0.14, no significant parallax.
- In HST it is the dominant point source within 1". WFPC2/PC 2007-08 (F606W, F814W) and WFC3 2024-07 (F555W, F814W, F110W, F160W) show nothing else bright and red there.
- Same 0.2" aperture, uncorrected AB:
  - F814W 21.20 (2007) → 21.10 (2024), so constant to about 0.1 mag while the mid-IR fell ×3;
  - F606W 20.72 (2007) and F555W 20.15 (2024), i.e. very blue;
  - F110W 21.22, F160W 20.92: a mild near-IR excess for a hot star.
- M_V ≈ −6.7 before any internal extinction, i.e. L_* ≈ 2-4×10⁵ L☉ for an OB supergiant.
- The neighbourhood holds massive stars (Castro et al. 2008): an Ofpe/WN9 star 9.5" away, O9 If 5" away, F5 I 4.4" away. None of them is this star.

**What it is.**
- **Not a failed supernova.** The star is still there at the same optical brightness, and the mid-IR fade is of dust, not of a photosphere.
- The infrared roughly equals the star's luminosity, but the star is optically bright and blue. That needs non-spherical dust: a disk, as in sgB[e] stars, or an LBV/WR dust shell seen through a gap.
- A factor-3 mid-IR fade over a decade at almost constant dust colour fits dust dissipating or dispersing after an earlier dust-forming episode (an LBV or WR dust maker), or the end of a B[e]-type mass-loss phase.
- **Background AGN:** not excluded, but disfavoured.
  - For it: the IRAC wedge colours, and a factor-3 decline is possible for AGN.
  - Against it: a coincident blue point source at 0.2" that is steady to 0.1 mag over 17 years (quasars usually vary more), and the dust colour stays at about 700 K rather than the 1,200-1,500 K of a torus.
- Not in SIMBAD (within 4"), TNS (within 30": AT 2022kms is 30.6" away) or SPIRITS (NGC 55 was never observed).

**Follow-up.**
- An optical spectrum of the G = 20.2 star: B[e]/LBV emission lines versus a quasar redshift. It is southern, so VLT/MUSE or SALT.
- An ADS check.
- SPHEREx or JWST spectra of the dust.
- **Case: yes, moderate.** It is a clean example of a mid-IR "vanishing" source that is not a vanishing star, which matters as a false-positive class for the failed-SN search.

## 3. NGC 925 obs#37: a late rise, undecided

Figures: `lead_NGC925_obs37.png`, `epochs_NGC925_obs37.png`.

- **Light curve.** Within ±25 µJy of zero from 2010 to 2022. Then W1 +32/+50 µJy in 2023 and +52 in 2024.0; W2 +55 in 2023.6 and **+150 ± 15 in 2024.0**. Against local empirical noise (16 offset apertures in the same difference image): W1 4.4-5.6σ in each of 2023.0, 2023.6 and 2024.0, and W2 8.3σ in 2024.0. The stamps show a compact positive source at the position in the last epoch.
- **Other numbers.** The rise has W1−W2 ≈ 1.8 (about 550 K). νLν(W2) ≈ 2.6×10⁵ L☉ at 9.29 Mpc.
- **Why it is new.** It was an h0012a candidate (0.2" away) classed `not-variable`. v2 re-classified it; it is not a core-unmasking product.
- **Context.**
  - It sits in an HII region ([VSH98] 2.7"). SEIP shows a pre-existing IR source: 127 / 177 / 467 / 1,089 µJy at 3.6-8 µm, i.e. PAH emission.
  - No Gaia source within 6". No ZTF alert object within 5". TNS: nothing near (AT 2023nzt, the LRN, is 78" away; AT 2024ts is far).
  - HST has nothing after 2010.
- **Caution.** The other NGC 925 candidates also read high in the final visit: their median change in 2024.0 is +42 (W1) and +57 µJy (W2). Those are bright variables, though, and a few-percent zero-point error on them would explain it. That cannot make +150 µJy on a 160 µJy (W2) source. Still, two-thirds of the evidence is the final short visit.
- **Independent check: the NEOWISE-R single-exposure catalogue** (IRSA `neowiser_p1bs_psd`, 3.96" cone; `neowise_ngc925.csv`, `neowise_ngc925_visits.txt`).
  - These are L1b profile fits, independent of the unWISE coadds and of our differencing. The blend with the HII region is included.
  - W2 per-visit medians are 14.2-15.0 (typically 14.5 ± 0.2) for 2014-2023.0, then **14.11 in 2023.60 and 13.82 in 2024.03**: the brightest visit of the mission, 0.7 mag above the median.
  - W1 2024.03 is 14.78 against a typical 15.05 ± 0.2.
  - So the W2 rise is confirmed independently at about 3σ against the visit-to-visit scatter. **This leans real.**
- **Follow-up.**
  - ZTF/ATLAS forced photometry over 2022-2025 (the referee did not queue ATLAS: no submissions).
  - SPHEREx 2025-26.
  - If it keeps rising, it is an obscured transient or an LRN precursor, a sibling of AT 2023nzt in the same galaxy.

## 4. The briefed artefacts

- **M81 fsn#24.**
  - The reference PSF flux is −128 / −95 µJy (W1/W2): there is no source, and the background is oversubtracted between two bright stars 25-60" away, whose residuals dominate the stacks.
  - Per-epoch PSF amplitudes are within ±1σ of local empirical noise in every NEOWISE epoch. Only the two 2010 W2 epochs reach +3σ.
  - The "step-down" is therefore a 2010-vs-NEOWISE offset of the local background (cryogenic-era PSF wings and background), measured where nothing sits.
  - W1 is `not-variable`. var_sig is 1.95.
  - ESO 274-001 fsn#51 and NGC 6946 fsn#71 are the same pattern: empty sky with negative reference flux, a W1-only 2010 offset, var_sig 1.6-1.7.
  - **Suggested triage rule:** demote step classes where the reference PSF flux is ≤ 0 in both bands.
- **NGC 2903 obs#75.**
  - The W1 "step-up" (+70-100 µJy, W2 none) rests on the 2010 epochs. The 2010.86 W1 epoch is −4.4σ by local noise; every NEOWISE epoch is within ±2.3σ.
  - The pixel is high-surface-brightness bulge (reference 745 µJy within the PSF). It sits 1.3" from an AllWISE source flagged `hhhH` (halo contamination) and about 40" from a nucleus that leaves a strong dipole residual.
  - L_up = 2.2×10⁵ L☉ with no W2 counterpart and no point source is not physical. This is galaxy-light systematics.
- **Circinus fsn#72 (and fsn#364, #482).**
  - The position is 31" east of the Circinus nucleus. The nucleus is a W1 ≈ 5-6 mag Seyfert 2, saturated, with a reference peak of 9.5×10⁴ nmgy per pixel.
  - The reference flux at the lead is −2.3 mJy (W1) and −1.5 mJy (W2), deep in the PSF wings. The difference images show ring residuals around the core.
  - The W2 decline with a season zig-zag is the core's wing changing between builds and seasons.
  - These are released-core pixels (mask code 80: HSB plus low-confidence).
  - **Suggested rule:** keep a saturated AGN or nucleus core's wings masked, or demote candidates whose reference flux is strongly negative.

## 5. AT 2020nqq: a correct recovery

| epoch (tile header) | W1 change (µJy) | W2 change (µJy) |
|---|---|---|
| 2010-2019 (19 epochs) | within ±30 | within ±40 |
| 2020-01-28 | +25 ± 15 | +39 ± 24 |
| **2020-07-08** (MJD 59038) | **+3,792 ± 15** | **+5,918 ± 30** |
| 2021-01-30 | +324 | +562 |
| 2021-07-07 | +117 | +385 |
| 2022-01-27 | +31 | +167 |
| 2022-07 | +32 | +133 |

- **Timing.** TNS gives discovery on 2020-06-27 (17.8 mag). The WISE peak epoch is +11 d after it, and the last WISE non-detection is 2020-01-28. The dates are tile-header midpoints; as the OS-0030 check found, the per-source exposure mean can differ by a few days. That does not change the conclusion.
- **Position.** 0.29" from TNS.
- **Peak.** νLν ≈ 1.5×10⁶ (W1) and 1.7×10⁶ L☉ (W2) at 3.75 Mpc. W1−W2 = 1.1 at +11 d. That is very red for a hot ILRT photosphere, so warm (pre-existing or newly heated) dust is already present.
- **Decline.** Slow in W2: still +130 µJy two years later.
- **Nothing else explains it.** A Gaia foreground star (G = 17.65, parallax/error = 5) is 2.1" away and is constant. The 2010-2020 baseline is flat, so there is no pre-outburst brightening above about 30 µJy (≈ 1.2×10⁴ L☉ in W1).
- **This is a genuine gain of the core release.** In h0012a the position sat under the geometric spike bits 29-30. JWST imaged the position in 2026 (programme 12496), so others are following it.

## 6. The other new survivors

- **Noise-level steps in crowded NGC 55: fsn#64, #90, #111 and obs#187.** var_sig 1.8-2.2; steps of 30-60 µJy at 4-6σ in the stacked statistic only. No compact residual in the stacks. 6-11 other candidates lie within 60". No case.
- **Moving or foreground stars and AGN, as flagged:**
  - NGC 55 fsn#203, #318 + obs#421 (a pair 9" apart), and obs#575;
  - NGC 253 fsn#226; M33 fsn#516 + obs#698 (a pair 8.6" apart); M51 fsn#518; NGC 4945 obs#176;
  - NGC 4236 obs#459; NGC 2683 obs#520; NGC 5128 obs#853 (a high-proper-motion Gaia star);
  - Circinus fsn#364 and #482 (Gaia stars, and in the core wings);
  - NGC 4945 fsn#525 (AGN).
- **HIZSS 012 obs#123 and IC 3104 obs#259:** linear streaks cross the position in the stacked differences. These are artefacts at low latitude and in the far south.
- **IC 3104 obs#283:** a +30 µJy W1 step on a faint source, with large-scale structure in the difference images. Noise.
- **M31 obs#302:** a real, smooth W1/W2 rise of +150/+220 µJy from 2016 to 2024 (2.6×10³ L☉), next to the carbon-star candidate PSO J010.5541+40.8954. AGB-like. No case.
- **M33 fsn#304 and obs#754:** an RSG/AGB star (Gaia BP−RP = 3.4) with a 10-15% fade and wiggles, and a source 0.4" from the known variable D33 J013348.8+303841.0. No case.

## 7. What v2's core unmasking gained

`why_new.py` (→ `why_new.csv`) asks why each of the 37 new survivors is new:

| reason | n | what they are |
|---|---|---|
| inside h0012a's wrong or oversized nucleus circles (NGC 55 centre 193" off; M33 radius 150" → 40"; NGC 2403 68" → 15") | 10 | **NGC 2403 obs#50 and NGC 55 fsn#7, the two real leads**; 4 ordinary NGC 55 stars or noise; 4 M33 AGB stars or moving stars |
| on released bright-star footprints (low-confidence core pixels) | 5 | **AT 2020nqq (a genuine recovery)**; 3 Circinus core-wing artefacts; 1 AGB-like M31 source |
| new search area from the NGC 55 recentring (≥ 1,350" from the old centre) | 4 | a faint step and three moving stars |
| the same source was an h0012a candidate (≤ 1.5"; one at 6.7") and v2 re-classified it | 11 | NGC 925 obs#37 (undecided), NGC 2903 obs#75 (artefact), moving stars, noise |
| other new detections (threshold and noise-calibration changes) | 7 | M81 #24 and ESO 274-001 #51 (empty-sky steps), two streaks, two moving stars, one noise source |

**Assessment.** The headline gains are modest but real, and they mostly do not come from the unWISE core release:

- **Core release.** It added one benchmark (AT 2020nqq: recovery 19/105 against 18/105, and the obscured top 31 holding 14 known objects against 13). It also lets recall photometry measure SN 2014J (18.8σ) and SN 2016adj (40σ), which still are not blind candidates. It contributed no new unknown astrophysical lead. Its other survivors are three artefacts in the wings of the saturated Circinus AGN, which shows that released pixels next to a saturated core need a negative-reference-flux or wing veto.
- **The two real new leads come from the geometry fixes.** The corrected NGC 55 centre and the acceptance-test nucleus radii for NGC 2403 and M33 had blanked 1-2' around each centre in h0012a.
- **Ranking changes.** The new step classes and ranking surfaced re-classified sources. Of these, one is undecided (NGC 925) and the rest are artefacts or noise.
- **The empty-sky step-down class needs a veto.** M81 #24 is the briefed example: reference flux ≤ 0, var_sig < 2, and a W1-only 2010 offset (3 of the 37).

In short: 37 new survivors gave 1 known-transient recovery, 2 real unknowns worth cases (neither a failed SN), 1 undecided, about 6 ordinary variable stars, and about 27 noise, artefacts or flagged foreground objects.

## 8. Files (`reviews/h0012b-referee/`)

| script | outputs |
|---|---|
| `inspect_leads.py` | `lead_<lead>.png` (light curves, aligned and raw per season; reference, late−early, event and NEO−early stamps; neighbours), `leads.json`, `leads_lc.csv` |
| `epoch_stamps.py` | `epochs_<lead>.png` (per-epoch W1/W2 difference stamps), `stamps.json` (PSF amplitude against local empirical noise per epoch) |
| `archives.py` | `archives.json`: SEIP, AllWISE, Gaia DR3 (6"), SIMBAD (CfA, 10"), MAST HST/JWST coverage |
| `spitzer_ngc55.py` | `spitzer_ngc55.json/.png` (IRAC 2005 photometry; 2003 does not cover fsn#7) |
| `spitzer_ngc2403.py` | `spitzer_ngc2403.json/.png` (IRAC 2004-2019 light curve and position of obs#50) |
| `hst_ngc55.py`, `hapcut_ngc55.py`, `hst_ngc55_fetch.py`, `hst_list.py` | `hst_ngc55.json/.png` (WFPC2 2007 against WFC3 2024; HLA fitscut cutouts) |
| `hst_ngc2403.py` | `hst_ngc2403.json/.png` |
| `last_epoch_null.py` | the NGC 925 last-visit comparison |
| `why_new.py` | `why_new.csv` |
| `alerce.sh` | `alerce.txt` (ZTF alert objects) |
| (IRSA TAP by hand) | `neowise_ngc925.csv`, `neowise_ngc925_visits.txt` (NEOWISE-R single exposures at NGC 925 obs#37) |
| `vizier_all.py` | all-catalogue VizieR query; failed (IDIA, CfA and CDS returned 502 / timed out) |

**Caveats on services.**
- The IRSA SEIP TAP reset several connections. Three positions were retried by hand (`~/oddsky-runs/imaging/scratch/h0012b-referee/seip_retry.txt`).
- VizieR all-catalogue searches failed on every mirror, so only targeted catalogues were checked (SPIRITS LPVs).
- No ADS search was possible: there is no token on this machine. **An ADS full-text check is owed for NGC 2403 obs#50 and NGC 55 fsn#7** before either is called unreported.

## Addendum (2026-11-02): literature and catalogue check of the two real leads

Done after the report, with the ADS token (`h0012b-referee/ads_novelty_h0012b.py`, `ads_novelty_h0012b.json`) and the VizieR
mirror at vizier.idia.ac.za.

- **NGC 2403 obs#50 (Spitzer position 114.22807 +65.59806): apparently unreported.**
  - ADS full text for the coordinates in five formats: only unrelated matches.
  - NGC 2403 topic searches turned up the SPIRITS dust-forming WC binaries (Lau et al. 2021; Rose et al. 2026, SPIRITS 19q).
    SIMBAD places SPIRITS 19q at 114.3259 +65.5636 (2.7′ away) and SPIRITS 16df at 114.2420 +65.6233 (1.5′ away), so neither is
    this source. The same mechanism (an eccentric colliding-wind WC binary forming dust each periastron) is the leading
    interpretation here, and P ≈ 5.3 yr fits that class.
  - Khan, Stanek & Kochanek 2013/2015 (η Car analogues): their nearest candidate, [KSK2013] N 2403 5, is 5.6″ away, and the
    Spitzer variable is good to about 0.3″, so they are different sources. No match within 3″ in J/ApJ/767/52, J/ApJ/799/187,
    the SPIRITS catalogue J/ApJ/839/88, Gaia DR3 or AllWISE.
  - SIMBAD within 15″: star clusters, SNRs and an X-ray source at ≥ 3.2″, none coincident.
- **NGC 55 fsn#7: no literature on the source.**
  - ADS coordinate searches: only unrelated matches.
  - Gaia DR3 4997972666905659392 lies 0.20″ away (the blue star of the report). AllWISE J001513.88-391251.4 lies 1.8″ away and
    is blended.
