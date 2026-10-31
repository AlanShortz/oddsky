"""r7: NEOWISE per-visit photometry (allwise_cntr as int64), visit quality (ccfrac = share of exposures with contamination
flags, rchi), and comparison with the ATLAS o light curve at the same time (log-linear interpolation of the excess between
the nearest ATLAS nights; quoted only when ATLAS nights bracket the visit within 3 d)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, mjd2date, neowise, targets  # noqa: E402

pd.set_option("display.width", 250)
T = targets()
TP = {"J175634": 59661.3, "J174744": 59654.4}
for k in KEYS:
    lc = neowise(k, T[k], raw=True).copy()
    base = np.abs(lc.t - TP[k]) > 400
    for b in ("w1", "w2"):
        lc[f"d{b}"] = lc[b] - np.median(lc[b][base])
        lc[f"r{b}"] = 10 ** (-0.4 * lc[f"d{b}"])
    nt = pd.read_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"))
    o = nt[nt.F == "o"].copy()
    ob = o[np.abs(o.t - TP[k]) > 400].groupby("cam").ujy.median()
    o["r"] = o.ujy / o.cam.map(ob)
    o = o.sort_values("t")
    rows = []
    for _, v in lc.iterrows():
        bef, aft = o[(o.t <= v.t) & (o.t > v.t - 3)], o[(o.t > v.t) & (o.t < v.t + 3)]
        if len(bef) and len(aft):
            a, c = bef.iloc[-1], aft.iloc[0]
            ea, ec = max(a.r - 1, 1e-3), max(c.r - 1, 1e-3)
            f = (v.t - a.t) / (c.t - a.t)
            ro = 1 + np.exp(np.log(ea) + f * (np.log(ec) - np.log(ea)))
            span = f"{a.r:.2f}@{a.t - v.t:+.1f}d..{c.r:.2f}@{c.t - v.t:+.1f}d"
        else:
            near = o.iloc[(o.t - v.t).abs().argsort()[:1]]
            ro = np.nan
            span = f"nearest o night {near.r.iloc[0]:.2f}@{near.t.iloc[0] - v.t:+.1f}d"
        rows.append((mjd2date(v.t), round(v.t - TP[k], 1), int(v.w1_n), int(v.w2_n), round(v.w1, 3), round(v.w2, 3), round(v.rw1, 3),
                     round(v.rw2, 3), round(v.w1_err, 3), round(v.ccfrac, 2), round(float(v.rchi), 1), round(ro, 2), span))
    print(f"== {k}: NEOWISE visits (baseline medians W1 {np.median(lc.w1[base]):.3f}, W2 {np.median(lc.w2[base]):.3f}; baseline "
          f"visit rms W1 {np.std(lc.dw1[base]):.3f}, W2 {np.std(lc.dw2[base]):.3f} mag)")
    print(pd.DataFrame(rows, columns=["date", "dt", "n1", "n2", "W1", "W2", "W1/base", "W2/base", "eW1", "ccfrac", "rchi",
                                      "o/base interp", "ATLAS o bracket"]).to_string(index=False))
