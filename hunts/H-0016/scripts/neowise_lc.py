"""H-0016: NEOWISE visit light curves (IRSA single exposures, Oddsky quality cuts) for a list of finalists, plus AllWISE 2010
and 2MASS 2000 epochs on the same axis. Writes work/lc/<designation>.csv and figures/lc_<tag>.png (grid).
usage: neowise_lc.py IN_CSV TAG [max_n]"""
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from oddsky.data.neowise import lightcurve

HERE = Path(__file__).resolve().parents[1]
x = pd.read_csv(sys.argv[1])
tag = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else len(x)
x = x.head(n)
(HERE / "work" / "lc").mkdir(parents=True, exist_ok=True)
(HERE / "figures").mkdir(exist_ok=True)
rows = []
cols = 4
r = int(np.ceil(len(x) / cols))
fig, axes = plt.subplots(r, cols, figsize=(4.2 * cols, 2.8 * r), squeeze=False)
for k, (_i, s) in enumerate(x.iterrows()):
    ax = axes[k // cols][k % cols]
    try:
        lc, prov = lightcurve(float(s.ra), float(s.dec))
    except Exception as e:  # noqa: BLE001
        print(s.designation, "fetch failed", e)
        lc = pd.DataFrame()
    if len(lc):
        lc.to_csv(HERE / "work" / "lc" / f"{s.designation}.csv", index=False)
        for band, c in (("W1", "C0"), ("W2", "C3")):
            b = lc[lc.band == band]
            yr = 2000 + (b.t_mjd - 51544.5) / 365.25
            ax.errorbar(yr, b.mag, b.err, fmt="o", ms=3, color=c, label=band)
            rows.append(dict(designation=s.designation, band=band, n_visits=len(b), med=float(b.mag.median()), ptp=float(b.mag.max() - b.mag.min()),
                             first=float(b.mag.iloc[0]), last=float(b.mag.iloc[-1])))
    for m, c, mk in ((s.w1mpro_allwise, "C0", "s"), (s.w2mpro_allwise, "C3", "s")):
        ax.plot([2010.5], [m], mk, color=c, ms=7, mfc="none")
    if np.isfinite(s.get("k_m_2mass", np.nan)):
        ax.plot([2000.0], [s.k_m_2mass], "^", color="k", ms=6, mfc="none")
    ax.invert_yaxis()
    ax.set_title(f"{s.designation}  d1={s.d1:+.2f} d2={s.d2:+.2f}", fontsize=8)
    ax.set_xlim(1999, 2025)
for k in range(len(x), r * cols):
    axes[k // cols][k % cols].axis("off")
fig.tight_layout()
fig.savefig(HERE / "figures" / f"lc_{tag}.png", dpi=110)
pd.DataFrame(rows).to_csv(HERE / "work" / f"lc_{tag}_summary.csv", index=False)
print("done", len(rows) // 2, "stars")
