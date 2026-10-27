"""Reproducibility as a command: re-run a case's ledger and compare result digests."""

from __future__ import annotations

from . import __version__
from .case.store import CaseStore, digest
from .tools import Toolbox

REPLAYABLE = {"describe_series", "compare_windows", "observer_agreement", "periodogram", "find_excursions", "cross_band", "wise_color", "ir_excess",
              "neighbors", "get_lightcurve"}


def replay(case: str) -> list[dict]:
    store = CaseStore.find(case)
    tb = Toolbox(author="replay")
    out = []
    for e in store.ledger():
        if e["tool"] not in REPLAYABLE:
            continue
        fn = getattr(tb, e["tool"])
        # Call the pure computation without writing a new ledger entry.
        tb_log = tb._log
        tb._log = lambda s, tool, args, result: result  # type: ignore[assignment]
        try:
            res = fn(case=case, **e["args"])
        finally:
            tb._log = tb_log  # type: ignore[assignment]
        d = digest(res)
        made_with = e.get("oddsky", "0.1.0")
        ok = d == e["digest"]
        note = "" if ok else f"digest {d} != {e['digest']}"
        if not ok and made_with != __version__:
            note += f" (recorded with oddsky {made_with}; tool output changed since)"
        out.append({"id": e["id"], "tool": e["tool"], "match": ok, "drift": not ok and made_with != __version__,
                    "note": note})
    return out
