# Hunt H-0004: stars that go dark

**Question.** Which of the stars the experts short-listed as R Coronae Borealis candidates have gone dark
since anyone last looked, and what else deep, aperiodic and unexplained is hiding in the same light curves?

**Why this hunt.** An R CrB star is confirmed the day it does the one thing only R CrB stars do: fade by
1-9 magnitudes in weeks, for no reason, and crawl back over months. Tisserand et al. (2020) selected 2,356
candidates from WISE and 2MASS colours; about 900 have since been classified with spectra (Tisserand+2020,
Karambelkar+2024), and the rest are waiting for a decline. Nobody had systematically looked at the
2022-2026 window, and the southern half (1,067 stars, where the Galactic bulge is) had never been screened
at ATLAS depth. The archive kept recording after the papers stopped. That is the whole trick.

**Data.** ZTF (dec > -30, 2018-), ATLAS forced photometry (whole sky, 2015-, new client `oddsky.data.atlas`),
then NEOWISE, Gaia DR3 and AAVSO for the picks. Known R CrB stars (Karambelkar+2022, 73 objects) run
through the same pipeline as the calibration set: the classifier's recall on them is reported, not assumed.

**Funnel** (every step is a script in `scripts/hunt_h0004*.py`; every number is reproducible):

| step | stars | what removed them |
|---|---|---|
| Tisserand+2020 WISE/2MASS candidates (pool A) + Gaia DR3 2014-17 faders from H-0003 (pool B) | 2,401 | |
| not already a known R CrB / dLHdC star, not classified by Karambelkar+2024's 453 NIR spectra (their 8 "RCB-cand" stay in) | 1,954 | 3 known RCB, 443 spectroscopic classifications, 1 SIMBAD RC* |
| north of -30 (ZTF, 2018-2025.7) | 887 | the 1,067 southern stars wait on ATLAS (see status) |
| ZTF light curve with 30+ usable nights | 473 | 49 with no ZTF source, 365 too faint, too bright (r < 13 saturates) or too few nights |
| `rcb_like`: a fast (>= 0.02 mag/day), unscheduled fade of >= 1 mag, not a periodic pulsator, not a one-night glitch | 63 | 247 flat, 110 Miras/pulsators, 10 slow variables, 14 erratic young-star-like, 3 glitches, 24 unclassified, 2 eclipse-like |
| not already a catalogued variable of a known kind (VSX 2026, SIMBAD 2026) | 16 | 16 Miras, 9 semiregulars, 5 RV Tau, 5 irregular giants, 5 young stars, 2 W Vir, 1 Cepheid, 1 dwarf nova, 2 eclipsing, 3 rotational, plus the eclipse-like pair |
| worth a case after a human looked at every plot | 2 | 14 are slow or noisy variables, faint stars with one season of data, or Gaia says "dwarf" |

**What survived.**

- **[OS-0013](../../cases/OS-0013)**, Tisserand candidate 2682 (2MASS J18205507-1340452). Not an R CrB star: a red giant at 2.4 kpc,
  flat for years, with three sharp 1.7-2.2 mag eclipses in ZTF (2019, 2021, 2022) and a fourth caught in ingress (2023), deeper in
  blue, on **P = 385.7 +/- 1 d**, no secondary. An eclipse lasting ~4% of a one-year orbit means the occulter is ~80 Rsun across: a
  dusty disk around a companion, the epsilon Aurigae / EE Cep configuration at a one-year period. Not in VSX; Gaia DR3 and the ZTF
  classifiers missed it because the eclipses are too brief for a periodogram. Two predictions sealed (2027 quiet season, 2028
  January eclipse). Referee report and the ATLAS record (2017-2026, independent of ZTF) in the case directory.
- **Tisserand candidate 41** (2MASS J07235669-1240141), one of Karambelkar+2024's eight "RCB-cand" stars: 4.5-mag aperiodic fades and
  recoveries across ATLAS and ZTF 2016-2026, but the field is crowded and most ATLAS exposures are flagged. Needs a careful case;
  not claimed.
- **Tisserand candidate 5021** ([KDM2001] 2730, a carbon star in the LMC outskirts, ATLAS only): two 5-mag drops with 0.4 mag/day
  declines and 500-day minima on a ~950-day cycle. A dusty long-period variable or a DY Per-type star; for the advisor.

**No new R CrB star has been confirmed yet.** In the north, every star that fades like one and is bright enough for ZTF turned out
to be in a catalogue already. The southern 1,067, where most R CrB stars live, are still queued.

**Calibration on real R CrB stars.** Before any candidate was scored, the classifier was run on the AAVSO
V-band records (2015-2026) of twenty well-known R CrB stars (`aavso_cal/`). All fourteen that declined in the
window come out `rcb_like` (R CrB, SU Tau, SV Sge, V482 Cyg, GU Sgr, S Aps, V CrA, WX CrA, Z UMi, DY Per,
RZ Nor, U Aqr, UW Cen, V854 Cen); the five that stayed at maximum (XX Cam, UV Cas, RT Nor, RS Tel, RY Sgr)
are `no_event`; V3795 Sgr's sparse visual record is `artifact`. Two rules changed because of this test:
active R CrB stars spend most of their time faint (so "has a maximum" replaced "mostly at maximum"), and
three declines can space evenly by chance (R CrB's did), so a cadence needs four events to count as periodic.

**Calibration on ZTF.** The same pipeline run on the 73 known RCB/dLHdC stars of Karambelkar+2022 (`calibration.csv`,
`scored_calibration.csv`): of the 28 with usable ZTF light curves, all 14 R CrB stars that declined come out `rcb_like` and all
12 dLHdC stars (which never decline) come out `no_event`; the two remaining are R CrB stars with no ZTF source. Most known R CrB
stars are brighter than ZTF's saturation limit, which is why the calibration set is small and why ATLAS matters.

**Status (2026-10-27 evening).** North done through ZTF. ATLAS (whole sky, 2015-2026) is a shared server that processes about
three of our stars an hour, so the southern half and the ZTF-saturated bright stars arrive over days: 10 done, queued in priority
order (Karambelkar colour and light-curve classes, dwarfs last). `scripts/hunt_h0004_fetch.py --surveys atlas --priority` resumes.

Files: `pool.csv` (all 2,401 with exclusion reasons), `candidates.csv`, `calibration.csv` (known RCB/dLHdC),
`ext/` (the input catalogues), `lc/` (per-star light curves, not committed: re-fetch with the scripts),
`scored.csv`, `vet/`, `vetted.csv`.
