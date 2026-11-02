# oddsky.ai: how it's deployed

Two halves, one domain:

| | where | what |
|---|---|---|
| the site | Vercel project `oddsky`, Tango team (`tango-98e9ccfa`) | `python3 site/build.py` → `dist/`: every page, case dossiers, llms.txt, docket.ics |
| the observatory service | Cloud Run `oddsky-api`, project `oddsky-sky-br3c3`, us-central1 | `oddsky.hosted.app`: `/mcp` (Streamable HTTP) and `/api/*` |

`vercel.json` rewrites `oddsky.ai/api/*` and `oddsky.ai/mcp` to Cloud Run, so the site, the API and passkeys
share one origin. Data: Firestore (native, nam5) for observers, passkeys, keys, notebooks and the Sky Ledger;
`gs://oddsky-sky-br3c3-data/notebooks/<CODE>/<case>/` for each observer's working copy of a case.

## Ship

```sh
python3 site/build.py && vercel deploy --prod --scope tango-98e9ccfa   # the site
bash infra/hosted/deploy.sh                                           # the service (built by Cloud Build)
```

If the Cloud Run URL ever changes, update the rewrites in `vercel.json`.

## Operate

- **Admin token**: Secret Manager `oddsky-admin-token`; a local copy at `~/.config/oddsky/admin-token`. Sent as
  `x-oddsky-admin`.
- **Invite a collaborator** (observer code + key, no passkey needed):
  `curl -X POST https://oddsky.ai/api/admin/invite -H "x-oddsky-admin: $(cat ~/.config/oddsky/admin-token)" -d '{"code":"SG","name":"the advisor","label":"Claude Code"}'`
- **The grader** runs daily at 09:17 UTC (Cloud Scheduler `oddsky-grade-daily` → `POST /api/admin/grade`).
  Dry run: add `?dry_run=1`.
- **Verify the ledger**: `curl https://oddsky.ai/api/ledger/verify`, or the button on /ledger (re-hashes in the browser).
- **Genesis** (`site/genesis.py --post`) imported the 20 predictions already sealed in git as entries 1-31.
  It refuses to run on a non-empty ledger.
- **Cost**: Cloud Run keeps one warm instance (1 vCPU, 2 GiB, CPU throttled when idle, max 3), a few dollars a
  month; Firestore and Storage are inside the free tier at this scale. The project's $150 budget alert covers it.

## Gaia DR4 day (2 December 2026, ~12:00 CET = ~11:00 UTC)

What is waiting: 15 sealed predictions on GAIA:G (OS-0016, OS-0018 to OS-0025; 11 have DR4-era windows, and OS-0018 P4-P6
and OS-0019 P2 are 2022-2023 windows that wait for DR5 by design), the H-0009 ensemble forecast (47 events, sealed in
47f90fa), and the blind searches of hunt H-0014 ([hunts/H-0014/README.md](../hunts/H-0014/README.md)). One command runs all
of it: `scripts/dr4_day.py` (code in `src/oddsky/dr4day/`). Outputs go to `~/oddsky-runs/h0014/dr4/` (`summary.md` first);
small tables are copied into `hunts/H-0014/dr4/`. Nothing is written to a case, the Sky Ledger or a sealed file, with one
documented exception: the ensemble's DR3→DR4 id map (`dr4_ensemble.md` §2.5 item 4), written once and never overwritten.

**What DR4 changes for the code** (draft data model of 2026-06-26; confirm with the probe):

- Epoch photometry comes by DataLink only, with G columns renamed: `g_transit_time` → `g_obs_time`, `g_transit_mag` →
  `g_mag`, `g_transit_flux_over_error` → `g_flux_over_error`. `rejected_by_photometry` and `variability_flag_*_reject` are
  gone; rejected values come back empty. `gaia_epoch.to_series` already reads both layouts (§2.5 item 2 of the ensemble).
- TAP schema `gaiadr4`. The classifier columns are now `classifier_best_class_name` and `classifier_best_class_prob`. The DR3
  match table is `dr3_neighbourhood`, with the DR4 id in `source_id`. `has_epoch_photometry` is in `all_source_flags`.
- Anonymous DataLink takes 50 ids per request. A logged-in session takes 5,000: put `GAIA_USER=` and `GAIA_PASSWORD=` in
  `~/.config/oddsky/gaia.env` and the pipeline logs in.

### Before the day

| when | step |
|---|---|
| by 24 Nov | merge the H-0014 branch and **deploy the service** (`bash infra/hosted/deploy.sh`), so the hosted grader's `gaia_epoch` can read DR4's columns. Without that, DR4 fails, the grader falls back to DR3 and the predictions keep waiting |
| by 24 Nov | dry run: `uv run python scripts/dr4_day.py --release dr3` (about 25 min). Expect every stage `ok` and the ensemble self-test `PASS` |
| 25 Nov 11:00 UTC | **the Gaia archive closes until DR4 is out**: no DR3 TAP or DataLink for a week. The daily grader's Gaia fetches fail; an outage grades nothing |
| 1 Dec | pause the daily grader so nothing grades before a human reads the readiness output: `gcloud scheduler jobs pause oddsky-grade-daily --location us-central1` (if that location is wrong, `gcloud scheduler jobs list` shows the right one) |

### On the day (times from the release, T = ~11:00 UTC)

| T + | command | takes | expect |
|---|---|---|---|
| 0, then every 15 min until exit 0 | `uv run python scripts/dr4_day.py --release dr4 --stages probe` | 1-2 min | `probe.json`. `fixes` lists what to change: `--set key=value` for tables, columns and labels (e.g. `--set microlensing_class=microlensing`), or a `COLUMN_MAPS` entry in `src/oddsky/data/gaia_epoch.py` for epoch columns |
| ~0:30 | `... --release dr4 --stages readiness` (or `uv run python scripts/dr4_readiness.py`) | 1 min | one line per prediction: the release that answered, `span`, points in the window and baseline, identity check, `provisional` outcome from the grader's own `evaluate`. Exit 1 means the DR4 request failed. **`HOLD THE GRADER`** means a DR4-era check was answered by the DR3 fallback |
| ~0:45 | if `gaia_epoch.py` changed: test (`uv run --extra dev pytest tests/test_dr4day.py tests/test_gaia_epoch_release.py`), merge, `bash infra/hosted/deploy.sh`, re-run readiness | 20 min | same provisional outcomes from the deployed code |
| ~1:00 | `... --release dr4 --stages idmap,ensemble` | 5 min | `idmap.csv`; `hunts/H-0009/predictions/work/ensemble/dr4_idmap.csv` (written once); the ensemble grade (`grade_dr4.csv`, `grade_dr4_summary.json` beside the forecast; log in `ensemble/grade.log`). Publish it with `git diff 47f90fa -- src/oddsky/data/gaia_epoch.py src/oddsky/data/series.py hunts/H-0009/predictions/dr4_ensemble_grade.py` |
| ~1:10 | `... --release dr4 --stages catalogue,epochs,search,report --tiers 1` | 15-30 min | ~260 targets: sealed cases, every case, the 118 strong NEOWISE events, the H-0010 67, cones at the 11 events with no DR3 star. `search/ranked.csv`, quick-looks in `search/quicklook/` |
| ~1:45 | `... --release dr4 --stages epochs,search,report --tiers 1,2` | 1-3 h anonymous (60 requests); minutes logged in | ~3,300 targets: the unclassified NEOWISE brightenings and H-0004's R CrB candidates |
| after | identity doubts resolved by hand, on the ledger by appending; then `POST /api/admin/grade?dry_run=1`, compare with readiness's provisional outcomes, then resume the scheduler (`gcloud scheduler jobs resume oddsky-grade-daily --location us-central1`) | | |

Ranked candidates are triage, not claims: each goes through the novelty checks (TNS, VSX, SIMBAD, ADS full text) and a
referee before anything is said in public. Fixing a release name or a column map is fine; changing a grading rule is not.

## Rules the code enforces

- The Sky Ledger is append-only and hash-chained; there is no delete or edit endpoint. Mistakes are corrected by
  appending, never by rewriting.
- Every prediction sealed through `/mcp` goes on the public ledger at once. There are no private predictions.
- QA and QA2 are smoke-test observers; their notebooks are scratch, and they have sealed nothing.
