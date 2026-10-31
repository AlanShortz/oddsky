"""r9: do the relaxed rules let artifacts in? Exposure-level diagnostics (framelib.analyse) for every strong unexplained event (122;
56 of them not in H-0008's clean list) and every known-lens recovery (118), plus the per-visit flag fractions of the survey tables.
Off-target test: the event-frame centroid should move toward the matched Gaia star by f_ex x (Gaia - quiet centroid); 'miss' is
the distance between observed and predicted shift, significant if > 0.3" and > 5 sigma (sigma from the quiet-frame scatter).
Writes data/r9_metrics.csv. Run after r0 has downloaded the frames (events without frames are reported, not dropped silently)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framelib import analyse  # noqa: E402
from lib import DATA, H9, W9, frames  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 50)
s = pd.read_csv(os.path.join(W9, "sky4_strong.csv"), dtype={"g_source_id": str, "allwise_cntr": str})
k = pd.read_csv(os.path.join(W9, "sky4_classified.csv"), dtype={"g_source_id": str, "allwise_cntr": str})
k = k[k["class"] == "microlensing (known)"].copy()
h8 = pd.read_csv(os.path.join(H9, "..", "H-0008", "work", "sky3_clean.csv"), dtype={"allwise_cntr": str})
s["grp"], k["grp"] = "strong", "known"
s["new"] = ~s.allwise_cntr.isin(h8.allwise_cntr)
k["new"] = ~k.allwise_cntr.isin(h8.allwise_cntr)
ev = pd.concat([s, k], ignore_index=True)
ev["allwise_cntr"] = ev.allwise_cntr.astype("int64")
rows, missing = [], []
for r in ev.itertuples():
    fr = frames(r.allwise_cntr)
    if fr is None:
        missing.append(r.designation)
        continue
    res = analyse(fr, r)
    if res is None:
        missing.append(r.designation + " (too few frames)")
        continue
    m = res[0]
    rW = 10 ** (-0.4 * m["d_all"])
    fex = (rW - 1) / rW if rW > 1 else 0.0
    if np.isfinite(r.g_ra):
        c = np.cos(np.radians(m["de0"]))
        gx, gy = (r.g_ra - m["ra0"]) * c * 3600, (r.g_dec - m["de0"]) * 3600
    else:
        gx = gy = 0.0
    px, py = fex * gx, fex * gy
    miss = np.hypot(m["ox"] - px, m["oy"] - py)
    sig = np.hypot((m["ox"] - px) / m["sx"], (m["oy"] - py) / m["sy"])
    rows.append(dict(designation=r.designation, grp=r.grp, new=r.new, nblock=r.nblock, dw1=r.dw1, g_sep=r.g_sep, n_gaia_3as=r.n_gaia_3as,
                     l=r.l, b=r.b, hdfrac_event=r.hdfrac_event, hdfrac_other=r.hdfrac_other, nbfrac_event=r.nbfrac_event,
                     nbfrac_other=r.nbfrac_other, satfrac_event=r.satfrac_event, satfrac_other=r.satfrac_other,
                     miss=miss, miss_sig=sig, gx=gx, gy=gy, **m))
out = pd.DataFrame(rows)
out.to_csv(os.path.join(DATA, "r9_metrics.csv"), index=False)
print(f"analysed {len(out)} events ({(out.grp == 'strong').sum()} strong, {(out.grp == 'known').sum()} known); missing {len(missing)}: {missing[:20]}")
