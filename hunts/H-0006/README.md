# Hunt H-0006: dust that vanished

**Question.** Which stars carried warm dust when WISE first looked, and lost it while NEOWISE was watching (2014-2024)?

**Why this hunt.** Disks are supposed to fade over millions of years. TYC 8241 2652 1 lost almost all of its infrared
excess in under two years (Melis et al. 2012), and nobody knows how many others have done the same, because nobody looks
for a signal that goes *away*. H-0002 already measured every star at Galactic latitude ≥ 10° on every NEOWISE visit, so
asking costs one query.

**Data.** The H-0002 sky pass as first run (`oddsky-sky-br3c3.sky.sky1_features`, |b| ≥ 10°, NEOWISE 2014-2024; see the re-run note below), AllWISE
2010 and CatWISE2020 (IRSA), Gaia DR3, NEOWISE single exposures, Gaia DR3 epoch photometry.

**Funnel** (`scripts/hunt_h0006_pull.py`, `hunt_h0006_vet.py`, `hunt_h0006_sheet.py`; every number is reproducible):

| step | n | what fell out |
|---|---|---|
| ≥ 12 visits, quiet 2014-15 baseline, W1 < 13, W1-W2 excess > 0.25, W2 fainter by > 0.2, excess down by > 60% | 108 | |
| a Gaia DR3 star with parallax/error > 5, not a Gaia QSO/galaxy candidate | 11 | 63 QSO/galaxy candidates, 19 with no Gaia source within 3", 15 too faint for a parallax |
| the excess is still down by > 40% if the final visit is ignored | 2 | 9 that miss the bar without their final visit: 8 single bad last W2 points (the sky1 merge bug, below), and a metal-poor halo star |
| no red CatWISE neighbour within 8", no Gaia AGN within 6", NEOWISE centroid moves with the star | **1** | an F star blended with a Gaia-classified AGN 2.1" away |

**The trap that looked like a halo debris disk.** J124045.55-155542.0 (Gaia DR3 3523857324467493760) is a G dwarf at 720 pc
with [M/H] = -1.4, RV +87 km/s and 131 mas/yr of proper motion: a halo star. Its WISE excess faded steadily for ten years.
CatWISE resolves the cause: the star itself is photospheric (W1-W2 = 0.01), and a static, very red source
(J124045.81-155540.1, W1-W2 = 1.58, W3 at 16σ, a dusty AGN) sits 5" east. The star is moving west, away from it. The
NEOWISE centroid sat 0.4" toward the AGN and drifted back as they separated (-14 ± 3 mas/yr relative to the star). It's a
blend coming apart, not dust leaving a halo star.

**The survivor.** [J160708.51-320101.1](plots/J160708.51-320101.1.png) (2MASS J16070852-3201009, Gaia DR3 6036595883378187008).
A catalogued Upper Sco (ρ Sco, Sco-Cen) member at 147 pc, spectral type M1.5 with weak Hα (Kuruwita et al. 2018), with a
"full" disk (Luhman 2022b). **Its 3-5 µm hot-dust excess vanished between August 2021 and February 2022, and was still
absent in September 2026.**

- 2010-2021: AllWISE W1-W2 = 0.43, W2-W3 = 1.9; NEOWISE W1-W2 0.29-0.57 over 16 visits, varying like a young star's.
- After the step: W1-W2 = 0.05-0.11 over all five remaining NEOWISE visits (to mid-2024). That is consistent with a bare
  photosphere: 0.067 against 0.09 ± 0.04 for field M dwarfs of the same colour, and K-W1 = 0.12 against 0.136.
  "Within six months" is an upper limit set by the NEOWISE cadence.
- SPHEREx (2025-26): 15.9 mJy at 4.4-5.0 µm against ~31 mJy before the step, so still no excess. The star did not dim:
  NEOWISE W1, SPHEREx 1-2.4 µm against 2MASS, and TESS all agree.
- Gaia 2014-17: one dip in 2015, deeper in BP (a dipper, so probably an inclined disk). Kuruwita's four radial velocities
  span 9 km/s, so it may be a spectroscopic binary, and a close companion could clear an inner disk.
- **Unknown:** the outer disk. Nothing has measured 10-24 µm since 2010 (W3 = 7.51, W4 = 5.05), so whether the dust is gone
  or hidden is open. This is not "the disk vanished".

**Referee** ([report](reviews/claude-referee-2026-10-28.md)): the step is real. It survives raw single exposures (12-26
per post-step visit; flags and fit quality unchanged), a constant 18" control star in the same frames, both scan
directions, and a centroid test against the 7.7" neighbour. Probability of a mundane explanation: about 3%.
**Novelty:** the star and its disk are catalogued; the fading is not in VarWISE, Park et al. 2021, the dipper papers, or
anything the web finds. SIMBAD and ADS have not been checked (CDS was unreachable all of 2026-10-28).

**Status (2026-10-28): survives the referee; interpretation open; not announced.** Before it becomes a case: SIMBAD and ADS
novelty (CDS down), and ATLAS forced photometry (task 5266397, queued) for the optical through 2021-22. The decisive
observation is 10-20 µm photometry now, against the 2010 W3/W4, which only an astronomer can arrange.

**Beyond the parallax limit: two evolved stars in the Magellanic Clouds.** Of the 34 flags with no usable parallax that
Gaia does not call a QSO or galaxy, 3 pass the final-visit test, and all three are in the LMC or SMC. Two are clean:

- J053700.12-712445.9 (LMC, G = 15.6, BP-RP = 3.5, M_W1 ≈ -9): W2 flat at 9.0 in 2014-17, faded to 9.6 by 2019; 18% of
  the excess left.
- J010347.02-723643.0 (SMC, G = 15.9, BP-RP = 2.6, M_W1 ≈ -8.4): the excess faded over 2017-18 and is gone.

Both turned in the same year, so the first suspect was the instrument. Similar stars in the same HEALPix pixels (35 in the
LMC, 30 in the SMC; W1 8.5-11.5, W1-W2 0.2-0.6) changed colour by less than 0.05 mag in every year, so the instrument is
not the cause. **The referee killed both** ([report](reviews/claude-referee-mc-2026-10-28.md)). They are catalogued
carbon-rich semi-regular AGB stars (OGLE-LMC-LPV-74526, P = 452 d with a 4,525 d trend; OGLE-SMC-LPV-15813, P = 1,159 d).
Both are already VarWISE mid-IR variables (Paz et al. 2026), and each is going through an ordinary dust cycle. The SMC star's
excess had only *risen* from W1-W2 ≈ 0.1 in 2008-10 to 0.34 in 2014 before falling, and Gaia shows it brightening in the
optical as the dust cleared (Spearman 0.81). Among 188 similar quiet red Magellanic sources, fades and rises pass the cut
about equally often: variability, not one-way loss.

**Re-run on the fixed sky pass (sky2, 2026-10-28).** The same query on `sky2_features` gives 24 flags instead of 108; most
of the 108 were made by the merge bug described below. The survivor still fades there (excess down 87%, W2 +0.80 mag), but
it no longer passes the quiet-baseline cut: with its real first visit restored, its baseline scatter is 0.137 mag (a young
star's variability) against a cut of 0.05. So its *selection* depended on the bug; its *vetting* (IRSA single exposures,
SPHEREx, the referee) did not. ATLAS forced photometry (task 5266397, 2016-2026): half-year medians stay within 0.1 mag
in c and o over the decade and within 0.04 mag across the August 2021 - February 2022 drop. No dimming, brightening or
accretion flare marks it in the optical.

**Lessons for the sky pass.**

- `color_end` and `w2_end` in `sky1_features` are changes from the baseline, not end values. The vanishing-dust query
  H-0002 left in `queries.sql` read them as colours and returned 1,995 red sources whose W2 faded slightly (fixed).
- **sky1 merges neighbouring stars' visits** (found 2026-10-28 in a parallel session; fix and sky1 re-run pending).
  `neowise_pixel.visits()` compared 19-digit AllWISE cntrs after a float64 upcast, so each star's first visit was medianed
  into its neighbour's last. That is where the 8 "single bad last W2 points" and the LMC phantom visit (MJD 58674.93, no
  IRSA exposure behind it) come from. `w2_end`, `color_end` and `sky1_lightcurves` are unreliable until the re-run, and
  this funnel should be repeated on it. Completeness is also low: the bad visit inflated baseline scatter, so a fixed run
  tests 38-120% more quiet stars. The survivor is unaffected: it was re-measured from IRSA single exposures by position.
- Pair every "fade" query with the mirror "rise" query in the same population: a one-way loss has to beat the rise rate.
- Blends with red AGN are the main stellar false positive. A Gaia G-band blend check misses them; CatWISE and the NEOWISE
  centroid track catch them.
