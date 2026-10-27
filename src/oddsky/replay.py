"""Reproducibility as a command: re-run a case's ledger and compare result digests."""

from __future__ import annotations

import json

from . import __version__
from .case.store import CaseStore, digest, digest10, platform_tag
from .tools import Toolbox

REPLAYABLE = {"describe_series", "compare_windows", "observer_agreement", "eclipse_period", "fold", "periodogram", "find_excursions", "cross_band", "wise_color", "ir_excess",
              "neighbors", "get_lightcurve"}


def replay(case: str, seal: bool = False) -> list[dict]:
    """Re-run every replayable call and compare. Entries with a rounded digest (digest10) are compared on
    that, so they replay on any platform. Older entries carry only an exact digest: a mismatch is drift if
    the tool version changed, platform drift if the platform differs, and a failure otherwise.
    seal=True adds digest10 to old entries that reproduce exactly here (on the platform that recorded them)."""
    store = CaseStore.find(case)
    tb = Toolbox(author="replay")
    here = platform_tag()
    out, entries, changed = [], store.ledger(), False
    for e in entries:
        if e["tool"] not in REPLAYABLE:
            continue
        fn = getattr(tb, e["tool"])
        tb_log = tb._log
        tb._log = lambda s, tool, args, result: result  # type: ignore[assignment]
        try:
            res = fn(case=case, **e["args"])
        finally:
            tb._log = tb_log  # type: ignore[assignment]
        made_with = e.get("oddsky", "0.1.0")
        made_on = e.get("platform", "darwin-arm64")  # every entry before 0.3.1 was recorded on the founder's Mac
        exact = digest(res) == e["digest"]
        rounded = "digest10" in e and digest10(res) == e["digest10"]
        ok = rounded if "digest10" in e else exact
        drift = (not ok) and made_with != __version__
        pdrift = (not ok) and not drift and "digest10" not in e and made_on != here
        note = ""
        if not ok:
            note = f"digest mismatch (recorded with oddsky {made_with} on {made_on}; replayed with {__version__} on {here})"
        if seal and exact and "digest10" not in e and made_on == here:
            e["digest10"] = digest10(res)
            e["digest10_added"] = "sealed by `oddsky replay --seal` after an exact match on the recording platform"
            changed = True
        out.append({"id": e["id"], "tool": e["tool"], "match": ok, "drift": drift, "platform_drift": pdrift, "note": note})
    if changed:
        with (store.path / "ledger.jsonl").open("w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
    return out
