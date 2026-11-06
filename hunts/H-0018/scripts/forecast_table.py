"""The DR4 forecast's model column, in the grader's statistic: each sense selected on its own, unit G bins in 12 <= G < 16."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402


def ratio(d, lo, hi, emin=0.0, emax=1.0):
    x = d[(d.P >= lo) & (d.P < hi) & (d.ecc >= emin) & (d.ecc < emax)]
    vals, w = [], []
    for g in range(12, 16):
        s = x[(x.G >= g) & (x.G < g + 1)]
        p, m = s[s.acc_plus].s_plx_plus, s[s.acc_minus].s_plx_minus
        if min(len(p), len(m)) >= 10:
            vals.append(np.nanmedian(p) / np.nanmedian(m))
            w.append(len(p) + len(m))
    return float(np.average(vals, weights=w)) if vals else float("nan")


def asym(d, lo, hi):
    x = d[(d.P >= lo) & (d.P < hi)]
    return (x.acc_plus.sum() - x.acc_minus.sum()) / max(x.acc_plus.sum() + x.acc_minus.sum(), 1)


for name in ["sim_nss", "sim_field", "sim_dr4_nss", "sim_dr4_field"]:
    d = pd.read_parquet(f"{hd.RUNS}/{name}.parquet")
    r = {b: ratio(d, *b) for b in [(340, 390), (600, 700), (700, 800), (800, 900), (1100, 1600)]}
    c = r[(700, 800)] - 0.5 * (r[(600, 700)] + r[(800, 900)])
    print(name, {f"{k[0]}-{k[1]}": round(v, 3) for k, v in r.items()}, f"contrast {c:.3f}",
          f"e<0.2 {ratio(d, 700, 800, 0, 0.2):.3f} e>=0.4 {ratio(d, 700, 800, 0.4, 1):.3f}", f"A(340-390) {asym(d, 340, 390):+.3f}")
