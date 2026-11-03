# DRAFT. TNS AT report for H-0012 NGC 4945 obscured #3 (mid-infrared transient, rise 2017/18-2022)

**Status: draft only. Nothing has been submitted to TNS (production or sandbox).** Prepared 2026-11-02/03 for the
packet `tns_packet_2026-11/`. Revised 2026-11-03 on the coordinator's decision: **the discovery is the Spitzer/IRAC
detection of 2018-06-02.** The earlier draft used the WISE first detection, and that was internally inconsistent:
the WISE "discovery" came after an 8σ Spitzer detection, and the WISE "last non-detection" both followed that
detection and was shallower than the discovery magnitude.

The checks behind every number are in `tns_packet_validation.md` and `numbers.json` (scripts in `scripts/`, in
particular `spitzer_discovery.py`). The form ids follow OS-0030 (AT 2020afkm); the fill is in
`fill_NGC4945-obs3.json`.

**Expect the designation AT 2018xxx.** TNS designations follow the discovery date; this is inferred from practice,
not a written rule.

There is no Oddsky case for this source. It is H-0012 triage lead "NGC 4945 obs#3" (h0012a, referee 2026-11-01) =
rank 3 of the h0012b obscured-transient ranking (`NGC4945|1974m500|14`). It is **not** OS-0033, the periodic source
140" away, which is excluded.

## Header

| # | field (form label / form id) | value | note |
|---|---|---|---|
| 1 | RA (`edit-ra-value`, `edit-ra-error`, `edit-ra-units`) | **13:05:52.700** (196.469582°), error **0.3**, arcsec [arcsec] | Spitzer/IRAC centroid of the brightening: mean (2019) − median (2013-2017), Gaussian fit. [3.6] and [4.5] agree to 0.13". 0.19" from the pre-existing SEIP 4.5 µm source; 0.79" from the Gaia-tied WISE centroid (13:05:52.761 −49:24:58.74, ±0.5"). |
| 2 | Dec (`edit-decl-value`, `edit-decl-error`, `edit-decl-units`) | **−49:24:58.23** (−49.416175°), error **0.3**, arcsec [arcsec] | |
| 3 | Reporting group (`edit-reporting-groupid`) | **None [0]** | as for OS-0030 |
| 4 | Discovery data source (`edit-data-source-groupid`) | **None [0]** | No Spitzer, SPIRITS or Oddsky data-source group is used. The data are credited in the remarks and comments: Spitzer data from IRSA, SPIRITS programmes 13053/14089, PI M. Kasliwal; unWISE coadds, courtesy A. Meisner. |
| 5 | Reporter/s (`edit-reporter`) | **Alan Shortz (Oddsky)** | |
| 6 | Discovery date, UT (`edit-discovery-datetime`) | **2018-06-02 05:10:43** (MJD 58271.2158) | Mean mid-time of the 7 IRAC [3.6] BCD frames that contain the source (IRSA SIA, 0.36" circle), AOR 60808960, 2018-06-02 05:04:29 to 05:16:57 UT. The mosaic/AOR span is 04:13-05:29. |
| 7 | AT type (`edit-at-type`) | **Other - Undefined [0]** | No spectrum. |
| 8 | Host name (`edit-host-name`) | **NGC 4945** | |
| 9 | Host redshift (`edit-host-redshift`) | **0.001878** | NED preferred, ± 0.00001 (2014MNRAS.440..696A) |
| 10 | Transient redshift | (blank) | |
| 11 | Internal name (`edit-internal-name`) | **Oddsky H0012-NGC4945-1** | |
| 12 | Remarks (`edit-remarks`) | see below | facts only |
| 13 | Proprietary period | **none** | |

### Remarks (1,344 characters; identical to `fill_NGC4945-obs3.json`)

> Mid-infrared transient found by Oddsky (oddsky.ai) in archival WISE/NEOWISE data, by difference imaging of the
> unWISE time-resolved coadds (NEO11 version, courtesy A. Meisner; Meisner, Lang & Schlegel 2018), and measured in
> public Spitzer/IRAC images from IRSA (SPIRITS programmes 13053 and 14089, PI M. Kasliwal). The discovery point is
> the earliest >= 5 sigma detection: IRAC [3.6] = 20.09 +- 0.10 AB (+33 +- 3 uJy) on 2018-06-02, against the median of
> 12 flat 2013-2016 epochs; [3.6] was +17 +- 4 uJy (3.9 sigma) on 2017-10-03. Later IRAC: [4.5] = 19.65 +- 0.11 AB on
> 2018-11-23; [3.6] = 18.13 +- 0.02 AB on 2019-07-02. WISE (difference flux, AB): flat in 11 epochs from 2010 to
> 2017-07; first >= 5 sigma on 2019-01-27 at W1 = 18.97 +- 0.10, W2 = 18.80 +- 0.22; peak on 2022-07-07 at W1 = 16.52
> +- 0.02, W2 = 16.71 +- 0.04; fading to W1 = 18.20 +- 0.09 by 2024-07-06, the last NEOWISE epoch; flux-scale
> systematic about 0.1 mag. The position is the IRAC centroid of the brightening, 0.8" from the WISE centroid and 0.2"
> from a 4.5 um source of 41 uJy with no 3.6 um detection in the cryogenic-era Spitzer SEIP catalogue (SSTSL2
> J130552.71-492458.3). No Gaia DR3 source within 6". ATLAS forced photometry shows no optical counterpart at the
> infrared peak (3-sigma limits c > 22.0, o > 21.0 AB). 309" NE of the centre of NGC 4945. No spectrum.

## Photometry

**Option values for the IRAC instrument and filters.** "SST - IRAC" = **193**, "3.6-Spitzer IRAC" = **40** and
"4.5-Spitzer IRAC" = **41**. These come from the TNS values mirror (tns_codes.json, 2026-09-02), the same source as
the WISE filters 45/46 that the live form confirmed for OS-0030. **The live AT form's IRAC entries were not seen**:
the OS-0030 session read only the Other/WISE/HST options, and the form needs a login. Check them when filling. If
193/40 are absent, use instrument Other - Other [0] and filter Other, with "Instrument=Spitzer/IRAC [3.6]" in the
comments.

### Last non-detection (`non_detection`)

| field (form id) | value |
|---|---|
| obsdate (`edit-non-detection-obsdate`) | **2017-10-03 09:08:01** UT (MJD 58029.3806; mean mid-time of the 9 [3.6] BCD frames at the source, 09:02:56-09:15:41; AOR 60808704, SPIRITS13 13053) |
| limiting_flux (`edit-non-detection-limiting-flux`) | **20.55** ([3.6], 5σ; 3σ 21.10) |
| flux units (`edit-non-detection-flux-units`) | **ABMag [1]** |
| filter (`edit-non-detection-filter-value`) | **3.6-Spitzer IRAC [40]** |
| instrument (`edit-non-detection-instrument-value`) | **SST - IRAC [193]** |
| exptime (`edit-non-detection-exptime`) | 666.0 (s; sum of the frame exposure times at the source) |
| observer (`edit-non-detection-observer`) | Spitzer Space Telescope (NASA/JPL-Caltech); SPIRITS, PI M. Kasliwal; data from IRSA |
| comments (`edit-non-detection-comments`) | "Instrument=Spitzer/IRAC (warm mission), [3.6], SPIRITS programme 13053 (PI M. Kasliwal), AOR 60808704; 9 BCD frames at the source, 2017-10-03 09:02 to 09:15 UT; public post-BCD mosaic from IRSA; difference-aperture photometry (2.4" radius, aperture-corrected) at the reported position against the median of 12 flat 2013-2016 epochs (leave-one-out). Measured +17.2 +- 4.4 uJy (3.9 sigma, below the 5-sigma threshold; the rise may already have begun). Limit is 5 sigma, AB. Same AOR [4.5]: +7.8 +- 4.6 uJy (1.7 sigma), 5-sigma limit 20.50 AB." |
| archiveid / archival_remarks | leave empty |

**This is the last epoch before discovery that has no ≥ 5σ detection.** Its [3.6] flux is +3.9σ (and 2017-06-08 is
+2.9σ), so the rise probably began in 2017. The 5σ limit (20.55) is fainter than the discovery magnitude (20.09),
so the pair is consistent. The last epoch consistent with zero in [3.6] is 2016-05-27 (+2.3 ± 3.7 µJy, 5σ > 20.74
AB). That one is the alternative if a strictly flat last non-detection is preferred; it was not chosen because TNS
asks for the *last* non-detection.

### Discovery photometry (`photometry` group 0; one row)

| # | obsdate (UT) | flux | flux_error | units | filter | instrument | exptime (s) | comments |
|---|---|---|---|---|---|---|---|---|
| 0 | 2018-06-02 05:10:43 | **20.09** | 0.10 | ABMag [1] | 3.6-Spitzer IRAC [40] | SST - IRAC [193] | 655.2 (7 frames) | "Instrument=Spitzer/IRAC (warm mission), [3.6], SPIRITS programme 13053 (PI M. Kasliwal), AOR 60808960; 7 BCD frames at the source, 2018-06-02 05:04 to 05:16 UT ([4.5] did not cover the position in this AOR); public post-BCD mosaic from IRSA; difference-aperture photometry (2.4" radius, aperture-corrected) at the reported position against the median of 12 flat 2013-2016 epochs (leave-one-out). Difference flux 33.3 +- 3.1 uJy (10.7 sigma). IRAC calibration/aperture systematic ~10%." |

**Only [3.6] is available.** IRAC's [3.6] and [4.5] arrays view adjacent fields. In AOR 60808960 no [4.5] BCD frame
contains the source, and the [4.5] mosaic covers 0% of the 36" box. The first [4.5] detection is 2018-11-23.

**Method** (`spitzer_discovery.py`).
- Each mosaic is resampled to a 0.6" grid by the H-0013 tool (`oddsky.imaging.spitzer`).
- Photometry is in a 2.4" aperture at the reported position, with a 6-15" annulus and aperture correction (1.213 /
  1.234).
- The reference is the median of the 12 [3.6] (4 [4.5]) flat 2013-2016 epochs, leaving the measured epoch out.
- The error is empirical: 12 apertures 10" away. The [3.6] reference epochs scatter by 3.5 µJy rms.
- 2017 is kept out of the reference because it is already marginally positive.

### Further Spitzer and WISE photometry (optional extra rows; full tables in `numbers.json`)

| UT | instrument / band | Δflux (µJy) | AB |
|---|---|---|---|
| 2017-06-08 22:27 | IRAC [3.6] | +15.5 ± 5.4 (2.9σ) | — |
| 2017-10-03 09:08 / 09:22 | IRAC [3.6] / [4.5] | +17.2 ± 4.4 (3.9σ) / +7.8 ± 4.6 | — |
| **2018-06-02 05:10** | **IRAC [3.6] (discovery)** | **+33.3 ± 3.1 (10.7σ)** | **20.09 ± 0.10** |
| 2018-07-07 14:37 | WISE W1 (last WISE non-detection) | +46.6 ± 23.5 (2.0σ) | > 18.72 (5σ) |
| 2018-11-23 00:27 | IRAC [4.5] | +49.9 ± 5.0 (10.0σ) | 19.65 ± 0.11 |
| 2019-01-27 17:43 | WISE W1 / W2 (first WISE ≥ 5σ) | 93.4 ± 8.7 / 109.5 ± 22.0 | 18.97 ± 0.10 / 18.80 ± 0.22 |
| 2019-05-20 10:21 | IRAC [3.6] | +181.7 ± 4.2 | 18.25 ± 0.03 |
| 2019-07-02 19:37 | IRAC [3.6] | +202.9 ± 3.2 (WISE W1 on 2019-07-07: +213 ± 17) | 18.13 ± 0.02 |
| 2019-10-25 02:57 / 03:14 | IRAC [3.6] / [4.5] | +322.1 ± 4.9 / +211.5 ± 4.1 | 17.63 / 18.09 |
| 2022-07-07 09:19 | WISE W1 / W2 (peak) | 897.7 ± 13.6 / 751.1 ± 30.9 | 16.52 ± 0.02 / 16.71 ± 0.04 |
| 2024-07-06 21:55 | WISE W1 / W2 (last NEOWISE) | 190.4 ± 15.4 / 238 ± 38 | 18.20 ± 0.09 / 17.96 ± 0.17 |

WISE times are the mean of the NEOWISE exposures at the source. The WISE fluxes are forced at the pipeline position,
0.8" from the reported one, which costs a few per cent, inside the 0.1 mag systematic.

### Related file

`NGC4945_obs3_summary.png` (90 kB): the Spitzer and WISE light curves with the IRAC discovery and last non-detection
marked, and WISE stamps. Comment (`edit-related-files-related-files-group-0-related-file-comments`): "Discovery
summary: Spitzer/IRAC (SPIRITS) and unWISE W1/W2 difference light curves 2007-2024 (IRAC discovery 2018-06-02
marked), and WISE W1/W2 difference stamps at the WISE last non-detection, first WISE detection and W1 peak (Oddsky
H0012-NGC4945-1)."

## Checklist before filing (Alan)

1. Re-run a TNS 60" cone (`unreal=all`) on the filing day. The 2026-11-03 search found nothing within 60".
2. Fill in the De-list column. SPIRITS (of which K. De was a member) observed the rise, so the source may be on an
   unpublished SPIRITS/WTP list. If it is, coordinate before filing. Claim no novelty beyond public records.
3. **Check the live drop-downs for SST - IRAC [193] and 3.6-Spitzer IRAC [40].** If either is missing, fall back to
   Other, with the instrument and band in the comments.
4. A courtesy note to the SPIRITS PI (M. Kasliwal) after filing would be gracious, since the discovery point is
   their public data. It is not required.
5. Expect **AT 2018xxx**.
