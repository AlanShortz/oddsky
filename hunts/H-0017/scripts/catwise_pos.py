"""H-0017: CatWISE2020 positions (2010-2018 mean, dominated by the later quiet years) at each AllWISE source, to compare
with the AllWISE (2010-11) position: an off-nuclear transient moves the centroid, a nuclear one does not.
One status-tracked IRSA cone per target. usage: catwise_pos.py IN_CSV(designation, ra, dec) OUT_CSV"""
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

x = pd.read_csv(sys.argv[1])
out = sys.argv[2]
rows = [pd.read_csv(out)] if os.path.exists(out) else []
rows = [rows[0][rows[0].status == "ok"]] if rows else []
seen = set(rows[0].designation) if rows else set()
for r in x.itertuples():
    if r.designation in seen:
        continue
    q = ("SELECT source_name, ra, dec, sigra, sigdec, w1mpro, w2mpro, w1snr, w2snr, nb, na, cc_flags, ab_flags FROM catwise_2020 "
         f"WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},0.00222))=1")
    rec = dict(designation=r.designation, status="failed")
    for k in range(4):
        try:
            t = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=240).text.strip()
            if not t.startswith("source_name"):
                raise RuntimeError(t[:100])
            g = pd.read_csv(io.StringIO(t)) if "\n" in t else pd.DataFrame()
            rec.update(status="ok", n_catwise=len(g))
            if len(g):
                g["sep"] = 3600 * np.hypot((g.ra - r.ra) * np.cos(np.radians(r.dec)), g.dec - r.dec)
                b = g.sort_values("sep").iloc[0]
                rec.update(cw_name=b.source_name, cw_ra=b.ra, cw_dec=b.dec, cw_sigra=b.sigra, cw_sigdec=b.sigdec, cw_w1=b.w1mpro, cw_w2=b.w2mpro,
                           cw_nb=b.nb, cw_sep=b.sep, dra=3600 * (b.ra - r.ra) * np.cos(np.radians(r.dec)), ddec=3600 * (b.dec - r.dec))
            break
        except Exception as e:  # noqa: BLE001
            rec["error"] = str(e)[:80]
            time.sleep(10 * (k + 1))
    rows.append(pd.DataFrame([rec]))
    pd.concat(rows).to_csv(out, index=False)
    print(r.designation, rec["status"], rec.get("n_catwise"), round(rec.get("cw_sep", float("nan")), 2), flush=True)
print("done;", int(sum((g.status == "failed").any() for g in rows)), "failed", flush=True)
