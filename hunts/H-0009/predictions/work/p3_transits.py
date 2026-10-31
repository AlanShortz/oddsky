"""p3: GOST transits in the DR4 span per target: counts per year, and every transit within +-400 d of the NEOWISE event."""
import os
import sys

import numpy as np
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gaialib import gost  # noqa: E402
from targets import T  # noqa: E402

for k, tg in T.items():
    t = gost(k)
    nights = np.unique(np.floor(t))
    yrs = Time(t, format="mjd").decimalyear.astype(int)
    print(f"== {k}: {len(t)} transits on {len(nights)} nights in DR4; per year " + ", ".join(f"{y}:{(yrs == y).sum()}" for y in np.unique(yrs)))
    sel = np.abs(t - tg["t_nw"]) < 400
    groups = []
    for x in t[sel]:
        if groups and x - groups[-1][-1] < 3:
            groups[-1].append(x)
        else:
            groups.append([x])
    for g in groups:
        print(f"    {Time(g[0], format='mjd').iso[:10]}  MJD {g[0]:.2f}  dt {g[0] - tg['t_nw']:+7.1f} d  n {len(g)}  nights {len(np.unique(np.floor(g)))}")
