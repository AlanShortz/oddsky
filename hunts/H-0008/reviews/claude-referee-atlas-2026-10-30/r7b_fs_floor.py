"""r7b: like r7, but each series keeps its own fs, only bounded below (fs >= floor). Per-unit fs differ at high significance in
ATLAS (additive per-unit offsets), so a common fixed fs (r7) over-penalises; a floor is the fair Gaia-informed prior."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import build  # noqa: E402
from lib import TARGETS  # noqa: E402

from oddsky.analysis.lensing import Problem  # noqa: E402


class Floored(Problem):
    floor = 0.02

    def bounds(self, t0c):
        lo, hi = super().bounds(t0c)
        lo[self.nlens:] = self.floor
        return lo, hi

    def starts(self, t0c):
        for p in super().starts(t0c):
            p = list(p)
            for i in range(self.nlens, len(p)):
                p[i] = max(p[i], self.floor + 0.01)
            yield p


for k, T in TARGETS.items():
    df = build(k)
    keep = df.groupby("g").t.transform(lambda t: (np.abs(t - T["tpk"]) < 150).sum() >= 3).astype(bool)
    df = df[keep]
    for par in (False, True):
        ref = None
        for fl in (0.02, 0.4, 0.6, 0.8, 0.9):
            prob = Floored(df.t.values, df.f.values, df.e.values, df.g.values, ra=T["ra"], dec=T["dec"], parallax=par, blend=True, t0par=T["tpk"])
            prob.floor = fl
            p, c = prob.fit(t0c=T["tpk"])
            ref = c if ref is None else ref
            print(f"{k} {'parallax' if par else 'static  '} fs >= {fl:.2f}: chi2 {c:8.1f} (d {c - ref:+6.1f}) tE {p[1]:6.1f} u0 {p[2]:+.3f} "
                  f"fs {np.round(p[prob.nlens:], 2).tolist()}" + (f" piE {np.round(p[3:5], 3).tolist()}" if par else ""), flush=True)
