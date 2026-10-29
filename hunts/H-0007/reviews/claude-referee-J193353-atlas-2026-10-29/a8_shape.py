"""a8: shape of the decline (ATLAS o+c nightly, 2020 Mar 11 - Nov) against transient-like decays: exponential excess,
power-law excess (t - t_peak)^-a with t_peak free <= Mar 11, and the static/parallax point lens (fs=1). Also the log-excess decline rate
between epochs, which a decaying transient keeps monotonically decelerating. Own scipy code. usage: uv run --with MulensModel python a8_shape.py"""
import warnings
import numpy as np
import pandas as pd
import MulensModel as mm
from scipy.optimize import least_squares

warnings.filterwarnings("ignore")
D = pd.read_csv("/tmp/j1933atl/joint.csv")
d = D[D.band.isin(["Ao", "Ac"]) & (D.mjd > 58915) & (D.mjd < 59160)]
t, f, e = d.mjd.values, d.f.values, d.e.values
J = 2400000.5


def fitp(fun, p0, lo, hi):
    r = least_squares(lambda p: (fun(p) - f) / e, p0, bounds=(lo, hi)); return 2 * r.cost, r.x


ex = fitp(lambda p: 1 + p[0] * np.exp(-(t - 58919) / p[1]), [1.4, 40], [0, 1], [10, 500])
pl = min((fitp(lambda p: 1 + p[0] * ((t - p[2]) / 30.0) ** (-p[1]), [1.5, a, tp], [0, 0.1, 58700], [100, 10, 58918.9])
          for a in (0.5, 1, 2, 4) for tp in (58800, 58880, 58910, 58918)), key=lambda x: x[0])
ln = fitp(lambda p: (lambda u: (u * u + 2) / (u * np.sqrt(u * u + 4)))(np.hypot(p[2], (t - p[0]) / p[1])), [58926, 63, 0.43], [58880, 5, 0.01], [58960, 500, 3])
lp = fitp(lambda p: mm.Model({"t_0": p[0] + J, "u_0": p[2], "t_E": p[1], "pi_E_N": p[3], "pi_E_E": p[4], "t_0_par": 58925 + J},
                             coords="19:33:53.067 -21:18:13.49").get_magnification(t + J), [58929, 45, -0.39, -0.07, 0.53], [58880, 5, -3, -5, -5], [58960, 500, 3, 5, 5])
N = len(t)
print(f"decline only (Mar 11 - Nov 2020, {N} ATLAS nights):")
print(f"  exponential excess   chi2 {ex[0]:.0f}/{N - 2}  amp {ex[1][0]:.2f} tau {ex[1][1]:.1f} d")
print(f"  power-law excess     chi2 {pl[0]:.0f}/{N - 3}  params {np.round(pl[1], 2)}")
print(f"  static point lens    chi2 {ln[0]:.0f}/{N - 3}  {np.round(ln[1], 3)}")
print(f"  parallax point lens  chi2 {lp[0]:.0f}/{N - 5}  {np.round(lp[1], 3)}")
o = d[d.band == "Ao"].copy()
for lab, (a, b) in [("Mar 11", (58919, 58920)), ("Apr 8-12", (58946, 58953)), ("May 2-7", (58970, 58978)), ("Jun 1-5", (59000, 59006)),
                    ("Jul 9-13", (59038, 59045)), ("Aug 6-14", (59066, 59077)), ("Sep 3-11", (59094, 59105)), ("Oct 1-9", (59122, 59133))]:
    s = o[(o.mjd > a) & (o.mjd < b)]
    print(f"  o {lab:9s} MJD {s.mjd.mean():.1f}  A {s.f.mean():.3f}  ln(excess) {np.log(s.f.mean() - 1):+.2f}")
