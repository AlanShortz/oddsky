# H-0017: nuclei that changed state across the WISE gap

Opened 2026-11-05 from H-0016 section 5.5. WISE stopped observing in February 2011 and resumed in December 2013. H-0016
found galaxy nuclei that were AGN-coloured (W1 − W2 ≥ 0.4) in AllWISE (2010-11) and were fainter, bluer and quiet in every
NEOWISE year from 2014 to 2024: a nucleus that was radiating warm dust in 2010 and was not afterwards. The question here is
whether that is a one-way street. If nuclei simply wander between states, as many should have heated across the gap as
cooled.

**Status (2026-11-05): two results, neither refereed as a claim yet.** (1) After the same image test on every source,
96 nuclei cooled and 13 heated. (2) The cooled nuclei were caught on the way down: between their two AllWISE visits in
2010-11, about 190 days apart, they faded by a median 0.10 mag in W2 more than an unchanged control sample, 45 of 96
significantly, against 3 that brightened. The 2010 state was a decaying episode, not a steady state that ended later.

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

Positive control: one of the 96 is the host of **PTF 10fgz**, a supernova discovered in 2010 (SIMBAD type SN*, z = 0.01).
The selection recovers a known 2010 transient without being told about it.

Identities of the 96: 15 carry a SIMBAD AGN or emission class (6 Sy1, 3 Sy2, a QSO, a LINER, an emission-line galaxy, a
radio galaxy, a radio and an X-ray source), 11 are plain galaxies, 1 is the supernova host, and 69 have no SIMBAD entry.
Of the 13 heated, 12 have no SIMBAD entry. Tables: `work/cooled_id.csv`, `work/heated_id.csv`.

## 3. What the 96 : 13 does and does not mean

- **Not the quiet cut alone.** Of 532,077 sources that pass the heated side's colour and magnitude cuts, 81% pass the
  quiet cut; of 48,461 sources that were red in 2010 and blue afterwards, 93% do (`work/sql/quiet_cut_counts.sql`). On
  population averages the cut favours coolers by a factor 1.2, not 7.
- **But the heated nuclei sit against the cut.** Their W2 peak-to-peak is 0.24-0.39 mag at W2 ≈ 13.5, well above the
  noise there, against a limit of 0.4. A nucleus that turned on keeps varying, and the ones that varied by more than
  0.4 mag are not in the sample. The 13 are a lower limit of unknown depth.
- **So the comparison is between "was on in 2010, then off and steady for ten years" and "was off in 2010, then on and
  steady for ten years".** The second is a rare kind of object whatever the physics. The imbalance says the quiet
  low state is the resting state and the red, bright state is the excursion. It does not say whether the excursions are
  decaying flares (tidal disruption or dust echoes, as LEDA 1815030 looks) or AGN that switched off.
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

| | n | median W2 change in 2010-11 | fading > 0.1 mag and > 3σ | brightening likewise | vs control (Mann-Whitney p) |
|---|---|---|---|---|---|
| control | 128 | 0 (by construction) | 2 | 4 | |
| **cooled** | 96 | **+0.100 mag** (W1 +0.096) | **45** | 3 | 1.6 × 10⁻¹² |
| heated | 13 | −0.072 mag (W1 −0.053) | 0 | 0 | 0.005 |

- 33 of the 96 faded by more than 0.2 mag in half a year and 11 by more than 0.3.
- The median rate, 0.18 mag/yr in W2, carried across the 3.4-year gap gives 0.6 mag; the observed median drop across the
  gap is 0.74 mag. A steady decline that began before or during 2010 accounts for the sample without a later switch-off.
- The 2010 fade and the drop across the gap are weakly correlated (Spearman ρ = 0.24, p = 0.017).
- The heated nuclei were already rising in 2010 (by 0.07 mag relative to control).
- The supernova host (PTF 10fgz) faded 0.47 mag in W2 between its two visits, as a 2010 transient should.
- The selection has no arrow of time inside 2010: it uses the AllWISE mean against the 2014-15 baseline. A source that
  flickered at random would be as likely to brighten between the two visits as to fade.

**Reading.** At least half of the cooled nuclei were mid-infrared transients in decline when WISE first looked: events
that peaked before or during 2010. Searches for nuclear mid-infrared flares in NEOWISE data need a rise after 2014 and
cannot see these. What they are (dust echoes of tidal disruptions, obscured supernovae, AGN that were shutting down) is
not settled by the fade alone.

## 5. What they were before 2010 (`scripts/sdss_spectra.py`)

16 of the 96 have an SDSS spectrum; 13 of those were taken before 2010 (all queries answered):

| pre-2010 SDSS class | n | examples |
|---|---|---|
| narrow-line AGN (GALAXY/AGN) | 5 | J130819.11+434525.6 (fading 0.64 mag in W2 within 2010), J100933.13+232255.7 |
| broad-line QSO | 3 | J090902.36+133019.5 |
| star-forming or starburst galaxy | 3 | **J142401.66+295028.4** |
| galaxy, no subclass | 2 | J150831.61+062924.6 |

So the sample is mixed: 8 of 13 already hosted an AGN, 5 did not. The strongest non-AGN case is J142401.66+295028.4
(z = 0.086, a star-forming spectrum in 2006): W2 = 11.92 in AllWISE, fading 0.51 mag between its two 2010 visits, 1.31 mag
fainter and 0.74 mag bluer by 2014, flat since. A flare of that size in a galaxy with no AGN lines is a candidate tidal
disruption echo or an obscured luminous transient, and the first object here that deserves a case of its own.

## 6. Not done

- Literature cross-match (Sheng et al. 2017, Stern et al. 2018, Yang et al. 2018 changing-look samples; the MIRONG
  outbursts of Jiang et al. 2021 start in 2013 and should not overlap).
- Pre-2010 state for the 80 without an SDSS spectrum (6dF, 2dF, LAMOST, NED), and 2MASS K against the 2010 W1.
- The light-curve shape after 2014 from the single exposures (the feature table says flat to 0.05 mag in W2).
- A rate: how many such decaying events per galaxy per year this implies, against published tidal-disruption and
  changing-look rates.
- No referee has seen this. Nothing here is a claim.

## 7. Files

`scripts/nuclei_state.py`, `scripts/identify.py`, `scripts/epochs_2010.py`, `scripts/sdss_spectra.py`;
`work/epochs_2010.csv`, `work/epochs_2010_control.csv`, `work/sdss_spectra.csv`, `work/mep_*.csv`; `work/nuclei_cooled_all.csv`, `work/nuclei_heated_all.csv` (image
verdicts for every selected source), `work/cooled_id.csv`, `work/heated_id.csv`, `work/sql/`.
