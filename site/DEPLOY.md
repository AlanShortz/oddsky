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

## Gaia DR4 day (scheduled 2 December 2026)

15 sealed predictions (OS-0016, OS-0018 to OS-0025) wait on Gaia DR4 epoch photometry. Their windows closed years ago, so the
daily grader already re-fetches them; until DR4 answers they stay "waiting". `gaia_epoch` falls back to DR3 on any DR4 error, so
a renamed release or a changed schema would leave them waiting until 60 days after resolve-by and then close them as
unresolvable. On release day:

1. `uv run python scripts/dr4_readiness.py`. It never grades. Each line says which release answered, the error if DR4 failed,
   the points the grader would use in each window and baseline, and whether the baseline G matches the DR3 mean (|Δ| ≤ 0.3 mag).
   Exit status 1 means the DR4 request failed.
2. If it failed, fix `src/oddsky/data/gaia_epoch.py`: map the DR4 release name and columns only, never the grading rules. Test,
   merge, `bash infra/hosted/deploy.sh`, and re-run step 1.
3. Identity doubts (a DR3 id that now points at another or a split source) are resolved by hand before the grader runs: note
   them on the ledger by appending, never by editing a seal.
4. Dry-run the grader (`POST /api/admin/grade?dry_run=1`) and read the notes before letting the daily run grade.

## Rules the code enforces

- The Sky Ledger is append-only and hash-chained; there is no delete or edit endpoint. Mistakes are corrected by
  appending, never by rewriting.
- Every prediction sealed through `/mcp` goes on the public ledger at once. There are no private predictions.
- QA and QA2 are smoke-test observers; their notebooks are scratch, and they have sealed nothing.
