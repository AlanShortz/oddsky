# Hunt H-0002: infrared afterglows on Sun-like stars

ASASSN-21qj was found because its debris cloud crossed our line of sight. Most collisions won't
be aligned that way, but their hot dust glows in the infrared from every direction. So the
infrared-first signature should be more common than the dimming that found ASASSN-21qj, and an
optical search cannot find it.

Method: upload Gaia DR3 FGK main-sequence stars to IRSA TAP, once per NEOWISE time window, and
let the server average W1/W2 per star per window. Look for stars whose W2 brightened by > 0.2 mag
and reddened in W1-W2 while staying photospheric before, then vet each one.

## Result (2026-10-27): run on the whole high-latitude sky

The bulk route worked: IRSA's NEOWISE Parquet on AWS, read from Google Cloud Batch (see `infra/gcp/`).

| | |
|---|---|
| sky | 10,145 HEALPix pixels (Galactic latitude ≥ 10°, plus ASASSN-21qj's pixel) |
| data | 146.6 billion NEOWISE detections, 2.99 TB of Parquet columns read |
| stars | 176.9 M AllWISE sources; 114.7 M with ≥ 8 visits; **18.1 M testable photospheres** |
| compute | 508 tasks, 24 spot VMs, 1 h 53 min (~$2-8) |
| calibration | ASASSN-21qj recovered blind: W2 +0.79 mag at 79σ |
| systematics | 18 M quiet photospheres drift 0.02-0.03 mag *fainter* in W2 by 2024; onset dates of flags are spread evenly over 2017-2023 |

**Funnel**

| step | n | what fell out |
|---|---|---|
| afterglow flags | 224 | |
| Gaia stellar parallax | 80 | 144 have no parallax: galaxies with nuclear infrared flares (kept as a separate sample) |
| no blend, no pair | 43 | 37 blends with a brighter Gaia neighbour, or pairs that rose on the same visit |
| centroid moves *toward* the star (proper-motion corrected); < 20% neighbour flux in W2 | 26 | moving objects and creeping neighbours (one 0.1"/yr intruder) |
| main sequence, no dust measured before 2010 | 6 | 11 hot stars (Be-star disks), 7 dusty young stars, 2 cool giants |
| not already catalogued | **2** | ASASSN-21qj (calibrator), AR UMa (a known polar), an RS CVn star, a Gaia YSO candidate |

**The two survivors** (both refereed; see each case's `reviews/`):

- [OS-0014](../../cases/OS-0014): **Gaia DR3 6733428488637673984 vanished for ~95 days in 2017** (≥ 99.5% occulted, grey in
  SkyMapper g/r/i/v, seen independently by ASAS-SN, SkyMapper and NEOWISE), then grew a ~650 K infrared excess that lasts to
  2024. Not in SIMBAD, VSX, or any alert stream. Referee: ≥ 97% astrophysical and on this system.
- [OS-0013](../../cases/OS-0013): Gaia DR3 5792808347020475136, a K3 dwarf whose ~1000 K excess appeared abruptly in 2018 and
  persists. Its variability is in VarWISE (Paz et al. 2026), labelled a long-period variable. Referee: ~93% astrophysical.

Both await what only an astronomer can arrange: spectra (lithium, Hα, radial velocities) and mid-infrared follow-up, plus
Gaia DR4 epoch photometry (Dec 2026), which covers both events.

**Also in the same table, for later:** 144 nuclear infrared flares in galaxies (candidate tidal-disruption dust echoes and AGN
flares) and ~2,000 fading AGN-coloured sources (candidate mid-infrared "changing-look" quasars). `queries.sql` has the SQL.
The full per-star table (176.9 M rows) is queryable in BigQuery: `oddsky-sky-br3c3.sky.sky1_features`.
