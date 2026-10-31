"""r11: repeats 2015-2026. ATLAS nightly o and c, ratio to own unit baseline, PSF-width corrected with the per-band slope of r1
(fraction per px of major axis), binned in 20 d; the largest off-event bins and their significance against the bin scatter.
Also the 2021 season of J174744 (the onset of the slow event, Hawaii units only)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, mjd2date  # noqa: E402

TP = {"J175634": 59661.3, "J174744": 59654.4}
EV = {"J175634": (59630, 59700), "J174744": (59380, 59900)}
SL = {"J175634": {"o": 0.0804, "c": 0.0828}, "J174744": {"o": 0.0321, "c": -0.0095}}  # r1 slopes (fraction/px)
for k in KEYS:
    nt = pd.read_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"))
    nt["r"] = np.nan
    for (F, cam), d in nt.groupby(["F", "cam"]):
        b = d[np.abs(d.t - TP[k]) > 400]
        corr = 1 + SL[k][F] * (d.maj - 2.4)
        base = np.median((b.ujy / (1 + SL[k][F] * (b.maj - 2.4))))
        nt.loc[d.index, "r"] = d.ujy / corr / base
    print(f"== {k}")
    for F in ("o", "c"):
        d = nt[(nt.F == F) & ~nt.t.between(*EV[k])].copy()
        d["bin"] = np.floor((d.t - 57200) / 20)
        g = d.groupby("bin").agg(t=("t", "mean"), r=("r", "median"), n=("r", "size"))
        g = g[g.n >= 3]
        s = 1.4826 * np.median(np.abs(g.r - np.median(g.r)))
        top = g.sort_values("r", ascending=False).head(4)
        low = g.sort_values("r").head(2)
        print(f"  {F}: {len(g)} off-event 20-d bins (>=3 nights), median {np.median(g.r):.3f}, robust bin scatter {s:.3f}; brightest: " +
              "; ".join(f"{mjd2date(r.t)} x{r.r:.3f} ({(r.r - np.median(g.r)) / s:+.1f} sig, n {int(r.n)})" for _, r in top.iterrows()) +
              " | faintest: " + "; ".join(f"{mjd2date(r.t)} x{r.r:.3f}" for _, r in low.iterrows()))
    if k == "J174744":
        d = nt[(nt.t > 59300) & (nt.t < 59520)].sort_values("t")
        d["bin"] = np.floor((d.t - 59300) / 20)
        print("  2021 season (all units, 20-d bins, PSF-corrected ratio):")
        for (F, b_), x in d.groupby(["F", "bin"]):
            print(f"    {F} {mjd2date(x.t.mean())} dt {x.t.mean() - TP[k]:+6.0f} x{x.r.median():.3f} (n {len(x)}, units {sorted(x.cam.unique())})")
