"""Optical history of the M31/M33 faders: LGGS (Massey+2006, ~2000-2001; VizieR J/AJ/131/2478), Pan-STARRS1 DR2
mean PSF mags (2010-2014; MAST), Gaia DR3 (2014-2017), and the ZTF DR light-curve trend (2018-2025, 2" radius).

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/optical_faders.py
Writes optical_faders.json.
"""
import io
import json
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from oddsky.data import ztf

HERE = Path(__file__).resolve().parent
L = {d["lead"]: d for d in json.loads((HERE / "leads.json").read_text())}
SEL = ["M31 fsn#4", "M33 fsn#10", "M33 fsn#12", "M33 fsn#13", "M33 fsn#14", "M31 fsn#3", "M31 fsn#7", "M31 fsn#9",
       "M31 fsn#11", "M31 obs#27", "NGC2976 fsn#5", "IC342 fsn#1", "M101 obs#19", "M81 obs#9"]
UA = {"User-Agent": "oddsky-referee/0.1"}
out = {}
for lab in SEL:
    d = L[lab]
    rec = {}
    # LGGS
    try:
        t = httpx.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={"-source": "J/AJ/131/2478", "-c": f"{d['ra']} {d['dec']}",
                      "-c.rs": 2, "-out": "LGGS,Vmag,B-V,U-B,V-R,R-I,_r"}, headers=UA, timeout=60).text
        rows = [ln for ln in t.splitlines() if ln and not ln.startswith("#") and not ln.startswith("-")]
        rec["lggs"] = rows[2:6] if len(rows) > 2 else []
    except Exception as e:  # noqa: BLE001
        rec["lggs"] = f"ERR {e}"
    # Pan-STARRS DR2 mean
    try:
        r = httpx.get("https://catalogs.mast.stsci.edu/api/v0.1/panstarrs/dr2/mean.csv",
                      params={"ra": d["ra"], "dec": d["dec"], "radius": 2 / 3600, "nDetections.gte": 1,
                              "columns": "[objID,raMean,decMean,gMeanPSFMag,rMeanPSFMag,iMeanPSFMag,zMeanPSFMag,yMeanPSFMag,iMeanKronMag,nDetections]"},
                      headers=UA, timeout=90)
        p = pd.read_csv(io.StringIO(r.text)) if r.status_code == 200 and r.text.strip() else pd.DataFrame()
        rec["ps1"] = p.to_dict("records")[:3]
    except Exception as e:  # noqa: BLE001
        rec["ps1"] = f"ERR {e}"
    # ZTF trend
    try:
        z, prov = ztf.lightcurve(d["ra"], d["dec"], 2.0)
        z = z[(z.flag == "") | z.flag.isna()] if "flag" in z else z
        tr = {}
        for b, g in z.groupby("band"):
            if len(g) > 20:
                yr = (g.t_mjd - 58500) / 365.25
                k = np.polyfit(yr, g.mag, 1)
                tr[b] = dict(n=len(g), slope_mag_per_yr=round(float(k[0]), 3), mag_2019=round(float(k[1]), 2),
                             rms=round(float(np.std(g.mag - np.polyval(k, yr))), 2))
        rec["ztf"] = tr or prov.status
    except Exception as e:  # noqa: BLE001
        rec["ztf"] = f"ERR {e}"
    out[lab] = rec
    print(lab, json.dumps(rec, default=str)[:700], flush=True)
(HERE / "optical_faders.json").write_text(json.dumps(out, indent=1, default=str))
