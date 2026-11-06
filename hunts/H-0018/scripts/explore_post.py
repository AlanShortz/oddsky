"""Exploratory, after the held-out run, on all orbits: short-period zoom and the model's handedness at fixed margin."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
from nss_rv_test import load  # noqa: E402

a = pd.concat([load(False), load(True)])
a = a[a.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])]
print("all orbits", len(a), "A", round(a.sense.mean(), 4), "N+ ", (a.sense > 0).sum(), "N-", (a.sense < 0).sum())
print("\nA in narrow bins (all orbits)")
for lo, hi in [(20, 50), (50, 57), (57, 60), (60, 66), (66, 72), (72, 85), (85, 100), (100, 115), (115, 130), (130, 150), (150, 170), (170, 180), (180, 190), (190, 200), (200, 225), (225, 250)]:
    s = a[(a.period >= lo) & (a.period < hi)]
    m = s.sense.mean()
    print(f"  {lo}-{hi} d N={len(s):5d} A={m:+.3f} ± {np.sqrt((1 - m**2) / max(len(s), 1)):.3f}")

print("\nModel vs data at fixed sense-blind margin, P 600-900 d")
f = pd.read_parquet(sys.argv[1])
f = f[(f.P >= 600) & (f.P < 900)]
f = f.assign(m=f.plx / f.s_plx_minus * f.P / 20000)
z6 = a[(a.period >= 600) & (a.period < 900)].copy()
ref = z6[z6.sense < 0].groupby(pd.cut(z6[z6.sense < 0].phot_g_mean_mag, np.arange(5, 19)), observed=True).parallax_error.median()
z6["m"] = z6.parallax / pd.cut(z6.phot_g_mean_mag, np.arange(5, 19)).map(ref).astype(float) * z6.period / 20000
wts_d, wts_m = [], []
for lo, hi in [(0, 1.5), (1.5, 2.5), (2.5, 5), (5, 10), (10, 1e9)]:
    x, y = f[(f.m >= lo) & (f.m < hi)], z6[(z6.m >= lo) & (z6.m < hi)]
    na, nb = x.acc_plus.sum(), x.acc_minus.sum()
    Am = (na - nb) / max(na + nb, 1)
    Ad = y.sense.mean()
    print(f"  [{lo},{hi:.3g}) model A={Am:+.3f} (N={na + nb}, frac {(na + nb) / (f.acc_plus.sum() + f.acc_minus.sum()):.3f}); data A={Ad:+.3f} ± {np.sqrt((1 - Ad**2) / len(y)):.3f} (N={len(y)}, frac {len(y) / len(z6):.3f})")
    wts_d.append(len(y) / len(z6))
    wts_m.append(Am)
print("  model A re-weighted to the data's margin distribution:", round(float(np.dot(wts_d, wts_m)), 3), " data:", round(float(z6.sense.mean()), 3))
