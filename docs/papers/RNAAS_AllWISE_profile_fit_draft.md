# DRAFT v4, not submitted. Research Notes of the AAS

**Unflagged AllWISE Sources with Profile-fit Magnitudes Wrong by 0.4–1.7 mag, and Their Correct Duplicates in the Reject Table**

Alan Shortz¹

¹ Oddsky (independent)

## Abstract

Comparing AllWISE (2010–11) with NEOWISE (2014–2024) photometry of 4.9 × 10⁷ quiet stars, I find clean, unflagged AllWISE
sources whose profile-fit magnitudes (w1mpro, w2mpro) are wrong by 0.4–1.7 mag in both bands, while the catalog's aperture
magnitudes, 2MASS, the unWISE images and NEOWISE agree with one another. Of 48 unflagged stars with apparent changes of
this size, 46 are such errors and two are real. For 19 of the 46 the AllWISE Reject Table holds a second extraction of the same star, from the same Tile, with the
correct magnitude at full signal-to-noise: duplicate resolution kept the worse one. The bad entries have a profile-fit signal-to-noise below
half the normal value for their magnitude, an aperture-minus-profile difference above 0.3 mag, and positions 0.35–2.6″
from Gaia. These tests and 2MASS select 631 such entries among 4.3 × 10⁷ clean sources (1.5 × 10⁻⁵). I provide the list.

## 1. How the errors appear

I compared AllWISE profile-fit magnitudes (Cutri et al. 2013) with the median of the first three NEOWISE visits (Mainzer et
al. 2014) for 4.9 × 10⁷ stars at |b| > 10° with 8 ≤ W1 ≤ 14.5, at least 12 NEOWISE visits, and peak-to-peak NEOWISE
variation below 0.3 mag. The median W1 difference between the two epochs is within 0.03 mag at every magnitude. A total of
19,818 stars differ by more than 0.4 mag in both W1 and W2 with the same sign; 99.4% carry an AllWISE contamination, blend,
extended-source, saturation, or χ² flag, or are detected in fewer than 70% of their frames. Of the 110 that carry none, 48
have a Gaia DR3 parallax above 3σ (Gaia Collaboration 2023).

For each of the 48 I measured aperture fluxes in the unWISE coadds built from the 2010–11 frames alone and from 2010–2020
(Lang 2014; Meisner et al. 2018). A real change gives a flux ratio R far from unity (0.23–2.5 in W1 for these stars); a
catalog error gives R = 1. Forty-six stars have R between 0.97 and 1.08 in both bands. For 44 of them the AllWISE aperture
magnitude (w1mag) agrees with NEOWISE to a median 0.02 mag while w1mpro is off by 0.44–1.73 mag (33 too faint, 11 too
bright). The other two are too bright by 0.5–0.7 mag in both w1mpro and w1mag; each has a star about 2 mag brighter about 12″ away. The
two real changes are early B stars whose 2010–11 circumstellar excess had gone by 2014.

## 2. Signature

The 46 entries have w1snr = 5.4–13.7. In a control sample of 697 clean sources the median w1snr is 47.2 for W1 ≤ 12.5,
falling to 38.9 at W1 = 14.5, with interquartile ranges of 1.3–2.0. Their AllWISE positions lie 0.35–2.63″ (median 0.86″) from the Gaia
positions, against 0.05″ for the two real stars; their position uncertainties are 0.10–0.42″; and their catalog apparent
motions have a median of 0.85″ yr⁻¹. In the Multiepoch Photometry Table their per-frame fits have median uncertainties of
0.09–0.27 mag (0.02 mag for the real stars), a median 15% null uncertainties, 5% negative fluxes, and a median reduced χ² of
3.2, so the per-epoch photometry cannot be used to check the catalog value. All 46 have cc_flags = 0000, nb = 1, na = 0,
ext_flg = 0 and w1rchi2 < 3.

## 3. Cause

For 19 of the 46 the AllWISE Reject Table holds a second extraction of the same star from the same Atlas Tile,
0.46–2.25″ (median 0.97″) from the catalog position, with w1snr = 44.5–49.0 and w1mpro within 0.08 mag of NEOWISE; 18 are
detected in every frame. All 19 are marked as duplicates not selected for the Catalog (use_src = 0), and for 17 of them
best_use_cntr names the erroneous catalog entry as the one selected. The Explanatory Supplement (section V.4.b) describes
two kinds of duplicate: small-separation same-Tile groups, in which a later, fainter extraction is pulled toward a
brighter one and is rejected (rel = 'r'), and Tile-overlap duplicates, for which the apparition farthest from its Tile
edge is kept whatever its quality. Here 16 of the 19 good extractions carry no same-Tile mark; the catalog entry is the
later extraction in 17 cases and the one farther from the Tile edge in 17, by at most 1.6 pixels. A displaced second
extraction of the star appears to have been resolved against the good one by the geometric rule. The errors concentrate
in a few Tiles: 204 of the 631 listed sources (Section 4) lie in 10 Tiles, 51 of them in Tile 2719m561.

Thirteen of the 46 have a second Gaia star within 8.5″ that is no more than 2.5 mag fainter (median separation 6″); four
of these are among the 19. For the 27 with no full signal-to-noise Reject Table entry the cause is not established.

## 4. Frequency and a test

Over both Galactic hemispheres at |b| > 10° there are 42,759,991 AllWISE sources with 8 ≤ W1 ≤ 14.5, cc_flags = 0000,
nb = 1 and ext_flg = 0. Among the 506,437 of these with |w1mag − w1mpro| > 0.4 or w1snr < 20, I select entries that fail at
least two of three catalog tests (below) and whose 2MASS K magnitude lies within 0.4 mag of w1mag but not of w1mpro: 631
sources (323 north, 308 south), or 1.5 × 10⁻⁵; for 591 of them w1mag and w1mpro differ by more than 0.4 mag. For a random 40
the 2010–11 unWISE magnitude matches w1mag in 36 and w1mpro in none. For 14 of the 40 the Reject Table holds a full signal-to-noise duplicate. A magnitude disagreement alone is not
sufficient: 23,492 clean sources have |w1mag − w1mpro| > 0.4 and w1snr < 15, and in most of those with 2MASS photometry it
is the aperture, contaminated by a neighbor, that is wrong.

The test, for 8 ≤ W1 ≤ 14.5: (1) |w1mag − w1mpro| > 0.3; (2) w1snr below half the median for the magnitude; (3)
w1nm/w1m < 0.6; (4) for a source with no close neighbor, a position more than 0.35″ from Gaia DR3 propagated to the AllWISE
epoch. One failure is a warning and two a rejection. The 46 were selected with w1nm/w1m ≥ 0.7; all fail (2) and 45 fail (4), while
none of the 697 control sources fails two tests; 436 of the 631 fail (3). A Reject Table entry within 3″ with use_src = 0 and several times the w1snr confirms the diagnosis and gives the correct
photometry. Figure 1 shows tests (1) and (2). Comparisons of AllWISE with CatWISE, NEOWISE or
Gaia-based spectral energy distributions should apply the test, or use the aperture magnitudes, before a star is called
variable across 2011–2013.

**Figure 1.** (a) AllWISE aperture minus profile-fit W1 magnitude against the apparent change between AllWISE and NEOWISE
for the 48 unflagged stars; catalog errors lie on the line where the aperture magnitude equals NEOWISE, and rings mark
those with a correct duplicate in the Reject Table. (b) Profile-fit
W1 signal-to-noise against W1 for a control sample, the 46 errors, and the 631 listed sources. The data behind the figure
include the list of 631 sources.

## Acknowledgments

This work used the AllWISE and NEOWISE data products of the Wide-field Infrared Survey Explorer, the unWISE coadds, Gaia
DR3, and 2MASS, served by IRSA, unwise.me, and ESA. The analysis and a first draft of the text were produced with the help of AI tools (Claude AI models and the Oddsky
tooling, oddsky.ai) under my direction. I reviewed the analysis and the text and take full responsibility for the content.

## References

Cutri, R. M., et al. 2013, Explanatory Supplement to the AllWISE Data Release Products
Gaia Collaboration, Vallenari, A., et al. 2023, A&A, 674, A1
Lang, D. 2014, AJ, 147, 108
Mainzer, A., et al. 2014, ApJ, 792, 30
Meisner, A. M., Lang, D., & Schlegel, D. J. 2018, AJ, 156, 69
Skrutskie, M. F., et al. 2006, AJ, 131, 1163
