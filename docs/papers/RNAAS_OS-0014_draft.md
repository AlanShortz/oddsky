# DRAFT, not submitted. Research Notes of the AAS

**A three-month, near-total occultation of the G dwarf Gaia DR3 6733428488637673984 in 2017**

Alan Shortz¹

¹ Oddsky (open-source project)

---

We report a previously unrecognised occultation of the field G dwarf Gaia DR3 6733428488637673984
(2MASS J18330620−3607130, TIC 313603515; J2000 α = 18ʰ33ᵐ06.21ˢ, δ = −36°07′13.05″; G = 12.46,
BP−RP = 0.80, ϖ = 2.35 mas, d ≈ 420 pc, Teff ≈ 6000 K). It was found in an all-sky search of the NEOWISE-R
single-exposure catalog (Mainzer et al. 2014) for main-sequence stars that change in the infrared, like
ASASSN-21qj before its dimming (Kenworthy et al. 2023). The search covered 1.77 × 10⁸ AllWISE sources at
|b| ≥ 10° and recovered ASASSN-21qj blindly.

**The occultation.** ASAS-SN V photometry (Shappee et al. 2014; Kochanek et al. 2017) is constant at
V = 12.70 (rms 0.015 mag) until MJD 57828.4. It falls by 11% on MJD 57831.4 and reaches V = 15.46 on
57837.4. The star is then undetected on 17 epochs from MJD 57839.3 to 57911.4: each epoch gives V > 15.7,
and the stacked forced flux gives ΔV > 4.1 mag (3σ). It recovers to V = 14.64 by 57923.3 and to 12.68 by
57933.3. On the same frames, eight comparison stars stay within 0.14 mag. NEOWISE observed the infrared
ingress: over one day (MJD 57839.9–57840.9), W1 fell from 1.13 to 3.65 mag and W2 from 0.41 to 2.03 mag
below normal, so the occulter is more transparent at 4.6 µm. SkyMapper DR4 (Onken et al. 2024) measured the
star at its catalogued position on 2017-05-25 (MJD 57898.6) at g = 18.58, r = 18.30, i = 18.31 and
v = 19.1–19.7, which is 5.4–6.0 mag below normal and nearly grey; field-star zero points agree to
0.006 mag. ATLAS forced photometry (Tonry et al. 2018; Shingles et al. 2021) independently gives 0.2–0.4% of normal flux in c and o
from MJD 57856 to 57911 and resolves an 8-day egress (22% → 95% over MJD 57922–57930). In total the star was
fainter than normal for 92–105 days, more than 3 mag fainter for at least 72 days, and at least 99.6% occulted
at mid-event. ATLAS shows no repeat between 2018 and 2026. We found no Gaia Science Alert for this position.

**Geometry.** The occulted fraction rose from 11% to 92% in about 6 days. For a sharp edge crossing a
1.1–1.2 R☉ star, that implies a transverse speed of at least about 2 km s⁻¹ and an occulter at least about
0.1 AU across. Requiring the occulter to be smaller than its orbit gives a ≳ 1.4 AU; a circular orbit at that
speed gives a ≲ 250 AU around a ~1.1 M☉ star.

**Before and after.** The star is photospheric in AllWISE (2010; W1−W3 = −0.18 ± 0.16) and in NEOWISE from
2014 to 2017. Between MJD 58008 and 58204, 3–9 months after the occultation ended, W1−W2 reddened by about
0.15 mag and stayed redder through 2024. The 1.8 × 10⁷ photospheric stars in the same search drift by only
+0.02–0.03 mag in W2. Over the same period the optical photosphere brightened by about 0.05 mag (ASAS-SN;
SkyMapper in six filters), so we do not quote infrared-excess fractions or a dust temperature. Gaia DR3 lists
a variable radial velocity (robust amplitude 51 km s⁻¹ from seven transits), RUWE = 1.15 and
duplicated_source = 1, so this may be a spectroscopic binary. TESS full-frame images (Ricker et al. 2015)
show a ~1.8-day signal centred on the star in Sector 13.

**A century of plates.** DASCH DR7 (Grindlay et al. 2009, 2012) has 2,348 plates from 1889 to 1989, with the
star detected on 1,176. A 95-day event would have been caught 46% of the time. Phased on 2017, and combined
with ASAS-SN and NEOWISE, the plates exclude all periods shorter than 12.9 yr and 97.6% of periods between 1
and 30 yr; periods near 93 and 46.5 yr remain allowed. Three plates from April–May 1924 miss the star, but
two brighter neighbours are also missing from them, so we do not claim an earlier event.

**Interpretation.** The simplest explanation is a dusty, mostly opaque structure, such as a disk or dust
cloud around an unseen companion, crossing the star. Comparable systems include ε Aurigae (Kloppenborg et al.
2010), EE Cep (Gałan et al. 2012) and the giant Gaia17bpp (Tzanidakis et al. 2023). Its ingress observed in
the infrared, its nearly grey depth and a century of plate photometry make this a well-constrained case of a
long, single occultation of a field main-sequence star.

**Requested follow-up.** Spectroscopy for lithium, Hα, Na D and radial velocities; mid-infrared and SPHEREx
spectroscopy; Gaia DR4 epoch photometry and radial velocities (which cover 2017); and continued monitoring
(V ≈ 12.7). Data, code and a replayable analysis ledger are public at [repository URL], case OS-0014.

---

*Figure 1.* Left: ASAS-SN V, SkyMapper g/r/i/v and NEOWISE single exposures through the 2017 occultation
(magnitudes below normal; open triangles mark ASAS-SN non-detections). Right: NEOWISE W1, W2 and W1−W2,
2014–2024.

*Acknowledgements.* This work uses data from NEOWISE (NASA/JPL/IPAC), ASAS-SN, SkyMapper, Gaia
(ESA/DPAC), TESS (MAST), ATLAS and DASCH. DASCH was supported by NSF grants AST-0407380, AST-0909073 and
AST-1313370. Work on DASCH Data Release 7 received support from the Smithsonian American Women's History
Initiative Pool. The search and vetting used the open-source Oddsky toolkit, with AI agents
(Claude) working under deterministic artifact checks and independent referee and fact-check steps.

*References.* Gaia Collaboration, Vallenari, A., et al. 2023, A&A, 674, A1 · Gałan, C., et al. 2012, A&A,
544, A53 [verify] · Grindlay, J., et al. 2009, ASPC, 410, 101 · Grindlay, J., et al. 2012, IAU Symp., 285, 29 ·
Kenworthy, M., et al. 2023, Nature, 622, 251 · Kloppenborg, B., et al. 2010, Nature, 464, 870 [verify] ·
Kochanek, C. S., et al. 2017, PASP, 129, 104502 · Mainzer, A., et al. 2014, ApJ, 792, 30 · Onken, C. A., et
al. 2024, PASA, 41, e061 · Ricker, G. R., et al. 2015, JATIS, 1, 014003 · Shappee, B. J., et al. 2014, ApJ,
788, 48 · Shingles, L., et al. 2021, TNS AstroNote 2021-7 [verify] · Tonry, J. L., et al. 2018, PASP, 130, 064505 · Tzanidakis, A., et al. 2023, ApJ, 955, 69
