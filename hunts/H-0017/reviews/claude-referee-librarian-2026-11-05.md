# Referee report: the Librarian and H-0017 section 6 (2026-11-05)

Basis: 110 live lookups; shelves against arXiv:1802.05105 and VizieR; all 31 re-searched (SIMBAD, NED, ADS full text, TNS, VarWISE, Milliquas, VSX, WISE AGN catalogues, Legacy Survey DR10).

## 1. The Librarian: FIT WITH FIXES

As a positive screen it works: 20/20 famous transients and 63/63 sample-table positions (Masterson 2024, Stern 2018, the shelved samples with shelves ignored) came back "studied"; failures are reported as unavailable; RA 0/360 works. But "catalogued" and "unlisted" are not safe as "nothing published", and "studied" says nothing about a well-known object.

1. **Proper motion ignored.** Barnard's Star at its AllWISE-epoch position: "Catalogued: WISEA J175747.94+044323.8 is in the archives with no paper attached", complete. At J2000: 933 papers. Fix: `prior_art(..., epoch=2000.0)`; in `simbad()` a second cone of radius + 11" x |epoch - 2000| restricted to `pmra*pmra+pmdec*pmdec > 2500`, propagated to the epoch; `vet.py` passes 2010.5.
2. **Large catalogues are invisible.** Three of H-0017's 31 are published NEOWISE variables classed "agn" in VarWISE (2026ApJS..284...41P); 26 are in Secrest+2015, 19 in Assef+2018 R90. Librarian: "catalogued". Fix: a source `catalogues()` (IRSA `varwiseext`; VizieR B/vsx, VII/294, J/ApJS/234/23, J/ApJS/221/12; a TNS cone); a variability or transient catalogue hit gives "studied".
3. **The ADS leg is hollow but says "empty".** It asks only NED's preferred name of the nearest object, which at a survey position is "WISEA J..." (108 of 109 H-0017 sources; ADS "empty" for 96). `object:"WISEA J044754.20-101042.7"` returns 0 papers, `object:"KT Eri"` 78. ADS translated all 9 names tried with `simbid:"0"`, unnoticed. Fix: query SIMBAD's `main_id` and every NED name in the cone; add NED's `z_bibcode`; status "not_asked" when nothing was asked; a note on `simbid:"0"`.
4. **"Studied" is noise.** 11/11 ordinary stars and galaxies (Vega, NGC 821...) are "studied": 1.8-5.8% of titles match (median 3%), so an unremarkable object with 23 papers is "studied" half the time, with 75, 90%. Causes: "variab*", rate papers attached to thousands of galaxies, the UGC catalogue's own title ("...Nova Regiae Societatis..."). Fix: select `ref.nbobject`; "studied" needs a topical paper with nbobject <= 500 or a shelf/catalogue hit; otherwise "mentioned".
5. **Object types unused; keywords miss.** SIMBAD otypes (SN*, No*, ev) never count. Nothing matches "Mrk 1018 returns to the shadows", "quasi-periodic eruptions", "Where's the flux?". Fix: transient otypes give "studied"; add `disrupt*`, `erupt*`, `kilonova*`, `awaken*`, `changing state*`, `variation*`, `burst*`.
6. **Silent truncation.** Above 1000 ADS papers (NGC 4472: 1373) the note is not printed and `complete` stays True. Fix: `complete=False`.
7. **Geometry.** 7" from Swift J1644+57: "Unlisted", complete (fix: name the nearest object within 30"). The summary names the nearest SIMBAD object ("[MKZ2003] XID 71" for NGC 4472). `_sep_arcsec` errs by up to pi/2 within 10" of a pole (fix: haversine).
8. **Shelves.** `graham2020_csq` holds 3 phantom positions from sign/typo errors in VizieR table B1 (J024533.60+000745.2, J025619.00+004501.0, J111930.40+312416.7: "studied" with nothing in any archive) and 61 literature CLQs (table A1) labelled as Graham's. `build_shelf.py`: take named tables, keep the paper's names. `wang2018`: 14/14 correct, but its comment is wrong: the paper names SDSS J095858.5+021459 outside Table 1. Loader: a zero-row shelf loads (fix: raise).

## 2. H-0017 section 6: HOLDS WITH CORRECTIONS

Counts and position-test numbers reproduce. Nothing found publishes any of the 31 as a TDE, supernova, nova or changing-look AGN. Replace:

- "Every lookup answered." -> "Every lookup answered, but for 69 of the 96 emptily: SIMBAD has no object, NED's object is the AllWISE entry itself, and ADS knows no paper under that name."
- "the variable Sy1 J095858.53+021459.2" -> add "(also named in Wang et al. 2018, outside their Table 1)".
- "26 have no paper attached at all, 4 have a redshift" -> "26 have no paper in SIMBAD or ADS; 3 have a NED redshift (0.07, 0.07, 0.16); a fourth, z = 3.875 for J104606.10+052919.7, is a photometric quasar-candidate estimate (Richards et al. 2009) that NED flags uncertain. Three are published NEOWISE variables classed AGN in VarWISE (Paz & Kirkpatrick 2026): J110629.07-443500.9, J231443.35+274048.1, J031930.03+773451.7. 26 are in the Secrest et al. 2015 AGN-candidate catalogue."
- "a table nobody linked (as Wang et al.'s was) is invisible until it is shelved" -> "SIMBAD does link Wang et al.'s table (all 14); the earlier miss was not looking. What the Librarian cannot see is membership of large catalogues, sources that have moved, and papers its keywords miss."
- "the two distributions are the same (Mann-Whitney p = 0.95)" -> "the two are indistinguishable (Mann-Whitney p = 0.95): every shift above 1" in either sample is a multi-component CatWISE match. Among single-component matches (32 here, 44 control) the control never exceeds 0.16"; 9 of the 32 do (p = 0.013, post hoc)."
- "Not shown object by object." -> "25 of the 31 are in Legacy Survey DR10 and all are resolved (21 Sersic or de Vaucouleurs, 4 round-exponential); J060052.59-172416.0 is an edge-on galaxy in PS1. Five at |b| < 19 deg remain open: J070453.55-425303.0, J153714.70-413353.8, J175925.99+005955.1, J000646.30+434554.8, J031930.03+773451.7."
- "(median |b| 34 deg, 8 below 20 deg)" -> "(median |b| 33 deg, 9 below 20 deg)"; to the dust-forming-nova sentence add "for those five".

## 3. Not checked

The OUP page (Table 1 read from arXiv v1); Open Supernova/TDE catalogues; an all-VizieR cone; the Flaires, Dou 2016, Yang 2018 and Sheng 2017 lists; J070453 and J153714 beyond DSS; the control sample's construction; TNS for 3 of the 31 (rate-limited: J222519, J184505, J053503; the 28 answered are empty).
