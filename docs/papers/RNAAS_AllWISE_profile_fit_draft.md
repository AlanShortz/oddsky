# DRAFT, not submitted. Research Notes of the AAS

**A silent failure of AllWISE profile-fit photometry on isolated stars, and a four-column test for it**

Alan Shortz¹

¹ Oddsky (open-source project)

---

We report that the AllWISE profile-fit magnitudes (w1mpro, w2mpro; Cutri et al. 2013) of a small set of clean, isolated,
unsaturated stars are wrong by 0.4-1.7 mag in both bands with no artifact or confusion flag set, while the same
catalogue's aperture magnitudes (w1mag, w2mag), 2MASS, the unWISE coadds and NEOWISE agree with each other. The failure
leaves a signature in four catalogue columns and is now a check in the Oddsky Skeptic.

**How it was found.** An all-sky comparison of the AllWISE 2010-11 magnitudes with the NEOWISE 2014-2024 baseline (visit
medians of the NEOWISE-R single exposures, Mainzer et al. 2014) for ~4.9 × 10⁷ quiet stars (≥ 12 visits, peak-to-peak < 0.3
mag, 8 ≤ W1 ≤ 14.5, |b| > 10°; the median offset between the two epochs is within 0.02 mag at these magnitudes) selected
19,818 stars whose W1 and W2 both stepped by > 0.4 mag in the same direction. 99.4% carry an AllWISE artifact, blend or
extended-source flag. Of the 110 that carry none, 48 are stars with a Gaia DR3 parallax. For each we measured the star's
flux in the unWISE coadds of the 2010-11 frames alone and of 2010-2020 (Lang 2014; Meisner et al. 2018; unwise.me): a real
step predicts a flux ratio far from unity, a catalogue error predicts 1.00. Forty-six of the 48 give 1.00 ± 0.03 in both
bands; the 2010 image flux equals the AllWISE aperture magnitude and NEOWISE to ≤ 0.08 mag and disagrees with the
profile-fit magnitude by 0.4-1.7 mag. The two exceptions are real (B stars whose circumstellar emission vanished between
2011 and 2014). An independent referee pass re-measured all of this with different apertures and reached the same numbers.

**What the failures look like in the catalogue.** For the 46, against 14 real steps and the 3,069 clean stars of a
1.5° control cone: profile-fit W1 signal-to-noise 5.4-13.7 where a clean source of the same magnitude has 39-48 (the
catalogue SNR is capped near 47.5 to W1 = 12.5 and falls to 38.9 at 14.5); |w1mag − w1mpro| = 0.44-1.67 mag (real steps
≤ 0.13); AllWISE position 0.35-2.6" from the Gaia DR3 position (real steps 0.05"); position uncertainty sigra 0.10-0.40"
(0.03-0.04"); apparent motion up to 2.4"/yr (median 0.85"/yr) with |pm|/σ ≈ 2; and in the multi-epoch table (allwise_p3as_mep)
per-frame uncertainties 0.09-0.27 mag with 15% null and 5% negative fluxes, frame scatter 0.07-0.35 mag, and reduced χ² of
0.8-8.7, against 0.024 mag, none, 0.02 mag and 1.3-1.6 for the real steps. The W2 profile fit is wrong in the same
direction in 82% of cases. There is no preference in ecliptic latitude, moon level, epoch or saturation. The picture is a
profile fit that converged off the star, in every frame, with the error propagating into the astrometry and the
apparent motion; cc_flags, nb, ext_flg, ph_qual and the catalogue w1rchi2 do not catch it. We have not identified why it
happens to these particular isolated stars.

**How common it is.** Of 2.06 × 10⁷ AllWISE sources with |b| > 10°, 8 ≤ W1 ≤ 14.5, cc_flags = 0000, nb = 1 and ext_flg = 0,
106,933 (0.52%) have |w1mag − w1mpro| > 0.4 and 10,995 (0.053%) also have w1snr < 15. Those 10,995 are two populations.
With 2MASS K as the arbiter (K − W1 ≈ 0-0.2 for a photosphere; 7,145 have K), 5,345 are aperture contamination by a
neighbour inside the 8.25" aperture (the profile fit is right; 58% at |b| < 20°; detected in 76% of frames), and 303 are
the failure described here (the aperture is right; 71% at |b| > 20°; detected in a median 47% of frames; AllWISE
position a median 1.31" from its own 2MASS association). A random 300 of the 10,995 through the image test gave 292 with
no real change between 2010-11 and 2014-2020 and a median AllWISE − Gaia offset of 1.67" for those whose image flux
matched the aperture. In that hemisphere of order 8,000 more are fits displaced inside blends where neither magnitude is the star's. Over both hemispheres at |b| > 10° the same tests applied to all 506,437 clean sources with |w1mag − w1mpro| > 0.4 or
w1snr < 20 give 631 sources whose K magnitude agrees with the aperture and not the profile fit and that fail at least two of
the catalogue tests (323 north, 308 south): 3 × 10⁻⁵ of clean sources. In a random 40 of them the 2010-11 unWISE image
magnitude matches the aperture magnitude in 36 and the profile fit in none, and the median AllWISE − Gaia offset is 0.86".
The list is released with this note (`hunts/H-0016/work/allwise_profile_fit_failures.csv`, tier A).

**The test.** For an AllWISE source at 8 ≤ W1 ≤ 16: (1) |w1mag − w1mpro| > 0.3; (2) w1snr below half the median SNR
for its magnitude (47.5 to W1 = 12.5, 45.6 at 13.0, 44.0 at 13.5, 41.5 at 14.0, 38.9 at 14.5); (3) detected in fewer than
60% of its W1 frames (w1nm/w1m); (4) position more than 0.35" from the Gaia DR3 position propagated to the AllWISE
epoch, for an isolated source. One failing test is a warning, two is a failure; saturated sources (W1 < 8) are exempt.
BD+28 4177, the brightest real step, passes all four (0.02 mag, SNR 47, 100%, 0.02"); the two strongest artifacts fail all
four (2.25" and 2.04" offsets). The check is `oddsky.data.allwise.diagnose` and runs on every case the Oddsky observatory
opens. Any comparison of AllWISE with CatWISE, NEOWISE or Gaia-based spectral-energy distributions should apply it, or
use the aperture magnitudes, before calling a star variable across the 2011-2013 gap.

*Data.* IRSA AllWISE Source Catalog and Multiepoch Photometry Table; NEOWISE-R single exposures; unWISE coadds
(unwise.me); Gaia DR3; 2MASS. Code and tables: Oddsky repository, hunts/H-0016.

**References.** Cutri R. M. et al. 2013, AllWISE Explanatory Supplement · Lang D. 2014, AJ 147, 108 · Mainzer A. et al. 2014,
ApJ 792, 30 · Meisner A. M., Lang D., Schlegel D. J. 2018, AJ 156, 69 · Schlafly E. F., Meisner A. M., Green G. M. 2019,
ApJS 240, 30 · Gaia Collaboration 2023, A&A 674, A1 · Skrutskie M. F. et al. 2006, AJ 131, 1163
