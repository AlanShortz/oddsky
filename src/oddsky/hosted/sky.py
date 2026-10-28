"""Sealing predictions on the Sky Ledger, grading them against the archives, and the scoreboard.

Grading is the same `evaluate` the local tools and trial scorer use. When a seal's window has closed,
the grader re-fetches that survey for the case, evaluates the check, and appends a "grade" entry that
points at the seal's hash. Archives publish with a lag, so a check with too few points in its window
stays pending until 60 days after its resolve-by date, then is graded "unresolvable".
"""

from __future__ import annotations

import datetime as dt
import logging
import shutil
import tempfile
import time
from pathlib import Path

from ..case.model import Check
from ..case.store import CaseStore
from ..paths import workspace
from . import notebooks
from .db import db
from .ledger import content, now

log = logging.getLogger("oddsky.hosted")
FETCH_KEY = {"aavso": "aavso", "ztf": "ztf", "asas-sn": "asassn", "asassn": "asassn", "neowise": "neowise",
             "tess": "tess", "gaia": "gaia_epoch", "atlas": "atlas"}
GRACE_DAYS = 60


def mjd_now() -> float:
    return time.time() / 86400 + 40587


def seal(*, observer: str, agent: str | None, model: str | None, case: str, target: str | None, prediction: dict,
         source: str = "mcp", at: str | None = None, extra: dict | None = None) -> dict:
    p = prediction
    entry = db().append_log({
        "kind": "seal", "at": at or now(), "source": source, "observer": observer, "agent": agent, "model": model,
        "case": case, "target": target, "prediction": p.get("id"), "hypothesis": p.get("hypothesis"),
        "statement": p["statement"], "probability": p["probability"], "check": p.get("check"),
        "resolve_by": p.get("resolve_by") or _default_resolve(p.get("check")), **(extra or {}),
    })
    if p.get("check"):
        db().set("pending", f"{entry['seq']:09d}", {"seq": entry["seq"], "hash": entry["hash"], "observer": observer,
                                                    "case": case, "check": p["check"], "resolve_by": content(entry)["resolve_by"]})
    _cache.clear()
    return entry


def _default_resolve(check: dict | None) -> str | None:
    if not check:
        return None
    end = dt.date(1858, 11, 17) + dt.timedelta(days=float(check["end"]))
    return (end + dt.timedelta(days=30)).isoformat()


def grade_entry(seal_entry: dict, outcome: str, observed=None, n_points=0, note="", source="grader", at=None) -> dict:
    e = db().append_log({"kind": "grade", "at": at or now(), "source": source, "ref": seal_entry["seq"],
                         "ref_hash": seal_entry["hash"], "outcome": outcome, "observed": observed,
                         "n_points": n_points, "note": note})
    db().delete("pending", f"{seal_entry['seq']:09d}")
    _cache.clear()
    return e


# ---- the grader ----------------------------------------------------------------------------------

def grade_due(dry_run: bool = False) -> list[dict]:
    from ..fetch import fetch
    from ..tools import Toolbox, evaluate

    out = []
    today = dt.date.today()
    for pend in db().all("pending", limit=2000):
        chk = Check.model_validate(pend["check"])
        if chk.end > mjd_now():
            continue
        seal_e = next(iter(db().log_range(after=pend["seq"] - 1, limit=1)), None)
        if not seal_e or seal_e["hash"] != pend["hash"]:
            out.append({"seq": pend["seq"], "error": "seal not found on the ledger"})
            continue
        tmp = Path(tempfile.mkdtemp(prefix="grade-"))
        try:
            src = notebooks.CANON / pend["case"]
            if not src.exists():
                notebooks.ensure(pend["observer"], pend["case"])
                src = notebooks.root(pend["observer"]) / "cases" / pend["case"]
            shutil.copytree(src, tmp / "cases" / pend["case"])
            with workspace(tmp):
                store = CaseStore(tmp / "cases" / pend["case"])
                survey = FETCH_KEY.get(chk.series.split(":")[0].strip().lower())
                if survey:
                    fetch(store, surveys=[survey])
                res = evaluate(chk, lambda ser, store=store: Toolbox(mode="open")._frame(store, ser))
        except Exception as e:  # an archive outage must not grade anything
            log.exception("grading seal %s", pend["seq"])
            out.append({"seq": pend["seq"], "error": str(e)[:300]})
            continue
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        late = pend.get("resolve_by") and today > dt.date.fromisoformat(pend["resolve_by"]) + dt.timedelta(days=GRACE_DAYS)
        if res.outcome == "unresolvable" and not late:
            out.append({"seq": pend["seq"], "outcome": "waiting", "note": res.note})
            continue
        if not dry_run:
            grade_entry(seal_e, res.outcome, res.observed, res.n_points, res.note)
        out.append({"seq": pend["seq"], "outcome": res.outcome, "note": res.note, "dry_run": dry_run})
    return out


# ---- the docket and the scoreboard ---------------------------------------------------------------
_cache: dict = {}


def docket() -> dict:
    if (c := _cache.get("docket")) and c[0] > time.time() - 20:
        return c[1]
    entries = db().log_range(0, 100000)
    seals, grades = {}, {}
    for e in entries:
        b = content(e)
        if b["kind"] == "seal":
            seals[e["seq"]] = {"seq": e["seq"], "hash": e["hash"], **b}
        elif b["kind"] == "grade":
            grades[b["ref"]] = {"seq": e["seq"], "hash": e["hash"], **b}
    items = []
    for seq, s in seals.items():
        g = grades.get(seq)
        items.append({**s, "outcome": g["outcome"] if g else "pending", "grade": g})
    board = {"observers": _board(items, lambda s: s["observer"]),
             "models": _board([s for s in items if s.get("model")], lambda s: s["model"])}
    out = {"head": db().head(), "items": items, "board": board, "n_entries": len(entries)}
    _cache["docket"] = (time.time(), out)
    return out


def _board(items, key) -> list[dict]:
    rows: dict[str, dict] = {}
    for s in items:
        r = rows.setdefault(key(s), {"who": key(s), "sealed": 0, "graded": 0, "true": 0, "brier_sum": 0.0, "pending": 0})
        r["sealed"] += 1
        if s["outcome"] in ("true", "false"):
            r["graded"] += 1
            hit = s["outcome"] == "true"
            r["true"] += hit
            r["brier_sum"] += (s["probability"] - (1.0 if hit else 0.0)) ** 2
        elif s["outcome"] == "pending":
            r["pending"] += 1
    out = []
    for r in rows.values():
        total = r.pop("brier_sum")
        r["brier"] = round(total / r["graded"], 4) if r["graded"] else None
        out.append(r)
    return sorted(out, key=lambda r: (r["brier"] is None, r["brier"] if r["brier"] is not None else 0, -r["sealed"]))
