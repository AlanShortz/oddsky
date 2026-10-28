# Referee report: H-0006, J160708.51-320101.1 (2MASS J16070852-3201009, Gaia DR3 6036595883378187008)

Author: claude-referee, 2026-10-28. Mandate: docs/REFEREE.md. There is no case yet, so there are no claim ids
or call ids. Every result below cites the scratch script or data file that produced it, under
`/tmp/referee_h0005/` (scripts in `scripts/`, downloads in `data/`, literature sweep in `novelty/`). Nothing in
the repo was changed except this file.

## 1. Verdict

The step is real. Raw IRSA single exposures, a constant 18" control star in the same frames, and new SPHEREx
2025-26 spectrophotometry all show that the 3-5 µm excess of this disk-bearing Upper Sco M1.5 star dropped to a
bare photosphere between Aug 2021 and Feb 2022. It was still there in Sep 2026, and the stellar photosphere did not
dim. **Probability that a mundane explanation (instrumental artifact, blend, sky-pass error or calibration
drift) is correct: about 3%.**

**Novelty.** The object is known: a catalogued Sco-Cen/Upper Sco member with a "full" disk (Luhman 2022b) and
spectral type M1.5 (Kuruwita+2018). Its fading is not known: it is absent from VarWISE and Park+2021, and no paper
or web page we could reach reports it. SIMBAD could not be checked, and ADS was not searched directly.

## 2. Attacks and results

**Re-derivation from raw data** (`scripts/pull_neowise.py`, `scripts/ana2.py`, `data/neowise/neowiser_p1bs_psd.csv`;
589 exposures within 20"). We re-fitted every visit from `neowiser_p1bs_psd`, with W1-W2 as the median of the
exposures in each visit:

| visits | W1-W2 (raw) | W1-W2 (clean: qual_frame>0, cc=0000, nb=1, moon=00, saa_sep>0) |
|---|---|---|
| 16 pre-step visits, MJD 56716-59432 | 0.29-0.56 (min 0.286, Mar 2019) | 0.30-0.57 |
| 5 post-step visits, MJD 59636-60365 | 0.070, 0.056, 0.109, 0.050, 0.067 | 0.069, 0.057, 0.112, 0.067, 0.065 |

- **AllWISE 2010** (`allwise_p3as_mep`): two epochs with W1-W2 of 0.40 and 0.47, and W3 = 7.50.
- **Exposures behind each post-2021 visit** (this answers the LMC phantom-visit concern). Each of the 5 visits has
  real IRSA exposures behind it:
  - 59636: 25 raw / 6 clean, from 21 distinct scan_ids (36798r…)
  - 59797: 26 / 5, from 23 scans (41791r…)
  - 60000: 12 / 5, from 11 scans
  - 60163: 13 / 6, from 11 scans
  - 60364: 14 / 6, from 13 scans
- **Flags and fit quality.** No w1sat or w2sat was set in any visit, and nb = 1 throughout. qual_frame, moon_masked
  and cc_flags show the same mix (0000 or h000) before and after the step. Median w2rchi2 is 1.8-4.1 before and
  1.8-3.1 after, so nothing changed at the step.
- **Scan geometry.** Pre and post visits both alternate between the two NEOWISE scan directions, so the step is
  not tied to one viewing geometry.
- **The step is not a final-visit or single-visit effect.** It persists through 5 consecutive visits spanning 2.3
  years.
- **Control star** (Gaia DR3 6036595883378178432, G = 14.64, 18.5" away, in the same exposures):
  - W1 is 12.03-12.07 in every one of the 21 visits.
  - Its W2 is 0.02-0.03 mag fainter after 2022 and its W1-W2 is 0.02 bluer, which matches the H-0002 drift.
  - No zero-point step at MJD 59432-59636.

**1. Period and aliases.** A periodic signal cannot produce this pattern. NEOWISE shows 16 high-excess visits, then
5 low ones in a row, and SPHEREx (below) shows the excess still low a year later. The TESS sectors show no
significant periodicity (Lomb-Scargle power ≤ 0.2, except a 9-day trend in the S12 SAP flux; `scripts/tess_ana.py`).
**Survives.**

**2. Instrument artifacts.** As in the re-derivation above, flags, saturation, scan direction and the control star
all rule out an instrumental cause. The sky pass's baseline was its first 3 visits (excess 0.47). The re-extraction
does not depend on the sky pass. **Survives.**

**3. Blends and neighbours** (`scripts/gaia_field.py`). The nearest Gaia source is 6036595883378188288 at 7.7" (PA
about 25°). It has G = 15.45 and BP-RP = 1.39, and is a distant background star (parallax 0.13 mas). TIC lists it
as TIC 94420210 (contamination ratio 0.41 in TESS). It supplies about 5% of the W1 flux.
- If that star had supplied the 0.4 mag of W2 that disappeared (about 30% of the pre-step W2 flux), the pre-step
  centroid would have been pulled about 2" toward it.
- The NEOWISE centroid relative to the proper-motion track actually moved 0.04" toward it after the fade
  (dx, dy = 0.06", 0.11" before; 0.09", 0.15" after). That is the expected small shift once the target got fainter,
  and it excludes the 7.7" star as the source of the excess.
- The vet's CatWISE red-neighbour test (8") and Gaia QSO/AGN test (6") were clean.

**Survives.** One caveat: the vet's drift test only uses RA; this one used both axes.

**4. "No X" claims.**
- **"Bare photosphere"** (`scripts/photcol.py`, `scripts/calib.py`). The comparison sample is field M dwarfs with
  the same BP-RP (2.25-2.45), W1 around 10, and W1-W3 < 0.4.
  - In AllWISE, their median W1-W2 is 0.12 (16th-84th percentile 0.09-0.15) and their K-W1 is 0.136 (0.11-0.16).
  - In NEOWISE single exposures of 5 such stars, W1-W2 in 2022-24 is 0.094 (range 0.02-0.15), 0.01 bluer than in
    2014-16, and their W2 is 15 mmag fainter.
  - The target's post-step W1-W2 of 0.067 ± 0.02 lies inside that spread and about 0.03 below its median. A small
    reddening (A_V of about 0.5 lowers the intrinsic BP-RP) would make the photosphere slightly bluer still.
  - Its K-W1 of 0.12 (2MASS 1999 K against NEOWISE 2022-24 W1) is exactly photospheric.
  - It is not significantly below the photosphere, so there is no sign of a systematic.
- **"Stayed off"**: tested past NEOWISE with SPHEREx (attack 7). Still off in Sep 2026.
- **"Photosphere did not dim"**:
  - SPHEREx in 2025-26 gives 61 mJy at 1.1-1.4 µm, 80 at 1.5-1.8 µm and 56 at 2.0-2.4 µm (aperture fluxes,
    uncorrected). These agree with 2MASS 1999 (J/H/K = 52/69/59 mJy) to within 0.95-1.16, and that factor is
    explained by the 7.7" blend and the aperture.
  - NEOWISE post-step W1 is 10.02 ± 0.01, constant over 5 visits.
  - TESS S65, S91 and S103 show no fading or dips beyond about 1%; the S103 ramps at orbit starts are scattered
    light.
  - **Supported.**
- **"Within 6 months"**: an upper limit set by the visit cadence (59432 to 59636). We have no optical light curve
  inside that window yet.

**5. Physical self-consistency.**

Stellar parameters:
- M_G = 7.85, BP-RP = 2.35, Teff 3660-3700 K, M1.5. L ≈ 0.10-0.13 L☉ and R ≈ 0.8-0.9 R☉.
- About 1 mag above the main sequence, consistent with the ρ Sco group at about 14 Myr (Ratzenböck+2023).

Where the vanished emission came from:
- Dust sublimation radius: 0.014 AU for blackbody grains, 0.025-0.04 AU for small grains. Corotation radius for a
  few-day rotation period: about 0.04 AU.
- The 3-5 µm excess comes from dust at about 700-1400 K, at roughly 0.02-0.1 AU. Orbital periods there are 2-10 days,
  so 6 months is 20-90 orbits.
- Viscous time at 0.05 AU (h/r ≈ 0.02-0.04, α = 0.01-0.1) is decades to centuries.
- So draining an inner *gas* disk in 6 months is not plausible. Removing or optically thinning the inner *dust*
  within 20-90 orbits is plausible, especially if the inner disk was dust-dominated and not being replenished.

Supporting and complicating evidence:
- Kuruwita+2018 measured Hα EW of -1.2 to -2.0 Å in 2015-17, which is weak and below the accretor threshold for
  M1.5. The inner disk was therefore already accreting little or nothing while the excess was present. This supports
  the idea that the inner dust was not being fed.
- Kuruwita's 4 RVs range from +1.3 to +10.2 km/s (errors about 1 km/s), so the star may be a spectroscopic binary.
  A close companion could truncate and clear the inner disk dynamically. Kuruwita's own classification was not
  checked.
- The excess reached its highest values in Mar and Aug 2021 (0.57 and 0.51, with W1 at its brightest, 9.40) just
  before it collapsed. Whatever happened was preceded by a brightening of the warm dust.

Mundane disk geometry does not fit:
- Gaia epoch photometry shows a 3-4-day dip of 0.3 mag in Jan 2015 (MJD 57032-57037), reddening BP-RP by about
  0.1 (`hunts/H-0006/vet/..._gaia_epoch.csv`). That makes the star a dipper in 2015, which implies a moderately high
  inclination.
- An outer warp or flared rim that hides the inner rim would also have to cover all of its 3-5 µm emission (from a
  region about 5-20 R* across) while leaving the star unobscured. That is geometrically implausible, and the W1 and
  SPHEREx fluxes show the star is not dimmed.
- An inner rim that puffs up or collapses moves flux between bands (the "seesaw") but cannot remove more than 90%
  of the 3-5 µm excess.

Analogues. These are from memory and were not re-checked:
- TYC 8241 2652 1 (Melis+2012): warm debris dust vanished in under 2 years.
- LRLL 31 (Muzerolle+2009; Flaherty+2011): 3-8 µm excess changed on week timescales.
- Pre-transitional "seesaw" disks (Espaillat+2011).
- The Upper Sco dipper J1604-2130, whose near-IR excess varies strongly between epochs (Zhang+2014;
  Sicilia-Aguilar+2020).

A complete, years-long loss of the 3-5 µm excess in a full-disk M star is at the extreme end of these.

**6. Novelty** (`novelty/scripts/*.txt`, delegated sweep, spot-checked).

Known object:
- Luhman 2022a/b (J/AJ/163/24, /25): Sco-Cen candidate; excess in W2, W3 and W4; disk class **"full"**.
- Kuruwita+2018 (2018MNRAS.480.5099K): spectral type M1.5, region "US".
- Kerr+2023 SPYGLASS-IV: Sco-Cen, Pmem 0.93.
- Ratzenböck+2023 SigMA: ρ Sco.
- Also listed in Zari+2018 PMS, Marton+2016 (Class I/II candidate), Prisinzano+2022 and eRASS1 (1eRASS J160708.6-320100).
- VSX lists it only as a Gaia DR3 YSO.
- The 2025 TESS 2-min data come from GI G07140, the TESS Sco-Cen Legacy Survey, which observes members as a group.
  No one targeted this star individually.

Not in these catalogues: Luhman & Esplin 2020, Esplin+2018, Luhman 2020 (Lupus), Galli+2020, Merín+2008,
Ansdell+2016, Marton+2023 (KYSO).

Fading not reported:
- Absent from VarWISE (Paz+2026; IRSA TAP query within 9" returns nothing, though the query works on a source 2.7'
  away).
- Absent from Park+2021, Cody & Hillenbrand 2018, Rebull+2018 and Capistrant+2022.
- Not mentioned in Ben+2026 or Kulkarni+2026.
- Web searches on all identifiers return nothing.
- No K2 data exist for this position.

Could not check:
- SIMBAD, on both CDS and Harvard (timed out throughout).
- ADS full-text search.
- Contreras Peña / Lee+ variability catalogues.
- Several VizieR volume prefixes that failed in the sweep (ApJ 792-832, AJ 141/159, I/26*, I/28*, I/32*, I/34*,
  II/28*, V/16*), and pre-2010 catalogues.

**7. Untapped data.**
- **SPHEREx (new, decisive for "stayed off")** (`scripts/spherex_dl.py`, `scripts/spherex_phot.py`,
  `spherex_phot.csv`).
  - 370 Quick-Release images cover the star, from MJD 60885 to 61290. We measured 62 IBE cutouts, spread over
    2025 Aug, 2026 Feb and 2026 Aug, with aperture photometry at r = 1.8 px.
  - At 3.0-3.7 µm the target gives **29.9 mJy** (epochs 31.3, 29.3, 28.7). The NEOWISE post-step W1 of 10.02 implies
    30.4 mJy; the pre-step median W1 of 9.75 implies 39 mJy.
  - At 4.4-5.0 µm it gives **15.9 mJy** (12 images; epochs 16.7, 15.8, 15.7). The post-step W2 of 9.95 implies
    18.0 mJy; the pre-step median of 9.36 implies 31 mJy, and AllWISE 30 mJy.
  - So the excess is still absent through Sep 2026, with no hint of recovery.
  - The 4.6 µm aperture flux is slightly below the photospheric value because the PSF is larger there. This is
    relative aperture photometry, not a calibrated SPHEREx spectrum.
- **TESS** (`data/tess/`). TIC 94420199. QLP covers S12 (2019, before the step) and S65, S91, S103 (after it); SPOC
  2-min covers S91, and CDIPS covers S12.
  - S12 shows 1-2% dips (BTJD 1634.5 and 1640.5) and a slow trend.
  - S65 and S91 (SPOC PDCSAP, p5-p95 range 1.9%) show no dips.
  - This is weakly consistent with less inner-disk dust in the line of sight after the step. Amplitudes before the
    step were already small, so it is not decisive.
- **Gaia epochs** end in 2017 and show the 0.3 mag dip in 2015. They say nothing about 2021-22.
- **ATLAS.** Task 5266397 (submitted 05:08 UTC) still had not started at 06:02 UTC. No duplicate was submitted.
- **ASAS-SN.** ID 472446800778. The Sky Patrol light-curve service is down for maintenance (notice dated
  13 Oct 2026).
- **ZTF.** The star is outside the ZTF footprint.
- So there is still **no optical light curve across the 2021-22 transition.**

## 3. Most plausible mundane explanation remaining

There is no credible instrumental explanation. The weakest point left is not an artifact but how the change is
interpreted. "Inner disk switched off" can mean either of two things:
- (a) the warm dust was destroyed, accreted or blown out, which would be a transition-disk cavity opening in real
  time;
- (b) the warm dust was cooled or hidden by a geometric change.

Option (b) has trouble explaining a loss of more than 90% with an undimmed star, but it is not excluded. A possible
close binary companion (RV range about 9 km/s) is the most likely ordinary *physical* driver of (a). Nothing
constrains the outer disk after 2010, because there is no W3 or W4 after AllWISE.

## 4. Required wording changes

- **Title and hook.** Say "the 3-5 µm (hot-dust) excess of a disk-bearing Upper Sco M1.5 star vanished between Aug
  2021 and Feb 2022 and is still absent in Sep 2026 (SPHEREx)". Do not say "the inner disk switched off" or "the
  disk vanished".
- **Outer disk.** Its state is unknown; the claim must not imply the whole disk dissipated.
- **"Within ~6 months".** Keep it, worded as an upper limit set by the cadence.
- **"The photosphere did not dim".** Keep it, citing NEOWISE W1, SPHEREx 1-2.4 µm against 2MASS, and TESS.
- **"Bare photosphere".** Change it to "consistent with a bare photosphere": W1-W2 = 0.067 against 0.09 ± 0.04 for
  NEOWISE field M dwarfs of the same colour, and K-W1 = 0.12 against 0.136.
- **Membership.** Upper Sco / ρ Sco (Sco-Cen), not "Upper Sco or Lupus". Cite Luhman 2022b ("full" disk) and
  Kuruwita+2018 (M1.5, weak Hα).
- **Context to add.** The 2015 Gaia dip (dipper, inclined disk) and the possible SB from the Kuruwita RVs.
- **Novelty sentence.** "A catalogued Upper Sco full-disk member; its mid-IR fading is not in VarWISE or the YSO
  variability literature we could reach. SIMBAD and ADS were not checked."
- **Status.** Survives the referee as a real astrophysical change. Interpretation is open. It is a candidate for
  announcement once SIMBAD/ADS novelty is closed.

## 5. Decisive follow-ups

1. **Settle novelty.** Run a SIMBAD/ADS check when CDS is reachable.
2. **Settle (a) against (b) and the cause.** Get mid-IR photometry now at 10-20 µm (JWST MIRI or ground N/Q band)
   and compare it with the 2010 values W3 = 7.51 and W4 = 5.05.
   - If the outer disk is still there, a cavity opened (option a).
   - If it is also gone, the whole disk dispersed.
3. **In the same campaign**, take one high-resolution optical spectrum, plus RV epochs to test the binary and to
   measure accretion now.
4. **Cheapest test inside our own data.** The pending ATLAS light curve for 2015-26 will show whether the dipping
   stopped, or the star changed, at the 2021-22 transition.

## 6. Tool fixes

- **TESS and ASAS-SN clients.** `oddsky.data.tess` fails silently in this venv (no `lightkurve`), and
  `oddsky.data.asassn` needs `skypatrol`. Neither raised an error the investigators would see. Make a missing
  optional dependency a hard warning in the sheet.
- **Drift test.** `hunt_h0006_vet.drift` fits only the RA offset. Fit both axes and report the shift toward the
  nearest Gaia neighbour.
- **Photosphere reference.** The sheet's "photosphere ~0.1-0.2 for an M star" line should be an empirical
  NEOWISE-epoch photosphere for the star's BP-RP. For BP-RP 2.25-2.45 that is 0.09 ± 0.04 in 2022-24; AllWISE gives
  0.12. Use the version from `scripts/calib.py`.
- **SPHEREx client.** Add `oddsky.data.spherex` (IBE cutouts plus aperture or forced photometry). It is the only
  post-2024 3-5 µm data and would have tested "stayed off" automatically.
- **Membership lookups.** Add a VizieR mirror fallback list (vizier.idia.ac.za, vizier.china-vo.org) so these work
  while CDS is down.
