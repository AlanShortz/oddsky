# H-0017: nuclei that changed state across the WISE gap

Opened 2026-11-05 from H-0016 section 5.5. WISE stopped observing in February 2011 and resumed in December 2013. H-0016
found galaxy nuclei that were AGN-coloured (W1 − W2 ≥ 0.4) in AllWISE (2010-11) and were fainter, bluer and quiet in every
NEOWISE year from 2014 to 2024: a nucleus that was radiating warm dust in 2010 and was not afterwards. The question here is
whether that is a one-way street. If nuclei simply wander between states, as many should have heated across the gap as
cooled.

**Status (2026-11-05, after the referee: `reviews/claude-referee-2026-11-05.md`).** The hunt rediscovered a published
class and found nothing new yet. About 40% of 96 galaxy sources that were red and bright in AllWISE and fainter, bluer
and quiet afterwards were already declining during 2010-11 (37 faded by more than 0.15 mag between their AllWISE visits,
against 2 that brightened). That population is Wang et al. 2018 (MNRAS 477, 2943): mid-infrared-declining galaxies read
as dust echoes of tidal disruption flares; four of their 19 are in this sample, including the object this write-up first
called its best candidate. What this selection adds is reach: it needs no spectrum and covers the whole sky at
|b| > 10°. After vetting (section 6), 8 of the 96 are already studied and 31 were declining in 2010-11 with no transient
literature found by the Librarian or by a second referee's independent search; 26 of the 31 are resolved galaxies in
optical surveys. They are candidates, not results: not shown to be nuclear, and three are catalogued NEOWISE variables. The 96 : 13 ratio of
cooled to heated is set by the quiet cut and means nothing about rates.

## 1. Selection

Parent: `oddsky-sky-br3c3.sky.sky2_features` (176.9 M AllWISE sources at |b| ≥ 10° with NEOWISE visit medians). Both
selections are in `work/sql/` and are mirror images:

| | cooled | heated |
|---|---|---|
| bright, red state | AllWISE: 9 ≤ W1 ≤ 15, W2 ≤ 14, W1 − W2 ≥ 0.4 | NEOWISE 2014-15 baseline: the same cuts |
| other epoch | fainter by > 0.3 mag (W1) and > 0.5 mag (W2), bluer by ≥ 0.25 | the same |
| after 2014 | ≥ 12 visits, peak-to-peak < 0.4 mag in W1 and W2 | the same |
| sources | 116 | 186 |

## 2. Validation (the same for both sides)

`scripts/nuclei_state.py --all`: aperture fluxes in the unWISE coadds of the 2010-11 frames and of 2010-2020; a real change
of the catalogued size predicts a flux ratio R = 7a/(a + 6), a = 10^(0.4 Δm), and a catalogue error predicts 1. A source is
real when the measured log R is more than 60% of the predicted one in both bands (mean), an artifact below 30%.
`scripts/identify.py`: Gaia DR3 (a star if parallax or proper motion is above 5σ) and SIMBAD, with failed lookups recorded
as failed (none failed).

| | cooled | heated |
|---|---|---|
| selected | 116 | 186 |
| real in the images | 105 | 16 |
| artifact | 9 | 168 |
| partial | 2 | 2 |
| stars (Gaia) among the real | 9 | 3 |
| **non-stellar and real** | **96** | **13** |

The 168 heated artifacts are one thing: 167 have AllWISE nb = 2. AllWISE split the source into two components and the
profile-fit magnitude of each is about 0.5 mag fainter than the aperture magnitude (median w1mag − w1mpro = −0.51), while
NEOWISE measured the whole. The first count from the catalogues alone (186 heated against 116 cooled, reported on
2026-11-05 as "no excess of coolers") compared a validated list with an unvalidated one and was wrong.

Positive control: one of the 96 is **PTF 10fgz** itself (SIMBAD type SN*, z = 0.01), 0.6" from the supernova and 4.5"
from its host's nucleus. The selection recovers a known 2010 transient without being told about it, and it shows that
"nucleus" is untested for the others: 59 of the 96 are non-stellar only for want of Gaia astrometry or a SIMBAD entry,
and no offset from a galaxy centre has been measured.

Identities of the 96: 15 carry a SIMBAD AGN or emission class (6 Sy1, 3 Sy2, a QSO, a LINER, an emission-line galaxy, a
radio galaxy, a radio and an X-ray source), 11 are plain galaxies, 1 is the supernova host, and 69 have no SIMBAD entry.
Of the 13 heated, 12 have no SIMBAD entry. Tables: `work/cooled_id.csv`, `work/heated_id.csv`.

## 3. What the 96 : 13 does and does not mean

- **The quiet cut decides the ratio.** Before any image test, 410 sources pass the cooled cuts and 772 the heated cuts
  without the quiet requirement; 116 (28%) and 186 (24%) are quiet (`work/sql/state_change_without_quiet_cut.sql`).
  Without the cut there are more heater candidates than coolers, unvalidated. 96 : 13 describes decade-quiet objects
  only. (An earlier version argued from all red sources, 81% and 93% quiet, that the cut favours coolers by only 1.2;
  those are the wrong populations.)
- **The heated sources sit against the cut.** Their W2 peak-to-peak is 0.24-0.39 mag at W2 ≈ 13.5, against a limit of
  0.4: a nucleus that turned on keeps varying, and the ones that varied more are not in the sample.
- **So the comparison is between "was on in 2010, then off and steady for ten years" and "was off in 2010, then on and
  steady for ten years".** The second is a rare kind of object whatever the physics, and the ratio says nothing about
  how often nuclei change state in either direction.
- A fair count of state changes needs no quiet cut, and then the image test used here no longer works, because it
  assumes the later state is steady. The tool to build is a time-resolved one on the yearly unWISE coadds.

## 4. They were already fading in 2010 (`scripts/epochs_2010.py`)

AllWISE visited each position two or three times between January 2010 and February 2011. The AllWISE Multiepoch
Photometry Table gives every frame; frames are grouped into visits (gaps over 60 days, at least 5 frames, `qi_fact > 0`,
`saa_sep > 0`), and the change is last visit minus first.

**Control** (`work/sql/control.sql`): 131 AGN-coloured, quiet sources in the same magnitude window whose AllWISE and
NEOWISE magnitudes agree within 0.1 mag in both bands; 128 have two visits. They show a systematic offset between the
visits of +0.049 mag in W2 and +0.045 in W1 (later visit fainter; instrument or calibration, not sky), with a scatter of
0.053 mag. Everything below is after subtracting that offset.

| | n | median W2 change in 2010-11 | fading by > 0.15 mag | brightening by > 0.15 mag | vs control (Mann-Whitney p) |
|---|---|---|---|---|---|
| control | 128 | 0 (by construction) | 1 | 2 | |
| **cooled** | 96 | **+0.100 mag** (W1 +0.096) | **37** | 2 | 1.6 × 10⁻¹² |
| heated | 13 | −0.072 mag (W1 −0.053) | 0 | 3 | 0.005 |

The per-visit errors used at first (MAD/√n) are 1.4 times too small against the control's own scatter, so the counts are
given at a fixed 0.15 mag (about 3 times the control scatter) and not in sigmas. The offset is instrumental: the referee
measured +0.044 (W2) and +0.027 (W1) for 1,906 field sources in the same frames as 50 of the nuclei, with no extra
offset for extended ones. The AllWISE Explanatory Supplement does not document it.

- 33 of the 96 faded by more than 0.2 mag in half a year and 11 by more than 0.3.
- The median rate, 0.18 mag/yr in W2, carried across the gap gives 0.6 mag against an observed median drop of 0.74. This
  holds for the medians only: 46 of the 96 show no 2010 change above 0.1 mag and dropped later, 33 would overshoot by
  more than half, and a decline still running at that rate would break the quiet cut.
- The heated sources were already rising in 2010 (by 0.07 mag relative to control; 3 by more than 0.15 mag).
- PTF 10fgz faded 0.47 mag in W2 between its two visits, as a 2010 transient should.
- **The selection does have an arrow of time** (an earlier version said it did not): the later visit is nearer the 2014
  baseline, and the quiet cut removes declines that began late. The referee put stationary red noise through the same
  cuts and got +0.02 to +0.06 mag; a straight line from the 2010 level to the 2014 level gives +0.10. The observed +0.10
  says the change was gradual and under way in 2010. It does not separate a flare from a shut-down.

**Reading.** About 40% of the cooled sources were already declining in 2010-11. The population is known: Wang et al.
2018 selected AllWISE-variable SDSS galaxies with declining light curves (J100933.13+232255.7, J123715.10+601207.0,
J130819.11+434525.6 and J142401.66+295028.4 are in both samples), after Dou et al. 2016. AllWISE's own variability flag
(`var_flg` ≥ 7) marks 23 of the 96, all among the decliners. This selection adds objects without a spectrum and outside
the SDSS footprint. Rise-selected NEOWISE samples do not contain them (0 of 96 in MIRONG and in Flaires, by the referee's
cross-match). What they are is not settled by the fade.

## 5. What they were before 2010 (`scripts/sdss_spectra.py`)

16 of the 96 have an SDSS spectrum; 13 of those were taken before 2010 (all queries answered):

| pre-2010 SDSS class | n | examples |
|---|---|---|
| narrow-line AGN (GALAXY/AGN) | 5 | J130819.11+434525.6 (fading 0.64 mag in W2 within 2010), J100933.13+232255.7 |
| broad-line QSO | 3 | J090902.36+133019.5 |
| star-forming or starburst galaxy | 3 | **J142401.66+295028.4** |
| galaxy, no subclass | 2 | J150831.61+062924.6 |

None of the 13 is a clean non-AGN (referee): 8 are SDSS AGN or broad-line objects, 4 are BPT composites in the MPA-JHU
catalogue (`bptclass` 3; SDSS's "star-forming" and "starburst" subclasses hide that, and one is a SIMBAD Sy1), and 1 is
unclassifiable (a SIMBAD Sy2). J142401.66+295028.4 (z = 0.086, composite in 2006) is already published: object 12 of
Wang et al. 2018, a candidate tidal-disruption dust echo. It fades 0.46 mag in W2 (control-corrected) over three AllWISE
visits spanning 363 days and is 1.31 mag fainter and 0.74 mag bluer by 2014. An earlier version of this section called it
a star-forming galaxy with no AGN lines and the first object deserving a case; both were wrong.

## 6. Vetting the 96 (`scripts/vet.py`, `scripts/catwise_pos.py`, `scripts/candidates.py`; table `work/candidates.csv`)

**Is it already published?** The Librarian (`oddsky librarian`, built for this after the referee's finding) was run on all
96 with the topic "transient": SIMBAD, NED through ADS, and four shelves (Wang et al. 2018; MIRONG, Jiang et al. 2021;
MacLeod et al. 2019; Graham et al. 2020). Every lookup answered, but for 69 of the 96 emptily: SIMBAD has no object, NED's
object is the AllWISE entry itself, and ADS knows no paper under that name.

| | n | |
|---|---|---|
| already studied | 8 | 4 on the Wang et al. 2018 shelf; 2 published changing-look AGN (J090902.36+133019.5, J120816.21+300738.3); PTF 10fgz; the variable Sy1 J095858.53+021459.2 (also named in Wang et al. 2018, outside their Table 1) |
| **declining in 2010-11, no transient literature found** | **31** | faded by more than 0.15 mag in W2 between AllWISE visits (control-corrected) |
| no change seen within 2010-11 | 57 | cooled across the gap only |

The 31: 26 have no paper in SIMBAD or ADS; 3 have a NED redshift (0.07, 0.07, 0.16); a fourth, z = 3.875 for
J104606.10+052919.7, is a photometric quasar-candidate estimate (Richards et al. 2009) that NED flags uncertain. None has
an SDSS spectrum; 18 are NED type G. Three are published NEOWISE variables classed AGN in VarWISE (Paz & Kirkpatrick
2026; a classifier label, not a spectrum): J110629.07-443500.9, J231443.35+274048.1, J031930.03+773451.7. 26 are in the
Secrest et al. 2015 AGN-candidate catalogue. The referee re-searched all 31 (SIMBAD and NED to 15", ADS full text,
VarWISE, Milliquas, VSX, and the Transient Name Server for 28) and found none published as a tidal disruption event,
supernova, nova or changing-look AGN. They dropped
0.63-1.71 mag in W2 by 2014. "No literature found" is not "new". SIMBAD does link Wang et al.'s table (all 14); the earlier miss
was not looking. What the Librarian could not see when this was run is membership of large catalogues, sources that
have moved, and papers its keywords miss (`reviews/claude-referee-librarian-2026-11-05.md`; fixes in progress). The shelves do
not yet hold Dou et al. 2016, Assef et al. 2018, Yang et al. 2018, Stern et al. 2018 or Masterson et al. 2024.

**Is it at the galaxy's centre? The test built for this does not work.** The AllWISE position (2010-11) was compared with
the CatWISE2020 position (dominated by the later years): an off-nuclear transient should move the centroid. PTF 10fgz
does (2.72"). But 22 of 131 unchanged control galaxies also shift by more than 1" (CatWISE splits galaxies into several
components), against 11 of the 96; the two are indistinguishable (Mann-Whitney p = 0.95): every shift above 1" in either sample is a
multi-component CatWISE match. Among single-component matches (32 here, 44 control) the control never exceeds 0.16" and 9
of the 32 do (p = 0.013, a cut chosen after seeing the data). Only PTF 10fgz lies beyond
the largest control shift (1.92"). An earlier status note that called ten sources "probably off-centre" is withdrawn.
Whether the 31 are nuclear is still untested; it needs optical images of the hosts.

**Are they galaxies?** Mostly yes (referee): 25 of the 31 are in Legacy Survey DR10 and all are resolved (21 Sérsic or de
Vaucouleurs, 4 round-exponential), and J060052.59-172416.0 is an edge-on galaxy in PS1. Five at |b| < 19° remain open:
J070453.55-425303.0, J153714.70-413353.8, J175925.99+005955.1, J000646.30+434554.8, J031930.03+773451.7. Their colours (W1 − W2 0.5-1.4, W2 − W3 2.1-3.8) are those of dusty
galaxies and AGN, and they are spread over the sky (median |b| 33°, 9 below 20°), which a Galactic population of dusty
stellar transients would not be. But Gaia sees most of them only as G ≈ 20-21 points or not at all, and a dust-forming
nova fading in the infrared (like KT Eri in H-0016) would pass every cut here; that caveat now applies to those five.

## 7. Not done

- Literature cross-match (Sheng et al. 2017, Stern et al. 2018, Yang et al. 2018 changing-look samples; the MIRONG
  outbursts of Jiang et al. 2021 start in 2013 and should not overlap).
- Pre-2010 state for the 80 without an SDSS spectrum (6dF, 2dF, LAMOST, NED), and 2MASS K against the 2010 W1.
- The light-curve shape after 2014 from the single exposures (the feature table says flat to 0.05 mag in W2).
- A rate: how many such decaying events per galaxy per year this implies, against published tidal-disruption and
  changing-look rates.
- For the 31: optical images of each host (is there a galaxy, and is the source at its centre?), a redshift, and shelves
  for Dou et al. 2016, Assef et al. 2018, Yang et al. 2018, Stern et al. 2018 and Masterson et al. 2024.
- The same-frame neighbour control covers 50 of the 96 (IRSA timed out on the rest).
- Nothing here is a claim. The referee's verdicts: section 4 holds with caveats, section 5's candidate did not hold,
  the population is not new, sections 2-3 hold with the quiet-cut correction.

## 8. Files

`scripts/nuclei_state.py`, `scripts/identify.py`, `scripts/epochs_2010.py`, `scripts/sdss_spectra.py`;
`work/epochs_2010.csv`, `work/epochs_2010_control.csv`, `work/sdss_spectra.csv`, `work/mep_*.csv`; `work/nuclei_cooled_all.csv`, `work/nuclei_heated_all.csv` (image
verdicts for every selected source), `work/cooled_id.csv`, `work/heated_id.csv`, `work/sql/`.
