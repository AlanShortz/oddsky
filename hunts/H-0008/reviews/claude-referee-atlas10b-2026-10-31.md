## 1. Verdict

Author: claude-referee (atlas10b pass), 2026-10-31. Scripts, logs and figures are in `reviews/claude-referee-atlas10b-2026-10-31/`
(r1-r13, run from the repo root with `uv run python`). I reduced both ATLAS files myself from the raw forced photometry
(`oddsky.data.atlas.parse`) and did not import the investigators' scripts. The fits are in **excess flux** (`fitlib.py`, copied
from the previous referee pass and extended with a blend-fraction floor). The magnification and parallax geometry come from
`oddsky.analysis.lensing`. I also used outside services: the Gaia scanning law (GOST), the live OGLE EWS 2022, KMTNet 2022 and
MOA 2022 pages, the Gaia alerts list, TNS (paced), SIMBAD (CfA), VizieR (idia mirror) and web search.

| star | verdict | P(microlensing) | P(mundane) | P(other / unexplained) | safe public wording |
|---|---|---|---|---|---|
| **J175634.35-205556.9** (G 15.24, l 8.15, b +1.96) | **lens candidate (strong)** | 0.75 | 0.07 | 0.18 | "an apparently unreported short microlensing candidate: a smooth, symmetric ×6 brightening of a bulge red giant peaking on 2022 Mar 25 (tE ≈ 10-14 d). It was equally bright in ATLAS c and o and in NEOWISE W1 and W2, and nothing like it happened in 2015-2026." |
| **J174744.42-374630.7** (G 13.84, l 352.66, b −4.95) | **inconclusive, leaning lens** (a lens fits only with annual parallax) | 0.40 | 0.30 | 0.30 | "a single, year-long ×2 brightening of a bulge M giant in 2021-22, equal in the optical and the infrared at its peak. A point lens fits only with annual parallax (tE ≈ 90-130 d), and the rise fell in the seasonal gap. Not classified." |

Robust parameters, and only these, should be quoted:

- **J175634.** t0 = MJD 59663.0 (2022 Mar 25.0, ±0.5 d). The peak falls in a 4.1-day gap between ATLAS nights (Mar 23.3 at ×5.95,
  Mar 27.4 at ×4.7). tE 9.5-13 d (Δχ² < 4, blending free), or 12.5-14 d with Gaia's blend prior. u0 0.08-0.15, so A_max 7-14, but
  the maximum itself was not observed. The source supplies essentially all the light (fs ≈ 1.0-1.2 in c, o, W1 and W2 alike). Annual
  parallax is not constrained.
- **J174744.** The peak is observed: a plateau at ×2.0-2.07 from 2022 Mar 9 to Apr 7. The event spans roughly 2021 Aug-Sep
  (×1.04) to 2022 Oct (×1.0). Neither the static lens nor a free-blend lens is physical. With physical blending (fs ≤ 1, as Gaia
  requires) a parallax lens gives tE 92-127 d across reductions (89-112 d at Δχ² < 4 in the default), |u0| 0.36-0.53 and |πE|
  0.23-0.39. These numbers are conditional on the lens hypothesis.

**What the first pass got wrong:**

1. **J175634's parallax solution is a blending degeneracy, not parallax.** It gave tE 92 d, u0 0.02 and fs 0.07. In my reduction
   tE fixed at 92.5 d costs Δχ² ≈ 400 for a static lens. With parallax it still costs Δχ² ≈ 40, and only with an unphysical
   |πE| ≈ 5. It needs the source to supply only 8-9% of the light, while Gaia puts 91% of the ATLAS flux on the target. With
   |πE| ≤ 1, parallax improves the static fit by only Δχ² 2 (tE 11.2 d). The static tE ≈ 11 d was right (r6, r9, r13).
2. **The fs values at the bounds belong to series with no event data.** In the first pass, J175634's c 02a (1.5), c 04a (0.02) and
   o 02a (1.5) sat at the bounds. c 02a has no night in the event, c 04a has none within 30 d of it, and o 02a has one wing night.
   In series that *do* sample the event, fs is constrained and consistent with Gaia.
3. **J174744's first-pass lens fits are unphysical.** Their fs values sit at the 1.5 bound because the light curve wants fs ≫ 1:
   my free static fit runs to u0 = 3 with fs ≈ 60. With fs ≤ 1, a static lens **loses** to an asymmetric Pearson VII bump by
   Δχ² ≈ 140. Only annual parallax rescues the lens.
4. **J174744's "brightening from ~2021 Oct" was not observed.** The rise from ×1.08 (2021 Oct 16) to ×1.85 (2022 Feb 6) falls in
   the solar-conjunction gap. The Hawaii units (01a, 02a) hold the only 2021 data, and a "≥ 3 nights within 150 d of the peak"
   rule drops them. I keep them (250 d).

**Why no survey reported them.**

- **OGLE was not observing.** It stopped on 2020 Mar 18 and resumed on 2022 Aug 12 (COVID-19). Both events peaked in March 2022.
  OGLE has catalogued variables 10″ (J175634) and 32″ (J174744) from these stars, so both lie in OGLE-IV fields. The local list
  and the live EWS 2022 page have no OGLE-2022 event before June, except one long event.
- **KMTNet does not cover them.** J175634 is just beyond the edge of KMT field BLG38: no KMT event in 2016-24 lies within 35′, and
  the 2022 events in that area all have l ≤ 7.53. J174744 (l −7.34) is outside the KMT footprint: the nearest event is 88′ away and
  the 2022 events reach only l −6.83.
- **Gaia.** For J174744, Gaia transited only at ΔG ≈ −0.75, below its ~1-mag alert threshold. **For J175634, GOST puts a Gaia
  transit at 2022 Mar 25 00:11 UT, at t0, when the lens model predicts ΔG ≈ −2.1 to −2.8.** There is no Gaia alert. This is the
  main open point for J175634; see §2.6.
- **MOA is unchecked.** The 2022 alert page returns an empty table.

## 2. Findings

### 2.1 Re-reduction (r1, r2, r11)

**Cuts and nightly binning.**
- Cuts: c and o only, err = 0, duJy > 0, mag5sig > 17.5.
- chi/N cut scaled with flux.
- Nightly per-unit weighted means (southern units binned by local night) with a 4σ clip. The error is the larger of the formal
  error and scatter/√n.
- Baseline |Δt| > 400 d through 2026. The error floor is the baseline's excess robust scatter.

**A fixed chi/N < 10 cut would remove the events.** chi/N grows with flux (04a: 110-170 at the peak). The cut removes 94% (J175634)
and 92% (J174744) of rows within 100 d of the peak, against 68% and 42% of baseline rows. In the "chi<10" fit variants the
J175634 peak disappears entirely. The investigators used no chi cut, which is fine.

**Baselines and zero points (r1, r3).**
- Both baselines are clearly detected and positive in both bands:
  - J175634: o 3300 uJy (15.10 AB), c 870 uJy.
  - J174744: o 12,040 uJy (13.70 AB), c 3120 uJy.
- So ratios are legitimate here, unlike J191120/J075219 in the last pass.
- The crude Gaia estimate o ≈ (G+RP)/2 gives 0.64 (J175634) and 0.65 (J174744) for the ATLAS/Gaia ratio. The factor is the same
  for two stars of the same colour (BP−RP 2.83-2.84), which points to the colour transform rather than a sky bias.
- The units agree to 2-4% in o: J175634 3258-3436 uJy; J174744 11,863-12,143 uJy.

**PSF width (r1).**
- J175634's baseline rises 8%/px with PSF major axis in both bands, the crowding signature: neighbours within the PSF.
- It explains the 2016 02a points at ×1.1-1.2 (major axis 4.3 px) and the 01a 2017-19 seasons at ×1.05-1.08.
- On the peak nights (04a, major axis 1.9-2.0 px) the bias is −3%, negligible against ×6.
- J174744: +3.2%/px in o, none in c.

**Frames on J175634's event nights (r2).**
- Every night from −13 to +25 d has 2-5 frames at 1-4 detector positions. The frame-to-frame scatter is 0.3-2.4%, at 0.5-2.8× the
  formal error.
- PSF, mag5sig and sky are normal for the season.
- The peak night (Mar 23, 04a) has 4 frames at 3 positions reading 19,758-20,043 uJy.
- The rise is seen by 01a, 03a and 04a, the decline by 04a and 03a (c), and the tail by 02a (+23 d, ×1.12, 8σ). So all four units
  and both bands see it.
- No satellite, ghost or bad frame. Multi-night, so not an asteroid.

**Saturation (r2).**
- **J175634 at the peak (o 13.15 AB): no sign of saturation.** Within a night, flux falls with PSF width (−10 ± 2%/px), the
  opposite of saturation. NEOWISE at −4.1 d agrees with ATLAS (below).
- **J174744 (o 13.70 baseline, 12.90 at the peak): at most mild non-linearity.**
  - On the peak nights, narrow-PSF frames read slightly low (+11 ± 4%/px against +1 ± 2%/px in the baseline), a 2.4σ hint.
  - But the nightly o excess at the peak is *larger* than c's (c doesn't saturate at 14.5), and o equals W1 and W2 at the peak
    (2.06 vs 2.06/2.08).
  - So any compression of the nightly peak is at the few-% level.

**Repeats, 2015-2026 (r11).** 20-d bins, PSF-corrected:
- J175634: the largest off-event bin is ×1.048 in o (2.2σ) and ×1.07 in c (2.9σ, 3 nights in 2016). No repeat.
- J174744: no repeat of ×2. It does show 2017 o bins at ×1.06-1.07 (3.4-3.9σ in 01a and 02a; PSF-corrected) and Gaia DR3 G scatter at the 73rd
  percentile, so this M giant has low-level (~5%) variability, as luminous bulge giants usually do.
- NEOWISE (20-21 visits, 2014-2024; r7) is flat to 0.02 mag (J175634) and 0.01 mag (J174744) outside the event.

### 2.2 Fits (r6: 13 reduction variants per star; r9 profiles; r13)

**Method.** Every model gets the same per-series freedom: an amplitude per series, solved exactly. The models are: static and
parallax point lens; a lens with separate rise and fall tE; Pearson VII, symmetric and asymmetric; a Norris FRED; and a nova-like
exponential rise with a power-law decline. As in the last pass, the non-lens χ² of the "fs<=1" variant are inflated by the cap
bookkeeping (it also caps the bump amplitudes); I compare against the uncapped non-lens fits of the same data.

**J175634 (r6, r9, r13).**

| | value |
|---|---|
| static lens (default) | χ² 1110.4 (n 834); t0 59663.00, tE 11.1 d, u0 0.118, fs: c 03a 1.20, o 01a/03a/04a 1.15-1.19, W1 1.14, W2 1.22 |
| tE profile, blending free | Δχ² < 1 for 10.5-12.4 d; < 4 for 9.5-13 d; tE 7 / 16 / 30 / 92 d cost 32 / 18 / 113 / **403** |
| Gaia blend prior 0.8 ≤ fs ≤ 1 | costs Δχ² 2.5; tE 12.5 (12-14), u0 0.093, A_max 10.8 |
| u0 profile | Δχ² < 4 for 0.08-0.15 (A_max 7-13) |
| symmetry | tE_rise/tE_fall = 1.08-1.09; asymmetric PV7 widths 2.52 / 2.42 d |
| lens − best bump | lens better by Δχ² 16-23 in 10 of 13 variants (e.g. 1110 vs PV7 1128); FRED worse by > 700, nova shape by ~100 |
| exceptions | chi<10 (the peak is cut: no preference); ±600-d window (the static lens loses to an asymmetric PV7 by 33 and the parallax fit wins only with |πE| at the bound of 5, which is unphysical: the short baseline span (400-600 d) leaves too few baseline nights to set the error floor) |
| parallax | runs to the |πE| = 5 bound in every variant (Δχ² 2.5-3); **not constrained**, as expected for tE ≈ 11 d |

- Every event night lies within 1.5σ of the static lens (r12 figure, residual panel), including the slow early rise (−13 to −5 d)
  that the symmetric bump misses by about 2σ.
- The only robust numbers are t0, tE ≈ 10-14 d, and fs ≈ 1 in every band.
- A_max is model-dependent: the peak falls in a 4.1-day gap.

**J174744 (r6, r9).** The Hawaii units are kept (ev_dt 250 d).

| | χ² (n 832) | notes |
|---|---|---|
| static lens, free blending | 1493.7 | u0 → 3 (bound), fs ≈ 60: unphysical |
| parallax lens, free blending | 1374.6 | fs ≈ 6 or runs to u0 = 3: unphysical |
| static lens, fs ≤ 1 | 1553.1 | tE 124, u0 0.53; rises too early (overpredicts 2021 Aug-Oct) |
| **parallax lens, fs ≤ 1** | **1379.1** | t0 59648.0 (2022 Mar 11), tE 96.6, u0 −0.53, πE (N +0.22, E +0.21), fs o 0.94, c 0.84-0.98, W1 0.98 (Gaia: 0.98 / 0.95) |
| asymmetric PV7 | 1414.9 | rise width 124 d, fall 175 d: rises faster than it declines |
| FRED / symmetric PV7 | 1432 / 1474 | |

Across variants (r9), the parallax lens with fs ≤ 1 against the best bump:

| variant | Δχ² (bump − lens) | tE | \|πE\| |
|---|---|---|---|
| most variants | +26 to +56 | 92-127 d | 0.23-0.39 |
| o only | +14.5 | | |
| chi<10 (removes most event nights) | +2.9 | | |

- tE profile: Δχ² < 4 for 89-112 d. tE 80 / 150 d cost 44 / 18.
- So **with physical blending the lens case rests entirely on annual parallax**. The rise is in the seasonal gap.
- χ²/dof is 1.7, with structured ±4σ residuals in the decline (r12).
- This is the same situation as J173150 in the last pass, but with a weaker margin and an unobserved rise.

### 2.3 Chromaticity (r7, r8)

The discriminating tests are blue against red and optical against infrared. W1 = W2 alone is not a test (both stars have
W1−W2 ≈ −0.1).

**J175634: achromatic from c to W2.**

| test | result | for comparison |
|---|---|---|
| ATLAS c night at +5.8 d | fractional excess 2.08 ± 0.03 vs o interpolated 2.12 (log) to 2.54 (linear): c/o 0.82-0.98. Excess colour Δc/Δo = 0.26 vs the baseline's 0.267 | a flat-F_ν (hot) addition would give c/o ≈ 3.8; a hot source behind the same dust (A_V ~ 3) still ~1.5-2.5× c's share |
| NEOWISE visit, 2022 Mar 19 (−4.1 d) | W1 ×2.224, W2 ×2.310 vs ATLAS o interpolated ×2.25 (bracketed by ×1.90 at −1.1 d and ×2.88 at +1.4 d) | |
| fitted fs per band | c 1.20, o 1.15-1.19, W1 1.14, W2 1.22: one blend fraction from 0.5 to 4.6 µm | |

The added light has the giant's colour (o−W1 ≈ 2.3 AB). That rules out hot additions: CV/dwarf-nova disc, nova, flare, Be disc.

**J174744: achromatic between o and the infrared at the peak, mildly chromatic in c.**

- *Optical vs infrared.* W1 ×2.057 and W2 ×2.079 against o ×2.06 at +1.3 d. In the wings: W1 ×1.037 at −199 d (lens 1.03), and W1
  and W2 ×1.152 at +165 d (lens 1.14, ATLAS o 1.04-1.11).
- *c vs o (r8).* The c/o fractional-excess ratio (a lens predicts a constant ~1.04 from the fitted fs):

  | phase | c/o ratio |
  |---|---|
  | −9 d | 0.74 |
  | +13 d | 0.92-0.94 |
  | +104 to +137 d | 1.1-1.4 |
  | +155 to +168 d | 0.7-0.9 |

- These departures are 2-4× the c baseline scatter (1.5-4% of the baseline). They are not monotonic, so I cannot call them a
  temperature trend, but they are not clean either.
- An LPV-type pulsation would give c amplitude ≫ o ≫ W1. The equal o and W1 at the peak excludes that.

### 2.4 The stars and the alternatives (r3, r11)

**What the stars are.**

| | J175634 | J174744 |
|---|---|---|
| Gaia DR3 | G 15.24, BP−RP 2.83, ϖ 0.107 ± 0.031, RUWE 0.99, IPD multi-peak 0, not variable-flagged; no vari_* entry | G 13.84, BP−RP 2.84, ϖ 0.087 ± 0.021, RUWE 0.87, not flagged; no vari_* entry |
| near-IR / mid-IR | 2MASS J−K 1.36, H−K 0.34; W1−W2 −0.10 (CO absorption): a reddened K/M giant at bulge distance (M_K ≈ −4.5) | J−K 1.38; W1−W2 −0.13; K−W3 0.13 (no excess), W4 8.3 ± 0.23 (≤ 3σ); a luminous bulge M giant (M_K ≈ −5.5) |
| Gaia classifications | GSP-Phot's "Teff 15,000 K, A_G 5.4, 2.4 kpc" is the hot-and-reddened degeneracy: it contradicts the parallax (ϖ would be 0.42) and the giant colours | ESP spectral-type field "M" |
| AllWISE flags | **ccf "ddhd"**: spike/halo flags from a bright neighbour (VSX LPVs G 12.4-12.8 at 50-67″); W3/W4 unreliable. The NEOWISE event visit has rchi 6 and ccfrac 0.56, both typical of this star's quiet visits | clean (ccf 000d) |
| Gaia neighbours | 1 within 2″ (G 19.25), 3 within 4″; Gaia-only share of the ATLAS forced flux 0.91 | 0 within 2″, 5 within 4″ (G ≥ 18.7); share 0.98 |
| DR3 G scatter (2014.6-17.4) | 43rd percentile | 73rd percentile |

**Scored alternatives.**

| alternative | J175634 | J174744 |
|---|---|---|
| CV / dwarf nova | **no.** A bulge-distance DN outburst is 3-4 mag too faint. A foreground one (~1 kpc) is still ~8× too faint and blue. The excess is red and the same in c, o, W1 and W2. | no (year-long, achromatic) |
| flare | no (2 weeks, symmetric, red) | no |
| nova | no (symmetric; nova shape worse by Δχ² ≈ 100; excess colour = giant's) | no |
| Be star | no colour or IR evidence (no H−K or W1−W2 excess) | no (M giant, CO absorption) |
| YSO | no (no IR excess; b = +2° but no SIMBAD/YSO association) | no (K−W3 0.13, b −5°) |
| LPV / semi-regular / LSP | no: 2-week symmetric event, no repeat; pulsation is strongly chromatic | **main mundane alternative**: a luminous M giant with ~5% low-level variability; but a single ×2 in 11 years with equal o and W1 at the peak is not LPV-like (LPV amplitude c ≫ o ≫ W1) |
| R CrB recovery | – | no (a brightening above a constant level, not a recovery from a dip) |
| symbiotic outburst | no (hot component) | no: a hot component would raise c far more than W1 |
| artifact | no: 4 units, 3-4 positions per night, NEOWISE simultaneous | no: 4 units, NEOWISE 3 visits |
| short point lens | **fits all nights within 1.5σ**; tE 10-14 d is ordinary for the bulge | – |
| binary lens / caustic crossing | cannot be excluded: the peak falls in a 4-day gap. The sampled rise and fall are smooth and point-lens-like | – |
| long blended lens | – | requires annual parallax; physical blending (fs 0.94-0.98) agrees with Gaia |

### 2.5 Novelty (r4, r5, r5b, web)

**Local reference lists (r4).**
- Nothing within 1′ of either star.
- J175634, nearest events:
  - OGLE: 2015-BLG-0765 (8.0′), 2015-BLG-0598 (9.8′), 2023-BLG-1081 (9.8′).
  - KMT: 2024-BLG-1445 (35.5′), 2022-BLG-0441 (38.6′).
  - Gaia DR3 ML: 100′. OGLE GVS: 94′. ZTF: 65′.
- J174744, nearest events: OGLE 24′ (2015 and 2025); KMT 85′; Gaia DR3 ML 66′.
- No event of any list within 30′ of either star had t0 in 2022.

**OGLE EWS 2022 (live page, 359 events, the same as the local list).**
- Event numbers 0001-0003 have tmax in July-August 2022. Only one event (0325) has tmax before June (Mar 5, a long event).
- The nearest 2022 events are 185′ (J175634) and 141′ (J174744).
- OGLE stopped on 2020 Mar 18 and resumed on 2022 Aug 12
  ([arXiv:2404.17715](https://arxiv.org/pdf/2404.17715), [arXiv:2309.06012](https://arxiv.org/pdf/2309.06012),
  [arXiv:2404.16089](https://arxiv.org/pdf/2404.16089), [arXiv:2203.16552](https://arxiv.org/pdf/2203.16552)).
- **J175634's event was over by April 2022, and J174744 was at ×1.1 and fading when OGLE returned.**
- Both stars lie in OGLE-IV fields: OGLE-BLG-ELL-012611 and OGLE-BLG-ECL-198335 are 10.7″ and 11.5″ from J175634, and
  OGLE-BLG-ECL-108727 is 32″ from J174744.
- If OGLE photometry before and after exists, the stars would be I ≈ 13.9 and 12.5 at baseline. J175634 would reach I ≈ 12 at
  peak, near OGLE saturation, but OGLE was not observing then anyway.

**KMTNet 2022 (live page, 2802 events parsed).**
- J175634: the nearest event is 38.6′ away, in field BLG38 (low cadence). All five 2022 events in a ±1.5° box lie at l 6.67-7.53,
  against l 8.15 for the star.
- J174744: the nearest event is 88′ away (BLG37); KMT's 2022 events reach only l −6.83.
- **Both stars are outside or at the very edge of the KMT fields.**

**MOA 2022.** moaprime returns HTTP 200 with an **empty table**, and the old alert-page URL returns 404. **MOA is unchecked.**

**Gaia alerts** (live list and the local index to 2025-01-15): none within 60″ of either star. The nearest are 24′ (J175634) and
18′ (J174744). None within 60′ in 2022.

**Other catalogues and searches.**
- **TNS** 60″ cone (HTTP 200, valid CSV header, 30-s pacing, no 429s): none for either star.
- **SIMBAD (CfA)** 30″: J175634 has only the two OGLE variables at 10.7″ and 11.4″; J174744 has nothing.
- **VSX** (idia mirror) 120″: neither target. The nearest entries are the OGLE variables above and Gaia LPV candidates at
  ≥ 50″ / ≥ 68″.
- **ASAS-SN variables (II/366)**: none within 120″.
- **Gaia DR3 vari_summary, vari_classifier and vari_long_period_variable**: none.
- **Web search** on the 2MASS, Gaia DR3 and AllWISE names: no hits.

### 2.6 Gaia's scanning law: a test for each star (r10)

**J175634.** GOST predicts FOV transits on 2022 Feb 25 (−25 d), **2022 Mar 25 00:11 UT** and Apr 18 (+26 d).

- The Mar 25 transit is a single transit (FOV2 only) at t0 (MJD 59663.007).
- The point lens predicts A ≈ 8.5 (free fs) to 10.8 (Gaia prior). With fs_G 0.8-1.2 that is **ΔG ≈ −2.1 to −2.8**. Even the
  model-free interpolation of the ATLAS nights gives ×5.4 (ΔG −1.8).
- There is no Gaia alert. Possible reasons (inference, untested):
  - dead time, which GOST does not model;
  - the alert pipeline's treatment of a single isolated transit;
  - crowded-field filtering in the bulge.
- Gaia DR4's epoch photometry ends in January 2020, so **only DR5 can test this**.

**J174744.** GOST predicts transits at −16 d and +12 d (model ×2.0, ΔG −0.74 to −0.77; below the alert threshold) and in the
decline on 2022 Sep 2 (ΔG −0.13) and Oct 3 (−0.08).

**Suggested sealed predictions** (both for DR5):
- J175634 brighter than its median by more than 1.5 mag on the 2022 Mar 25.0 transit, if that transit exists.
- J174744 brighter by 0.6-0.9 mag on 2022 Feb 28 and Mar 28, and by 0.05-0.2 mag on Sep 2 and Oct 3.

## 3. Corrections the investigators must make

1. **J175634.**
   - Withdraw the parallax solution (tE 92.5 d, u0 0.02, fs 0.07). It is the high-magnification blending degeneracy:
     - Δχ² ≈ 400 worse without parallax;
     - Δχ² ≈ 40 worse even with |πE| ≈ 5;
     - Gaia also excludes it (fs ≥ 0.8).
   - Quote the static lens: t0 2022 Mar 25.0, tE ≈ 10-14 d, u0 0.08-0.15. Say the peak itself fell in a 4-day gap (A_max not
     measured; 7-14) and that parallax is unconstrained.
   - Do not report fs for c 02a, c 04a or o 02a (no event data). In the series that sample the event, fs ≈ 1.0-1.2 in c, o, W1 and
     W2, consistent with Gaia's 0.91.
   - Use "sharp, symmetric ×6, about four weeks above ×1.2 and a few days above ×3". Do not use "lasting ~2 weeks" for the whole
     event.
   - Add the achromaticity evidence: c at +5.8 d, and W1/W2 at −4.1 d equal to o. That is what excludes CV, nova and flare.
2. **J174744.**
   - Do not quote the first-pass lens fits. Their fs at 1.5 means the light curve wants fs ≫ 1.
   - Say: a static lens with physical blending loses to an asymmetric bump (Δχ² ≈ 140); a parallax lens with fs ≈ 0.95 wins by
     Δχ² 15-56 (tE ≈ 90-130 d, |πE| ≈ 0.3).
   - The rise (2021 Oct-2022 Feb) was not observed.
   - Note the mild, non-monotonic c/o chromaticity and the star's ~5% low-level variability.
   - Wording: "unclassified, parallax-dependent", not "lens candidate (strong)".
3. **Both.**
   - "Neither matches the reference lists" should be followed by the reason. OGLE was paused from 2020 Mar to 2022 Aug 12, and both
     events are outside or at the edge of the KMT fields. "Apparently unreported" is then the strongest statement allowed, with MOA
     unchecked.
4. **Pipeline (`hunt_h0008_atlas10.py`).**
   - Nights are floor(MJD), which splits South African nights at 0h UT.
   - There is no per-night clip, and the nightly error is formal only.
   - Series with no event nights are fitted and their fs reported.
   - The "max ratio elsewhere" (1.17 / 1.15) comes from the 99.5th percentile of single nights, including the wide-PSF 2016 data.
     My PSF-corrected 20-d bins give 1.048 / 1.073.

## 4. What remains unchecked

- **MOA 2022.** The alert page is empty and was not checked.
- **ASAS-SN Sky Patrol light curves.** J174744 (V ≈ 15.5, peak ≈ 14.7) may be within reach; J175634 at peak (V ≈ 15) too.
- **OGLE photometry** of the 2010-2020 and 2022-2025 baselines, and **VVV/VIRAC2** Ks light curves. Both stars are probably
  saturated in VVV.
- **Gaia DR5** epoch photometry at the GOST transits above; this is the decisive test for J175634.
- **ADS full text.**
- **Spectra.** None exist. A spectrum would settle the source type and distance, and could reveal symbiotic or emission features
  that the colours argue against.
- **A binary-lens search for J175634.** Its peak is unsampled, so a caustic crossing cannot be excluded or modelled from these data.
- **Exposure-level NEOWISE.** The 2022 Mar 19 visit of J175634 is −4.1 d before t0, where the lens predicts a rise of about 15% per
  day. An intra-visit slope in single exposures would be a further check.

Files:

| script | what it does |
|---|---|
| `r1_reduce` (+ `r1b_overview.png`) | cuts, yearly baselines, PSF slopes, event nights |
| `r2_frames` | frames and saturation |
| `r3_catalogs` | Gaia DR3, neighbours, AllWISE/2MASS, VSX |
| `r4_novelty_local` | local reference lists |
| `r5_online`, `r5b_kmt2022` | TNS, SIMBAD, OGLE/KMT/MOA 2022 pages, Gaia alerts |
| `r6_fits` (+ `data/r6_*.json`, `data/r6_*_series.csv`) | 13 variants per star |
| `r7_neowise` | NEOWISE visits against ATLAS |
| `r8_chromatic` | c against o |
| `r9_profiles` | tE/u0/t0 profiles; J174744 parallax lens with physical blending across variants |
| `r10_gost` (+ `data/gost_*.xml`) | Gaia scanning law |
| `r11_repeats` | repeats, 2015-2026 |
| `r12_figure` (`r12_lightcurves.png`) | figure and model predictions at Gaia and NEOWISE epochs |
| `r13_firstpass_check` | the first-pass parallax solution |
