"""r8: exposure-level NEOWISE look at the ten ATLAS targets (framelib.analyse), plus a frame table of the event visit and of the
visits on either side: W1/W2, aperture W1, cc_flags, nb, w1sat, w1rchi2, offset from the quiet-visit centroid, detector x/y, scan."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framelib import analyse  # noqa: E402
from lib import KEYS, frames, mjd2date, targets  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
T = targets()
for k in KEYS:
    t = T[k]
    fr = frames(t["cntr"])
    if fr is None:
        print(f"== {k}: frames not downloaded")
        continue
    res = analyse(fr, t["row"])
    if res is None:
        print(f"== {k}: too few frames")
        continue
    m, d, ev, blk = res
    print(f"== {k} {t['name']}  event visit {mjd2date(t['tvis'])}")
    print("   " + "  ".join(f"{a}={b:.3g}" if isinstance(b, float) else f"{a}={b}" for a, b in m.items()))
    vt = d.groupby("vis").mjd.median()
    near = [v for v in vt.index if abs(vt[v] - t["tvis"]) < 400]
    q = d[~d.vis.isin(blk)]
    dec0 = np.radians(q.dec.median())
    d["dx"] = (d.ra - q.ra.median()) * np.cos(dec0) * 3600
    d["dy"] = (d.dec - q.dec.median()) * 3600
    x = d[d.vis.isin(near)].sort_values("mjd")
    x["date"] = [mjd2date(v) for v in x.mjd]
    print(x[["date", "mjd", "w1mpro", "w1sigmpro", "w2mpro", "w1mag", "cc_flags", "nb", "w1sat", "w1rchi2", "dx", "dy", "w1x", "w1y",
             "ndet", "tot"]].assign(tot=lambda z: -2.5 * np.log10(z.tot)).round(3).to_string(index=False))
    # other detections within 3" not associated with the star, at the event visit
    oth = fr[(fr.allwise_cntr.astype("Int64") != t["cntr"]) | fr.allwise_cntr.isna()]
    oth = oth[np.abs(oth.mjd - t["tvis"]) < 3]
    if len(oth):
        sep = np.hypot((oth.ra - t["ra"]) * np.cos(np.radians(t["dec"])), oth.dec - t["dec"]) * 3600
        print(f"   other detections within 6\" at the event visit: {len(oth)}; within 3\": {(sep < 3).sum()}; their W1 median "
              f"{oth.w1mpro.median():.2f}, sep median {np.median(sep):.1f}\"")
