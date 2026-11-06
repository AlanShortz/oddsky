"""The grader's ratio statistic applied to the model: each sense selected on its own, unit G bins in 12 <= G < 16."""
import numpy as np


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
