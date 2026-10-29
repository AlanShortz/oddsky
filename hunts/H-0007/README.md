# Hunt H-0007: one night in the infrared

**Question.** NEOWISE looked at every star for about a day, every six months, for ten years. Which ordinary stars were
dramatically brighter or fainter on just one of those days and normal on every other? A star that changes for a day and
then goes back is rare. Almost every physical cause is either a binary (eclipses, outbursts) or something passing in
front of the star: a dust cloud, or a gravitational lens.

**Why this hunt.** The H-0002 sky pass already holds visit-level W1/W2 light curves for every bright star that changed. Two
pilots on the first pass (sky1) asked a similar question and drowned in a bug (see [`../H-0002/BUG-2026-10-28.md`](../H-0002/BUG-2026-10-28.md)):
46,760 "single-visit dips", 98% of them made by the merged-visit bug. The fixed pass (sky2) had not been searched for
single-visit events, so this hunt does that. It also asks for the mirror image, a star that **brightens** by the same factor in
W1 and W2. Nothing a star does by itself is grey from 3.4 to 4.6 µm while tripling its flux for a day. A microlensing event is.

**Data.** `oddsky-sky-br3c3.sky.sky2_lightcurves` (NEOWISE 2014-2024, visit medians, |b| ≥ 10°; stored for stars with
W1_base < 13 and W2 peak-to-peak ≥ 0.3 mag, or a W2 rise), `sky2_features`, IRSA AllWISE and NEOWISE single exposures, Gaia DR3
(source, astrophysical parameters, epoch photometry, `vari_microlensing`), ZTF DR (IRSA), ALeRCE, TESS FFI cutouts (TESScut),
VSX through a VizieR mirror (vizier.idia.ac.za; CDS and www.aavso.org were unreachable or behind a CAPTCHA on 2026-10-29), TNS,
the Gaia alerts list (`../H-0005/alerts.csv`).

## Pass 1: quiet photospheres (`scripts/hunt_h0007_dips.py`)

17,545,832 sky2 stars with ≥ 10 visits, |W1-W2| < 0.15, W1 < 13 and a quiet first-three-visit baseline; 5,303 of them have W2
peak-to-peak ≥ 0.3 mag and a stored light curve. Event visit: W1 **and** W2 both ≥ 0.25 mag and ≥ 5σ off the star's median.

| | stars |
|---|---|
| with a dimming visit | 74 (onsets spread evenly over 2014-2024: no instrumental epoch) |
| in VSX already | 58: eclipsing binaries (EA/EB/EW), LPVs, YSOs, a DY Per star, nova-likes in low state |
| not in VSX | 16. **The deepest Sun-like one is OS-0014**, recovered blind (2017.23, W1 +1.64). The rest: LMC giants, hot stars with disk changes, single 0.3-0.5 mag dips (likely uncatalogued long-period eclipsing binaries; see "open leads") |
| with a brightening visit | 62, mostly sustained (H-0002 afterglows); 47 single- or double-visit |

## Pass 2: achromatic one-visit events in every stored light curve (`scripts/hunt_h0007_lens.py`)

79,191 stars (≥ 10 visits). Event: a run of 1-3 consecutive visits brighter (or fainter) in both bands by ≥ max(0.15 mag, 6σ),
with |ΔW1 − ΔW2| ≤ 0.08 + 0.12|ΔW|, and **every other visit within 4σ (or 0.1 mag) of the median**.

| | brighten | fade |
|---|---|---|
| events | 107 | 87 |
| not at the first or last visit | 76 | 67 |
| stellar colours (W1−W2 < 0.4; the rest are quasar flares) | 36 | 63 |
| already in VSX | 20 | 38 |

**What the brightening list turned out to be** (blind recoveries, every one checked at the position):

- **Dwarf novae and other CVs in outburst:** DX And, GY Cnc, BF Eri, EX Hya, V364 Lib, V1483 Oph, ASASSN-19ax, V1129 Cen, Karachurin 3,
  BE UMi, MR UMa, GK Per, plus the polar AR UMa in a high state. NEOWISE catches a dwarf nova in outburst at ×2-3, achromatic
  at the 0.05-mag level, because the disk's Rayleigh-Jeans tail has W1−W2 ≈ 0.
- **Two microlensing events Gaia already found:** Gaia20fnr (a ~2-year binary-lens event; NEOWISE shows it rise to A = 1.38 in 2021.7 and fall back,
  ΔW1 = −0.35 / ΔW2 = −0.34; its NEOWISE light curve is already published, arXiv:2601.15969) and **Gaia DR3 4084984459435880064** (Wyrzykowski et al. 2023, `vari_microlensing`: u0 = 0.063,
  tE = 53.2 d, peak MJD 57297.4). NEOWISE caught it at A ≈ 12 on 2015 Sep 29-30, still rising 0.24 mag across the visit,
  1.5 days before Gaia's own epochs at A = 16. Gaia's amplitude is 2.99 / 3.01 / 3.02 mag in BP / G / RP; NEOWISE's ΔW1 = −2.69, ΔW2 = −2.71
  (two days before peak). Achromatic from 0.5 to 4.6 µm. From the NEOWISE slope alone, before reading the Gaia catalogue, we estimated
  tE ≈ 50 d and peak ≈ 3 days after the visit.
  - *Catalogue error found on the way:* VSX types this star as a young stellar object (ASASSN-V J185744.81-204632.6, "YSO"). It is a
    microlensing event in a K giant (Gaia DR3: Teff 4,990 K, log g 2.9, RV +88 km/s).
- Hot stars whose Be-type disks grew or shrank, Orion M dwarfs (YSO flares), symbiotics (LT Del, V2873 Cyg).

**What the fade list turned out to be:** mostly eclipsing binaries caught in eclipse, nova-likes in low states (BG Tri, LS Peg).
The two deepest uncatalogued fades are **artifacts**: J191517.51-230501.6 and J181854.69-500545.7 are close pairs (Gaia neighbour 1.9";
RUWE 22) that NEOWISE splits into two detections in some exposures. In the event visit the AllWISE association flipped to the faint
component. Visible in the single exposures as two detections per frame within 2.5" and reduced χ² of 30-200 in every visit.

## Pass 3: the faint stars, W1 13-15 (`scripts/hunt_h0007_faint_fetch.py`, `hunt_h0007_faint.py`; 2026-10-29)

sky2 stored visit light curves only for W1 < 13, but `sky2_features` records each star's W1/W2 peak-to-peak. Of 64,451,651 stars with
13 ≤ W1 < 15 and ≥ 10 visits, 7,804 have W1 and W2 swings ≥ 0.4 mag, stellar colours (|W1−W2| < 0.4) and a quiet first three visits. For
each, every NEOWISE single exposure within 3" came from IRSA (Gator). The same one-visit test was then applied with faint-star
thresholds (≥ max(0.3 mag, 6σ) in both bands, achromatic to 0.1 + 0.15|ΔW|), plus the exposure-level traps this hunt had met.

| | stars |
|---|---|
| events | 64 (55 brightenings, 9 fades) |
| clean: ≤ 20% of event-visit frames with a W1/W2 artifact flag, χ² ratio < 3, no split detections, not extended | 30 (22 brightenings, 8 fades) |
| clean brightenings already in VSX | 11: ten cataclysmic variables in outburst (IR Gem, SW UMa, OY Car, TU Men, AR UMa, ASASSN-14cd, ASASSN-14hd, ASASSN-17oz, Mis V1448, CSS 090201:090210-113032) and a semiregular |
| the rest | 6 optically faint, very red sources (G ≈ 20-21: quasars), 2 hot LMC stars (Be disks), 1 Orion M dwarf (a young star), 1 borderline K dwarf, and **J193353.06-211813.4** |

**Most faint brightenings are latents.** 33 of the 55 sit in a visit whose frames carry persistence or halo flags (cc_flags P/H/D) in
20-80% of exposures, against about 0% in every other visit. Their χ² is 3-13 times the star's normal. Latent images of bright stars
crossing a faint star's position mimic a one-day, roughly grey brightening. The visit medians keep only unflagged frames, but the latent
contaminates those too.

**Cross-check.** Re-reading NEOWISE from the AWS Parquet for the same 7,804 stars on Google Cloud (run `sky2keep`,
`infra/gcp/neowise_keep.py`; 3,610 of 3,635 pixels; the job ended FAILED because tasks on 25 dense pixels did not finish) and applying `hunt_h0007_lens.py` unchanged finds 39 isolated
brightenings. 37 of them are also in the exposure-level list, J193353 among them.

**A second microlensing event: [J193353.06-211813.4](J193353.md)**, now case [OS-0017](../../cases/OS-0017) (Gaia DR3
6772245406602788608; l = 18.0°, b = −18.6°). A K giant, probably in the halo: Teff ≈ 4,900 K with map extinction, beyond ≈ 6 kpc,
v_t ≳ 350 km/s.
- *NEOWISE:* on 2020 Apr 9-10 it was ×1.98 brighter in both bands, and the only one of 2,021 stars in those frames to change.
- *ATLAS* confirmed it (task 5271652): one event on 88 nights of 2020, in two units and both bands. ×2.42 on Mar 11 (the first night of
  the season), ×1.99 on Apr 10 (the NEOWISE night), ×1.30 in mid-May, ×1.05 in September, nothing else in 2015-2026.
- *ZTF* catches the June-July tail; it is the only star of 84 in its quadrant to move ([figure](figures/J193353.png)).
- *Fit:* the peak fell in an ATLAS gap and is unobserved. A lens with annual parallax fits all three surveys: peak 2020 Mar 17-22 at
  about ×2.7-2.9, tE 40-55 d. A lens without parallax leaves an asymmetry.
- *Referees:* [first](reviews/claude-referee-J193353-2026-10-29.md) P(mundane) = 0.08, then
  [second, with ATLAS](reviews/claude-referee-J193353-atlas-2026-10-29.md) 0.02. Status: **reproduced**.
- The first referee's prediction for ATLAS, made from NEOWISE and ZTF, placed the peak on Apr 10 at ×1.95. ATLAS showed it about three
  weeks earlier and higher.

## The candidate: a microlensing event toward the Galactic anticentre (reproduced by ATLAS; case [OS-0016](../../cases/OS-0016))

**[J040025.77+323527.4](J040025.md)** (Gaia DR3 170329679884731008; l = 162.8°, b = −15.3°). A red-clump K giant (Teff 4,820 K,
log g 2.5, R ≈ 8 R☉, L ≈ 33 L☉, ~3 kpc). It is flat to 0.01-0.02 mag in 21 NEOWISE visits (2014-2024), ZTF (2018-2025, r rms 0.011 with catflags = 0)
and Gaia DR3 (not variable). On **2017 Aug 27-28** all 13 NEOWISE exposures were brighter by a factor **2.731 in W1 and 2.716 in
W2**: achromatic to 0.5%, colour change −0.008 ± 0.008 mag. The centroid stayed on the star (0.08"). 211 stars with W1 < 12.5 within 20' in the same frames changed by +0.002 ± 0.007 mag
(W1 10-11); the target is the only one that moved by more than 0.3 mag. Visits 6 months before and after were normal. A point-lens fit
that includes the flat neighbouring visits gives tE = 6-53 d (95%), with the peak within −1 to +12 d of the visit. Not in VSX, TNS or the Gaia
alerts. Gaia observed the star on 2017 Aug 22, five days before NEOWISE. It raised no alert, but the predicted ΔG ≈ −0.8 is below the
2017 alert threshold. About 0.07 events like this were expected among the anticentre stars in this hunt, so finding one is a 1-in-15 outcome.
ASAS-SN (service down) and ATLAS 2017 data are not yet examined.
Not in Gaia DR3 `vari_microlensing`, because DR3 ends in May 2017. Refereed ([report](reviews/claude-referee-2026-10-29.md)): survives every instrumental, association and physics attack; P(mundane) = 0.15
before optical data. **Then ATLAS confirmed it** (task 5270459, 2026-10-29): one smooth event in eleven years, ×2.79 on the night NEOWISE
measured ×2.73, peaking at about ×7 around 2017 Sep 16 ([figure](figures/J040025_atlas.png)). The light curve is **asymmetric**: a symmetric
point-lens curve is rejected (Δχ² ≈ 365). A second referee ([report](reviews/claude-referee-2-2026-10-29.md)) confirms the asymmetry is
astrophysical (0.95) and most likely annual parallax (0.80). Only π_E,∥ ≈ 0.6 is robust, |πE| ≈ 0.6-1.6, and tE = 47.7 or 51.8 d (u0 sign).
**The lens mass is not measured.** Gaia DR4 astrometry may measure θE. Status: event **reproduced**; parallax a candidate measurement.

## Open leads (not pursued yet)

- Single-visit 0.3-0.5 mag grey dips on Sun-like stars with no VSX entry, probably uncatalogued long-period eclipsing binaries:
  J051437.36-103357.0 (a halo giant at ~6 kpc; NEOWISE dips 2018.11 and 2023.11; ZTF shows 40 points 0.2-0.43 mag deep in g, r and i),
  J181519.10+093636.5 (a giant; ZTF dips in pairs ~25 d apart, repeating every ~324 d), J173006.47-101342.6 (a giant; ZTF dips 2018-2024,
  P ≈ 222 d or an alias), J160841.91-105450.3 (F star; six deep ZTF points), J233050.98-092126.7. These are probably uncatalogued
  eclipsing binaries. Periods are ambiguous with ZTF's sampling (`work/ztf_*.csv`).
- Pass 3 covers W1 13-15 only for stars whose catalogue swing is ≥ 0.4 mag in both bands. Smaller events in faint stars (A < 1.45)
  still need a full re-read of NEOWISE.
- **DX And** (a known U Gem dwarf nova): TESS and ATLAS independently put its orbital period at 0.440972 d, not the catalogued
  0.440502 d (a likely one-year alias in the old spectroscopy). It is **in outburst now** (ATLAS, 2026 Oct 25-26). See [`DX_And.md`](DX_And.md).

## Lessons for the sky pass

- For faint stars, latents (cc_flags P/H) are the main source of one-visit "brightenings". Measure the share of flagged frames in the
  event visit against the other visits; unflagged frames from that visit are not clean either.
- 19-digit ids (AllWISE cntr, Gaia source_id) lose precision as float64. It happened twice here: the sky1 bug, and a cross-match
  table whose Gaia ids became float once a row had no match. Keep ids as int64 or text end to end.
- Query the mirror. The brightening run found more physics than the dimming run, and its dominant content (dwarf novae) was a
  surprise.
- A NEOWISE "fade" in a close pair is usually the association flipping between deblended components. Check for two detections
  per frame before believing it.
- VSX through `vsx.aavso.org` rate-limits after ~150 cone queries and then serves a CAPTCHA. The script read the CAPTCHA page as "no
  match", so DX And looked uncatalogued for an hour. `scripts/hunt_h0007_vsx.py` now goes through the VizieR mirror and
  reports errors as errors.

Inputs not committed (re-create them): `data/quiet_ptp_lc.csv` is the BigQuery join of `sky2_features` and `sky2_lightcurves` with
n_visits >= 10, |color_base| < 0.15, w1_base < 13, base_scatter_w2 < 0.05, w2_ptp >= 0.3 (30 MB). `work/lc.parquet` is written by
`hunt_h0007_dips.py`. TESS cubes come from TESScut (`astrocut?ra=..&dec=..&x=15&y=15&units=px&sector=N`).

Files: `scripts/hunt_h0007_*.py`; `work/events.csv`, `work/lens_events.csv` (every event), `work/*_x.csv` (with Gaia, VSX), `data/`
(per-object archive pulls; TESS cubes are not committed, see `J040025.md` for how to re-fetch).
