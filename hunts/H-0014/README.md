# Hunt H-0014: Gaia DR4 day

**Question.** Gaia DR4 (2 December 2026) publishes a 66-month light curve for every one of its ~2.8 billion sources. Oddsky
holds a few thousand stars where something odd happened between 2014 and 2020: infrared brightenings seen by NEOWISE, lens
candidates the Gaia classifier saw but its catalogue left out, R CrB candidates never observed in a decline, and the stars of
our own cases. Within hours of release, what do their DR4 light curves show, and which of them are new?

**Status: built and dry-run against Gaia DR3 (2026-11-02). Waiting for DR4.** Nothing here is a discovery claim.

One command: `uv run python scripts/dr4_day.py --release dr4` (code: `src/oddsky/dr4day/`; the day's runbook:
[site/DEPLOY.md](../../site/DEPLOY.md#gaia-dr4-day-2-december-2026-1200-cet--1100-utc)). `--release dr3` runs the same
pipeline against the stand-in release.

## 1. What DR4 contains (checked 2026-11-02)

Tags: **[C]** stated by ESA, **[D]** the draft data model (could change), **[I]** our inference.

| | | source |
|---|---|---|
| date | **2 December 2026, ~12:00 CET (~11:00 UTC)** [C]; data public as soon as preparations finish [C] | [news 2026-05-07](https://www.cosmos.esa.int/web/gaia/news), [release](https://www.cosmos.esa.int/web/gaia/release), [data-release-4](https://www.cosmos.esa.int/web/gaia/data-release-4), [dr4-events](https://www.cosmos.esa.int/web/gaia/dr4-events) (2026-10-30) |
| archive outage | **closed from 25 Nov 2026 12:00 CET until DR4 opens** [C]: no DR3 TAP or DataLink for a week | news of 2026-10-08 |
| span | 66 months, 2014-07-25 10:30 to 2020-01-20 22:00 UTC; reference epoch J2017.5; TCB [C] | [DR4 content page](https://www.cosmos.esa.int/web/gaia/dr4) (updated 2026-09-14) |
| sources | ~2.8 billion processed (2,793,009,568). `gaia_source` holds only the 2,000,033,276 with good astrometry and photometry; the rest are in `all_source_astrometry` / `_photometry` / `_flags` [C/D] | DR4 page; draft data model |
| volume | ~400 TB, mostly epoch data (DR3: 10 TB). Older pages said ~500 TB [C] | DR4 page |
| epoch photometry | **for all sources** [C]. `epoch_photometry`: per-transit G, BP, RP, 121.8 billion rows, 7.2 TB (~44 transits per source [I]); `epoch_photometry_ccd`: per-CCD G, 23 TB [C]. **DataLink only, not TAP** [C]; `has_epoch_photometry` in `all_source_flags` [D] | DR4 page; [DataLink products](https://www.cosmos.esa.int/web/gaia-users/archive/datalink-products) |
| epoch columns | G renamed: `g_transit_time` → `g_obs_time`, `g_transit_mag` → `g_mag`, `g_transit_flux_over_error` → `g_flux_over_error`; BP/RP names unchanged; same time zero point (BJD_TCB − 2455197.5). `rejected_by_photometry` and `variability_flag_*_reject` are **gone**; rejected values are empty; variability rejections are a separate product, `EPOCH_FLAGS_VARI` ("used" flags, the reverse of DR3). Magnitudes use a new DR4 zero point [D] | draft data model, 2026-06-26 |
| other epoch products | epoch astrometry (62 TB, `EPOCH_ASTROMETRY`), epoch images (113 TB), RVS epoch spectra and parameters, XP epoch spectra (119 TB), all DataLink [D] | draft data model |
| variability | 20 `vari_*` tables: `vari_microlensing` **1,360** rows (DR3: 363), `vari_classifier_result` 315M (columns renamed `classifier_best_class_name` / `classifier_best_class_prob`, plus ~50 `prob_*` including `prob_microlensing`, `prob_rcb`), `vari_summary` 403M, `vari_eclipsing_binary` 2.39M, `vari_long_period_variable` 4.44M, `vari_yso` 218k, `vari_compact_companion` 6,224, `vari_planetary_transit` 1,007, ... No transients table [C/D]. The microlensing label string in the classifier is not given in the draft [D] | DR4 page; draft data model |
| exoplanets / binaries | no dedicated exoplanet table; `nss_two_body_orbit` (5.9M), `nss_masses` with `exoplanet_candidate_hrd_proba` and `lowmass_candidate_hrd_proba` [C/D] | DR4 page; [papers](https://www.cosmos.esa.int/web/gaia/dr4-papers) |
| DR3 match | `dr3_neighbourhood` (2.45 billion rows): DR4 `source_id`, `dr3_source_id`, `angular_distance` (mas), `magnitude_difference`, `probable_match`. Most ids carry over; merges and splits get new ids [D] | draft data model |
| alerts | `science_alerts`: 10,856 Gaia alerts in the DR4 span [C] | DR4 page |
| access | TAP (schema `gaiadr4` [D]) and DataLink. **DataLink: 50 ids per request anonymous, 5,000 logged in**; 5 concurrent TAP jobs logged in [C]. No `gdr4` directory on the bulk CDN, and none announced; `archive/documentation/GDR4/` is 404 [C] | [quotas](https://www.cosmos.esa.int/web/gaia-users/archive/collaborate); [release notes 3.15](https://www.cosmos.esa.int/web/gaia-users/archive/release-notes) (2026-10-14) |
| DR5 | not before the end of 2030 (10.5 years) [C] | release page |

**Uncertain until the day:** the exact minute; the DataLink CSV column names (the draft gives the internal layout); the
classifier's microlensing label; DataLink limits under DR4 load; any bulk files. The probe stage settles each within minutes.

Observed on 2026-11-02: the archive was already refusing synchronous TAP jobs ("maximum number of synchronous queued jobs (150)
reached", HTTP 503). The pipeline uses small async jobs with backoff, and fell back to async correctly during the dry run.

## 2. The plan

### 2.1 Grade what was sealed (stages `probe`, `readiness`, `idmap`, `ensemble`)

| | n | rule | code |
|---|---|---|---|
| sealed case predictions on GAIA:G | 15 (11 DR4-era; OS-0018 P4-P6 and OS-0019 P2 are 2022-23 windows that wait for DR5) | each prediction's `check`, graded by the hosted grader (`tools.evaluate`); the pipeline only previews it | `dr4day/readiness.py`, `scripts/dr4_readiness.py` |
| H-0009 ensemble forecast | 47 testable events | `dr4_ensemble.md` §2, run by the sealed grader, unchanged, as a subprocess | `hunts/H-0009/predictions/dr4_ensemble_grade.py` |

Gaps found and fixed:

1. **`gaia_epoch.to_series` could not read DR4.** The draft renames the G columns and drops the flag columns, so every DR4
   request would have raised KeyError. The grader would then have fallen back to DR3, which has no data for any of these
   sources, and all 15 predictions and the ensemble would have waited until the resolve-by date + 60 days and been closed
   "unresolvable". `to_series` now reads both layouts (`COLUMN_MAPS`, `column_map`). The DR3 output is identical (unit test;
   the ensemble self-test still passes). This is the change `dr4_ensemble.md` §2.5 item 2 allows (column names only). It was
   made before release, against the draft, and is published with the grade.
2. **Readiness could not dry-run** and reported DR5 windows as failures. It now takes `--release`, labels windows after the
   release span "waits for a later release", previews the outcome with the grader's own `evaluate`, and raises
   **HOLD THE GRADER** if a DR4-era check was answered by the DR3 fallback. The hosted grader falls back the same way, so a
   DR4 prediction could otherwise be graded on DR3 data alone. None can be today (no target has DR3 epoch photometry).
3. **The daily grader would grade on 3 December at 09:17 UTC** without anyone having read the readiness output. The runbook
   now pauses it from 1 December until identity doubts are resolved.
4. **H-0004's Gaia ids had been saved as floats** (`4.756341994426711e+18`), up to ±512 off, so DR4 light curves could not
   be fetched for them. A float pins the id to a 2,048-wide window, and `source_id` is the archive's key, so one `BETWEEN`
   per id, matched on G to 0.02 mag, recovers it: **1,695 of 1,695** listed ids recovered, 2 with two candidates (nearest
   kept), and 259 candidates had no Gaia id to start with (`data/h0004_ids.csv`, `scripts/recover_h0004_ids.py`).
5. The ensemble's DR3→DR4 id map (`dr4_ensemble.md` §2.5 item 4) needed a producer: the `idmap` stage builds it from
   `dr3_neighbourhood` with the pre-registered rule (nearest within 0.5″ and 0.3 mag). It writes `dr4_idmap.csv` only for
   the real release and never overwrites it.

### 2.2 Search where Oddsky has an edge (stages `catalogue`, `epochs`, `search`)

Ranked by discovery odds against effort. Every search reads DR4 epoch photometry for targets we already hold, a few thousand
DataLink requests' worth (about 100 MB), not the 7.2 TB table.

| # | search | targets | why the odds are good | effort |
|---|---|---|---|---|
| 1 | **NEOWISE strong events in DR4's span** | 64 events (50 with a Gaia star, 11 without; tier 1) | an achromatic infrared brightening that Gaia also saw, with BP = RP, is a microlensing event confirmed in two instruments. DR3 confirmed 3 of 3 it could test (OS-0026, OS-0027, OS-0029); the ensemble expects ~9 passes | minutes |
| 2 | **H-0010's 67 classifier-only lenses** | 67 (tier 1) | DR4's 1,360-event catalogue says which of our 21 candidates Gaia now catalogues (not ours to claim) and which it still does not. Two and a half more years of baseline test "single event", the strongest lens criterion | minutes |
| 3 | **every Oddsky case star** | 29 (tier 1) | OS-0014 vanished for ~95 days in 2017 and OS-0016 lensed in 2017, both inside DR4 and outside DR3; OS-0015's 385.7-day eclipses give ~5 cycles in 2014-2020 | minutes |
| 4 | **cones at the 11 events with no Gaia DR3 star** | 11 (tier 1) | DR4 adds sources; a new faint source at a strong event's position is a fresh test | minutes |
| 5 | **R CrB candidates' first declines** | 1,695 H-0004 candidates (tier 2) | an R CrB decline is 3-8 magnitudes and lasts months, impossible to miss even in Gaia's sampling. H-0004 searched 2018-2026 in the north (ZTF/ATLAS); DR4 adds 2014-2020 over the whole sky, including the southern half still queued on ATLAS | 1-3 h anonymous |
| 6 | **unclassified NEOWISE brightenings** | 902 (tier 2) | the 892 + 428 one-visit IR events (902 with a Gaia star, after de-duplication) no catalogue explains; an optical counterpart at the right time sorts lenses, dwarf novae and young stars from artifacts | same |
| 7 | **DR4 lenses nobody reported, with NEOWISE** | 1,360 catalogue rows (TAP only) | the catalogue minus our lists and the reference lists (OGLE, KMTNet, ZTF, Gaia alerts), matched to the NEOWISE event tables. A long-tE Gaia lens with a NEOWISE peak gets an infrared parallax baseline out to 2024 | minutes |

Not planned for the day: epoch astrometry (62 TB) for astrometric microlensing of our best events (worth a targeted request
later for OS-0016 and the strongest new candidates); generic eclipses of giants (`vari_eclipsing_binary` long-period
selection: a follow-up hunt); whole-catalogue searches, which need bulk files that do not exist yet.

**Per light curve** (`dr4day/lightcurves.py`; H-0010's refereed method, release-agnostic): clean, drop BP/RP window
contamination, take an iterative quiet baseline, find brightening and fading episodes (≥ 2 transits beyond max(4σ, 0.08 mag)),
test colour (ΔBP−RP and the excess-flux ratio k), fit a point lens (blend per band) against non-lens Pearson VII and FRED
shapes, and at a NEOWISE event time apply the sealed ensemble rule, imported unchanged. Labels, in order: lens-like
brightening, deep decline, dip, brightening not lens-shaped, chromatic, repeating, one-date (possible scan-angle artifact),
periodic large-amplitude variable, high-scatter variable, quiet. A Gaia peak within 60 d (or 2 tE) of a NEOWISE event moves a source up one priority. Sources already in the release's
lens catalogue or in the reference lists are kept but not ranked.

Acceptance test on H-0010's cached DR3 epoch data: see section 3. Triage still needs a referee, as designed.

## 3. Dry run against Gaia DR3 (2026-11-02)

`uv run python scripts/dr4_day.py --release dr3` with Gaia DR3 standing in for DR4. Every stage ran, with no failed
request (outputs: [`dryrun_dr3/`](dryrun_dr3/), `summary.md` first). Anonymous access, 50 ids per DataLink request,
2 s between requests.

| stage | time | result |
|---|---|---|
| probe | 2 min | all tables and columns found; DataLink offers EPOCH_PHOTOMETRY, MCMC_GSPPHOT, MCMC_MSC; epoch layout `dr3`; times inside the span. The same probe against `--release dr4` today fails as it should, exit 1: "schema gaiadr4 has no tables", DataLink `NotFoundFault`, "No services found ... Gaia DR4" |
| readiness | 8 s | 15 predictions. Against DR3, 10 windows lie after the span and 5 (OS-0018 P1-P3, OS-0019 P1, OS-0024 P1) lie partly outside it; none of the 10 target stars has DR3 epoch photometry, so: gradable 0, provisional true/false 0/0, identity doubts 0, no fallback. As expected |
| idmap | 38 s | 2,647 ids; 408 have no DR2 counterpart; for 2 of our DR3 ids the DR2 source of the same number is now a different DR3 star. The stand-in's map is therefore recorded but not applied (a DR2→DR3 table queried with DR3 ids is not a valid map); DR4's `dr3_neighbourhood` is the real thing |
| ensemble | 5 s | the sealed grader, unchanged: 47 of 47 "untestable (data)" on DR3 (none of the stars has DR3 epoch photometry, as the sweep found); it stops with "no event resolved". **Self-test PASS**: the 3 DR3-confirmed events pass, 0 of 6 shifted and 0 of 181 sliding controls pass, using the patched `gaia_epoch` |
| catalogue | 3 min | `vari_microlensing` 363 rows; classifier MICROLENSING 254, of which **67 are missing from the catalogue, the identical 67 of H-0010** (acceptance test); flags for 2,647 targets (885 have DR3 epoch photometry); cones at the 7 in-span no-Gaia events find no source, as in DR3; all 363 catalogue lenses are in the reference lists (H-0008 put DR3's catalogue there), so 0 "unreported", and 25 coincide with a NEOWISE brightening |
| epochs | 16 min | 2,647 sources in 56 requests (~17 s per request): tier 1 73 with data, 106 without; tier 2 817 with data, 1,740 without (DR3 published light curves for variables only). 0 chunks failed |
| search | 4 min | 896 light curves analysed, lens fits included, then VSX for the top 60 |

**Positive controls, recovered blind.** The three lens events DR3 confirmed (OS-0026, OS-0027, OS-0029) come out "lens-like
brightening", with the Gaia peak at the NEOWISE time and the sealed ensemble rule passing. Two of H-0010's candidates,
J072830.43-204112.5 (P 0.60) and J200958.93+321427.9 (P 0.40), are also in the H-0009 unclassified NEOWISE list, and their
NEOWISE times fall on their Gaia peaks: an infrared-optical coincidence the pipeline found by itself. Both are already Oddsky
candidates, so nothing new.

**Did DR3 turn up anything new? No.** After the release's own catalogues, the reference lists and VSX, 52 sources rank as
unknown to them: 29 are Oddsky's own H-0010 candidates (unreported, already ours), and 23 are on H-0004's R CrB list. Of
those 23, every one but one has a VSX entry: 7 known R CrB stars (Gaia16aau, ASASSN-V J161156.22-575527.2,
ASASSN-V J174257.20-362052.1, WISE J110008.77-600303.6, WISE J170343.87-385126.6, WISE J163450.35-380218.5, and
Gaia DR2 5845550927709092352), Miras and LPVs, two cataclysmic variables (Gaia20fgk, NSV 1586) and a UX Ori star (HQ Tau).
H-0004 had run VSX only on its final shortlist and never fetched these southern or non-ZTF stars, so the DR3 light curves
"found" stars VSX already knew. The exception, Gaia DR3 198809985981609600 (H-0003's DR3 fader list, Dec +37.8), has two
short 1.6-1.8 mag dips 471 days apart, 2015 April and 2016 August. That looks like a long-period eclipsing binary; VSX lists
it only as a generic Gaia DR3 variable. It is not claimed. DR4's 2017-2020 data and ZTF will test the period.

**What the dry run changed in the code** (each was a real defect, now with a test):

1. 45 R CrB-list "deep declines" were mostly Miras (33 had Lomb-Scargle power ≥ 0.6 at 300-700 d, and the Gaia classifier
   says LPV). Added: periodicity outside the strongest episodes, with a ≥ 0.3 mag amplitude requirement there. A periodogram
   of a single lens event, or of 20 clustered Gaia points, gives power 0.6-0.8 by chance; the first version wrongly called 18
   lens candidates periodic. Also added: the release classifier's class lowers the priority; VSX runs automatically on the
   top 60.
2. H-0010's event times are Gaia's own peaks. Testing Gaia "at the event" there is circular (61 trivial passes in the first
   run), so only NEOWISE times count as event times.
3. Sync TAP was refused under load (HTTP 503) during the run. The client now gives up on sync after two tries and goes
   async, and raises on an unexpected job phase instead of polling for an hour. Sources with no light curve are cached as
   absent, so re-runs do not ask again.
4. The ensemble self-test rewrites committed files; the pipeline restores their exact bytes, and a DR3 dry-run grade is moved
   out of the sealed directory.

The light-curve code was also checked against H-0010's refereed DR3 analysis of its 67 sources. Episode peak times and
amplitudes are identical for all 67. "Lens-like" applies to 3 of 3 Oddsky cases, 22 of 28 catalogued lenses and 18 of 21
H-0010 candidates, but only 1 of 7 H-0010 non-lenses (5 come out chromatic, 1 repeating).

**Release-day timing estimate.** Probe, readiness, idmap and ensemble take under 10 minutes once DR4 is served. Tier 1 is ~4
DataLink requests (179 sources) plus the catalogue queries: 15-30 minutes. Tier 2 is 50 requests anonymous (17 s each in
the dry run, so ~15 minutes on a quiet archive; plan 1-3 h under DR4-day load), or one request logged in. DR4 light curves
exist for every source, so tier 2 analyses ~2,600 light curves instead of 817: ~15 minutes on one core.

## 4. What is sealed in advance (this commit)

Nothing new goes on the Sky Ledger, and no case's prediction changes. Fixed by this commit, so that release-day results
cannot be tuned after the fact:

- the target lists (`data/targets.csv`, 2,822 rows, 2,647 distinct Gaia DR3 ids, with sets and NEOWISE event times;
  `data/h0004_ids.csv`);
- the triage rules and thresholds of `src/oddsky/dr4day/lightcurves.py` (episode threshold max(4σ, 0.08 mag), colour
  0.10 mag / 0.05 error or |k−1| ≤ 2σ_k, lens-vs-shape ΔBIC ≥ −10, periodic = LS power ≥ 0.6 with ≥ 0.3 mag and ≥ 20
  transits outside the strongest episodes, a NEOWISE-time match within max(60 d, 2 tE));
- what "new" means: not in the release's `vari_microlensing`, not in `H-0008/ext/reference_lenses.csv` (6″, |Δt| <
  max(2 tE, 60 d)), and not a catalogued lens, CV or YSO in our hunts' classification. A candidate still needs TNS, VSX,
  SIMBAD and ADS full-text checks and a referee before it is called unreported;
- already sealed elsewhere and graded unchanged: the 15 case predictions and the H-0009 ensemble (47f90fa).

**Drafted for sealing before release (2026-11-02):** five numerical forecasts of the searches' outcomes,
[`predictions/dr4_search_forecast.md`](predictions/dr4_search_forecast.md) (H-0010's 67 in DR4 `vari_microlensing`; whether
Oddsky's P(lens) ranks those sources as the catalogue does; the single-event test of H-0010's 21 candidates; strong NEOWISE
events in the catalogue; a controlled test of whether the unclassified NEOWISE brightenings have optical counterparts in
Gaia), with a grader that has passed its self-test on the DR3 dry run. Refereed 2026-11-02 ("seal after changes"; changes
applied). They are sealed only when merged to `main` before 2026-12-02.

## Files

| | |
|---|---|
| `scripts/dr4_day.py` | the one command |
| `src/oddsky/dr4day/` | `config.py` (the release switch), `archive.py` (polite client), `probe.py`, `readiness.py`, `catalogue.py`, `targets.py`, `lightcurves.py`, `idfix.py`, `pipeline.py` |
| `tests/test_dr4day.py` | 17 offline tests (plus the 5 in `tests/test_gaia_epoch_release.py`, unchanged and passing) |
| `data/targets.csv`, `data/h0004_ids.csv` | sealed inputs |
| `predictions/` | the draft forecasts (`dr4_search_forecast.md`), their sample, grader (`dr4_search_grade.py --self-test`) and Monte Carlo (`work/forecast.py`); tests in `tests/test_dr4_search_grade.py` |
| `dryrun_dr3/` | the dry run's small outputs (summary, status, probe, readiness, ranked, metrics, cross-matches, ensemble logs) |
| `~/oddsky-runs/h0014/<release>/` | everything else, including the epoch-photometry cache and quick-look plots (not in git) |
