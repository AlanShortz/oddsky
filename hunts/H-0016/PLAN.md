# Expedition 2026-11-02/03: plan and opportunity ranking

Written before any candidate was vetted (reconnaissance done; two pilots started). Kept as the record of what was
considered and why the choice fell where it did. Results go in README.md.

## Reconnaissance (what Oddsky can do today, 2026-11-02)

- All-sky NEOWISE visit-level light curves for 211.7 M stars (runs `sky3lens`, `sky4long`; events and light curves on
  GCS and in `~/oddsky-runs/h0008`, `h0009`) and per-star features for 176.9 M AllWISE sources at |b| >= 10 (BigQuery
  `sky.sky2_features`, with the AllWISE 2010 magnitudes alongside the NEOWISE 2014-15 baseline).
- unWISE difference imaging of 318 galaxies <= 10 Mpc (H-0012/H-0013) and forced light curves 2010-2024 (+ Spitzer).
- Gaia DR3 TAP (open until 2026-11-25), IRSA TAP (AllWISE, NEOWISE single exposures, ZTF DR), ATLAS forced photometry
  (slow queue), VSX via vizier.idia.ac.za, SIMBAD via simbad.harvard.edu, TNS (403 to plain curl tonight).
- Referee protocol (docs/REFEREE.md), Skeptic, cases, sealed predictions (Sky Ledger).

Leads the earlier hunts left on the table: H-0008's 821 isolated one-visit *fades* (never followed up); H-0002's 144
nuclear infrared flares in galaxies and ~2,000 fading AGN-coloured sources; H-0007's five grey single-visit dips.

## Five opportunities

| # | question | kind | value if positive | novelty risk | cost | ranking |
|---|---|---|---|---|---|---|
| 1 | **The WISE gap.** Which stars changed permanently between AllWISE (2010-11) and NEOWISE (2014-24) and were quiet afterwards? Nothing observed the mid-infrared sky from Feb 2011 to Dec 2013. The sky2 table already holds both epochs for 164.7 M stars: one query. | original detection strategy; cross-archive (2MASS 2000 as the third epoch, Gaia DR3 for the star) | a census of one-way mid-infrared changes: FU Ori-type eruptions that began in the gap, stars whose dust vanished, novae and eruptions whose 2010 state was the odd one, and OS-0014-like occultations caught by AllWISE | no AllWISE-vs-NEOWISE step census found in the literature (search 2026-11-02; the WTP group's image subtraction uses a 2010 reference but works the Galactic plane, |b| < 10 mostly) | one BigQuery query (done: 19,818 stars with a > 0.4 mag step in both bands), IRSA/Gaia cross-matches, a few dozen NEOWISE single-exposure light curves | **1** |
| 2 | **The dark sky.** H-0008 recorded 821 isolated one-visit fades in both bands over all 194.7 M stars and never looked at them. Which are not catalogued eclipsing binaries, and is any an OS-0014-like occultation? | extends a demonstrated method (H-0007/H-0008) | new long-period eclipsing binaries and dust occultations; a rate of deep one-day mid-IR fades per star per year, with the census tables giving the efficiency | low: nobody has published this list | positions + Gaia + VSX for 701 clean fades (done tonight), ZTF for the unclassified | **2** |
| 3 | **Nuclear infrared flares in quiet galaxies.** H-0002's 144 parallax-less afterglows at |b| >= 10 with W1 < 13: dust echoes of tidal disruptions in the nearest galaxies? | cross-archive | obscured-TDE candidates in bright nearby galaxies | high: Masterson et al. 2024 (WTP) searched all NEOWISE galaxies within 200 Mpc; MIRONG covered SDSS | cross-match only | 3 (deferred) |
| 4 | **Long fades.** A `--mode long` fade search (multi-visit, colour-dependent dimming with recovery) over the sky4 data for R CrB declines and long occultations in the plane | extends H-0009 | RCB and occultation census in the plane | medium | a new cloud run ($) | 4 (deferred) |
| 5 | **Rate limit.** Even if 1 and 2 find no new object, the census tables of sky3lens give the number of star-years searched; a null yields the first all-sky upper limit on deep day-long mid-infrared fades of bright stars | constraint-even-if-null | a number the occultation literature does not have | low | folds into 2 | folded into 2 |

Higher-risk idea kept in 1: a star that brightened by 1-2 mag between 2011 and 2013 and has been flat since is the
signature of an FU Ori eruption (decades-long plateau). Known FUors are ~30; one found at high latitude, outside the known
star-forming clouds, would be new.

## Controls planned

- Systematics: AllWISE-vs-NEOWISE median offset per magnitude from 18 M quiet stars (measured: |offset| <= 0.02 mag for
  8 <= W1 <= 14.5; W2 bias grows past W2 ~ 13.5, hence the cuts).
- Three epochs: 2MASS K (1998-2001) decides which of the two WISE epochs is the star's normal state (K - W1 ~ 0.0-0.1 for a
  photosphere).
- AllWISE artifact and blend flags (cc_flags, nb, ext_flg, w1rchi2), Gaia DR3 neighbours within 6", NEOWISE single-exposure
  light curves for the finalists (is the step a step?).
- Positive controls: catalogued classes that must show up (novae of 2010 such as KT Eri; eruptive YSOs; R CrB declines),
  checked after the SIMBAD/VSX cross-match. Negative: the 19,546 "brighter now" stars are expected to be dominated by blends
  and crowding (NEOWISE single frames resolve less than the AllWISE coadd); the fraction with a Gaia neighbour tells.
