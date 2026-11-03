"""H-0016 fades: plot NEOWISE visit light curves (from the local sky3lens run) for a list of fade events.
usage: fades_plot.py IN_CSV TAG [max_n]"""
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[1]
RUN = Path.home() / "oddsky-runs" / "h0008" / "lightcurves"
x = pd.read_csv(sys.argv[1])
tag = sys.argv[2]
x = x.head(int(sys.argv[3]) if len(sys.argv) > 3 else len(x))
cols = 4
r = int(np.ceil(len(x) / cols))
fig, axes = plt.subplots(r, cols, figsize=(4.2 * cols, 2.6 * r), squeeze=False)
for k, (_i, s) in enumerate(x.iterrows()):
    ax = axes[k // cols][k % cols]
    lc = pd.read_parquet(RUN / f"pixel={int(s.pixel)}.parquet")
    lc = lc[lc.allwise_cntr == int(s.allwise_cntr)].sort_values("t")
    yr = 2000 + (lc.t - 51544.5) / 365.25
    ax.errorbar(yr, lc.w1, lc.w1_err, fmt="o", ms=3, color="C0", label="W1")
    ax.errorbar(yr, lc.w2, lc.w2_err, fmt="s", ms=3, color="C3", label="W2")
    ax.axvline(2000 + (s.t - 51544.5) / 365.25, color="k", lw=0.5, ls=":")
    ax.invert_yaxis()
    g = f"G={s.g_phot_g_mean_mag:.1f}" if np.isfinite(s.get("g_phot_g_mean_mag", np.nan)) else "no Gaia"
    ax.set_title(f"{s.designation} dW1={s.dw1:.2f} dW2={s.dw2:.2f} {g}", fontsize=7.5)
for k in range(len(x), r * cols):
    axes[k // cols][k % cols].axis("off")
fig.tight_layout()
(HERE / "figures").mkdir(exist_ok=True)
fig.savefig(HERE / "figures" / f"fades_{tag}.png", dpi=100)
print("saved", len(x))
