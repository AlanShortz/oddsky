# H-0019 preregistration: two points per star

Written 2026-11-09, before any long-lag pair of a star above the red-giant tip was computed. What had been looked at by then:
the Hubble Source Catalog (HSC v3) coverage probe (`scripts/01_probe.py`, still running), short-lag (< 10 d) pair statistics
in WLM, ESO410-005 and Sc22 (`04_measure.py --noise`, which skips long-lag AGB pairs), and the OGLE-III reference for the two
Magellanic Clouds (`scripts/02_lmc_model.py`).

## Question

Among stars brighter than the red-giant tip, is the fraction that changes by more than 0.3 mag between two visits the same in
every galaxy, or does it depend on the galaxy?

Most giant stars Hubble has resolved in other galaxies were measured only a few times. The Hubble Catalog of Variables
required five or more visits. Two visits say almost nothing about one star, but the distribution of the difference over a
population is a measurement of that population.

## Data and cuts (fixed in `scripts/04_measure.py`)

- Galaxies: Karachentsev+2013 within 4.5 Mpc with HSC v3 ACS/WFC F814W detections; cone of radius a26/2 (1.5' to 12').
- Detections: `Flags = 0`, `0.85 < CI < 1.30`, one detection per image for the star.
- Magnitudes: `MagAper2` (AB, 0.15"), relative to the galaxy's tip: the Sobel edge of the red-star luminosity function if it
  is significant (>= 4) and within 0.5 mag of the prediction from the catalogue distance, else the prediction.
- Colour from the summary table (F606W, F555W or F475W minus F814W, dereddened): red and blue as coded.
- One long pair per star: first and last detection, lag >= 100 d. One short pair per star: the closest two, lag < 10 d.
- The median difference of each image pair (all stars from 2.5 mag above to 1 mag below the tip, at least 30) is removed.
- Boxes: AGB = red, 0 to 1 mag above the tip. Bright AGB = red, 1 to 2 mag above. RGB control = red, 0 to 0.5 mag below.
  Blue control = blue, 0 to 2 mag above.
- A galaxy enters if it has at least 50 long pairs in the AGB box and 50 in the RGB control.

## Statistic

`E_x = f_AGB(|d| > x) - f_RGB(|d| > x)` on long pairs, x = 0.3 mag (primary), 0.2 and 0.5 (secondary). Errors are binomial.

## Reference

The same statistic from OGLE-III periods and I amplitudes in the central LMC and SMC, with Gaia DR3 members as the
denominator, sampled at two random times (`scripts/05_compare.py` repeats it with the two-visit mean magnitude and 0.03 mag
noise). First pass: E_0.3 about 0.028 (LMC) and 0.014 (SMC); E_0.2 about 0.057 and 0.033. Beyond 100 d the lag does not matter.

## Tests

- **T1, the tool works.** Pooled over galaxies, E_0.3 > 0 at 5 sigma or more. If not, stop: no population result is claimed.
- **T2, noise.** Pooled short pairs: f(|d| > 0.3) in the AGB box below 0.5%. Pooled long pairs in the blue control: below 1.5%.
  If either fails, results are reported as noise-limited.
- **T3, lag control.** Pooled E_0.3 from short pairs is within 2 sigma of zero.
- **T4, universality.** The pooled E_0.3 lies between 0.007 and 0.042 (half the SMC value to 1.5 times the LMC value).
- **T5, dependence on the galaxy.** Split the galaxies at the sample median of M_B. Prediction, from the SMC being lower than
  the LMC: the luminous half has the larger E_0.3. Claimed only if the pooled difference is positive with one-sided
  p < 0.01. Spearman's rho of E_0.3 against M_B is reported with it. Crowding should push luminous galaxies the other way
  (blends dilute changes), so a negative difference is not read as physics.

Everything else is exploratory and will be labelled so: other thresholds, the bright box, trends with lag, comparison with
published variable lists, per-star candidates.

## What would make me drop the interpretation

A positive T5 is a difference between galaxies, not yet a metallicity effect: age mix, crowding, and the tip placement all
change who sits in the box. Before any physical reading: repeat with the tip shifted by +-0.1 mag, with the colour cut moved,
with galaxies split by distance and by stellar density instead of luminosity.
