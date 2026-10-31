"""Re-query TNS (60") for the rows of a vetted table whose lookup failed (tns starts with "ERR"), slowly: 45 s between
requests, and on HTTP 429 wait as long as the server's Retry-After asks (default 120 s) and try the same row again, up to
5 times. A row that still fails stays "ERR ..." (never "nothing found"). Rewrites the table in place.
usage: hunt_tns_retry.py STRONG_CSV"""

import io
import sys
import time

import pandas as pd
import requests

path = sys.argv[1]
s = pd.read_csv(path, dtype={"g_source_id": str})
s["tns"] = s.tns.fillna("").astype(str)
todo = s.index[s.tns.str.startswith("ERR")]
print(len(todo), "lookups to retry", flush=True)
for n, i in enumerate(todo):
    r = s.loc[i]
    for _ in range(5):
        try:
            resp = requests.get("https://www.wis-tns.org/search", params={"ra": r.ra, "decl": r.dec, "radius": 60,
                                "coords_unit": "arcsec", "format": "csv"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        except Exception as e:  # noqa: BLE001
            s.loc[i, "tns"] = f"ERR {str(e)[:60]}"
            time.sleep(60)
            continue
        if resp.status_code == 429:
            s.loc[i, "tns"] = "ERR HTTP 429"
            time.sleep(float(resp.headers.get("Retry-After", 120)))
            continue
        if resp.status_code != 200:
            s.loc[i, "tns"] = f"ERR HTTP {resp.status_code}"
            break
        d = pd.read_csv(io.StringIO(resp.text)) if resp.text.strip() else pd.DataFrame()
        s.loc[i, "tns"] = "; ".join(f"{a} ({b}, {c})" for a, b, c in zip(d["Name"], d["Obj. Type"], d["Discovery Date (UT)"],
                                                                         strict=True)) if "Name" in d else ""
        break
    print(n + 1, r.designation, s.loc[i, "tns"] or "(none)", flush=True)
    s.to_csv(path, index=False)
    time.sleep(45)
print("still failing:", int(s.tns.str.startswith("ERR").sum()), "| with TNS objects:",
      int(((s.tns != "") & ~s.tns.str.startswith("ERR")).sum()))
