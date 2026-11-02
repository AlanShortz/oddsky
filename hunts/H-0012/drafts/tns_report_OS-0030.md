# DRAFT — NOT FILED. TNS AT report for Oddsky case OS-0030 (NGC 3239 mid-infrared transient)

**Status: draft only. Nothing has been submitted to TNS (production or sandbox).** Prepared 2026-11-01/02 from the
validation in `tns_OS-0030_validation.md`; every number below is recomputed there
(`tns_validation/recompute_numbers.py`). Fields follow the order of the TNS AT-report form / bulk-report JSON
(TNS2.0 Bulk API manual, Jan 2025, §5.5). Codes in brackets are from TNS's AUX tables as mirrored on GitHub;
**pick the values from the live drop-downs when filing** and check they match.

## Header

| # | field (form label / JSON key) | value | note |
|---|---|---|---|
| 1 | RA (`ra.value`, `ra.error`, `ra.units`) | **10:25:09.894** (156.291224°), error **0.1**, arcsec | HST WFC3/UVIS 2021-02-16 point source, Gaia-tied (±0.004" statistical; 0.1" quoted to cover the Gaia tie and the identification). See remarks for the WISE centroid. |
| 2 | Dec (`dec.value`, `dec.error`, `dec.units`) | **+17:09:49.60** (+17.163778°), error **0.1**, arcsec | |
| 3 | Reporting group (`reporting_groupid`) | **ALAN TO PROVIDE**: "None" [0], or an "Oddsky" group once TNS approves it | No Oddsky, WISE, NEOWISE or WTP group exists on TNS today. Individual reports with no group are accepted (e.g. AT 2022am in this galaxy). |
| 4 | Discovery data source (`data_source_groupid`) | **"None" [0]**, unless an Oddsky group exists | No WISE/NEOWISE data-source group exists. Name the data in the remarks and photometry comments instead. |
| 5 | Reporter/s (`reporter`) | **ALAN TO PROVIDE**, e.g. "A. Shortz (Oddsky), on behalf of Oddsky" | Free text: the authors on the ADS-indexed TNS discovery report. Decide whether to offer A. Meisner co-reporter or acknowledgement. |
| 6 | Discovery date, UT (`discovery_datetime`) | **2020-11-23 16:30:29** (MJD 59176.688) | Mean time of the 13 NEOWISE exposures covering the position in the unWISE epoch-15 coadd (2020-11-23 05:02 to 2020-11-24 04:34 UT). Not the tile-wide header midpoint, MJD 59176.37, used in earlier notes. |
| 7 | AT type (`at_type`) | **"Other - Undefined" [0]** (recommended); "PSN" [1] is the alternative | No spectrum. "Other" avoids implying a supernova. |
| 8 | Host name (`host_name`) | **NGC 3239** | = Arp 263 = UGC 5637 (NED, SIMBAD) |
| 9 | Host redshift (`host_redshift`) | **0.002368** | NED preferred, cz = 710 km/s (2024ApJ...964..172B) |
| 10 | Transient redshift | (blank) | none measured |
| 11 | Internal name (`internal_name`) | **ALAN TO DECIDE**, e.g. "Oddsky OS-0030" | |
| 12 | Remarks (`remarks`) | see the text below | facts only |
| 13 | Proprietary period | **none (public immediately)** | |

### Remarks (proposed text, facts only)

> Mid-infrared transient found in archival WISE/NEOWISE data by Oddsky (oddsky.ai): difference imaging of the unWISE
> time-resolved (epochal) coadds (neo11 build, courtesy A. Meisner; Meisner, Lang & Schlegel 2018; Meisner et al. 2023)
> against a pre-event reference. Nothing at this position in 15 W1/W2 epochs from 2010 to 2020-04-28. First detected
> 2020-11-23 at W1 = 17.99 +- 0.04 and W2 = 17.67 +- 0.07 AB (W1-W2 = 0.95 Vega). Fading: W1 = 18.96 / W2 = 18.63 AB on
> 2021-04-30, W1 = 19.92 AB on 2021-11-22. Magnitudes are of the difference flux (no quiescent source); the flux-scale
> systematic is about 0.1 mag. WISE centroid 156.29118 +17.16387 (+-0.3"). The reported position is a point source in
> public HST WFC3/UVIS images of 2021-02-16 (programme 16179; F606W = 25.9, F814W = 25.0 AB), 0.36" from the WISE
> centroid, absent from HST images of 2022-12-11 and 2025-01-09. Public JWST/NIRCam images (programme 3707,
> 2024-04-24 and 05-22) show an unresolved source at the HST position in F300M/F335M (22.6/22.0 AB), with none in
> F150W (> 26.5 AB). No optical transient was reported. ATLAS has no data from 2020-06-17 to
> 2020-10-10 (solar conjunction), so the onset is unconstrained. 70.6" E of the centre of NGC 3239. No spectrum.

(About 1,000 characters. If Alan prefers to leave the HST/JWST details for Oddsky's own write-up, cut the
sentences from "The reported position" to "F150W", and report the WISE centroid with a 0.3" error instead.)

## Photometry

### Last non-detection (`non_detection`)

| field | value |
|---|---|
| obsdate | **2020-04-28 18:15:00** UT (MJD 58967.760; mean of 11 exposures, 2020-04-28 05:59 to 04-29 05:31 UT) |
| limiting_flux | **19.92** (W1, 5σ). The W2 5σ limit is 19.00 AB; the 3σ limits are W1 > 20.48 and W2 > 19.56. |
| flux_units (`flux_unitid`) | **ABMag [1]** |
| filter (`filterid`) | **3.4-WISE [45]** (W1) |
| instrument (`instrumentid`) | **Other - Other [0]**. TNS has no WISE/NEOWISE instrument; the "Wise-C18/C28/Wise1m" entries are the Wise Observatory in Israel, **not** the WISE satellite. |
| exptime | 84.7 (s; 11 × 7.7 s) |
| observer | WISE/NEOWISE (NASA/JPL/IPAC) |
| comments | "Instrument=WISE (NEOWISE-R reactivation), unWISE neo11 epochal coadd (epoch 14), forced PSF photometry on a difference image at the reported position, measured flux +13.8 +- 7.8 uJy (1.8 sigma). Limit is 5 sigma, AB." |
| archiveid / archival_remarks | leave empty: a measured non-detection is given |

### Discovery photometry (`photometry["0"]`, `["1"]`)

| # | obsdate (UT) | flux | flux_error | units | filter | instrument | exptime (s) | comments |
|---|---|---|---|---|---|---|---|---|
| 0 | 2020-11-23 16:30:29 | **17.99** | 0.04 | ABMag [1] | 3.4-WISE [45] (W1) | Other - Other [0] | 84.7 (11 × 7.7) | "Instrument=WISE (NEOWISE-R), unWISE neo11 epochal coadd (epoch 15; exposures 2020-11-23.21 to 11-24.19). Difference flux 231.8 +- 8.3 uJy (28 sigma) vs 2010-2020.3 reference. Vega 15.31. Flux-scale systematic ~0.1 mag." |
| 1 | 2020-11-23 16:30:29 | **17.67** | 0.07 | ABMag [1] | 4.6-WISE [46] (W2) | Other - Other [0] | 92.4 (12 × 7.7) | "Instrument=WISE (NEOWISE-R), unWISE neo11 epoch 15. Difference flux 310.0 +- 20.0 uJy (15.5 sigma). Vega 14.36." |

### Optional extra photometry (same instrument, filter and units conventions)

| obsdate (UT) | W1 (AB) | W2 (AB) | exposures |
|---|---|---|---|
| 2021-04-30 17:44 (MJD 59334.739) | 18.96 ± 0.09 (94.3 ± 7.4 µJy) | 18.63 ± 0.14 (128.6 ± 17.0 µJy) | 13 frames, 04-30.20 to 05-01.31 |
| 2021-11-22 23:39 (MJD 59540.985) | 19.92 ± 0.24 (39.1 ± 8.6 µJy, 4.6σ) | > 18.84 (5σ; measured 41.8 ± 21.1 µJy) | 12 frames, 11-22.55 to 11-23.53 |

Per the TNS FAQ, follow-up photometry is "less relevant to the scope of the TNS", so HST/JWST points are better left
to the remarks. If wanted, they could go in as `HST - WFC3` [194]: F606W 25.93 ± 0.06 and F814W 24.95 ± 0.06 AB on
2021-02-16 18:39 / 18:30 UT.

### Related files (optional)

`hunts/H-0012/reviews/ngc3239-check-2026-11-01/summary.png` or `wise_lc.png` as the discovery figure, plus an
HST/JWST stamp (`hst_stamps.png`, `jwst_stamps.png`) if the HST/JWST remarks are kept.

## What Alan must provide or decide before filing

1. **A TNS user account** (wis-tns.org → Login / Create new account), to use the interactive AT-report form. A **bot
   + API key** is only needed for JSON bulk submission. Test bulk JSON on sandbox.wis-tns.org first; the sandbox is
   reset from production every Sunday.
2. **The reporting group**: report as an individual (group "None"), or create an "Oddsky" group (GROUPS menu; up to
   three owners; needs TNS-admin approval) and wait for approval.
3. **The reporter names**, exactly as they should appear on the ADS-indexed discovery certificate, and whether to
   credit A. Meisner as co-reporter or only in the remarks.
4. **The internal name** (e.g. "Oddsky OS-0030").
5. **AT type**: "Other - Undefined" (recommended) or "PSN".
6. **Whether to keep the HST/JWST sentences** in the remarks. If they go, report the WISE centroid with a 0.3" error.
7. **Written confirmation from A. Meisner (recommended before filing).** The README records verbal permission (by
   phone, 2026-11-01) and the credit wording; the drafted email was never sent. A short email that confirms the
   permission, the credit line and that a public TNS report will name the neo11 epochal coadds leaves a written
   record.
8. In the live form, **check the filter/unit IDs** (3.4-WISE, 4.6-WISE, ABMag) and that "Other" is used for the
   instrument with "Instrument=WISE (NEOWISE-R)" in the comments, as the TNS FAQ asks.
9. Expect the name to be **AT 2020xxx**: TNS designations follow the discovery date. This is inferred from practice,
   not from a written rule.
