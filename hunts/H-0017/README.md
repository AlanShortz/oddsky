# H-0017: nuclei that changed state across the WISE gap

Opened 2026-11-05 from H-0016 section 5.5. WISE stopped observing in February 2011 and resumed in December 2013. H-0016
found galaxy nuclei that were AGN-coloured (W1 − W2 ≥ 0.4) in AllWISE (2010-11) and were fainter, bluer and quiet in every
NEOWISE year from 2014 to 2024: a nucleus that was radiating warm dust in 2010 and was not afterwards. The question here is
whether that is a one-way street. If nuclei simply wander between states, as many should have heated across the gap as
cooled.

**Status: first census done, both directions, with the same image test on every source. 96 nuclei cooled and 13 heated.
The imbalance is real in the data and is not yet interpretable as a rate, for the reason in section 3.**

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

## 4. Not done

- Literature cross-match (Sheng et al. 2017, Stern et al. 2018, Yang et al. 2018 changing-look samples; the MIRONG
  outbursts of Jiang et al. 2021 start in 2013 and should not overlap).
- Pre-2010 state per object: 2MASS K against the 2010 W1, and archival optical spectra. A nucleus with no AGN lines
  before 2010 was a flare; one with broad lines turned off.
- No referee has seen this. Nothing here is a claim.

## 5. Files

`scripts/nuclei_state.py`, `scripts/identify.py`; `work/nuclei_cooled_all.csv`, `work/nuclei_heated_all.csv` (image
verdicts for every selected source), `work/cooled_id.csv`, `work/heated_id.csv`, `work/sql/`.
