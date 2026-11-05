"""H-0017: SDSS spectra (class, subclass, redshift, date) at the positions of the nuclei: what was each one before or after
2010? One SkyServer query per target, with a status so a failed query is not read as "no spectrum".
usage: sdss_spectra.py IN_CSV(designation, ra, dec) OUT_CSV"""
import io
import sys
import time

import pandas as pd
import requests

URL = "https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch"
x = pd.read_csv(sys.argv[1])
rows = []
for r in x.itertuples():
    q = ("SELECT s.specObjID, s.class, s.subClass, s.z, s.zWarning, s.mjd, s.plate, s.fiberID, s.survey, s.snMedian, n.distance "
         f"FROM dbo.fGetNearbySpecObjEq({r.ra},{r.dec},0.05) n JOIN SpecObjAll s ON s.specObjID = n.specObjID")
    rec = dict(designation=r.designation, status="failed", n_spec=0)
    for k in range(4):
        try:
            t = requests.get(URL, params={"cmd": q, "format": "csv"}, timeout=60).text
            body = "\n".join(ln for ln in t.splitlines() if not ln.startswith("#"))
            if "error" in body[:200].lower() and "specObjID" not in body:
                raise RuntimeError(body[:120])
            g = pd.read_csv(io.StringIO(body)) if body.strip() and "specObjID" in body else pd.DataFrame()
            rec.update(status="ok", n_spec=len(g))
            for j, s in enumerate(g.sort_values("mjd").itertuples()):
                rows.append(dict(rec, k=j, spec_class=s._2, subclass=s.subClass, z=s.z, zwarning=s.zWarning, mjd=s.mjd, plate=s.plate,
                                 fiber=s.fiberID, survey=s.survey, sn=s.snMedian, dist_arcmin=s.distance))
            break
        except Exception as e:  # noqa: BLE001
            rec["error"] = str(e)[:80]
            time.sleep(3 * (k + 1))
    if not rec["n_spec"]:
        rows.append(rec)
    print(r.designation, rec["status"], rec["n_spec"], flush=True)
    time.sleep(0.4)
o = pd.DataFrame(rows)
o.to_csv(sys.argv[2], index=False)
print("failed:", int((o.status == "failed").sum()), " with spectra:", o[o.n_spec > 0].designation.nunique())
