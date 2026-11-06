"""Exploratory, after the held-out run: does the -2.3 sigma prograde hint in wide pairs behave like a signal?"""
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
import wb  # noqa: E402

path = f"{hd.RUNS}/data/elbadry/cat.parquet"
held = wb.load(path, True)
dev = wb.load(path, False)
z, s, n = wb.rotation(held)
print("held-out, by |z|/sigma cut")
for lo, hi in [(0, 1), (1, 2), (2, 3), (3, 5), (5, 10), (10, 1e9)]:
    k = (np.abs(z) >= lo * s) & (np.abs(z) < hi * s)
    print(hd.fmt(f"  |z|/s in [{lo},{hi:.3g})", hd.fit_dipole(np.sign(z[k]), n[k])))
d = wb.select(held)
print("\nheld-out, mean y by Galactic latitude (prograde: negative at b>0, positive at b<0)")
b = np.degrees(np.arcsin(d.nz))
for lo, hi in [(-90, -30), (-30, -10), (-10, 0), (0, 10), (10, 30), (30, 90)]:
    x = d[(b >= lo) & (b < hi)]
    print(f"  b {lo:>4} to {hi:>4}: N={len(x):6d} mean y = {x.y.mean():+.4f} ± {np.sqrt((1 - x.y.mean()**2) / len(x)):.4f}")
all_ = wb.select(dev)
y = np.r_[d.y.values, all_.y.values]
nn = np.r_[d[["nx", "ny", "nz"]].values, all_[["nx", "ny", "nz"]].values]
r = hd.fit_dipole(y, nn)
print("\n" + hd.fmt("dev + held-out", r))
print(f"  95% limit on |<L_z>| with gain 3/2: {(abs(r['Dz']) + 1.96 * r['Dz_se']) * 2 / 3:.4f}")
