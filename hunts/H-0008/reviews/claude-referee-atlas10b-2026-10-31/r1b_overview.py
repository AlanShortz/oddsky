"""r1b: overview plots of the full 2015-2026 ATLAS record (nightly, per unit/band, ratio to own baseline) + NEOWISE, for
visual checks of repeats and of the event shape. Writes r1b_overview.png."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, HERE, KEYS, neowise, targets  # noqa: E402

T = targets()
TP = {"J175634": 59661.3, "J174744": 59654.4}
fig, ax = plt.subplots(4, 1, figsize=(13, 14))
col = {"01a": "C0", "02a": "C1", "03a": "C2", "04a": "C3"}
for i, k in enumerate(KEYS):
    nt = pd.read_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"))
    n = neowise(k, T[k])
    for j, (lo, hi) in enumerate(((57100, 61400), (TP[k] - (60 if k == "J175634" else 350), TP[k] + (60 if k == "J175634" else 350)))):
        a = ax[2 * i + j]
        for (F, cam), d in nt.groupby(["F", "cam"]):
            base = np.median(d.ujy[np.abs(d.t - TP[k]) > 400])
            m = (d.t > lo) & (d.t < hi)
            a.errorbar(d.t[m], d.ujy[m] / base, d.ujy_err[m] / base, fmt="o" if F == "o" else "s", ms=3, color=col[cam],
                       mfc="none" if F == "c" else col[cam], lw=0.5, label=f"{F} {cam}")
        for b, d in n.groupby("band"):
            base = np.median(d.fl[np.abs(d.t - TP[k]) > 400])
            m = (d.t > lo) & (d.t < hi)
            a.plot(d.t[m], d.fl[m] / base, "k*" if b == "W1" else "m^", ms=8, label=b)
        a.set_title(f"{k} {'full record' if j == 0 else 'event'}")
        a.axvline(TP[k], color="0.7", lw=0.5)
        a.set_ylabel("flux / own baseline")
        if j == 0:
            a.set_ylim(0.6, 2.4 if k == "J174744" else 3)
    ax[2 * i].legend(ncol=10, fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(HERE, "r1b_overview.png"), dpi=80)
