## 1. Verdict

Author: claude-referee (ATLAS pass), 2026-10-30. Scripts, logs and figures are in `reviews/claude-referee-atlas-2026-10-30/`
(r1-r11). They run from the repo root with `uv run python`. I reduced ATLAS myself from the raw forced-photometry files
(`oddsky.data.atlas.parse`); I did not import the investigators' scripts. Point-lens fits use the Oddsky tool
`oddsky.analysis.lensing.Problem`. Everything else is my own code or an outside service: Gaia TAP, GOST, ALeRCE, IRSA, TNS,
the KMTNet list and web search.

| | J180624.78-090411.4 | J183040.98-220950.3 |
|---|---|---|
| P(microlensing) | **0.95** | **0.65** |
| P(mundane variable / artifact) | 0.03 | 0.15 |
| P(other, unexplained) | 0.02 | 0.20 |
| one line | ATLAS samples the peak: a symmetric, achromatic point-lens event; the lens beats any flexible symmetric bump; no repeat 2015-2026. | Achromatic, single, centred on the Gaia star, but **not a clean point lens**: tE is unconstrained (77 to >500 d), and the fit needs 80-90% blend light that Gaia does not see. |
| safe public wording | "an apparently unreported microlensing event (peak 2022 Sep 20, tE ≈ 115-150 d)" | "an apparently unreported **microlensing candidate**: an achromatic 2022 brightening of a bulge M giant" (not "event") |

**The Gaia predictions as drafted cannot resolve.** Gaia's scanning law (GOST) puts only **2 transits** in J180624's DR5 window
(2022-08-25..10-15) and **1** in J183040's (2022-08-01..09-30). The grader returns "unresolvable" below 3 points. Both need new
windows (§4). There is a second risk to the J180624 peak prediction: Gaia's own outlier flags may remove the event transits, and
the grader drops flagged points.

## 2. Findings

### 2.1 Re-reduction and robustness (r1, r3, r4, r7)

**My reduction.**
- Cuts: c/o only, err = 0, mag5sig > 17.5.
- A chi/N cut scaled with flux. The investigators' fixed cut is chi/N < 10, and chi/N grows with flux (below).
- Per night, per unit and per band: a 4σ clip, then a weighted mean.
- Baseline at |t − t0| > 400 d, with all data through 2026.
- An error floor from the baseline's excess robust scatter.

I then refitted 18 variants per target, changing one choice at a time: window, chi cut, baseline span, error floor, merged vs
per-unit series, survey subsets, unit subsets, and a PSF-width correction (`r3_variants_*.log`, `r3_summary.log`).

**Problems in the investigators' pipeline.**
1. **The chi/N < 10 cut removes the event preferentially.**
   - J180624: 19.7% of rows within 100 d of the peak vs 2.4% of baseline rows.
   - J183040: 43.5% vs 25.3%.
   - chi/N rises with flux (median 9.4 in J180624's brightest bin), so the cut thins out the peak.
   - Effect on J180624 is small (tE 137 → 141 d). On J183040 it is large: fs 0.14 → 0.03, parallax tE 206 → 572 d.
2. **The baseline sits inside the lens wings.**
   - They use |Δt| > 250 d with the window ending in 2024. At 250 d, J180624's model still has A ≈ 1.08.
   - The southern units (03a/04a) start in 2022, so their baseline is mostly the 2023 wing. Their 2023 seasons read +10-16%
     (J180624) and +4-5% (J183040) above 2025-26.
   - Use ≥ 400 d and include 2025-26.
3. **The rise data in ZTF were dropped.**
   - The "≥ 5 baseline nights" rule removed ZTF r field 1428, the only ZTF data on J180624's rise.
   - Series with no event data were kept, and their fs is meaningless: J180624 ZTF_i_383 has fs = 0.02 (at the bound; 2020 data
     only), and J183040 has ATLAS_c_02a = 1.39 and c_01a.
   - Report fs only for series with ≥ 3 points within 150 d of the peak.
4. **The Gaussian is a straw man.** It has thin wings. A free symmetric Pearson VII (Lorentzian-like) bump with the same
   per-series freedom is the fair test.
   - **J180624:** the lens beats it by Δχ² = 26-50 across variants (e.g. 1111 vs 1161 static).
   - **J183040:** the bump beats every lens fit, by 16-25 with free fs and by 48 with Gaia-consistent blending.
   - A fast-rise/slow-decay (FRED) profile fits far worse than both for both targets: Δχ² ≈ 500 (J183040) and ≈ 4000
     (J180624). My FRED fits ran into a parameter bound, so treat these numbers as indicative.
5. **The error floor is double-counted.** `mad_inv` adds the whole baseline MAD in quadrature on top of the formal errors. In my
   emulation of their pipeline χ²/dof is 0.79, so the profile ranges are too wide in one direction and are not comparable
   across series.

**J180624 survives every choice** (parallax + blend):

| | across 18 variants | investigators' 95% |
|---|---|---|
| t0 | 59841.4-59841.9 (2022 Sep 19-20) | Sep 17-21 |
| tE | 113-153 d static, 113-131 d parallax | 110-133 d |
| u0 | 0.155-0.23 (A_max 4.4-6.5) | 0.17-0.21 |
| fs (ATLAS) | 0.75-0.98 per unit; up to 1.1-1.2 in the merged and southern-only fits (u0 sign flip) | 0.85-0.95 |
| fs (W1) | 0.65-0.73 | ~0.75 |

- The **peak is now observed**: 24-26 ATLAS nights within |u0| tE of t0, plus the decline to +60 d.
- Rise/decline symmetry: separate rise and fall timescales give tE_rise/tE_fall = 0.91-0.95.
- Quote **tE ≈ 115-150 d**. The investigators' 110-133 d understates the systematic spread.

**J183040 does not survive.**
- tE runs from 77 to 764 d and fs from 0.02 to 0.45, depending on choices, and the parallax solutions jump between minima.
- Only t0 (59810-59815, 2022 Aug 15-20), the peak flux ratio (1.55-1.6) and t_eff = |u0| tE ≈ 34-38 d are robust.
- **Blending as a prior (r5, r7b):**
  - Gaia resolves every neighbour. The G = 14.32 M giant should give **97%** of the ATLAS forced flux.
  - The ZTF difference-image centroid of ZTF22aalviwh (38 alerts) lies **0.09″** from that star.
  - Requiring fs ≥ 0.9 costs Δχ² = 78 (static) and 27 (parallax, πE ≈ 0.49).
  - The best lens solutions need fs ≈ 0.1-0.2 in g, r, o, c, W1 and W2 alike. That means 80-90% of the light coming from an
    unresolved companion closer than ~0.3″ with the **same SED from g to W2**. Gaia sees none: RUWE 0.97, ipd_frac_multi_peak 0.
- The light curve has broader wings than any point lens with plausible blending. Their "event residual rms ~2σ" is this misfit.

### 2.2 J180624's 2015-2019 ATLAS drift is instrumental (r1, r2)

**Size of the drift.** Relative to each unit's 2023-26 median:
- c 02a: 0.61 in 2016-17, then 0.91 in 2018.
- o 02a: 0.79, then 0.94 in 2018.
- o 01a: 0.88-0.90 in 2017-19, then 1.01 in 2020.

**Evidence it is instrumental.**
- *It follows PSF width, not time.* Each unit steps up when its own PSF narrows: 02a between 2017 and 2018 (major axis 3.5-4.1 →
  2.1-2.6 px), 01a between 2019 and 2020 (3.1 → 2.4 px). In 2018-19 the two units differ by 5-6% at the same epoch, matching
  their PSF difference. A real change in the star would happen in both units at once.
- *The regression.* Baseline flux against PSF width, with a zero point per unit: **−0.134 ± 0.004 mag/px in o and −0.25 ± 0.02
  in c**, Δχ² = 1868 for 2 parameters.
  - A time-only model is far worse (χ² 2708 vs 1230).
  - After the PSF term, a residual slow trend of ≤ 0.05 mag (2016 → 2020; 6.5 mmag/yr in o) remains.
  - The comparison star J183040, also very red, shows a similar c-band trend: +3.7 ± 1.1 mmag/yr after the PSF term. That
    points to colour-dependent calibration of very red stars.
- *NEOWISE is flat.* W1 2014-2017.3 vs 2018.5-2021 differs by −0.001 ± 0.009 mag, and W2 by −0.005 ± 0.013.
- *Gaia DR3 shows little scatter.* The G-flux scatter is 0.022, at the 91st percentile of 45 stars within 3′ and 0.5 mag
  (median 0.016). That allows at most ~1.5% rms intrinsic variability over 2014.6-2017.4.
- *ZTF has no coverage* before 2019 at this position.

**Does it matter for the lens claim?** No.
- Fits from 2017 or 2015 with a PSF correction give the same t0, tE and u0, within 3 d and 16 d.
- The only consequence is the stated reason. "Likely a template or a moving neighbour" should become "forced-PSF flux depends on
  PSF width (−0.13 mag/px in o) in early 01a/02a data".

### 2.3 Chromaticity (r7b, r8)

**Each band fitted alone** (blend free, so the comparison does not depend on blending):

| target | band | t0 | t_eff | Pearson VII width |
|---|---|---|---|---|
| J180624 | c | 59841.4 [39.7, 43.3] | 24.7 d | 37 d |
| J180624 | o | 59841.7 [41.3, 42.1] | 24.1 d | 35 d |
| J183040 | c | 59809.7 [02.7, 14.3] | 36.6 d | – |
| J183040 | o | 59815.2 [13.3, 17.0] | 34.3 d | – |
| J183040 | ZTF g | 59817.2 [12.4, 23.4] | 37.6 d | – |

- **J180624.** No colour-dependent timing or width.
  - fs is c 0.84-0.98, o 0.79-0.88, ZTF r 0.72, W1/W2 0.68-0.70.
  - Gaia predicts 0.93 in ATLAS and ~0.86 in W1. The resolved neighbours are red (G 18.09 at 6.1″; G 20.15, BP − RP 3.8 at 2.5″),
    so the blend is redder than the source. More unresolved red light in WISE's 6″ beam explains the lower IR fs.
  - Achromatic in the source flux.
- **J183040.** The bluest band peaks first in c, but ZTF g peaks after o, so there is no blue-first pattern. fs is equal in all
  six bands. The amplitude is achromatic from g to W2. Only the blend fraction is unphysical (§2.1).

### 2.4 Alternatives, scored (r5, r9)

**What the sources are.**
- *J180624:* Gaia DR3 GSP-Phot gives a K giant/subgiant (Teff 4770, logg 3.4, A_G 3.56). Its parallax of −0.32 ± 0.13 mas puts
  it beyond ~5 kpc, which contradicts GSP-Phot's 1.26 kpc. Colours: J − K 1.46 (reddened), W1 − W2 −0.13, W2 − W3 0.10.
  **No IR excess.**
- *J183040:* an M giant (ESP-HS type M; J − K 1.28, W1 − W2 −0.17 from CO absorption, W2 − W3 0.22). **No IR excess.** Parallax
  0.04 ± 0.02 mas, so a bulge giant.

**Repeats and periodicity, 2015-2026 (20-day bins, PSF-corrected).**
- J180624: no off-event bin above 1.13 (1.6σ) in o; W1 bin rms 0.015.
- J183040: none above 1.05 in o; W1 rms 0.007. Lomb-Scargle on the ATLAS o baseline finds a best period of 323 d with
  semi-amplitude **1.1%**.
- Gaia DR3 has no vari_* entries for either star.

| alternative | J180624 | J183040 |
|---|---|---|
| Be/shell outburst | excluded: K-type, not B (the colour needs Teff ~4800) | excluded: M giant |
| FUor/EXor | excluded: no IR excess, achromatic, symmetric, FRED Δχ² > 1000 | excluded: no IR excess, achromatic g-W2. ALeRCE's "YSO" comes from its stochastic branch, which has **no microlensing class** |
| classical/slow nova | excluded: 1.8 mag symmetric bump on a giant, achromatic | excluded |
| symbiotic outburst | excluded: blue and fast-rise in the optical, small in W1; here W1 ≈ o | excluded, same reason |
| dwarf nova | excluded: timescale and colour | excluded |
| R CrB recovery | excluded: baseline equal before and after; not a fade | excluded |
| LPV/Mira/SR | excluded: no periodicity, W1 flat to 1.5% | **the label to take seriously, and it fails**: the only period is 1.1% at 323 d, W1 rms 0.7% over 10 yr, and a pulsation would be 3-10× larger in g than in W1, not equal |
| ellipsoidal/eclipse | excluded: a single brightening | excluded |
| artifact (ghost, latent, neighbour) | excluded: 4 ATLAS units + ZTF + NEOWISE agree; ZTF centroid 0.12″ from the Gaia star | excluded: centroid 0.09″ from the Gaia star; 3 surveys |
| non-standard lens (binary lens or source, xallarap, heavy same-colour blend) | not needed | **most likely form if it is a lens** |

J183040's residual 0.20 is the shape problem in §2.1. I cannot name an intrinsic class that gives one achromatic, symmetric
0.5-mag brightening of a quiet M giant in 11 years. That is why the remainder is "unexplained" rather than "mundane".

### 2.5 Parallax and lens physics (r3, r11)

**J180624's parallax is a hint, not a measurement.**
- πE,N is −0.15 to −0.28 and πE,E ≈ −0.01 to −0.02 in 17 of 18 variants.
- Δχ² over the static fit is **4 to 36** (Hawaii units alone: 4). It is a one-dimensional signal, equivalent to the ~8%
  rise/decline asymmetry, and of the same size as the residual ATLAS systematics.

**Mass and distance.** M = μrel tE / (κ πE).
- For πE 0.18-0.27 and μrel 2-7 mas/yr: **M ≈ 0.3-1.7 M☉ at D_L ≈ 1.2-3.6 kpc**.
- For πE ≈ 0.03 (not excluded): **3-10 M☉**.

**Is a dark lens needed?**
- Any main-sequence lens up to 1 M☉ beyond ~2 kpc adds less than 30% of the light, which is consistent with fs. A dark lens is
  neither required nor favoured.
- tE ≈ 130 d is long for the disk but not exceptional.

**No mass is measured** without θE: there is no finite-source signal and no astrometry. Gaia DR5 astrometry may supply θE later.

**J183040.** The Gaia-consistent fit gives πE ≈ 0.49, tE ≈ 100 d, so M ≈ 0.15-0.5 M☉. That fit is itself disfavoured (§2.1).

### 2.6 Novelty (r6, r6b)

**Checked, all negative:**
- **TNS:** cone 60″, HTTP 200 with a valid header, nothing for either target.
- **Gaia Science Alerts:** the full index, 27,076 alerts to the end of observations (2025-01-15). None within 60″; the nearest
  are 0.4° and 0.22° away.
- **KMTNet 2022 public list** (2,803 events): nearest 764′ and 179′. The KMT footprint reaches only l ≤ 8.5°.
- **Investigators' reference tables:**
  - OGLE EWS, nearest of any year: 396′ and 45′ (OGLE-2025-BLG-0118, a different event); nearest 2022 event: 520′ and 129′.
  - Zhai et al.: nearest event 76′ and 137′.
- **Web search** on both ZTF names and on the coordinate and short names: no hits.

**Could not check:**
- MOA 2022: the moaprime alert page serves an empty table for every year, and the old host returns 404. MOA cross-ids in the KMT
  list are nearest at 179′.
- ASAS-SN: the API returns 500 and Sky Patrol returns 404.
- XOSS candidate pages; ATel and ADS full text (I did not redo the investigators' ADS pass).

## 3. Corrections the investigators must make

1. **J180624.**
   - Say the peak is observed by ATLAS, not "unobserved".
   - Quote tE 115-150 d, u0 0.16-0.23, ATLAS fs 0.75-1.0, with a systematic range from reduction choices rather than the 95%
     profile range alone.
   - Call πE "a one-dimensional parallax hint (Δχ² 4-36 depending on reduction)". Make no mass or "dark lens" statement.
2. **J183040.**
   - Withdraw the parameters (tE 76-203 d, fs 0.15-0.45). Report only t0 (2022 Aug 15-20), peak ratio 1.55-1.6 in six bands,
     and t_eff ≈ 35 d.
   - State that a point lens needs ≥ 80% blend light that Gaia does not see, and that a generic symmetric bump fits better.
   - Keep it as a "candidate". Note that ALeRCE's classifier has no microlensing class.
   - Do not plot "source magnification" for it: that axis depends on the degenerate fs.
3. **Pipeline (`hunt_h0008_atlas_fit.py`).**
   - Replace chi/N < 10 with a flux-scaled cut.
   - Baseline at |Δt| ≥ 400 d, including 2025-26.
   - Keep ZTF r 1428.
   - Drop series with no event points, or flag their fs as unconstrained.
   - Fix the double-counted error floor.
   - Compare the lens against a flexible symmetric profile (Pearson VII) and a FRED, not a Gaussian.
4. **Drift wording.** Change "likely a template or a moving neighbour" to "a PSF-width dependence of the forced flux in early
   01a/02a data". Pre-2019 data are usable with that correction.
5. **Gaia predictions.** Rewrite them as in §4 before sealing. Fix or acknowledge the grader's flag handling.

## 4. The Sky Ledger predictions (r10, r10b, r10c)

**How I tested them.** GOST forecast (fetched today, `data/gost_*.csv`):
- J180624: 96 transits over the mission; 50 in the DR4 window (on 33 nights).
- J183040: 140 transits; 89 in the DR4 window (37 nights).

The Monte Carlo puts the lens model through the grader's exact logic: nightly medians, < 3 points = unresolvable, per-transit
noise, 2% outliers of 0.2-1 mag, and 10-20% transit loss.

**Critique of the drafts:**
- **(a) J180624 DR4 no repeat, > −0.3, p 0.85.**
  - Sound in principle, but the only realistic way it fails is a Gaia outlier: P(true) = 0.74-0.76 with a 2% outlier rate.
  - **Fix:** use > −0.5 (P 0.86-0.88) at p 0.85. Or keep −0.3 at p 0.75.
  - resolve_by 2027-12-31.
- **(b) J180624 early − late DR4 median.**
  - Phrase it as window 2014-07-25..2016-06-30 (15 transits, 11 nights), baseline 2018-01-01..2020-01-20 (18 transits,
    13 nights), statistic `median`, op `<`, value **0.1**.
  - What each hypothesis predicts: instrumental drift gives 0.00-0.05; a real drift would give +0.2-0.3 in G.
  - **p 0.90.** Optionally add the mirror prediction, op `>`, value −0.1, at p 0.95.
- **(c) J180624 DR5 2022-08-25..10-15 < −1.0.** **Unresolvable for certain:** only 2 transits (Sep 8, Oct 7).
  - **Fix:** window 2022-02-01..2023-05-31 (13 transits on 10 nights), statistic `brightest`, baseline 2015-01-01..2021-12-31,
    op `<`, value **−1.2**.
  - The model gives ΔG −1.66 to −1.85 on Sep 8 and −1.54 to −1.73 on Oct 7, for fs_G 0.8-1.0. P(true) 0.96-0.99.
  - **But** the grader drops Gaia `variability_flag_g_reject` points, and Gaia's cleaning may flag the 4 event transits among
    96. If so, P → 0 (r10c).
  - Either change the grader to keep variability-rejected points (drop only `rejected_by_photometry`), or state p **0.75**.
  - Add two wing predictions that are immune to that flag, each `median` minus the 2015-2021 baseline < −0.1:
    - 2022-02-01..2022-04-30: model −0.16 to −0.26; p 0.80.
    - 2023-03-01..2023-04-30: model −0.16 to −0.24; p 0.85.
  - resolve_by **2032-12-31**: DR5 is "not before end of 2030".
- **(d) J183040.**
  - *DR4 no repeat (> −0.3):* P 0.76-0.77 with my outlier model; real outliers are rarer at G = 14.3. Use p 0.80, or −0.5 at
    p 0.90.
  - *DR5 2022-08-01..09-30 < −0.3:* **unresolvable for certain**, with 1 transit (Sep 7).
  - **Fix:** window 2022-02-01..2023-05-31, `brightest`, < −0.3. The model gives −0.48 to −0.51 on Sep 7 and −0.35 on Oct 4.
    P 0.95-0.99, or 0.82-0.99 if the event transits are flagged. **p 0.85.**
  - Gaia cannot break J183040's blend degeneracy: an unresolved blend gives Gaia the same flux ratio as ATLAS.

**Gaia's resolution vs ATLAS.**
- J180624 should be at least as bright in G as in ATLAS (fs_G ≈ 0.93-1.0 vs 0.8).
- A G amplitude at Sep 8 well below −1.6 would support fs_G ≈ 1.
- If both stars' DR5 BP and RP amplitudes match on the same transits, that is the cleanest achromaticity test Gaia offers.
  Register them as separate GAIA:BP and GAIA:RP predictions if wanted.

Files: `r1_reduce` (cuts, nightly table, `r1_baseline_*.png`), `r2_drift`, `r3_variants` (18 variants and shapes), `r4_figure`
(`r4_fits.png`), `r5_catalogs`, `r6_novelty`/`r6b_kmt2022`, `r7_fixed_fs`/`r7b_fs_floor`, `r8_chromatic`, `r9_repeats`,
`r10_gaia_predictions`/`r10b_windows`/`r10c_proposed`, `r11_physics`; `data/gost_*.csv`.
