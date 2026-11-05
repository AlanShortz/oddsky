"""H-0016: AllWISE Reject Table entries near a list of catalogue sources (is a better extraction of the same star there?).
One IRSA cone per target (allwise_p3as_psr). Every target gets at least one output row with status 'ok' or 'failed', so a
query that timed out is never read as "no entry". Resumable: targets already 'ok' in OUT_CSV are skipped.
usage: reject_table.py IN_CSV OUT_CSV [RADIUS_ARCSEC]     IN_CSV needs designation, ra, dec, cntr"""
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

COLS = ("designation, ra, dec, cntr, coadd_id, src, wx, wy, w1mpro, w1snr, w1mag, w2mpro, w2snr, w1nm, w1m, nb, na, cc_flags, "
        "rel, pmcode, best_use_cntr, use_src, ngrp")
x = pd.read_csv(sys.argv[1], dtype={"cntr": str})
out = sys.argv[2]
radius = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
rows = [pd.read_csv(out, dtype=str)] if os.path.exists(out) else []
rows = [rows[0][rows[0].status == "ok"]] if rows else []
seen = set(rows[0].target) if rows else set()
for r in x.itertuples():
    if r.designation in seen:
        continue
    q = (f"SELECT {COLS} FROM allwise_p3as_psr WHERE CONTAINS(POINT('ICRS',ra,dec),"
         f"CIRCLE('ICRS',{r.ra},{r.dec},{radius / 3600:.6f}))=1")
    text = None
    for k in range(5):
        try:
            t = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=300).text.strip()
            if t.startswith("designation"):
                text = t
                break
        except Exception as e:  # noqa: BLE001
            print("retry", k, str(e)[:100], flush=True)
        time.sleep(15 * (k + 1))
    base = dict(target=r.designation, target_cntr=r.cntr)
    if text is None:
        g = pd.DataFrame([dict(base, status="failed")])
    elif "\n" not in text:
        g = pd.DataFrame([dict(base, status="ok", n="0")])
    else:
        g = pd.read_csv(io.StringIO(text), dtype=str)
        sep = 3600 * np.hypot((g.ra.astype(float) - r.ra) * np.cos(np.radians(r.dec)), g.dec.astype(float) - r.dec)
        g = g.assign(sep=sep.round(3).astype(str), status="ok", n=str(len(g)), **base)
    rows.append(g)
    pd.concat(rows).to_csv(out, index=False)
    print(r.designation, g.status.iloc[0], g.n.iloc[0] if "n" in g else "", flush=True)
bad = sum((g.status == "failed").any() for g in rows)
print("done;", bad, "targets failed", flush=True)
sys.exit(1 if bad else 0)
