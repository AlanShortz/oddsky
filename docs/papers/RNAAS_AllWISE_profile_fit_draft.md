# DRAFT v7, not submitted. Research Notes of the AAS

**Unflagged AllWISE Sources with Profile-fit Magnitudes Wrong by 0.4–1.7 mag, and Their Correct Duplicates in the Reject Table**

Alan Shortz¹

¹ Oddsky (independent)

## Abstract

Comparing AllWISE (2010–11) with NEOWISE (2014–2024) photometry of 4.9 × 10⁷ quiet stars, I find AllWISE sources with no
contamination or blend flag whose profile-fit magnitudes (w1mpro, w2mpro) are wrong by 0.4–1.7 mag in both bands, while
the catalog's aperture magnitudes, the unWISE images and NEOWISE agree. Of 48 such stars with apparent changes of this
size, 46 are errors and two are real. For 19 of the 46 the AllWISE Reject Table holds a second extraction of the same
star, from the same Tile, with the correct magnitude at full signal-to-noise: duplicate resolution kept the displaced one.
The bad entries have a profile-fit signal-to-noise below half the normal value for their magnitude and positions
0.35–2.6″ from Gaia. Catalog tests and 2MASS select 631 such entries among 4.3 × 10⁷ clean sources (at least
1.5 × 10⁻⁵). I provide the list.

## 1. How the errors appear

I compared AllWISE profile-fit magnitudes (Cutri et al. 2013) with the median of the first three NEOWISE visits (Mainzer et
al. 2014) for 4.9 × 10⁷ stars at |b| > 10° with 8 ≤ W1 ≤ 14.5, at least 12 NEOWISE visits, and peak-to-peak NEOWISE
variation below 0.3 mag. The median W1 difference between the two epochs is within 0.03 mag at every magnitude. A total of
19,818 stars differ by more than 0.4 mag in both W1 and W2 with the same sign; 99.4% carry an AllWISE contamination, blend,
extended-source, saturation, or χ² flag, or are detected in fewer than 70% of their frames. Of the 110 that carry none, 48
have a Gaia DR3 parallax above 3σ (Gaia Collaboration 2023).

For each of the 48 I measured aperture fluxes in the unWISE coadds built from the 2010–11 frames alone and from 2010–2020
(Lang 2014; Meisner et al. 2022). A real change of the cataloged size predicts a flux ratio R of 0.23–2.5 in W1 for
these stars; a catalog error gives R = 1. Forty-six stars have R between 0.97 and 1.08 in both bands. For 44 of them the
AllWISE aperture magnitude (w1mag) agrees with NEOWISE to a median 0.02 mag while w1mpro is off by 0.44–1.73 mag (33 too
faint, 11 too bright). The other two are too bright by 0.5–0.7 mag in both w1mpro and w1mag; each has a star about 2 mag
brighter about 12″ away. The two real changes are B stars (B0.5 III, B4e) whose 2010–11 excess, presumably circumstellar,
had gone by 2014.

## 2. Signature

The 46 entries have w1snr = 5.4–13.7. In a control sample of 697 clean sources in one field at b > +80° the median w1snr
is 47.2 for W1 ≤ 12.5, falling to 38.9 at W1 = 14.5, with interquartile ranges of 1.3–2.0. The 46 lie
0.35–2.63″ (median 0.86″) from the Gaia positions, against 0.05″ for the two real stars; their position uncertainties are
0.10–0.42″; and their catalog apparent motions have a median of 0.85″ yr⁻¹. In the Multiepoch Photometry Table their
per-frame fits have median uncertainties of 0.09–0.27 mag (0.024 and 0.025 mag for the real stars), a median 15% null uncertainties,
5% negative fluxes, and a median reduced χ² of 3.2, so the per-epoch photometry cannot be used to check the catalog value.
All 46 have cc_flags = 0000, nb = 1, na = 0, ext_flg = 0 and w1rchi2 < 3; 39 have W1 ph_qual = 'B', as the low w1snr
implies, and seven have rel = 's'.

## 3. Cause

For 19 of the 46 the AllWISE Reject Table holds a second extraction of the same star from the same Atlas Tile,
0.46–2.25″ (median 0.97″) from the catalog position, with w1snr = 44.5–49.0 and w1mpro within 0.08 mag of NEOWISE; 18 are
detected in every frame, and 18 lie within 0.5″ of the Gaia position (median 0.06″). All 19 are marked as duplicates not selected for the Catalog (use_src = 0). The Explanatory
Supplements describe two steps. Same-Tile groups within 3.9″ are classified first, one extraction being kept and the
others rejected (rel = 'r'; Cutri et al. 2013, section V.4.b). Remaining groups within 2.5″, which may include several
detections from one Tile, are resolved by keeping the detection farthest from its Tile edge (Cutri et al. 2012, section
V.3.c). Two of the 19 good extractions were rejected by the first step. The other 17 pairs carry no same-Tile mark
although they lie within 3.9″; why is not established. For 16 of them best_use_cntr names the catalog entry, which in all
16 is the one farther from the Tile edge, by 0.01–1.2 pixels. The edge rule thus kept the displaced extraction. The
errors concentrate in a few Tiles: 204 of the 631 listed sources (Section 4) lie in 10 Tiles, 51 of them in Tile 2719m561.

Thirteen of the 46 have a second Gaia star within 8.5″ that is no more than 2.5 mag fainter (median separation 6″); four
of these are among the 19. For the 27 with no full signal-to-noise Reject Table entry the cause is not established.

## 4. Frequency and a test

Over both Galactic hemispheres at |b| > 10° there are 42,759,991 AllWISE sources with 8 ≤ W1 ≤ 14.5, cc_flags = 0000,
nb = 1 and ext_flg = 0. Among the 506,437 of these with |w1mag − w1mpro| > 0.4 or w1snr < 20, I select entries that fail at
least two of three catalog tests (below) and whose 2MASS (Skrutskie et al. 2006) K magnitude lies within 0.4 mag of w1mag
but not of w1mpro: 631 sources (323 north, 308 south), or at least 1.5 × 10⁻⁵, since the list recovers only 31 of the 46.
For 591 of them w1mag and w1mpro differ by more than 0.4 mag. For a random 40 the magnitude in the 2010–11 unWISE coadd
agrees within 0.3 mag with w1mag alone in 36 and with w1mpro alone in none, and for 14 the Reject Table holds a full signal-to-noise
duplicate.

The test, for 8 ≤ W1 ≤ 14.5: (1) |w1mag − w1mpro| > 0.3; (2) w1snr below half the median for the magnitude; (3)
w1nm/w1m < 0.6; (4) for a source with no close neighbor, a position more than 0.35″ from Gaia DR3 propagated to the AllWISE
epoch. The 46 were selected with w1nm/w1m ≥ 0.7; all fail (2) and all 33 with no close neighbor fail (4); 436 of the 631
fail (3). None of the 697 control sources fails two tests. Two failures reject an entry but do not say which magnitude is
wrong: 31,549 of the 506,437 fail at least two of tests (1)–(3), and where 2MASS decides it favors w1mpro for 16,749 and w1mag for
631. A Reject Table entry within 3″ with use_src = 0 and several times the w1snr settles it and gives the correct
photometry. Figure 1 shows tests (1) and (2). Comparisons of AllWISE with CatWISE, NEOWISE or Gaia-based spectral energy
distributions should apply the test and, for entries that fail, decide between w1mag and w1mpro with 2MASS, the Reject
Table or the images, before a star is called variable across 2011–2013.

**Figure 1.** (a) AllWISE aperture minus profile-fit W1 magnitude against the apparent change between AllWISE and NEOWISE
for the 48 unflagged stars; catalog errors lie on the line where the aperture magnitude equals NEOWISE, and rings mark
those with a correct duplicate in the Reject Table. (b) Profile-fit W1 signal-to-noise against W1 for the control sample,
the 46 errors, and the 631 listed sources. The data behind the figure include the list of 631 sources.

## Acknowledgments

This work used the AllWISE Source Catalog (doi:10.26131/IRSA1), Reject Table (doi:10.26131/IRSA136) and Multiepoch
Photometry Table (doi:10.26131/IRSA134), the NEOWISE-R Single Exposure Source Table (doi:10.26131/IRSA144), the unWISE
coadds, Gaia DR3, and 2MASS, served by IRSA, unwise.me, and ESA. The analysis and a first draft of the text were produced with the help
of AI tools (Claude AI models and the Oddsky tooling, oddsky.ai) under my direction. I reviewed the analysis and the text
and take full responsibility for the content.

## References

Cutri, R. M., et al. 2012, Explanatory Supplement to the WISE All-Sky Data Release Products
Cutri, R. M., et al. 2013, Explanatory Supplement to the AllWISE Data Release Products
Gaia Collaboration, Vallenari, A., et al. 2023, A&A, 674, A1
Lang, D. 2014, AJ, 147, 108
Mainzer, A., et al. 2014, ApJ, 792, 30
Meisner, A. M., Lang, D., Schlafly, E. F., & Schlegel, D. J. 2022, RNAAS, 6, 62
Skrutskie, M. F., et al. 2006, AJ, 131, 1163
