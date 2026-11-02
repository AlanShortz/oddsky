"""Gaia DR4 readiness: before the daily grader touches the sealed Gaia predictions, check that it will see DR4 data at all.

For every case with an ungraded prediction on a GAIA series, fetch the epoch photometry for its Gaia DR3 source_id with
`gaia_epoch.fetch_report` (nothing is written to the case) and print one JSON line per prediction: which release answered
(and any that failed, with the error), whether the window lies inside the release's span (2022-2023 windows wait for DR5
by design), the G points the grader would use in the window and baseline, the identity check (baseline median G against the
DR3 mean, |difference| <= 0.3 mag), whether a DR4 check was answered by the DR3 fallback, and the provisional outcome of the
hosted grader's own `evaluate` on these data. The logic is `oddsky.dr4day.readiness`.

It never grades and never writes to a case or the ledger. Exit status 1 if the requested release failed: the case before DR4
is published, and also if the archive renamed the release or changed the schema (fix src/oddsky/data/gaia_epoch.py: release
name and column map only, never the grading rules).

usage: uv run python scripts/dr4_readiness.py [--release dr4|dr3] [CASE ...]
"""

from __future__ import annotations

import argparse
import json
import sys

from oddsky.dr4day import config, readiness


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default="dr4", help="dr4 (default; DR3 fallback as in the grader) or dr3 (dry run)")
    ap.add_argument("cases", nargs="*")
    a = ap.parse_args(argv)
    rel = config.release(a.release)
    rows, failed = readiness.check(rel, a.cases)
    for r in rows:
        print(json.dumps(r))
    print(readiness.summary(rows, failed, rel))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
