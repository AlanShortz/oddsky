# Referee report: Gaia20cdd (Gaia DR3 1624711296862985472)

Author: claude-referee, 2026-10-28. Mandate: docs/REFEREE.md. I did not modify the repo. I wrote my scripts, downloads and
intermediate tables to `cdd/referee/` (scripts in `cdd/referee/scripts/`, downloads in `dl_*`). All of this work is
outside the Oddsky tools: pandas/numpy on archive CSVs, plus my own permutation tests. There is no case ledger, so the
citations below are to files, not to call ids.

## 1. Verdict

The dimming is real and belongs to the target. It is not an instrument, neighbour or catalogue artefact. But the
**392.2-day clock does not survive**:
- Data from before 2016, which the case did not fetch (CRTS 2006-2016, Pan-STARRS 2010-2014), contain three more deep
  minima (1.62, 1.33 and ≥1.2 mag). They fall at phases −0.12, −0.44 and −0.48, so a deep event at "phase 0.5" breaks
  the primary/secondary picture.
- Once those minima are included, P = 392.2 d is no better than its half, ~196 d. The ~196-d grid is itself only
  marginal once the post-hoc choices are counted (MC 0.7% before those choices), and it leaves ≥9 well-sampled cycles
  with no dip.
- The star is also not new as a variable: VSX lists it (NL/VY:, Otero 2020) and so does ATLAS-VAR (2018).
- The dimming is not "nearly grey": W1 dropped 0.42 mag while i dropped 3.07 mag.

Probability that the mundane reading is correct: **~0.85**. That reading is an old K dwarf with warm circumstellar dust,
occulted aperiodically or quasi-periodically: a field "main-sequence dipper", not a clock. Probability that the specific
392.2-d ephemeris is real: ≲0.1. Probability that the dimming is instrumental or caused by a blend: <0.01.

## 2. Attacks and results

### 2.1 Period and aliases (fatal for the claim as stated)

**Re-derived from the case's four minima.** 57787, 58971, 59751, 60926 give rms 2.8 d at P = 392.3 d. P/2 = 196.1 d fits
equally well (rms 2.8 d), and nothing else in 150-1300 d comes close (`scripts/period.py`).

**Trial factor.** Monte Carlo with 4 random epochs over MJD 57700-61000:
- Scanning only 300-500 d gives FAP = 0.23%, which reproduces the case's 0.25%.
- Scanning 150-1300 d gives FAP = **2.5%**.

That is before counting the other free choices: which dips count as "deep" (0.74 mag in 2023 and 0.8 mag in 2019 were
excluded), what a "minimum" means, and permission to skip cycles.

**Timing precision is illusory.** The 2017 minimum is one Gaia point, with neighbours 34 d before and 25 d after. Moving
it by ±8-15 d changes the rms from 1.0 to 6.7 d.

**Untapped data falsify the primary/secondary picture.** These are ≥1-mag minima the case did not use:

| date | MJD | depth | source | phase at 392.2 d |
|---|---|---|---|---|
| 2007-04-24 | 54210 | 1.62 mag | CRTS, 4 points in one night | −0.12 (47 d early) |
| 2011-03-29/31 | 55651-55653 | 1.33 mag | CRTS, confirmed by PS1 z +1.17 | **0.56** |
| 2014-06 | 56808-56818 | 0.90 / +1.2 / +0.67 mag | CRTS / PS1 r / PS1 i | **0.50-0.52** |

The 2014 event is part of a complex lasting ~280 d (MJD 56775 → ~57060; Gaia still +0.25 in Nov 2014 and Feb 2015).
Deep events therefore occur at "phase 0.5". With all 7 ≥1-mag minima from 2007-2025, the best period anywhere in
150-1300 d has rms 15 d, and random epochs do that well 10% of the time.

**P/2 is the better clock, and still not established.** I used all 11 ≥0.5-mag minima from 2007-2025 (54210, 55402,
55652, 56814, 57595, 57787, 58768, 58971, 59751, 60127, 60926):
- At P ≈ 195.5-196.1 d, 8 of the 11 fall within ±8 d of one grid.
- Drawing 11 epochs from the actual observing nights, scanning 150-1300 d, gives MC P = 0.7% (N = 600;
  `scripts/perm2.py`, `perm_W8.txt`). The window, threshold and event set were chosen after looking, so the real
  significance is a few percent.
- The 2007 minimum is 47 d off the grid, and the 2011 minimum is 22 d off.
- Well-sampled 196-d cycles with no dip: n = 3, 4, 8, 14 (ZTF, 10-25 nights each); n = 1, 2, 7 (Gaia/ZTF); n = −7
  (CRTS, 6 nights); and others. More than half of the covered cycles are empty.

The case's "secondaries at phase 0.5" are exactly what the 196-d alias predicts. Calling P = 392.2 d the period, with
"primaries" and "secondaries", is an interpretation the data do not prefer.

**Episode durations are incompatible with a single orbiting occulter at either period.** Several dimming complexes last
230-300 d, longer than 196 d and ~70% of 392 d:
- 2014-05 → 2015-03
- 2016-10 → 2017-07
- 2019-08 → 2020-06: one continuous episode. ZTF shows g still 0.15-0.35 mag faint throughout Dec 2019-Mar 2020, so the
  "2019" and "2020" episodes are a single event.
- 2025-02 → 2025-10+: ≥225 d. ZTF is 0.1-0.3 mag faint from MJD 60723 onward.

The events also span <1 d to ~300 d. On MJD 60127, g faded 1.12 mag and recovered in about 6 h, while the nights before
and after were normal. A random-onset dipper behaves like this; a clock does not.

**Unfalsifiable as stated.** If cycles may be skipped, a null on 2026 Nov 14 falsifies nothing. The P/2 grid point of
2026-04-29 (MJD 61121) has already passed. ATLAS data, being fetched elsewhere, have not arrived; they should be checked
for that date.

**Annual systematics: attack failed.** The deep minima fall in Feb, May, Jun and Sep. They drift through the calendar,
so they do not track a season.

### 2.2 Instrument artefacts (claim survives)

- **ZTF single quadrant.** I re-fetched the raw ZTF data with all columns (`dl_ztf/ztf_raw.csv`, 3933 rows). 3884 rows
  come from one quadrant (field 824, CCD 3, quadrant 1), so a per-quadrant test is weak. However, field 1829 (CCD 11,
  quadrants 3/4, an independent detector) records g = 2.52 mag deep on MJD 59770, when field 824 shows 2.6.
- **ZTF diagnostics.** In-dip versus out-of-dip medians agree: airmass 1.20 vs 1.23, chi 0.83 vs 0.76, magzprms 0.027
  vs 0.027, limitmag 21.1 vs 21.0. The out-of-dip depth correlates with airmass at r = 0.10.
- **ZTF flags.** catflags = 32768 rows (375) were excluded by the case. They are not concentrated in the dips.
- **The 1-night dips are real.** MJD 60127 has five measurements in g/r/i over 6 h with normal chi, sharp and
  zero-points, recovering in time order. MJD 59690 has 3 bands. Neither is an artefact.
- **Gaia.** Every dip in the Gaia alert data is seen in both FoV transits. A G = 13.6 star 16" away cannot dim a
  G = 16.3 window by 0.85-2 mag. The 2010-2015 dips are seen independently by CRTS and PS1.
- **TESS.** I did not re-run TESScut; the TESS evidence adds nothing beyond ZTF, which resolves 16" easily. Its
  consistency is noted below.

### 2.3 Blends and neighbours (claim survives)

**Gaia neighbours** within 45": the G 19.23 star at 13.7" and the G 13.58 star at 16.1". Neither can supply a 3.5-mag
dip in 2" ZTF PSF photometry.

**NEOWISE single exposures** (MJD 59749-59752, `neowiser_p1bs_psd`):
- The target is detected in about 50 frames at 0.03-1.0" from its position, at W1 = 14.60-14.95, with W1 14.79 in the
  frame paired with the 59750.34 visit.
- The 15.6-mag W1 neighbour is separately detected at 12-14" (the AllWISE source 13" away).
- The W1 0.42-mag dimming is therefore robust and on-target.

**TESS.** The S24 and S52 drops coincide in time with the ZTF dips and are consistent with the expected dilution: the
target is ~10-25% of its pixel. This is consistent, not independent localization.

`tess_pix_cdd.py` has a copy-paste docstring naming Gaia20fmb's neighbour (2900506490050064384, 21"). The code queries
the correct neighbour, 1624712052777229824.

### 2.4 "No X" claims (two claims fail)

**"Nearly grey": wrong.**
- At the deep minimum on MJD 59750 the depths are g/r/i 3.49/3.26/3.07. Meanwhile NEOWISE W1 dimmed only 0.42 mag and
  W2 about 0.2 mag, so A_W1/A_i ≈ 0.14. That is ISM-like chromaticity into the infrared.
- In shallow states the reddening is strong:

| MJD | g/r/i depth (mag) | A_g/A_i |
|---|---|---|
| 58767 | 0.71/0.50/0.42 | ≈1.7 |
| 58971 | 1.41/1.18/0.84 | ≈1.7 |

  In the 2025 low state, g ≈ 0.25 while r ≈ 0.13.
- Only the deepest points look grey (g/i 1.14). That is the usual sign of partial covering or a scattered-light floor
  in a dust occultation, not of an opaque body.

**"No dip" at cycles n = 1, 2, 4, 7: correct but misleading.** Those nulls are real. But the case never checked
2006-2015, where the period predicts nothing and deep dips occur.

**"No other designations / nothing found": wrong.** See 2.6.

### 2.5 Physical self-consistency and known classes

**A dwarf, confirmed.**
- Parallax 0.624 ± 0.035 (18σ), RUWE 0.95.
- Gaia MSC: logg 4.6-4.8, Teff 5100-5380 K, distance 1663 pc.
- SDSS 2004: u-g 1.71, g-r 0.71, r-i 0.26.
- 2MASS J-K 0.47.
- Galactic velocity: |v − v_LSR| ≥ 70 km/s for any RV between −100 and +100 km/s, at z = 1.09 kpc. Thick disk and old.

**DR3 summary values are biased.** The DR3 mean photometry includes the 2016-17 episode: phot_g_mean_flux_over_error is
59.6, roughly 20-30× below normal for G = 16.3. The out-of-dip G is ≈16.13, so M_G ≈ 5.1, not 5.3. The DR3 BP-RP of
1.18 is also biased red. Missing GSP-Phot is plausibly a consequence of that variability.

**Classes excluded:**

| class | why excluded |
|---|---|
| CV / VY Scl (the VSX type) | GALEX AIS NUV 22.79 ± 0.31 with no FUV, which is photospheric for a K1V; ESP-ELS Hα EW 0.09 ± 0.11 nm (no emission); u-g normal |
| R CrB, background giant | parallax and logg |
| RS CVn spots | cannot reach 3.5 mag |
| rigid eclipsing binary | depth varies from 0 to 3.5 mag and cycles are skipped |
| YSO dipper | location and kinematics |

**Warm dust is present, which the case missed.**
- AllWISE W1-W2 = 0.23 ± 0.04, about 6σ redder than a K dwarf (≈ −0.03).
- W3 = 12.61 at 4.8σ, about 1.6 mag above the photosphere.
- Fitting both gives T ≈ 500 K and L_IR/L* of order 10⁻².
- The 6-h, 0.8-mag egress on MJD 60127 needs a transverse speed of ≳26 km/s, which puts the occulter within ~1 AU.

All of this points to dust clumps in the inner system of an old K dwarf. Comparable cases are ASASSN-21qj-type collision
debris and the ZTF main-sequence dippers (Tzanidakis et al. 2025, arXiv:2508.03964).

### 2.6 Novelty (the claim of no prior designation fails)

**SIMBAD: still unreachable today.** Both CDS hosts time out, and so does the main VizieR host. The VizieR mirror at
vizier.china-vo.org works, and VSX works at vsx.aavso.org (www.aavso.org is behind Cloudflare).

**VSX:** Gaia20cdd, OID 1543994, AAVSO UID 000-BNM-472. Type **NL/VY:**, range 16.0-17.7 CV, entered by S. Otero on
2020-05-08 ("Range from CRTS data"). Aliases: CSS_J162053.8+592622 and GALEX J162053.9+592622.

**ATLAS-VAR** (Heinze et al. 2018, J/AJ/156/241): ATO J245.2240+59.4395, class "dubious", P(LPV) = 0.85.

**Literature:** none found. Web search on Gaia20cdd, AT2020jem and the CSS/SDSS names returned no papers, and the star
is not in the visible part of the Tzanidakis 2025 table (the machine-readable table was not checked).

Conclusion: the variability has been catalogued since 2018/2020 and mistyped. The correct nature (dusty-dipper K dwarf)
appears unpublished.

### 2.7 Untapped data (fetched)

- **CRTS** 2006-2016: 187 points (`dl_crts/crts.csv`).
- **PS1 DR2 detections** 2010-2014: 81 points (`ps1_det.csv`).
- **SDSS** 2004 photometry.
- **GALEX** AIS.
- **2MASS** 1999: J 14.82, which is normal brightness.
- **Gaia DR3** astrophysical_parameters.
- **NEOWISE** single exposures.
- **LAMOST** DR9/DR10: no spectrum.
- **SDSS spectra:** none.
- **ASAS-SN Sky Patrol:** unavailable (client error). It would in any case be blended with the 13.6-mag star.
- **TESS sectors not used by the case:** 15, 18, 19, 21, 22, 41, 48-50, 56-59, 75-86. Sectors 75-86 give near-continuous
  coverage of 2024, which tests the P/2 grid points 60336 and 60532 and short dips.
- **ATLAS** (`gsa/lc/Gaia20cdd_atlas.csv`): had not appeared when this report was written.

## 3. Most plausible mundane explanation remaining

An old (thick-disk) K1-2 dwarf with warm (~500 K) circumstellar dust. Dust clumps or streams within ~1 AU occult it on
timescales from <1 d to ~300 d, and the shallow states show ISM-like reddening.

Recurrence is irregular. There may be a weak preference for ~196-d spacing, which would fit dust orbiting at ~0.6 AU
(P = 196 d around 0.8 M☉ means a ≈ 0.61 AU, T_eq ≈ 280-500 K). This is a known (if rare) class: field main-sequence
dippers and collisional-debris occultations. It is interesting, but it is not a clock.

## 4. Required wording changes

| item | change |
|---|---|
| **Title/hook** | Drop "on a 392.2-day clock" and "predicts 2026 November 14". Suggested: "An old K dwarf with warm dust that has dimmed by up to 3.5 mag at least ten times since 2007." |
| **"Five nearly grey dimming episodes 2016-2025"** | Replace with "≥10 dimming events 2007-2025 (CRTS, PS1, Gaia, ZTF), from <1 d to ~300 d; reddened (A_g/A_i ≈ 1.7) when shallow, greyer only at the deepest points; W1 dimmed 0.42 mag when i dimmed 3.07 mag." |
| **2019 and 2020 episodes** | Merge into one 2019-08 → 2020-06 complex. Likewise 2025 starts in 2025-02, not 2025-08. |
| **Period claim (392.2 d, rms 2.9 d, FAP 0.25%)** | **Retract.** If any period is quoted: "dip minima tend to fall near a ~196-d grid (8 of 11 within ±8 d; chance ~1-5% after trials); depth unrelated to phase; most cycles empty; two deep minima off-grid." |
| **"Shallower dips at phase 0.5"** | Retract. That is the P/2 alias, and dips at phase 0.5 can be deep (2011: 1.33 mag; 2014: ≥1.2 mag). |
| **"Thick-disk K1 dwarf, abs G 5.3"** | Keep "thick-disk K dwarf". Change to M_G ≈ 5.1 (out-of-dip G 16.13) and note that the DR3 G and BP-RP are biased by the 2016-17 dip. |
| **Infrared** | Add "W1-W2 = 0.23 (6σ) and W3 excess (4.8σ): warm dust." |
| **Novelty** | Replace "nothing found" with "catalogued variable: VSX NL/VY: (Otero 2020, from CRTS), ATLAS-VAR 'dubious'. The VY Scl type is excluded by GALEX and Gaia Hα; no publication on its nature found; SIMBAD still unreachable." |
| **TESS claim** | Keep, but as "consistent with" rather than "localizes". |
| **Ladder status** | The dimming is **reproduced** (Gaia, ZTF, CRTS, PS1, NEOWISE, TESS). The clock hypothesis does **not** reach "interpreted". |

## 5. Decisive follow-ups

1. **The single best test of the clock** costs nothing: the ATLAS light curve (being fetched) for 2025-10 → today.
   - Is the 2025 complex over?
   - Was there a dip at the P/2 grid point **2026-04-29 ± 10 d (MJD 61121)**?
   - Any ≥0.5-mag dip starting more than ~20 d off the 196-d grid argues against even the alias.
   - Also check TESS sectors 75-86 (2024) at MJD 60336 and 60532.
2. **For the physics:** one moderate-resolution spectrum (Hα, Li 6708, [Fe/H], RV). It would confirm an old dwarf and
   exclude youth or accretion. Repeated through the next dip, it would give a reddening law and gas absorption.
3. Watching 2026 Nov 14 is fine, but under skip-allowed rules a null there is not decisive, and the report should say so.

## 6. Tool fixes

- **Novelty searches.** Fall back to vsx.aavso.org and the VizieR mirrors (vizier.china-vo.org works) when CDS or VSX
  time out. "Unreachable" should not end the search.
- **Period claims.** Require every archive covering the epoch range before an ephemeris is quoted: CRTS (no Oddsky
  module exists; the endpoint is nunuku.caltech.edu `getcssconedb_release_imgN.cgi` with RADec), and PS1 DR2 detections.
  - An automatic P/2 and 2P fold, plus a "covered cycles with no event" count.
  - Monte Carlo over the full period range, with events drawn from the real sampling.
- **Colour claims.** A "grey" claim should be computed automatically from near-simultaneous multi-band depths,
  including NEOWISE against ZTF.
- **DR3 caution.** Flag DR3 mean photometry as suspect when phot_g_mean_flux_over_error is anomalously low for the
  magnitude.
- **ZTF metadata.** `oddsky.data.ztf` should keep the qid (readout channel), airmass, chi and magzprms instead of only
  field:ccd.
- **TESS script.** Fix the wrong neighbour ID in the `tess_pix_cdd.py` docstring.
