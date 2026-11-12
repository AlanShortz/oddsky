# Sealed forecasts: how to check them

A forecast counts only if it was fixed before the data that grade it. To check one, hash the file at the commit that sealed
it and compare the date with the release of the data (Gaia DR4: 2 December 2026):

    git show <commit>:<file> | shasum -a 256

| forecast | sealed (UTC) | commit here | original commit | sha256 of the file at that commit |
|---|---|---|---|---|
| `hunts/H-0009/predictions/dr4_ensemble.md` | 2026-11-01 03:17 | `c9e0cfb` | `47f90fa` | `cb4bd6126cf0caf4a518d0e40018cb943bd5899cefd571a5fbe4ff081a07d187` |
| `hunts/H-0014/predictions/dr4_search_forecast.md` | 2026-11-02 21:49 | `15541ff` | `00e2e53` | `65e0c48481b3a50f2dcc73b665c27b553a48a2f64b2d6e766c96194374ce5e34` |
| `hunts/H-0015/predictions/dr4_astrometric_forecast.md` | 2026-11-03 02:29 | `583e437` | `2db9d5f` | `338f4a2d638cb9ffeb6ea52ebcee2f9bcdbbed9f35c19992d07defcfa5ff2de2` |
| `hunts/H-0018/predictions/dr4_handedness.md` | 2026-11-06 19:53 | `4697510` | `4bc4074` | `1466472d0833b942f879b9ad3ab5ac8b7eea09a32fc2949be938a6d1d388cd95` |

Trial 001's answers were sealed in commit `3cb51e8` (original `eac42b3`). Predictions made through the hosted server are on
the hash-chained [Sky Ledger](https://oddsky.ai/ledger), which has its own record.

## What the dates rest on

This repository was developed in private and published on 12 November 2026. Before publication, one pass over the history
removed the name of a private individual from old files and commit messages and replaced a personal email address. That
changed every commit hash and nothing else that matters here: the commit dates are the original ones, and the sealed files
are byte for byte the same, so the sha256 values above are the ones recorded when each forecast was sealed.

- `docs/commit-map.tsv` lists every original commit beside its commit here. Commit hashes quoted in documents written before
  publication (hunt write-ups, trial records) are original ones; look them up there.
- The dates in the table are when each forecast was merged in the private repository, as GitHub recorded it. Nobody outside
  could check those at the time. What anyone can check is weaker and still sufficient for Gaia DR4: this repository, with
  these files in it, was public from 12 November 2026, three weeks before the data.
- The original repository is kept, unchanged and private, and can be shown to a referee.

From publication on, history on `main` is not rewritten.
