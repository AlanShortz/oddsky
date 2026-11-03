# DRAFT. TNS AT report for Oddsky case OS-0035 (M81 mid-infrared eruption of 2023-24)

**Status: draft only. Nothing has been submitted to TNS (production or sandbox).** Prepared 2026-11-02/03 for the
packet `tns_packet_2026-11/`. The checks behind every number are in `tns_packet_validation.md`, and the numbers are
in `numbers.json` (scripts in `scripts/`). Fields follow the TNS AT-report form exactly as it was filled for OS-0030
(AT 2020afkm). The form ids and values are in `fill_OS-0035.json`. Codes in brackets are the live-form option
values used for OS-0030. **Check them against the live drop-downs when filing.**

What is reported: **the 2023-24 eruption.** The source had an earlier infrared event at the same position, seen by
Spitzer in 2009-10, and the remarks mention it. Two eruptions 14 years apart do not establish a period; see
validation §M81.2 for why this is still in scope for TNS.

## Header

| # | field (form label / form id) | value | note |
|---|---|---|---|
| 1 | RA (`edit-ra-value`, `edit-ra-error`, `edit-ra-units`) | **09:54:57.378** (148.739074°), error **0.5**, arcsec | Gaia-tied WISE centroid: an S/N-weighted Gaussian fit to the 2023-10 and 2024-03 W1+W2 difference images, with the tile zero point tied to 60 Gaia DR3 stars (WISE−Gaia = +0.28", −0.27", removed). Formal error 0.24"/0.32". 0.5" is quoted as the realistic WISE floor. |
| 2 | Dec (`edit-decl-value`, `edit-decl-error`, `edit-decl-units`) | **+69:08:48.75** (+69.146874°), error **0.5**, arcsec | |
| 3 | Reporting group (`edit-reporting-groupid`) | **None [0]** | as for OS-0030 |
| 4 | Discovery data source (`edit-data-source-groupid`) | **None [0]** | as for OS-0030 |
| 5 | Reporter/s (`edit-reporter`) | **Alan Shortz (Oddsky)** | as for OS-0030 |
| 6 | Discovery date, UT (`edit-discovery-datetime`) | **2023-10-23 05:41:33** (MJD 60240.237) | Mean of the 19 NEOWISE-R exposures covering the position in unWISE epoch 21 (2023-10-22 16:22 to 10-23 21:51 UT; n-m at the source W1 17, W2 16). Not the tile-wide header midpoint (MJD 60240.620). |
| 7 | AT type (`edit-at-type`) | **Other - Undefined [0]** | No spectrum. |
| 8 | Host name (`edit-host-name`) | **NGC 3031** | = M81. TNS stores the host as "NGC3031, M81". |
| 9 | Host redshift (`edit-host-redshift`) | **leave blank** | The NED preferred value is negative (z = −0.00013 ± 0.00001, 2012ApJ...752...52S). AT 2026dvq in M81 has no host redshift on TNS. If Alan prefers, enter −0.00013 and check that the form accepts a negative value. |
| 10 | Transient redshift | (blank) | none measured |
| 11 | Internal name (`edit-internal-name`) | **Oddsky OS-0035** | |
| 12 | Remarks (`edit-remarks`) | see the text below | facts only |
| 13 | Proprietary period | **none (public immediately)** | |

### Remarks (proposed text, facts only; 1,092 characters; identical to `fill_OS-0035.json`)

> Mid-infrared eruption found in archival WISE/NEOWISE data by Oddsky (oddsky.ai): difference imaging of the unWISE
> time-resolved coadds (NEO11 version, courtesy A. Meisner; Meisner, Lang & Schlegel 2018) against a 2014.8-2023.2
> reference. Nothing at this position in 18 W1/W2 epochs from 2014-10 to 2023-03-27. First detected 2023-10-23 at W1 =
> 18.18 +- 0.07 and W2 = 18.05 +- 0.12 AB; on 2024-03-28, the last NEOWISE epoch here, W1 = 16.71 +- 0.02 and W2 =
> 16.36 +- 0.02 AB, still rising. Magnitudes are of the difference flux; the flux-scale systematic is about 0.1 mag.
> An earlier infrared event at the same position: public Spitzer/IRAC 3.6 um images show +0.22 mJy on 2009-11-25,
> declining to +0.13 mJy by 2010-04/06, after a flat 2003-2005, and WISE 2010 was still above the 2014-2023 level. The
> source lies in the HII region [HAE2008] 7; Gaia DR3 1070474934439610752 (G = 20.25, BP-RP = 0.37) is 0.28" away. No
> ZTF alert object within 35". ATLAS forced photometry shows no brightening at the WISE epochs (3-sigma limits c >
> 21.3, o > 21.2 AB). 351" NW of the centre of M81. No spectrum.

(The Gaia sentence could go to shorten it. The Spitzer sentence is the one that matters.)

## Photometry

### Last non-detection (`non_detection`)

| field (form id) | value |
|---|---|
| obsdate (`edit-non-detection-obsdate`) | **2023-03-27 18:12:04** UT (MJD 60030.758; mean of 22 exposures, 2023-03-26 17:40 to 03-31 08:25 UT) |
| limiting_flux (`edit-non-detection-limiting-flux`) | **19.57** (W1, 5σ). W2 5σ: 18.78 AB. 3σ: W1 > 20.12, W2 > 19.34. |
| flux units (`edit-non-detection-flux-units`) | **ABMag [1]** |
| filter (`edit-non-detection-filter-value`) | **3.4-WISE [45]** (W1) |
| instrument (`edit-non-detection-instrument-value`) | **Other - Other [0]** (no WISE/NEOWISE instrument on TNS; "Wise-C18/C28/Wise1m" are the Wise Observatory, Israel) |
| exptime (`edit-non-detection-exptime`) | 161.7 (s; n-m = 21 × 7.7) |
| observer (`edit-non-detection-observer`) | WISE/NEOWISE (NASA/JPL/IPAC) |
| comments (`edit-non-detection-comments`) | "Instrument=WISE (NEOWISE-R reactivation), unWISE neo11 epochal coadd (epoch 20), forced PSF photometry on a difference image at the source, measured flux +18.9 +- 10.8 uJy (1.7 sigma). Limit is 5 sigma, AB. W2 +5.6 +- 22.3 uJy, 5-sigma limit 18.78 AB." |
| archiveid / archival_remarks | leave empty: a measured non-detection is given |

### Discovery photometry (`photometry` groups 0 and 1)

| # | obsdate (UT) | flux | flux_error | units | filter | instrument | exptime (s) | comments |
|---|---|---|---|---|---|---|---|---|
| 0 | 2023-10-23 05:41:33 | **18.18** | 0.07 | ABMag [1] | 3.4-WISE [45] (W1) | Other - Other [0] | 130.9 (17 × 7.7) | "Instrument=WISE (NEOWISE-R), unWISE neo11 epochal coadd (epoch 21; exposures 2023-10-22.68 to 10-23.91). Difference flux 194.0 +- 12.6 uJy (15 sigma) vs 2014.8-2023.2 reference. Vega 15.51. Flux-scale systematic ~0.1 mag." |
| 1 | 2023-10-23 05:41:33 | **18.05** | 0.12 | ABMag [1] | 4.6-WISE [46] (W2) | Other - Other [0] | 123.2 (16 × 7.7) | "Instrument=WISE (NEOWISE-R), unWISE neo11 epoch 21. Difference flux 218.1 +- 23.4 uJy (9.3 sigma). Vega 14.74." |

### Optional extra photometry (same conventions)

| obsdate (UT) | W1 (AB) | W2 (AB) | exposures |
|---|---|---|---|
| 2024-03-28 13:22:28 (MJD 60397.557) | 16.71 ± 0.02 (753.0 ± 11.1 µJy) | 16.36 ± 0.02 (1035.6 ± 14.9 µJy) | 19 frames, 2024-03-27 21:08 to 03-29 05:31; n-m 17/17 |

NEOWISE stopped surveying on 2024-08-08, before M81's next visit, so the peak and the decline were not observed.

Earlier event, for reference only (not for the form). These are differences against the 2014.8-2023.2 reference:
- WISE 2010-04 (cryogenic): W1 +129 ± 10, W2 +285 ± 24 µJy.
- WISE 2010-10: W1 +77 ± 17, W2 +168 ± 17 µJy.
- Spitzer [3.6], against the 2003.8-2005.0 level: +0.22 mJy on 2009-11-25, +0.2 mJy to 2010-01-06, +0.13 mJy on 2010-04-24 to 06-07.

### Related file

`M81_OS-0035_summary.png` (84 kB). Comment (`edit-related-files-related-files-group-0-related-file-comments`):
"Discovery summary: unWISE W1/W2 difference light curve 2010-2024 with Spitzer/IRAC 2003-2019, and W1/W2
difference stamps at the last non-detection, discovery and latest epoch (Oddsky case OS-0035)."

## Checklist before filing (Alan)

1. Re-run a TNS 60" cone (`unreal=all`) on the filing day. The 2026-11-03 search found only AT 2026dvq (22.6", ATLAS, 2026).
2. Fill in K. De's list column in `tns_packet_validation.md` when the list arrives. If the source is on it, coordinate
   with K. De before filing. Make no novelty claim beyond public records.
3. Decide on the host redshift (blank or −0.00013).
4. In the live form, check the option values 45/46 (3.4-/4.6-WISE), 1 (ABMag), 0 (Other - Other, None,
   Other - Undefined), and that "Instrument=WISE (NEOWISE-R)" is in the comments.
5. Expect the designation **AT 2023xxx**: TNS names follow the discovery date. This is inferred from practice.
6. The case file is not edited by this packet. After filing, record the TNS name in OS-0035 through the case tools.
