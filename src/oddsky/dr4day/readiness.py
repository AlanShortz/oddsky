"""Readiness of the sealed Gaia predictions, plus a provisional local grade (never written to a case or the ledger).

For every case with an ungraded prediction on a GAIA series, fetch the target's epoch photometry and report, per prediction:
  release     which release answered, and any release that failed (with the error);
  span        whether the window and baseline fall inside the release's epoch span. Windows after it wait for a later
              release (OS-0018 P4-P6 and OS-0019 P2 are 2022-2023 windows: Gaia DR5, not DR4); this is not a failure;
  coverage    G points the grader would use in the window and the baseline (photometry rejects dropped, variability
              outliers kept, exactly as `Toolbox._frame(grading=True)`);
  identity    baseline median G against the DR3 mean G in the case (|difference| > 0.3 mag: the DR3 id may now point at
              another or a split source. DR4 magnitudes have a new zero point; dr3_neighbourhood's own window is
              -0.25 to +0.35, so 0.3 is still the right size);
  provisional the outcome `oddsky.tools.evaluate`, the hosted grader's function, gives on these data. The ledger grade
              comes only from the hosted grader (POST /api/admin/grade, dry run first);
  fallback    True if a DR4-mode check was answered by an older release: the hosted grader falls back the same way, so a
              DR4-era prediction must never be graded on DR3 data alone. Hold the grader if this is ever True with a
              resolvable outcome.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..case.model import Check
from ..case.store import CaseStore
from ..data import gaia_epoch
from .config import Release


def targets(only: list[str] | None = None, root: Path = Path(".")) -> list[tuple]:
    out = []
    for d in sorted((root / "cases").glob("OS-*")):
        if only and d.name not in only:
            continue
        s = CaseStore(d)
        c = s.load()
        preds = [p for p in c.predictions if p.check and p.check.series.upper().startswith("GAIA") and p.resolution is None]
        if preds and c.target and c.target.gaia_source_id:
            out.append((s, c, preds))
    return out


def grading_frame(df: pd.DataFrame | None, band: str) -> pd.DataFrame | None:
    if df is None:
        return None
    return df[(df.band.str.upper() == band) & ((df.flag == "") | (df.flag == "rejected_by_variability"))]


def span_status(chk: Check, rel: Release) -> str:
    lo = min(chk.start, chk.baseline[0]) if chk.baseline else chk.start
    hi = max(chk.end, chk.baseline[1]) if chk.baseline else chk.end
    if chk.start > rel.epoch_end_mjd:
        return "window after the release span: waits for a later release"
    if hi > rel.epoch_end_mjd + 1 or lo < rel.epoch_start_mjd - 1:
        return "partly outside the release span"
    return "inside"


def provisional(chk: Check, g: pd.DataFrame | None) -> dict:
    from ..tools import evaluate

    if g is None or g.empty:
        return {"outcome": "unresolvable", "observed": None, "note": "no epoch photometry"}
    res = evaluate(chk, lambda _ser: g)
    return {"outcome": res.outcome, "observed": None if res.observed is None else round(float(res.observed), 3),
            "note": res.note}


def check(rel: Release, only: list[str] | None = None, fetch=None, root: Path = Path(".")) -> tuple[list[dict], bool]:
    """Rows (one per prediction) and whether the requested release failed. `fetch(ids, releases)` defaults to
    gaia_epoch.fetch_report; in DR4 mode DR3 is the fallback, as in the hosted grader."""
    fetch = fetch or (lambda ids, releases: gaia_epoch.fetch_report(ids, releases=releases))
    releases = (rel.name,) if rel.stand_in or rel.previous == "" else (rel.name, rel.previous)
    rows, failed_req = [], False
    for s, c, preds in targets(only, root):
        sid = int(c.target.gaia_source_id)
        try:
            got, rep = fetch([sid], releases)
        except Exception as e:  # noqa: BLE001  recorded per case; the other cases still run
            got, rep = {}, {"releases": [{"release": releases[-1], "ok": False, "error": f"{type(e).__name__}: {e}"[:300]}],
                            "source_release": {}}
        df = got.get(sid)
        failed = [r for r in rep["releases"] if not r["ok"]]
        failed_req |= any(r["release"] == rel.name for r in failed)
        used = rep["source_release"].get(sid)
        ctx = s.context().get("gaia", {})
        for p in preds:
            chk = p.check
            band = chk.series.partition(":")[2].strip().upper() or "G"
            g = grading_frame(df, band)
            n_win = int(((g.t_mjd >= chk.start) & (g.t_mjd <= chk.end)).sum()) if g is not None else 0
            n_base, dmag = 0, None
            if g is not None and chk.baseline:
                b = g[(g.t_mjd >= chk.baseline[0]) & (g.t_mjd <= chk.baseline[1])]
                n_base = len(b)
                if n_base and ctx.get("G") is not None:
                    dmag = round(float(np.median(b.mag) - ctx["G"]), 3)
            span = span_status(chk, rel)
            prov = provisional(chk, g)
            rows.append({"case": c.id, "prediction": p.id, "gaia": str(sid), "probability": p.probability,
                         "statement": p.statement[:160], "release_used": used,
                         "failed": "; ".join(f"{r['release']}: {r['error']}" for r in failed),
                         "fallback": bool(used and used != rel.name),
                         "span": span, "last_epoch_mjd": round(float(g.t_mjd.max()), 1) if g is not None and len(g) else None,
                         "window": [chk.start, chk.end], "n_window": n_win, "n_baseline": n_base,
                         "baseline_minus_dr3_G": dmag, "identity_ok": None if dmag is None else abs(dmag) <= 0.3,
                         "gradable": n_win >= 3 and (not chk.baseline or n_base >= 3),
                         "provisional": prov["outcome"], "observed": prov["observed"], "note": prov["note"]})
    return rows, failed_req


def summary(rows: list[dict], failed: bool, rel: Release) -> str:
    later = sum(r["span"].startswith("window after") for r in rows)
    hold = [f"{r['case']} {r['prediction']}" for r in rows if r["fallback"] and r["provisional"] in ("true", "false")]
    s = (f"{len(rows)} Gaia predictions checked against {rel.name}; gradable now: {sum(r['gradable'] for r in rows)}; "
         f"waiting for a later release by design: {later}; identity doubts: {sum(r['identity_ok'] is False for r in rows)}; "
         f"provisional true/false: {sum(r['provisional'] == 'true' for r in rows)}/{sum(r['provisional'] == 'false' for r in rows)}; "
         f"{rel.name} request failed: {failed}")
    if hold:
        s += f"\nHOLD THE GRADER: graded on a fallback release: {', '.join(hold)}"
    return s
