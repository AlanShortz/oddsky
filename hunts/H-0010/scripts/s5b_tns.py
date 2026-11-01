"""s5b: TNS cone (60") for every one of the 67 positions, 45 s between requests; on HTTP 429 wait Retry-After (default
120 s) and retry, up to 5 times. A lookup that still fails is recorded "ERR ..." -- never as "nothing found".
Resumable: rows already answered in data/tns.csv are skipped.

Run from the repo root: uv run python -I hunts/H-0010/scripts/s5b_tns.py"""
import io
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, targets  # noqa: E402

OUT = os.path.join(DATA, "tns.csv")


def main():
    T = targets()
    done = pd.read_csv(OUT, dtype={"source_id": str}).fillna("") if os.path.exists(OUT) else pd.DataFrame(columns=["source_id", "tns"])
    res = dict(zip(done.source_id, done.tns, strict=True))
    for n, r in enumerate(T.itertuples()):
        if r.source_id in res and not str(res[r.source_id]).startswith("ERR"):
            continue
        val = "ERR not tried"
        for _ in range(5):
            try:
                resp = requests.get("https://www.wis-tns.org/search", params={"ra": r.ra, "decl": r.dec, "radius": 60,
                                    "coords_unit": "arcsec", "format": "csv"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
            except Exception as e:  # noqa: BLE001
                val = f"ERR {str(e)[:60]}"
                time.sleep(60)
                continue
            if resp.status_code == 429:
                val = "ERR HTTP 429"
                time.sleep(float(resp.headers.get("Retry-After", 120)))
                continue
            if resp.status_code != 200:
                val = f"ERR HTTP {resp.status_code}"
                break
            if resp.text.strip().startswith("<"):
                val = "ERR html response"
                break
            d = pd.read_csv(io.StringIO(resp.text)) if resp.text.strip() else pd.DataFrame()
            if "Name" in d:
                val = "; ".join(f"{a} ({b}, {c}, {e})" for a, b, c, e in zip(d["Name"], d["Obj. Type"], d["Discovery Date (UT)"],
                                d.get("Disc. Internal Name", [""] * len(d)), strict=True)) or "none"
            else:
                val = "none"
            break
        res[r.source_id] = val
        print(n + 1, r.source_id, val, flush=True)
        pd.DataFrame({"source_id": list(res), "tns": list(res.values())}).to_csv(OUT, index=False)
        time.sleep(45)
    s = pd.Series(res)
    print("errors:", int(s.str.startswith("ERR").sum()), "| with objects:", int(((s != "none") & ~s.str.startswith("ERR")).sum()))


if __name__ == "__main__":
    main()
