"""r10: a second optical instrument for the strong events whose NEOWISE peak falls inside Gaia DR3's epoch-photometry span
(2014-07-25 .. 2017-05-28): any Gaia DR3 source within 3" of the AllWISE position flagged VARIABLE has published epoch
photometry. For those, the G light curve within 60 d of the NEOWISE visit against the source's median (and BP/RP)."""
import io
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, mjd2date, strong  # noqa: E402

from oddsky.data import gaia_epoch  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
s = strong()
w = s[(s.t > 56863) & (s.t < 57901)]
print(len(w), "strong events with the NEOWISE peak inside the DR3 epoch span")
cand = []
for r in w.itertuples():
    q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={"-source": "I/355/gaiadr3", "-c": f"{r.ra} {r.dec}", "-c.rs": 3,
                     "-c.u": "arcsec", "-out": "Source,Gmag,VarFlag", "-out.add": "_r"}, headers=UA, timeout=120)
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 3:
        continue
    g = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    g.columns = [c.strip() for c in g.columns]
    for x in g.itertuples():
        if x.VarFlag.strip() == "VARIABLE":
            cand.append((r.designation, r.t, r.dw1, int(x.Source), float(x._1) if hasattr(x, "_1") else np.nan, float(x.Gmag)))
print(len(cand), "VARIABLE Gaia sources within 3\":")
c = pd.DataFrame(cand, columns=["designation", "t", "dw1", "source", "sep", "G"])
print(c.to_string(index=False))
got = gaia_epoch.fetch(c.source.tolist(), releases=("Gaia DR3",))
for r in c.itertuples():
    df = got.get(r.source)
    if df is None or df.empty:
        print(f"== {r.designation} {r.source}: no epoch photometry")
        continue
    df.to_csv(os.path.join(DATA, f"r4_gaia_{r.source}.csv"), index=False)
    g = df[(df.band == "G") & (df.flag != "rejected_by_photometry") & np.isfinite(df.mag)]
    med = g.mag.median()
    near = g[np.abs(g.t_mjd - r.t) < 60]
    print(f"== {r.designation} (NEOWISE {mjd2date(r.t)}, W1 x{10 ** (-0.4 * r.dw1):.2f}) Gaia {r.source} G {r.G:.2f}: median {med:.2f}, "
          f"robust scatter {1.4826 * np.median(np.abs(g.mag - med)):.3f}; within 60 d: " +
          (", ".join(f"{x.t_mjd - r.t:+.0f}d x{10 ** (-0.4 * (x.mag - med)):.2f}" for x in near.itertuples()) or "no transit"))
