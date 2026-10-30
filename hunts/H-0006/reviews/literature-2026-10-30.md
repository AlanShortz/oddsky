# Literature and novelty check: H-0006, J160708.51-320101.1

Author: claude (literature check), 2026-10-30. Target: 2MASS J16070852-3201009 = Gaia DR3 6036595883378187008 =
TIC 94420199 = UCAC4 290-088054 = WISEA J160708.51-320101.1 (Kuruwita+2018 call it UCAC4-39156047; eRASS1 calls it
1eRASS J160708.6-320102). SIMBAD ICRS J2000 position: 241.785503, -32.016950. Gaia DR3 (ep 2016): 241.785424,
-32.017051. There are no EPIC or K2 data.
Claim tested: the W1-W2 (3-5 µm) excess vanished between Aug 2021 and Feb 2022 and stayed gone through 2024 (NEOWISE)
and 2025-26 (SPHEREx).
Raw outputs and scripts are in `literature-2026-10-30/`. No other repo file was changed, nothing was committed and
nothing was posted.

## (a) Verdict on novelty

**Not reported anywhere we could search.** The fading was not found in:

- **SIMBAD** (CfA mirror, live 2026-10-30): 5 references, all membership or census papers.
- **ADS:** full text and abstracts, 26 name and coordinate strings, all with 0 hits. The positive controls hit 2-53 papers.
- **VizieR** (idia mirror): 3" cones on 69 catalogues. The star is in 13 of them, and none is a variability or
  disk-change catalogue.
- **VarWISE** (IRSA TAP, all three tables, 30" cone): no match. The positive control works.
- **Gaia DR3** (ESA TAP).
- **Five arXiv sources grepped:** Mathews Ben+2026, Ben+2025, Kulkarni+2026, Polnitzky+2026, Gaidos+2024.
- **Web search:** 5 queries.

The phenomenon itself, a 3-5 µm inner-disk excess vanishing in a Sco-Cen disk, **has a published precedent**: PDS 70
(Gaidos+2024). There the excess vanished for up to one year and then came back. What is new here is the length (at
least 4.5 yr, still off in Sep 2026) and the star.

## (b) Every hit, with relevance

SIMBAD (`simbad_cfa_sim-id.txt`, `simbad_cfa_tap.txt`). Otype is `Y*?`, with no spectral type and no variability
measurements. Parents are `[RGM2023] SigMA 7` (ρ Sco) and the Upper Sco association. The complete bibliography:

| bibcode | title | relevance |
|---|---|---|
| 2018MNRAS.480.5099K | Multiplicity of disc-bearing stars in Upper Scorpius and Upper Centaurus-Lupus | 4 RVs and Hα EWs (2015-17); see (c) |
| 2018A&A...620A.172Z | 3D mapping of young stars in the solar neighbourhood with Gaia DR2 | PMS membership only |
| 2021ApJ...917...23K | SPYGLASS I | young-star membership, age 13.5 Myr |
| 2023MNRAS.522.1288B | Substructure, supernovae, and a time-resolved star formation history for Upper Scorpius | membership only |
| 2023A&A...677A..59R | SigMA for hierarchical structures ... Sco-Cen | ρ Sco cluster (SigMA 7) |

SIMBAD's bibliography leaves out Luhman 2022a/b, Kerr+2023 and Marton+2016, all of which list the star in VizieR
tables. These are catalogue-only mentions.

VizieR rows that contain the star (`vizier_targeted_3arcsec.txt`):

| catalogue | what it says about the star | data epoch |
|---|---|---|
| J/AJ/163/25, Luhman 2022b, **2022AJ....163...25L** | excess in W2, W3 and W4; **Disk = "full"** | AllWISE (2010) |
| J/AJ/163/24, Luhman 2022a, 2022AJ....163...24L | Sco-Cen candidate; **no spectral type given** | Gaia EDR3 |
| J/MNRAS/480/5099, Kuruwita+2018 | 4 epochs at MJD 57236-57908: RV 3.56, 1.31, 6.20, 10.19 km/s; Hα EW -1.24 to -1.97 Å; "Temp. SpT" M1.5 | 2015-17 |
| J/MNRAS/458/3479, Marton+2016 (2016MNRAS.458.3479M) | Class I/II YSO candidate | AllWISE |
| J/A+A/677/A59 and J/A+A/709/A181 (Ratzenböck+2023, Großschedl+2026) | ρ Sco, 13.7 Myr; Gaia RV 4.0 ± 2.3 km/s | Gaia |
| J/ApJ/954/134, Kerr+2023 (2023ApJ...954..134K) | Pmem 0.93 | Gaia |
| J/ApJ/917/23; J/A+A/620/A172; J/A+A/664/A175; J/A+A/623/A112; J/A+A/661/A40 (eRASS1 X-ray, CRate 0.12 ct/s) | membership or PMS only | — |
| B/vsx/vsx | "Gaia DR3 6036595883378187008", type YSO, G 13.63-13.97 | Gaia DR3 |
| I/358/vclassre | Gaia DR3 class YSO, score 0.87 | 2014-17 |

Gaia DR3 TAP (`gaia_dr3_tap.txt`):
- phot_variable_flag = VARIABLE.
- G range 0.34 mag, skewness +1.67 (fading excursions, which fits the dipper reading).
- RUWE 1.12, ipd_frac_multi_peak = 0, non_single_star = 0.
- rv_chisq_pvalue is null because grvs = 12.05 is fainter than the 12.0 limit.

ADS (`ads_names.txt`, `ads_topics.txt`, `ads_abstracts.txt`). Every name query returned 0:
- "2MASS J16070852-3201009", "J16070852-3201009", "16070852-3201009"
- "J160708.51-320101.1/.2", "160708.51-320101"
- the Gaia id
- "TIC 94420199", "94420199"
- "UCAC4 290-088054", "UCAC4-39156047", "39156047"
- "J1607-3201", "J160708-320101", "J160708.5-320101", "1607085-320101", "J16070852", "160708.52-320100.9"
- "J160708.6-320100", the eRASS names, the WISE/WISEA names, and the ASAS-SN id

Positive controls: "J16042165-2130284" returned 40 hits, "J1604-2130" 53, "TYC 8241 2652 1" 31, "ASASSN-21qj" 32 and
"J16064385-1908056" 3.

Caveat: "16064385-1908056" without the leading J returned 0 although the J form returned 3. ADS also does not index
machine-readable tables: Luhman 2022b lists this star and is not found. So ADS misses catalogue-only mentions, and the
VizieR checks above cover that gap.

Topical hits read (abstracts; none mentions this star):

| bibcode | relevance |
|---|---|
| 2024ApJ...966..167G Gaidos+ "The Dynamic, Chimeric Inner Disk of PDS 70" | **Closest precedent.** A Sco-Cen K7 star's 3.4/4.6 µm disk emission "(nearly) disappears for ~1 yr" around MJD 57000 in NEOWISE, then returns. Their explanations: a weakened stellar dipole lets the disk edge move inside the sublimation radius, or the inner-dust geometry changes. They exclude a halt in accretion (viscous time ≳10² yr). |
| 2026arXiv260913955M Mathews Ben+ NEOWISE variability of disks older than 10 Myr | Same kind of study; parent sample is 32 Cantat-Gaudin clusters (Ben+2025, 2025MNRAS.541.2246B) and **contains no Upper Sco/ρ Sco cluster**, so the star is not in it |
| 2026ApJ..1000..188K Kulkarni+ 27-yr IR YSO survey | "fading" class exists; star not in source; Spitzer-YSO sample |
| 2026ApJS..284...41P VarWISE | star absent (see below) |
| 2025ApJS..281...64Z Zhang+, 2026ApJS..284...59K Kang+ (unTimely variables) | **Cannot contain the step**: unTimely ends in 2020 (2023AJ....165...36M) |
| 2021ApJ...920..132P Park+; 2024ApJ...962...38L Lee+ | NEOWISE YSO variability; data end before the 2021-22 step; star-forming-region samples |
| 2025ApJS..278...10N Neha+ (SPICY YSOs) | Galactic-plane sample; J/ApJS/278/10 has 0 rows here |
| 2026A&A...707A.216P Polnitzky+ Sco-Cen disk lifetimes | AllWISE-based; its sources table does not list this star (positive control within 30' works; reason not checked) |
| 2025ApJ...978...34X Xie+ (T Cha) | Inner-wall destruction during an outburst; 5-10 µm dropped by ~2/3 over 17 yr |
| 2026ApJ...999L..31T Thanathibodee+ (CVSO 1942) | The reverse case: ≤10 µm excess appeared within about 2 weeks (1400 K dust) |
| 2026arXiv261036223P Perez Paolino+ | The only SPHEREx young-star paper found (CMa N); it finds SPHEREx fluxes agree with 2MASS/WISE to 3-6% |
| 2020A&A...633A..37S, 2016ApJ...816...69A, 2018AJ....156...71C, 2017MNRAS.470..202B | Upper Sco dipper context; star absent from the K2 catalogues (no K2 data) |

VarWISE (`irsa_varwise.txt`):
- No source within 30" in either the pure or the extended table.
- Control: the query finds VarWISE J160658.04-320253.1 2.9' away.
- VarWISE does carry a `yso` class (342 sources within 5° of Upper Sco).
- RX J1604.3-2130A is not in it either, so VarWISE is incomplete for YSOs.

## (c) What changes or weakens the claim

1. **"M1.5" is not a spectral classification.** In Kuruwita+2018, "Temp. SpT" is the RV cross-correlation template.
   Luhman 2022a gives no spectral type. Gaia GSP-Phot gives Teff 3700 K, which is consistent with about M1, but the
   README's "spectral type M1.5 (Kuruwita et al. 2018)" should read "best-fit RV template M1.5". No published optical
   or IR spectral type exists.
2. **The spectroscopic-binary hint is weaker than the README says.** Kuruwita+2018 computed a Bayes factor of **0.86**
   for this star, marked "(N)", against a binary threshold of 300, with Δv_r = 8.88 km/s over 4 epochs. Their own
   analysis does not favour a binary. Gaia shows RUWE 1.12 and no multi-peak IPD; the RV-scatter test is not computed at
   grvs 12.05. Keep "possible SB" only as "RV range 9 km/s over 4 epochs; not significant in Kuruwita's Bayesian test".
3. **Temporary loss has a precedent in the same association.** PDS 70 (Gaidos+2024) lost its 3-5 µm inner-disk
   emission in NEOWISE for up to a year and got it back.
   - Novelty should therefore rest on the duration (≥4.5 yr, with SPHEREx), the full-disk M star and the
     undimmed photosphere, not on the vanishing itself.
   - The return case means "hidden or dormant, then returning" must stay open. Six-monthly NEOWISE cadence also hides
     short returns.
4. **The "full" class is from 2010 data.** Luhman 2022b used AllWISE (2010). Any newer disk census built on AllWISE or
   CatWISE describes the pre-step state, so these catalogues neither confirm nor contradict the change.
5. **Weak Hα.** Kuruwita's EWs (-1.2 to -2.0 Å, 2015-17) support a weakly accreting or non-accreting inner disk. This
   is consistent with the README; no change needed.
6. Nothing found contradicts the step itself: no published post-2021 photometry or spectroscopy of this star exists.

## (d) Key references an astronomer would expect (bibcodes verified in ADS)

- 2012Natur.487...74M: Melis+ 2012, the rapid disappearance of TYC 8241 2652 1's warm dust. Follow-up: 2017A&A...598A..82G (Günther+, "no smoking gun yet").
- 2024ApJ...966..167G: Gaidos+ 2024, PDS 70. The inner-disk 3-5 µm emission disappeared in NEOWISE for about 1 yr; this is the closest analogue.
- 2021ApJ...920..132P: Park+ 2021, NEOWISE YSO variability classes, including "drop".
- 2011ApJ...728...49E (Espaillat+ 2011, seesaw), 2009ApJ...704L..15M (Muzerolle+ 2009, LRLL 31) and 2012ApJ...748...71F (Flaherty+ 2012): inner-disk scale-height variability.
- 2016ApJ...816...69A (Ansdell+ 2016) and 2017MNRAS.470..202B (Bodman+ 2017): dippers and inclined inner disks in Upper Sco.
- 2022AJ....163...25L (Luhman 2022b) for the disk class, and 2018MNRAS.480.5099K (Kuruwita+ 2018) for the RVs and Hα.
- Optional: 2023Natur.622..251K (ASASSN-21qj; IR afterglow of a collision, a debris rather than protoplanetary case), 2025ApJ...978...34X (T Cha wall destruction), 2026ApJ...999L..31T (rapid appearance of inner dust), and 2026ApJS..284...41P (VarWISE).

## (e) Still unchecked

- **CDS SIMBAD** timed out (40 s). The CfA mirror answered and is a live CDS copy, so this gap is small.
- **CDS and CfA VizieR** timed out. The **all-catalogue VizieR cone failed**: 502 errors, or output truncated at I/317.
  - Only the 69 named catalogues were checked.
  - These were not found on the idia mirror: J/ApJS/281/64, J/ApJ/962/38, J/ApJS/284/59, J/ApJS/284/41,
    J/ApJ/1000/188, J/AJ/172/185, J/A+A/712/A222, J/MNRAS/541/2246, J/MNRAS/522/1288 and I/358 vari_summary. Gaia
    vari_summary was checked via ESA TAP instead.
- **Contreras Peña and Lee NEOWISE catalogues**: abstracts read; tables not queried. Both end before 2021.
- **Paywalled and conference full text**: AAS abstracts (Banks, Westman, Eyestone) were read as abstracts only.
- **ATels, TNS, AAVSO forums, and the SPHEREx team's internal variability products** were not searched.
- **ADS cannot see machine-readable tables**, so a catalogue-only listing in a journal not mirrored by VizieR would be
  missed.
- **arXiv submissions from the last few days** may not be indexed in ADS yet.
