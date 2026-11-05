"""H-0016: selected AllWISE Catalog columns (Tile, position in Tile, duplicate-resolution and quality flags) for a list of
sources, one IRSA query per cntr, with a status per target so a failed query is never read as a missing row.
usage: catalog_rows.py IN_CSV OUT_CSV     IN_CSV needs designation, cntr"""
import io
import os
import sys
import time

import pandas as pd
import requests

COLS = "designation, cntr, coadd_id, src, wx, wy, rel, ph_qual, cc_flags, nb, na, ext_flg, pmcode, w1mpro, w1snr, w1mag, w1nm, w1m"
x = pd.read_csv(sys.argv[1], dtype={"cntr": str})
out = sys.argv[2]
rows = [pd.read_csv(out, dtype=str)] if os.path.exists(out) else []
rows = [rows[0][rows[0].status == "ok"]] if rows else []
seen = set(rows[0].target) if rows else set()
for r in x.itertuples():
    if r.designation in seen:
        continue
    text = None
    for k in range(5):
        try:
            t = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": f"SELECT {COLS} FROM allwise_p3as_psd WHERE cntr = {r.cntr}", "FORMAT": "csv"}, timeout=300).text.strip()
            if t.startswith("designation") and "\n" in t:
                text = t
                break
        except Exception as e:  # noqa: BLE001
            print("retry", k, str(e)[:100], flush=True)
        time.sleep(15 * (k + 1))
    g = pd.read_csv(io.StringIO(text), dtype=str).assign(target=r.designation, status="ok") if text else pd.DataFrame([dict(target=r.designation, status="failed")])
    rows.append(g)
    pd.concat(rows).to_csv(out, index=False)
    print(r.designation, g.status.iloc[0], flush=True)
bad = sum((g.status == "failed").any() for g in rows)
print("done;", bad, "targets failed", flush=True)
sys.exit(1 if bad else 0)
