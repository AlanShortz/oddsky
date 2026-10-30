"""r3: whole light curves (ZTF catflags=0 nightly, NEOWISE visits) for the five targets; zooms relative to each series'
baseline = median of nights more than 200 d from the NEOWISE event visit."""
import os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import ztf, neowise, D
from targets import TARGETS
fig, axs = plt.subplots(5, 2, figsize=(16, 20))
col = {"g": "tab:green", "r": "tab:red", "i": "tab:purple"}
for i, (k, (name, ra, dec, t, pix)) in enumerate(TARGETS.items()):
    z = ztf(k); n = neowise(k)
    for j, (lo, hi) in enumerate(((58150, 60700), (t - 250, t + 250))):
        ax = axs[i, j]
        for s, d in z.groupby("series"):
            base = d[(d.mjd - t).abs() > 200].mag.median()
            if not np.isfinite(base): base = d.mag.max()
            d = d[(d.mjd > lo) & (d.mjd < hi)]
            if len(d) == 0: continue
            ax.errorbar(d.mjd, d.mag - base, d.magerr, fmt="o" if "1428" in s or "1804" in s or "1585" in s else ".", ms=3,
                        color=col[s[4]], alpha=0.7, label=f"{s} ({len(d)})")
        nb = n[(n.t - t).abs() > 100]
        for b, c in (("w1", "k"), ("w2", "orange")):
            m = (n.t > lo) & (n.t < hi)
            ax.errorbar(n.t[m], n[b][m] - nb[b].median(), n[f"{b}_err"][m], fmt="s", color=c, ms=5, label=b.upper())
        ax.axvline(t, color="gray", lw=0.5)
        ax.invert_yaxis(); ax.set_title(f"{name}"); ax.legend(fontsize=6); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "r3_lightcurves.png"), dpi=80)
