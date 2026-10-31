"""Gaia DR4 readiness: before the daily grader touches the sealed Gaia predictions, check that it will see DR4 data at all.

For every case with an ungraded prediction on a GAIA series, fetch the epoch photometry for its Gaia DR3 source_id with
`gaia_epoch.fetch_report` (nothing is written to the case) and report:
  release   which release answered for this source, and any release that failed (with the error);
  coverage  the last epoch, the number of G points the grader would use (photometry rejects dropped, variability-outlier
            transits kept) in the prediction's window and in its baseline;
  identity  the baseline median G against the DR3 mean G in the case (|difference| > 0.3 mag suggests the DR3 id now points
            at a different or differently split source in DR4; positions need the DR4 catalogue and are not checked here).
It never grades. Exit status 1 if the DR4 request failed, which is the case before DR4 is published, and also if the archive
renamed the release or changed the schema: in that case fix src/oddsky/data/gaia_epoch.py before the grader closes anything.
usage: uv run python scripts/dr4_readiness.py [CASE ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from oddsky.case.store import CaseStore
from oddsky.data import gaia_epoch


def targets(only: list[str]) -> list[tuple]:
    out = []
    for d in sorted(Path("cases").glob("OS-*")):
        if only and d.name not in only:
            continue
        s = CaseStore(d)
        c = s.load()
        preds = [p for p in c.predictions if p.check and p.check.series.upper().startswith("GAIA") and p.resolution is None]
        if preds and c.target and c.target.gaia_source_id:
            out.append((s, c, preds))
    return out


def main(argv: list[str]) -> int:
    rows, dr4_failed = [], False
    for s, c, preds in targets(argv):
        sid = int(c.target.gaia_source_id)
        got, rep = gaia_epoch.fetch_report([sid])
        df = got.get(sid)
        failed = [r for r in rep["releases"] if not r["ok"]]
        dr4_failed |= any(r["release"] == "Gaia DR4" for r in failed)
        ctx = s.context().get("gaia", {}) if hasattr(s, "context") else {}
        for p in preds:
            chk = p.check
            band = chk.series.partition(":")[2].strip().upper() or "G"
            g = df[(df.band.str.upper() == band) & ((df.flag == "") | (df.flag == "rejected_by_variability"))] if df is not None \
                else None
            n_win = int(((g.t_mjd >= chk.start) & (g.t_mjd <= chk.end)).sum()) if g is not None else 0
            n_base, dmag = 0, None
            if g is not None and chk.baseline:
                b = g[(g.t_mjd >= chk.baseline[0]) & (g.t_mjd <= chk.baseline[1])]
                n_base = len(b)
                if n_base and ctx.get("G") is not None:
                    dmag = round(float(np.median(b.mag) - ctx["G"]), 3)
            rows.append({"case": c.id, "prediction": p.id, "gaia": str(sid), "release_used": rep["source_release"].get(sid),
                         "failed": "; ".join(f"{r['release']}: {r['error']}" for r in failed),
                         "last_epoch_mjd": round(float(g.t_mjd.max()), 1) if g is not None and len(g) else None,
                         "window": [chk.start, chk.end], "n_window": n_win, "n_baseline": n_base,
                         "baseline_minus_dr3_G": dmag,
                         "identity_ok": None if dmag is None else abs(dmag) <= 0.3,
                         "gradable": n_win >= 3 and (not chk.baseline or n_base >= 3)})
    for r in rows:
        print(json.dumps(r))
    print(f"{len(rows)} Gaia predictions checked; gradable now: {sum(r['gradable'] for r in rows)}; "
          f"identity doubts: {sum(r['identity_ok'] is False for r in rows)}; DR4 request failed: {dr4_failed}")
    return 1 if dr4_failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
