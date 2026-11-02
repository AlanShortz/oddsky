# OS-0030: validation of every assumption behind a TNS AT report (2026-11-01/02)

**Nothing was filed, submitted or posted** to TNS (production or sandbox) or anywhere else. Nothing was committed.
Scripts are in `drafts/tns_validation/`. Their raw outputs are outside the repo, in
`~/oddsky-runs/imaging/scratch/tns-validation-os0030/` (`tns/`, `numbers/`, `mast/`, `ads/`, `brokers/`,
`policy/`). The draft report is `drafts/tns_report_OS-0030.md`.

## Verdict

**Nothing blocks a TNS report: it is technically sound and not premature.** The transient is not in TNS or any broker that could be reached (Fink timed out), and TNS accepts this kind of report. It must be filed with a few corrections and conventions:

- **The dates in the case need correcting.**
  - The discovery time is **2020-11-23 16:30 UT (MJD 59176.688)**, the mean of the exposures at the source. The
    earlier MJD 59176.37 was the tile-wide header midpoint.
  - The last non-detection is **2020-04-28 18:15 UT (MJD 58967.760)**, not "2020-05-02".
  - The rise window is **< 209 d**, not < 205 d.
- **Use "Other - Other" for the instrument.** TNS has no WISE/NEOWISE instrument. Do not pick "Wise-C18/C28/Wise1m":
  that is the Wise Observatory in Israel.
- **WTP does not report to TNS.** There is no WTP-format example to copy.
- **Get a written note from A. Meisner before filing (recommended).** The data permission is verbal and recorded only
  in the README.

## Validation table

| # | assumption | status | evidence |
|---|---|---|---|
| 1a | Not already in TNS within 60" (all dates, all types, including "unreal") | **verified** | §1.1. Within 60": only SN 2012A (49.9"). This holds with `unreal=all` and with no date limit. |
| 1b | No other AT/SN in NGC 3239 besides SN 2012A | **corrected** | §1.1. **AT 2022am** (host NGC3239; amateur report, 2022-01-04, Clear 19.2) lies **72.2"** away. The reporter's own comment the next day calls it a Galactic star. It is unrelated, but it exists. |
| 1c | No WTP (De et al.) report on TNS | **verified** | §1.1. `internal_name=WTP` returns 9 objects, all ZTF names that merely contain "wtp". There is no WTP group, data source or instrument on TNS. |
| 1d | No broker/alert/catalogue object near the position | **verified, except Fink (unreachable)** | §1.2. ALeRCE, Lasair, Gaia alerts, ASAS-SN, the sne.space dump, Rochester 2020-22, ATel, SIMBAD and VSX: nothing within 8". The OSC API is shut down (410). The CBAT list ends in 2015. Fink timed out, which is an error, not a null result. |
| 1e | Not in ATel/CBAT/literature | **verified** | §1.3. ADS ATel hits for NGC 3239 are the five 2012 SN 2012A telegrams. There are no TNS reports and no new papers since 2026-10-01. |
| 2a | TNS accepts reports from archival data, years after the event | **verified in substance; no explicit rule found** | §2. The AT form allows "archival info" instead of a non-detection. The only date rule is that the last non-detection must precede the discovery date. Nothing in the docs limits the report delay. |
| 2b | TNS accepts infrared-only discoveries | **verified** (with a convention) | §2. Filters "3.4-WISE"/"4.6-WISE" exist, but there is **no WISE/NEOWISE instrument**. The FAQ says to choose "Other" and give Instrument=… in the comments. TNS takes "other extra-galactic transients" beyond SNe. |
| 2c | WTP reports exist on TNS as a format model | **corrected: none exist** | §1.1, §2. WTP names are internal (Masterson+2024). Karambelkar+2026 notes a WTP source "has not been reported to the Transient Name Server". |
| 2d | Required fields and the mag system | **verified** | §2. Mandatory: RA/Dec, reporting group (may be "None"), data source, discovery date, AT type, a discovery photometry point, and a last non-detection or archival info. Units include ABMag [1] and VegaMag [3]; there is no µJy unit. |
| 3a | Discovery epoch = first ≥5σ epoch | **verified** | §3. Epoch 15 in both bands: W1 28σ, W2 15.5σ. No earlier epoch exceeds +2.9σ (W1 epoch 6). The pipeline's own detections also start at epoch 15. |
| 3b | Epoch timestamp = mean of the exposures at the source | **corrected** | §3. The header MJDMIN/MAX are tile-wide (2.7 d). At the source, the 13 frames span 0.98 d with mean MJD 59176.688. The old value was early by 0.31 d. |
| 3c | Discovery W1/W2 flux and mags | **verified** (to ≤ 3%) | §3. W1 231.8 ± 8.3 µJy = 17.99 ± 0.04 AB (15.31 Vega). W2 310.0 ± 20.0 µJy = 17.67 ± 0.07 AB (14.36 Vega). Systematic about 0.1 mag. |
| 3d | Last non-detection epoch and limit | **corrected (date)** | §3. 2020-04-28.760: W1 +13.8 ± 7.8 µJy, W2 +0.7 ± 18.2 µJy. 5σ limits W1 > 19.92 and W2 > 19.00 AB; 3σ limits 20.48 and 19.56. |
| 3e | Best position | **verified** | §3. HST 156.291224 +17.163778 (±4 mas, Gaia-tied). The WISE centroid 156.29118 +17.16387 (±0.18-0.3") is 0.36" away. |
| 4a | HST 2021/2022/2025 and JWST 3707 data public, none proprietary when used | **verified** | §4. MAST release date = observation date for every dataset (zero exclusive access). JWST 3707 is a Treasury whose data are "immediately public". |
| 4b | PIs | **verified** | §4. HST 16179 Filippenko; 15446 Dalcanton; 17502 Thilker. JWST 3707 Leroy. |
| 4c | unWISE epochal-coadd permission and credit | **unverifiable by me; credit wording verified** | §4. The permission is recorded only as a phone call (README); the drafted email was never sent. |
| 5a | Unclassified AT (no spectrum) | **verified** | §5. TNS: "Classifications must be supported by a spectrum". |
| 5b | Host NGC 3239 = Arp 263 = UGC 5637 | **verified** | §5. NED resolves "Arp 263" and "UGC 5637" to NGC 3239. SIMBAD idents include "APG 263" and "UGC 5637". |
| 5c | Host redshift | **verified** | §5. z = 0.002368305 ± 0.0000033 (cz 710 km/s), NED preferred value (2024ApJ...964..172B). |
| 5d | Distance 7.9-12.2 Mpc | **corrected (wider)** | §5. NED lists 12 redshift-independent distances, 6.95-12.4 Mpc (median 10.15). The 12.2 Mpc CF4 value is not in NED; it is in VizieR J/ApJ/944/94 and comes from SN II only. Not a TNS field; omit it from the remarks. |
| 5e | Remarks factual, no SN claim | **done in the draft** | at_type "Other - Undefined" recommended |
| 6 | Anything making the report wrong or premature | **no blocker; three cautions** | §6 |

## 1. Not already reported

### 1.1 TNS (public web search, `tns_validation/tns_search.py`, `tns_pages.py`)

All requests returned HTTP 200, with no 429s. Pacing: the five scripted searches were 60-65 s apart. **Two later
page fetches came too soon after the previous request**: the search-form page 36 s after the last search, and the
FAQ 26 s after the getting-started page, because they ran in separate invocations. Both returned 200. The fetcher
now sleeps 60 s before every request.

| query (UTC 2026-11-02) | URL | result |
|---|---|---|
| 60" cone, 04:04:46 | `https://www.wis-tns.org/search?ra=156.291224&decl=17.163778&radius=60&coords_unit=arcsec&format=csv&num_page=500` | 1 row: **SN 2012A** 10:25:07.390 +17:09:14.62, SN II, disc. 2012-01-07 |
| 60" cone, `unreal=all`, 04:11:13 | same + `&unreal=all` | the same single row |
| 15' cone, 04:05:51 and again with `unreal=all` at 04:12:14 | `…radius=15&coords_unit=arcmin…` | 8 rows: AT 2026agzo, AT 2025jwq, AT 2023ukp, AT 2023eab, **AT 2022am**, AT 2019zby, SN 2019vbl, SN 2012A. None other than SN 2012A is within 60". |
| host "NGC 3239", 04:06:52 | `…hostname=NGC+3239…` | header only, 0 rows (TNS stores the host as "NGC3239") |
| host "NGC3239", 04:07:56 | `…hostname=NGC3239…` | 2 rows: **AT 2022am**, SN 2012A |
| internal name "WTP", 04:08:57 | `…internal_name=WTP…` | 9 rows: SN 2025abwg (ZTF25acaswtp), SN 2025ina, SN 2024adqz (ZTF24abwtpan), AT 2024ssf, AT 2023guz, AT 2022qsd, AT 2020mxy, SN 2020kzp, AT 2019mqg. All are ZTF/GOTO names containing "wtp"; **none is a WISE Transient Pipeline report** |

Notes on the searches:
- **No date limit applied.** The TNS help says the search *page* loads with "Discovered Within the Last 1 Months",
  but URL queries without that parameter are unrestricted. SN 2012A (2012) is returned.
- **Coverage.** Every object type is included (no `objtype` filter) and `unreal=all` adds flagged objects. Only
  public objects are searchable: the form offers just "public=yes". A proprietary AT report by someone else would not
  be visible. If one existed, TNS would attach our report to the existing object and return its name; it would not
  create a duplicate.
- **AT 2022am** (`https://www.wis-tns.org/object/2022am`): 10:25:06.750 +17:08:53.20, discovered 2022-01-04 18:31:32
  at 19.2 (Clear, VegaMag, "Other - Other", 0.4-m), reporter Kunihiro Shima, AT type PSN, host NGC3239. The
  reporter's comment of 2022-01-05: *"No PSN One day past, there is no brightening so tha this is a star in our
  galaxy."* It is 72.2" from OS-0030 and 13 months later, so it is unrelated.
- **No relevant group, data source or instrument.** The search form's option lists (`tns/pages/www_wis_tns_org_search.html`)
  have 295 discovery instruments and 215 groups. Not one is WISE, NEOWISE, WTP or Oddsky.
  - The only "Wise" entries are "Wise-C18 - C18-Cam" (114), "Wise-C28 - C28-Cam" (277) and "Wise1m - FOSC/Laiwo/PI"
    (20-22). Those are the Wise Observatory (Israel), not the WISE satellite.
  - Space instruments present: "HST - WFC3" (194), "HST - STIS" (83), "JWST - NIRCam/MIRI/NIRISS/NIRSpec"
    (185-188). The GitHub mirror of TNS's values also lists "SST - IRAC" (193).

### 1.2 Brokers, alerts and catalogues

Run 2026-11-02 04:03-04:29 UTC by a sub-check that did not query TNS. Raw files are in
`…/tns-validation-os0030/brokers/dl/`. Errors are recorded as errors.

| service | query | status | result |
|---|---|---|---|
| ALeRCE (ZTF alerts) | `https://api.alerce.online/ztf/v1/objects/?ra=156.291224&dec=17.163778&radius=60&page_size=100` | 200 | 8 objects, all 8-50" away. Nearest: ZTF26aafzrde, 8.0", alerts only in 2026-02. ZTF20acukuiz (43.3") has a 2020-11-30 history point. **Nothing coincident.** |
| Lasair (ZTF) | the API needs a token (401); public web search `"156.291224 17.163778 60"` | 200 | "Your search returned 4 matches", all 38-50" away (the same ZTF objects). "NGC3239": 0 matches. **Empty at the position.** |
| Fink | `POST https://api.fink-portal.org/api/v1/conesearch` (radius 60"), 3 tries by the sub-check, plus mine at 04:29:40 | **ERROR**: connection timed out (curl exit 28, no HTTP status) | **Not checked.** CDS Strasbourg also timed out from this machine, so this is likely a route problem to France. Fink processes the same ZTF alert stream as ALeRCE and Lasair, which are both clean. Retry before filing if convenient. |
| Gaia Science Alerts | `http://gsaweb.ast.cam.ac.uk/alerts/alerts.csv` (27,076 alerts, 2014-07 to 2025-01) | 200 | None within 60" or 10'. Nearest: Gaia16bvb at 29.7'. **Empty.** |
| ASAS-SN transients | `https://www.astronomy.ohio-state.edu/asassn/transients.html` (9,570 rows, to 2026-10-25) | 200 | Within 10': only AT2019vbl (385"). No NGC 3239 entries. **Empty.** |
| Open Supernova Catalog | `api.astrocats.space` | **410** "permanently shut down" | The API is dead. The `sne.space` catalogue dump (110,867 entries, to 2026-11-01) has only SN 2012A (50.1"), AT2019zby (145") and SN2019vbl (384") within 10'. |
| CBAT | `cbat.eps.harvard.edu/lists/Supernovae.html`, `RecentSupernovae.html` | 200 | The only NGC 3239 line is "2012A NGC 3239 2012 01 07 … CBET 2974 II". **The list ends in 2015-12, when TNS took over**, so it cannot cover 2020. |
| Rochester (Bishop) | `rochesterastronomy.org/sn{2012,2019,2020,2021,2022}/snlocations.html` | 200 | 2012: SN 2012A. 2019: AT2019zby, SN2019vbl. **2020-2022: nothing within 10'.** |
| ATel | archive keyword search, 1997-2026 | 200 | "NGC 3239": 5 hits, ATel 3855/3857/3860/3861/3863 (all SN 2012A, 2012). "UGC 5637", "10:25:09", "102509": 0. **Nothing after 2012.** |
| SIMBAD | TAP 10" cone; CDS timed out, so the CfA mirror was used | CfA 200 | **No object within 10".** Within 60": an [SST2011] UX? source at 24.3" (the ULX region), an HII region at 45", and SN 2012A at 50.1". |
| VSX | `vizier.idia.ac.za … B/vsx/vsx`, 30" (VSX version 2026-10-18) | 200 | **0 rows.** |
| MIRONG (J/ApJS/252/32), SPIRITS (J/ApJ/886/40, J/ApJ/877/110) | VizieR 60" cones | 200 | **0 rows each.** I found no De et al. WTP catalogue on VizieR; WTP was instead checked through TNS (§1.1) and ADS full text (`work/ads_novelty.json`). |

**Conclusion.** No broker, alert stream or catalogue has anything within 8" of the position. The only optically
catalogued transient in NGC 3239 is SN 2012A. Fink could not be reached (an error, not a null result).

### 1.3 ATel, CBAT, literature (`tns_validation/ads_recheck.py`; `work/ads_novelty.json`)

- **ADS, re-run 2026-11-02.**
  - `full:("NGC 3239" OR …) bibstem:ATel`: 5 hits, all SN 2012A from 2012 (ATel 3855, 3857, 3860, 3861, 3863).
  - TNS report/AstroNote bibstems (TNSTR/TNSAN/TNSCR) mentioning NGC 3239: 0.
  - Papers entered since 2026-10-01 that mention NGC 3239, Arp 263 or UGC 5637: 4, all false matches (M33
    extinction, WDS catalogue, and so on).
  - Position-string searches: only unrelated full-text noise.
- **Earlier check, still standing.** The 2026-11-01 full-text check (`work/ads_novelty.json`) found no mention of
  NGC 3239 in 67 De et al./SPIRITS papers.
- **CBAT and Rochester:** only SN 2012A (`reviews/ngc3239-check-2026-11-01/archive/raw/cbat_ngc3239_line.txt`,
  `rochester_ngc3239_lines.txt`). The live pages were re-read in §1.2.

## 2. TNS policy and the format of the report

Sources:
- the TNS help page, `https://www.wis-tns.org/content/tns-getting-started`, fetched 2026-11-02 04:13 UTC
- the TNS FAQ, `https://www.wis-tns.org/content/faq`
- the TNS2.0 Bulk API manual, `https://www.wis-tns.org/sites/default/files/api/tns2_manuals/TNS2.0_bulk_reports_manual.pdf`
  ("Updated: Jan 2025")
- TNS values mirrored on GitHub (`HeloiseS/tns_wizard/tns_codes.json`; `LCOGT/hermes` test options), and broker
  reporter code (ALeRCE, Fink, SkyPortal, TOM Toolkit, YSE_PZ)

**Scope.**
- Help page: *"the Transient Name Server (TNS) is the official IAU mechanism for reporting new astronomical
  transients (ATs) such as supernova candidates."* and *"Variable stars and CVs, including in particular Galactic
  nova candidates, … should not be submitted to the TNS."*
- Yaron (TNS), Sept 2024 talk: *"Initiated mainly for SN candidates, the TNS also handles other extra-galactic
  transients, including novae (CVs), AGN flares, TDEs, Kilonovae… BUT NOT variable stars, asteroids or other such
  galactic/local variable/moving sources."*
- OS-0030 is in NGC 3239 (cz 710 km/s, b = +54.8°). It is extragalactic and not a variable star (the review rules
  out Cepheid, Mira and LBV), so it is in scope.

**Archival discoveries.**
- Help page: *"If there is no measured last non-detection photometry point but you are certain that your discovery
  is a valid transient candidate, you can specify instead of the non-detection photometry point the archival info
  and comments."*
- Bulk manual, blocking errors: *"1 Last non-detection should precede the Discovery Datetime"*, *"2 At least one
  Photometry point - that of the discovery - should be filled"*, *"6 Last non-detection or archival info must be
  filled"*.
- I found no rule limiting how long after the event a report may come. Brokers routinely report from archival or
  public streams (ALeRCE/Fink use `"archiveid": "0", "archival_remarks": "ZTF non-detection limits not available"`).
- **Unverified:** a clean example of an AT report filed *years* after the event from archival infrared data. I did
  not find one; TNS cannot be searched by report delay.
- We have a real measured non-detection (2020-04-28), so the archival option is not needed.

**Instruments, filters and units.**
- FAQ: *"What to do if I don't find the required values in the pop-down lists for Units/Filter/Instruments …? Select
  'Other' from the pop-down list, and specify the relevant details in the following Comments field. These comments
  will then appear also in the Discovery/Classification certificate."* It adds that a new facility "that will report
  regularly" may ask the administrators to add its instrument.
- TNS values (GitHub mirror, committed 2026-09-02):
  - filters `"45": "3.4-WISE"` and `"46": "4.6-WISE"`
  - units `"1": "ABMag"`, `"3": "VegaMag"`, `"8": "Jy"`, `"9": "mJy"` (no µJy)
  - archives `"0": "Other"`, `"1": "SDSS"`, `"2": "DSS"`
  - at_types `0` Other - Undefined, `1` PSN, `2` PNV, `3` AGN, `4` NUC, `5` FRB
  - no WISE/NEOWISE instrument among 309 entries
- **Magnitudes:** TNS takes either AB or Vega; the unit is stated per point. The draft uses ABMag, -2.5 log10(f/3631
  Jy), and gives Vega in the comments.

**Mandatory fields** (form: red asterisks; bulk JSON: §5.5):
- `ra`/`dec` (value, error, units)
- `reporting_groupid` (may be "None"; AT 2022am was filed with no group)
- `data_source_groupid`
- `reporter`
- `discovery_datetime`
- `at_type`
- `non_detection` (obsdate, limiting_flux, flux_unitid, filterid, instrumentid) **or** (`archiveid`,
  `archival_remarks`)
- at least one `photometry` entry (obsdate, flux, flux_error, flux_unitid, filterid, instrumentid)

The bulk manual's example also has `host_name`, `host_redshift`, `internal_name`, `remarks`, `end_prop_period`,
`exptime`, `observer` and `comments`.

**WTP.**
- Masterson+2024 (arXiv:2401.01403): WTP names are internal, *"akin to the TNS naming scheme"*. A TNS name is listed
  only when an optical survey found the transient.
- Karambelkar+2026 (ApJ 1000, L8) on a WTP source: *"This source has not been reported to the Transient Name
  Server"*.
- So the premise "copy the WTP format" fails: no WISE-instrument AT reports exist to imitate.
- NEOWISE-based TNS **AstroNotes** do exist (2021TNSAN.212, Thévenot+, "100 SNe detected in the NEOWISE-R 2021 Data
  Release"; 2026TNSAN.241, Uno, De & Mo). They are commentary on known objects, not AT reports.

**Naming.** One example (SN 2020aeuh, first detected 2020-12-25, reported 2021-01) and TNS practice suggest the
designation follows the discovery date, so expect **AT 2020xxx**. This is inferred, not a written rule.

## 3. The numbers (`tns_validation/recompute_numbers.py`)

**Method.**
- Cached unWISE neo11 epochal coadds of tile 1556p166 (23 epochs).
- Per-season pre-event (MJD < 59000) median references, **leave-one-out**: an epoch never enters its own reference.
  The earlier light curve used full medians, which slightly bias the pre-event epochs.
- A 5×5 least-squares kernel plus a constant, and forced PSF photometry **at the HST position**. The earlier
  `wise_lc.py` forced at the rounded 156.2910 +17.1639, 0.65" away, which explains its 2-8% lower post-peak fluxes.
- Noise rescaled by the robust scatter of D/σ in a 120-px box.
- µJy from unWISE Vega nanomaggies with the repo's F0 = 309.540 / 171.787 Jy. AB = −2.5 log10(f/3631 Jy).

**Timing at the source.**
- Source: IRSA NEOWISE-R L1b frame index (`https://irsa.ipac.caltech.edu/ibe/search/wise/neowiser/p1bm_frm?POS=156.291224,17.163778&ct=csv`;
  569 frames contain the position).
- unWISE `n-m` exposure counts read at the source pixel.
- The coadd header's MJDMIN/MJDMAX cover the whole 1.56° tile. `oddsky.imaging.stack.epoch_mjd` takes their
  midpoint, so the "epoch MJD" used so far is the **tile** midpoint, not the source's.

| epoch | tile MJDMIN-MAX (span) | frames at source (all qual_frame > 0) | n-m at source W1/W2 | **mean MJD at source** | UT (mean) | first to last exposure (UT) |
|---|---|---|---|---|---|---|
| 13 | 58810.76-58813.58 (2.8 d) | 11 | 9/11 | 58812.548 | 2019-11-25 13:09 | 11-25 01:44 to 11-26 01:17 |
| **14 (last non-det.)** | 58965.94-58968.62 (2.7 d) | 11 | 11/10 | **58967.760** | **2020-04-28 18:15** | 04-28 05:59 to 04-29 05:31 |
| **15 (discovery)** | 59175.03-59177.71 (2.7 d) | 13 | 11/12 | **59176.688** | **2020-11-23 16:30** | 11-23 05:02 to 11-24 04:34 |
| 16 | 59333.02-59335.83 (2.8 d) | 13 | 11/11 | 59334.739 | 2021-04-30 17:44 | 04-30 04:42 to 05-01 07:22 |
| 17 | 59539.24-59545.71 (6.5 d) | 12 | 12/10 | 59540.985 | 2021-11-22 23:39 | 11-22 13:11 to 11-23 12:43 |

What the timing shows:
- Each unWISE epoch is a stack over about 2.7-6.5 days across the tile. **At any one position it spans only about
  1 day** (11-13 single exposures, 7.7 s each).
- The coadd timestamp (the header midpoint) is **not** the mean of the exposures at the source. It is early by
  0.31 d at epoch 15, 0.48 d at epoch 14, and 1.49 d at epoch 17.
- n-m is 1-3 below the frame count. unWISE dropped some frames, and which ones is not recorded, so the true mean is
  uncertain by about ±0.1 d. That is negligible.
- **Corrected dates:**
  - discovery 2020-11-23 16:30 UT
  - last non-detection 2020-04-28 18:15 UT. The review and case said "2020-05-02", which matches neither the tile
    midpoint (04-28 06:46) nor the source mean.
  - HST epoch +85.1 d after discovery
  - rise window < 208.9 d (the case says < 205 d)

**Photometry** (leave-one-out, at the HST position):

| epoch (UT) | band | flux (µJy) | S/N | AB | Vega | 5σ limit (AB) |
|---|---|---|---|---|---|---|
| 2020-04-28.76 | W1 | +13.8 ± 7.8 | 1.8 | — | — | **> 19.92** (3σ > 20.48) |
| 2020-04-28.76 | W2 | +0.7 ± 18.2 | 0.0 | — | — | **> 19.00** (3σ > 19.56) |
| **2020-11-23.69** | **W1** | **231.8 ± 8.3** | **27.9** | **17.987 ± 0.039** | 15.314 | |
| **2020-11-23.69** | **W2** | **310.0 ± 20.0** | **15.5** | **17.672 ± 0.070** | 14.359 | |
| 2021-04-30.74 | W1 | 94.3 ± 7.4 | 12.7 | 18.96 ± 0.09 | 16.29 | |
| 2021-04-30.74 | W2 | 128.6 ± 17.0 | 7.6 | 18.63 ± 0.14 | 15.32 | |
| 2021-11-22.99 | W1 | 39.1 ± 8.6 | 4.6 | 19.92 ± 0.24 | 17.25 | |
| 2021-11-22.99 | W2 | 41.8 ± 21.1 | 2.0 | — | — | > 18.84 |

- **Checks.**
  - The pre-event epochs (0-14) are consistent with zero: W1 rms 12 µJy, extremes +2.9σ (epoch 6, 2016) and −3.1σ
    (epoch 12, 2019); W2 rms 18 µJy, none beyond ±1.8σ.
  - **First ≥5σ epoch = 15 in both bands.** The production pipeline (`~/oddsky-runs/h0012a/1556p166/NGC3239/detections.parquet`)
    also has its first detections at epoch 15 (W1 S/N 26.8, W2 16.8), then epoch 16.
  - W1 and W2 at epoch 15 agree with the review (232 ± 8, 308 ± 20) to within 1%. W1−W2 = 0.955 (Vega).
- **Systematics on the magnitudes.**
  - (a) The repo's flux scale is 8.7% (W1) and 4.8% (W2) above De et al.'s NEOWISE fluxes for DS1 (README), i.e.
    0.09 and 0.05 mag.
  - (b) AB from F0-converted fluxes differs from Vega + the WISE AB offsets (2.699, 3.339) by 0.026 mag in each
    band. Vega + offset gives 18.01 and 17.70.
  - (c) The unWISE builds vary between epochs, but the kernel normalisation absorbs this.
  - **Quote about ±0.1 mag systematic.**
- **No quiescent source.** The reference flux at the position is about −3 µJy (triage). A difference-flux magnitude
  is therefore the transient's magnitude.
- **Position.**
  - HST 2021 point source: 156.291224 +17.163778 = **10:25:09.894 +17:09:49.60** (±4 mas statistical; the image is
    tied to Gaia with 8-12 mas scatter).
  - Gaia-tied WISE centroid (peak epochs): 156.29118 +17.16387 = 10:25:09.883 +17:09:49.93, ±0.18" formal (χ²-scaled)
    and about 0.2-0.3" realistic. It lies **0.36"** from HST (1-2σ).
  - The identification rests on the JWST 2024 source 0.01" from the HST source and the 0.23% chance of a vanishing
    source within 0.37".
  - Recommended TNS position: HST, error 0.1".

## 4. Data rights and credit (`tns_validation/mast_rights.py`; MAST CAOM via astroquery, 2026-11-02)

| programme (PI) | instrument | observed (UT) | MAST release | rights |
|---|---|---|---|---|
| HST 16179 (Filippenko, Alex), SNAP | WFC3/UVIS F606W, F814W | 2021-02-16 18:29-18:39 | 2021-02-16 | PUBLIC |
| HST 15446 (Dalcanton, Julianne) | ACS/WFC F606W | 2022-12-11 23:14 | 2022-12-12 | PUBLIC |
| HST 17502 (Thilker, David), treasury | WFC3/UVIS F275W/F336W/F438W/F555W/F814W/F657N | 2025-01-09 15:23-20:07 | 2025-01-10 | PUBLIC |
| JWST 3707 (Leroy, Adam), Cycle 2 GO Treasury | NIRCam F150W/F187N/F300M/F335M; MIRI F770W/F2100W | 2024-04-24, 2024-05-22 | same days | PUBLIC |

- Every dataset was released on the day it was observed, so **none was proprietary when used**.
- JWST 3707 Phase II text (`archive/raw/jwst_phase2_3707.txt`): *"As a Treasury, the data will be immediately public
  and supported by fast releases from our team."*

**unWISE epochal coadds.**
- Provenance: A. Meisner's NERSC directory `portal.nersc.gov/project/cosmo/temp/ameisner/neo11/`, with "no official
  release, no licence and no README" (README *Data provenance*).
- Permission: README *Provenance*: *"Aaron Meisner agreed by phone with Alan Shortz on 2026-11-01 to Oddsky using the
  time-resolved unWISE (neo11) epochal coadds for this search … The drafted email (`drafts/email_meisner.md`) was not
  sent."*
- **I cannot verify a phone call.** There is no written record. It would be prudent to confirm by email that a public
  TNS report naming these coadds is fine, and how he wants credit (co-reporter or acknowledgement).
- **Credit wording for remarks and any write-up:**
  - unWISE coadds: Lang 2014 (AJ 147, 108); Meisner, Lang & Schlegel 2017 (AJ 153, 38) and 2018 (AJ 156, 69;
    arXiv:1710.02526, the time-resolved coadds)
  - unTimely: Meisner, Caselden, Schlafly & Kiwy 2023 (AJ 165, 36)
  - WISE: Wright et al. 2010 (AJ 140, 1868)
  - NEOWISE: Mainzer et al. 2011 (ApJ 731, 53) and 2014 (ApJ 792, 30)
  - All seven bibcodes were checked in ADS on 2026-11-02 (2014AJ....147..108L, 2017AJ....153...38M,
    2018AJ....156...69M "Time-resolved WISE/NEOWISE Coadds", 2023AJ....165...36M, 2010AJ....140.1868W,
    2011ApJ...731...53M, 2014ApJ...792...30M). TNS remarks need only "unWISE (Meisner et al.)".
- HST/JWST data are public. The usual MAST acknowledgement applies if used in a paper; TNS needs nothing.

## 5. Classification and wording

- **Unclassified AT.** There is no spectrum, and TNS (Yaron 2024) says *"Classifications must be supported by a
  spectrum"*. The case's own hypotheses are LRN/ILRT-like 0.55, low-energy or obscured SN 0.35.
- **AT type.** Use "Other - Undefined" [0] rather than "PSN" so as not to imply a supernova. PSN is an acceptable
  alternative; TNS uses it loosely.
- **Host.** NED ObjectLookup resolves "Arp 263" and "UGC 5637" to NGC 3239 (2026-11-02). SIMBAD idents for
  "NGC 3239" include "APG 263" and "UGC 5637". TNS stores the host as "NGC3239". The source is 70.6" E of the NED
  centre.
- **Redshift.** NED preferred z = 0.002368305 ± 3.3e-6 (2024ApJ...964..172B, Baer-Way et al.), cz = 710 km/s.
- **Distance.**
  - NED `nDistance`: 12 values, 6.95-12.4 Mpc, median 10.15. Tully-Fisher gives 6.95, 7.91 and 8.10; SN 2012A gives
    8.79 to 12.4, e.g. 10.1.
  - CF4 (VizieR J/ApJ/944/94): galaxy DM 30.43 ± 0.45 from SN II (≈ 12.2 Mpc); group distance 12.2 Mpc. It is not in
    NED and not independent of SN 2012A.
  - "7.9-12.2 Mpc" is a fair working range, but the full range is about 7-12.4 Mpc. TNS has no distance field; the
    draft remarks leave distance out.
- **Remarks** (draft): observed facts only, with numbers, the data source and credit. There is no class claim and no
  luminosity or interpretation.

## 6. Other things that could make the report wrong or premature

1. **JWST 3707 / PHANGS team.** The data are a zero-exclusive-access Treasury intended to be "immediately public".
   - TNS reports from public data are normal practice: brokers report from the public ZTF stream, crediting it
     (*"Data provided by ZTF"*).
   - I found no TNS etiquette rule requiring notice to data owners; that point is unverified.
   - The discovery itself rests on WISE, not JWST. HST/JWST appear only in the remarks, and those sentences can be
     cut (draft, item 6).
   - A courtesy note to the 3707 PI (Leroy) and the 16179 PI (Filippenko, whose SN 2012A snapshot caught the source)
     after filing would be gracious, not required.
   - Nothing in ADS suggests anyone has published this source.
2. **Proprietary reports by others are invisible.** If one existed, TNS would attach our report to the existing
   object and return its name. That is harmless.
3. **Instrument "Other".** Unavoidable today. TNS asks for "Instrument=…" in the comments, and the comments appear on
   the discovery certificate. Asking TNS to add WISE/NEOWISE is warranted only if Oddsky will report WISE transients
   regularly; H-0012 has further IR-only leads (NGC 4945, M81, NGC 55), so that may be worth doing.
4. **Unofficial data product.** The discovery photometry comes from an unreleased, mixed-build product. The draft
   says so, with the ~0.1 mag systematic stated. It does not undermine the detection: 28σ in W1 and 15σ in W2,
   confirmed by HST and JWST.
5. **Case-file corrections to make before or with filing** (not done here; I was asked to write only these drafts):
   - C1: "flat from 2010 to 2020 May 2" → 2020 Apr 28; "2020 Nov 23" stays, but give MJD 59176.69.
   - C2: "< 205 d" → "< 209 d".
   - The review table: epoch 14 is "2020-04-28", epoch 16 is 2021-04-30 (not 04-28), epoch 17 is 2021-11-22.
   - The distance range wording.
