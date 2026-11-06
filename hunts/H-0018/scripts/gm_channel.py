"""Does the parallax cut carry the asymmetry in the blind cascade? Its effect depends on how many orbits lie near the cut, so stratify by true parallax."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from nss_rv_test import load  # noqa: E402

d = pd.read_parquet(f"{hd.RUNS}/gm_dr3.parquet")
o = d[d.kind == 12].copy()
o["c_plx"] = o.plx / o.s_plx > 20000 / o.P_fit
o["base"] = (o.a0_fit / o.s_a0 > 158 / np.sqrt(o.P_fit)) & (o.a0_fit / o.s_a0 > 5) & (o.s_e < 0.079 * np.log(o.P_fit) - 0.244) & (o.F2 < 25)


def a(s):
    m = s.mean()
    return f"{m:+.3f}±{np.sqrt((1 - m**2) / max(len(s), 1)):.3f} (N={len(s)})"


for lo, hi in [(300, 450), (450, 600), (600, 900), (900, 1100)]:
    z = o[o.base & (o.P_fit >= lo) & (o.P_fit < hi)]
    print(f"P {lo}-{hi}")
    for pl, ph in [(0.3, 0.7), (0.7, 1), (1, 1.5), (1.5, 2.5), (2.5, 1000)]:
        x = z[(z.plx_true >= pl) & (z.plx_true < ph)]
        print(f"   parallax {pl}-{ph}: no parallax cut A = {a(x.sense_fit)}; with it A = {a(x[x.c_plx].sense_fit)}; share cut +NEP {1 - x[x.sense_fit > 0].c_plx.mean():.3f}, -NEP {1 - x[x.sense_fit < 0].c_plx.mean():.3f}")

print("\nObserved A, same bins, all orbits: (parallax low edge, A, N)")
real = pd.concat([load(False), load(True)])
real = real[real.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])]
for lo, hi in [(300, 450), (450, 600), (600, 900), (900, 1100)]:
    z = real[real.period.between(lo, hi)]
    print(lo, hi, [(pl, round(z[z.parallax.between(pl, ph)].sense.mean(), 3), int(z.parallax.between(pl, ph).sum())) for pl, ph in [(0.3, 0.7), (0.7, 1), (1, 1.5), (1.5, 2.5), (2.5, 1000)]])
