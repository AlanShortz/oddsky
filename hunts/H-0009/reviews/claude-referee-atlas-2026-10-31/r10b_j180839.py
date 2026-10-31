"""r10b: the third strong event with Gaia DR3 epoch photometry (J180839.93-151910.5): G/BP/RP around the NEOWISE visit,
the DR3 classifier label, and the NEOWISE visits."""
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, LC, mjd2date, strong  # noqa: E402

s = strong()
r = s[s.designation == "J180839.93-151910.5"].iloc[0]
sid = 4145977633638478336
df = pd.read_csv(os.path.join(DATA, f"r4_gaia_{sid}.csv"))
df = df[(df.flag != "rejected_by_photometry") & np.isfinite(df.mag)]
for b in ("G", "BP", "RP"):
    x = df[df.band == b]
    med = x.mag.median()
    n = x[np.abs(x.t_mjd - r.t) < 120]
    print(b, f"median {med:.3f}:", ", ".join(f"{v.t_mjd - r.t:+.0f}d {v.mag - med:+.3f}" for v in n.itertuples()))
q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={"-source": "I/358/vclassre", "Source": sid, "-out": "Source,Class,ClassSc"},
                 timeout=120)
print("vclassre:", [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")][3:])
lc = pd.read_parquet(f"{LC}/pixel={int(r.pixel)}.parquet")
lc = lc[lc.allwise_cntr.astype("int64") == np.int64(r.allwise_cntr)].sort_values("t")
b1 = np.median(lc.w1)
print(f"row: dw1 {r.dw1:.2f} dw2 {r.dw2:.2f} nblock {r.nblock} hdfrac {r.hdfrac_event:.2f}/{r.hdfrac_other:.2f} nbfrac {r.nbfrac_event:.2f}/"
      f"{r.nbfrac_other:.2f} G {r.g_phot_g_mean_mag:.2f} BP-RP {r.g_bp_rp:.2f} l {r.l:.2f} b {r.b:+.2f} W1 {r.w1mpro_allwise:.2f}")
print(", ".join(f"{mjd2date(v.t)} x{10 ** (-0.4 * (v.w1 - b1)):.2f}" for v in lc.itertuples()))
