"""TNS packet 2026-11: NED host lookup (preferred redshift) and redshift-independent distances (nDistance), with
retries; a failure is recorded as an ERROR. Needs lxml for the distance table: `uv run --with lxml python ...`.

    uv run --with lxml python hunts/H-0012/drafts/tns_packet_2026-11/scripts/ned_hosts.py "NGC 4945" "NGC 3031"
Output: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/archives/ned_<name>.json and ned_distances_<name>.csv
"""
import io
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/archives"
UA = {"User-Agent": "oddsky-tns-packet/1.0"}


def get(fn, tries=4):
    last = None
    for k in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(15 * (k + 1))
    raise last


for name in sys.argv[1:]:
    rec = {"name": name}
    try:
        r = get(lambda: requests.post("https://ned.ipac.caltech.edu/srs/ObjectLookup", timeout=120, headers=UA,
                                      data={"json": json.dumps({"name": {"v": name}})}))
        j = r.json()
        pr = j.get("Preferred", {})
        rec["lookup"] = dict(result_code=j.get("ResultCode"), interpreted=j.get("Interpreted"), preferred_name=pr.get("Name"),
                             objtype=pr.get("ObjType", {}).get("Value"), z=pr.get("Redshift", {}).get("Value"),
                             z_unc=pr.get("Redshift", {}).get("Uncertainty"), z_ref=pr.get("Redshift", {}).get("RefCode"),
                             ra=pr.get("Position", {}).get("RA"), dec=pr.get("Position", {}).get("Dec"))
    except Exception as e:  # noqa: BLE001
        rec["lookup"] = f"ERROR {type(e).__name__}: {e} (not a null result)"
    time.sleep(5)
    try:
        h = get(lambda: requests.get("https://ned.ipac.caltech.edu/cgi-bin/nDistance", timeout=120, headers=UA,
                                     params={"name": name}))
        t = pd.read_html(io.StringIO(h.text))
        big = max(t, key=len)
        dcol = [c for c in big.columns if "Mpc" in str(c)][0]
        mcol = [c for c in big.columns if "Method" in str(c)][0]
        big["D"] = pd.to_numeric(big[dcol], errors="coerce")
        big = big.dropna(subset=["D"])
        big[[mcol, "D"]].to_csv(OUT / f"ned_distances_{name.replace(' ', '_')}.csv", index=False)
        by = big.groupby(mcol).D.agg(["count", "median", "min", "max"]).round(2)
        rec["distances"] = dict(n=len(big), min=float(big.D.min()), median=float(big.D.median()),
                                max=float(big.D.max()), by_method=by.reset_index().astype(str).to_dict("records"))
    except Exception as e:  # noqa: BLE001
        rec["distances"] = f"ERROR {type(e).__name__}: {e} (not a null result)"
    (OUT / f"ned_{name.replace(' ', '_')}.json").write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps(rec, indent=1, default=str)[:3000])
