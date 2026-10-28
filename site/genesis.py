#!/usr/bin/env python3
"""Seed the Sky Ledger with the predictions already sealed in git, once.

    python3 site/genesis.py                    # print the payload
    python3 site/genesis.py --post https://oddsky.ai   # needs ~/.config/oddsky/admin-token

Case predictions keep their machine-checkable form, so the grader resolves them like any other.
Trial 001 hindsight forecasts were stated in the trial's scrubbed day numbers; the graded ones are
imported with the trial scorer's (v2) outcome, and the pending ones are graded by the trial scorer
at reveal, not by the ledger's grader.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def items() -> list[dict]:
    index = json.loads((ROOT / "web/data/index.json").read_text())
    meta = {c["id"]: c for c in index["cases"]}
    out = []
    for cid in sorted(meta):
        p = ROOT / "web/data/cases" / f"{cid}.json"
        c = json.loads(p.read_text())["case"]
        for pr in c.get("predictions") or []:
            out.append({"at": pr["registered_at"], "case": cid, "target": meta[cid].get("target"), "model": pr.get("author"),
                        "agent": "local MCP", "provenance": f"git: cases/{cid}/case.yaml",
                        "prediction": {k: pr.get(k) for k in ("id", "hypothesis", "statement", "probability", "check", "resolve_by")}})
    for sc in index.get("scorecards", []):
        packets = {x["case"]: x for x in sc.get("cases", [])}
        for pr in sc.get("predictions") or []:
            pk = packets.get(pr["case"], {})
            real = pk.get("real_case")
            m = re.search(r"MJD\s*(\d+(?:\.\d+)?)", pr.get("note") or "")
            resolve = None
            if m:
                import datetime as dt
                resolve = (dt.date(1858, 11, 17) + dt.timedelta(days=float(m.group(1)))).isoformat()
            out.append({"at": f"{sc['run_at']}T00:00:00+00:00", "case": real or pr["case"], "target": meta.get(real, {}).get("target"),
                        "model": sc["agent"], "agent": "Trial 001 investigator", "trial": sc["trial"], "packet": pr["case"],
                        "provenance": f"git: trials/{sc['trial']} (answers sealed sha256 {sc.get('answers_sha256', '')[:12]}…)",
                        "prediction": {"id": pr["id"], "statement": pr["statement"], "probability": pr["probability"], "check": None,
                                       "resolve_by": resolve},
                        "outcome": pr["outcome"] if pr["outcome"] in ("true", "false", "unresolvable") else None,
                        "observed": pr.get("observed"), "n_points": pr.get("n_points") or 0, "note": pr.get("note") or "",
                        "graded_by": f"trial scorer {sc.get('grader', '')}".strip(), "graded_at": sc.get("scored_at")})
    out.sort(key=lambda x: (x["at"], x["case"], x["prediction"]["id"]))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--post")
    a = ap.parse_args()
    payload = {"items": items()}
    if not a.post:
        print(json.dumps(payload, indent=1))
    else:
        tok = (Path.home() / ".config/oddsky/admin-token").read_text().strip()
        req = urllib.request.Request(f"{a.post.rstrip('/')}/api/admin/genesis", data=json.dumps(payload).encode(),
                                     headers={"content-type": "application/json", "x-oddsky-admin": tok,
                                              "user-agent": "oddsky-genesis/1"}, method="POST")
        print(urllib.request.urlopen(req, timeout=120).read().decode())
