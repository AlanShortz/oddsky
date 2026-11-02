"""Is NGC 925 obs#37's 2023-24 rise unusual among all candidates photometered in NGC 925 (tile 0359p333)? For every
group: change of the last three epochs vs the 2014-2022 mean, in sigma, W1 and W2.

    uv run python hunts/H-0012/reviews/h0012b-referee/last_epoch_null.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

from oddsky.imaging import metrics

D = Path("~/oddsky-runs/h0012b/0359p333/NGC0925").expanduser()
lc = pd.read_parquet(D / "lightcurves.parquet")
rows = []
for g, l in lc.groupby("group"):
    r = dict(group=g)
    for b in (1, 2):
        lb = l[l.band == b].sort_values("mjd")
        rf = lb.groupby("season").ref_flux.first().to_dict()
        f = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
        e = lb.err.to_numpy(); t = lb.mjd.to_numpy()
        ok = np.isfinite(f) & (e > 0)
        mid = ok & (t > 56600) & (t < t.max() - 550)
        late = ok & (t >= t.max() - 550)
        if mid.sum() < 5 or late.sum() < 2:
            continue
        w = 1 / e**2
        m0 = np.sum(w[mid] * f[mid]) / w[mid].sum(); e0 = 1 / np.sqrt(w[mid].sum())
        m1 = np.sum(w[late] * f[late]) / w[late].sum(); e1 = 1 / np.sqrt(w[late].sum())
        r[f"w{b}_late_sig"] = (m1 - m0) / np.hypot(e0, e1)
    rows.append(r)
t = pd.DataFrame(rows)
print(len(t), "groups")
for b in (1, 2):
    s = t[f"w{b}_late_sig"].dropna()
    print(f"W{b}: median {s.median():.2f}, robust sd {1.4826 * np.median(np.abs(s - s.median())):.2f}, n>5: {(s > 5).sum()}, n<-5: {(s < -5).sum()}")
print(t.set_index("group").loc[11])
print(t.sort_values("w2_late_sig", ascending=False).head(6))
