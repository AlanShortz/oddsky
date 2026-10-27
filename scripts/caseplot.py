"""All series of a case on one time axis (magnitudes, brighter up). python scripts/caseplot.py OS-0010 out.png"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from oddsky.case.store import CaseStore

s = CaseStore.find(sys.argv[1])
fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
colors = {"G": "#222", "BP": "#3b6fd4", "RP": "#c8442f", "ZTF_g": "#2a9d5c", "ZTF_r": "#d98c1f", "ZTF_i": "#7a3fb0",
          "W1": "#c9832b", "W2": "#b0303f", "V": "#2a9d5c", "B": "#3b6fd4", "TESS": "#555"}
for surv in s.surveys():
    df = s.series(surv)
    df = df[df.flag == ""]
    for band, g in df.groupby("band"):
        ax = axes[1] if surv == "neowise" else axes[2] if surv == "tess" else axes[0]
        ax.plot(g.t_mjd, g.mag, ".", ms=2 if surv == "tess" else 4, color=colors.get(band, "#999"),
                label=f"{surv}:{band} ({len(g)})", alpha=0.6 if surv == "tess" else 0.9)
for ax, t in zip(axes, ("optical (Gaia, ZTF, AAVSO)", "infrared (NEOWISE)", "TESS (relative)"), strict=False):
    ax.invert_yaxis()
    ax.legend(fontsize=7, ncol=4)
    ax.set_title(t, fontsize=9, loc="left")
axes[2].set_xlabel("MJD")
fig.suptitle(f"{s.load().target.name}", fontsize=11)
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=85)
