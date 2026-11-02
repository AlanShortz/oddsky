"""ZTF DR light curves (IRSA, 3") and NEOWISE-R single-exposure visit photometry (IRSA) at northern leads.

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/ztf_neowise.py
Writes ztf_<lead>.csv, neowise_<lead>.csv and ztf_neowise.json (summaries).
"""
import json
from pathlib import Path

import numpy as np

from oddsky.data import neowise, ztf

HERE = Path(__file__).resolve().parent
L = {d["lead"]: d for d in json.loads((HERE / "leads.json").read_text())}
SEL = ["NGC3239 obs#33", "M81 obs#9", "M101 obs#19", "IC342 fsn#1", "NGC2976 fsn#5", "IC342 obs#26", "HolmII obs#21",
       "NGC4945 obs#3", "NGC55 obs#14", "UGCA127 obs#30"]
summ = {}
for lab in SEL:
    d = L[lab]
    tag = lab.replace(" ", "_").replace("#", "")
    rec = {}
    try:
        df, prov = ztf.lightcurve(d["ra"], d["dec"], 3.0)
        df.to_csv(HERE / f"ztf_{tag}.csv", index=False)
        rec["ztf"] = dict(status=prov.status, n=len(df), notes=prov.notes)
        if len(df):
            for b, g in df.groupby("band"):
                g = g[g.flag == ""] if "flag" in g else g
                if len(g):
                    rec["ztf"][b] = dict(n=len(g), mag_med=float(np.median(g.mag)), mag_min=float(g.mag.min()),
                                         mag_max=float(g.mag.max()), t0=float(g.t_mjd.min()), t1=float(g.t_mjd.max()),
                                         t_min=float(g.t_mjd.iloc[int(np.argmin(g.mag.to_numpy()))]))
    except Exception as e:  # noqa: BLE001
        rec["ztf"] = f"ERR {e}"
    try:
        df, prov = neowise.lightcurve(d["ra"], d["dec"])
        df.to_csv(HERE / f"neowise_{tag}.csv", index=False)
        rec["neowise"] = dict(status=prov.status, n=len(df), notes=prov.notes[:3])
    except Exception as e:  # noqa: BLE001
        rec["neowise"] = f"ERR {e}"
    summ[lab] = rec
    print(lab, json.dumps(rec, default=str)[:600], flush=True)
(HERE / "ztf_neowise.json").write_text(json.dumps(summ, indent=1, default=str))
