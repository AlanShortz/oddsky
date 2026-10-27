"""Quick-look sheet: a grid of candidates, Gaia G/BP/RP per transit (2014-17), one panel each.

python scripts/quicklook.py out.png id1 id2 ...   (ids from hunts/H-0001/epoch/)
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

out, ids = sys.argv[1], sys.argv[2:]

HUNT = os.environ.get("HUNT", "H-0001")
tri = None
n = len(ids)
cols = 3
rows = (n + cols - 1) // cols
fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 2.6 * rows), squeeze=False)
for ax, sid in zip(axes.flat, ids, strict=False):
    df = pd.read_parquet(f"hunts/{HUNT}/epoch/{sid}.parquet")
    for band, c in (("BP", "#3b6fd4"), ("G", "#222"), ("RP", "#c8442f")):
        b = df[df.band == band]
        good, bad = b[b.flag == ""], b[b.flag != ""]
        off = good.mag.median() if len(good) else 0
        ax.plot(good.t_mjd, good.mag - off, ".", ms=3, color=c, label=band)
        ax.plot(bad.t_mjd, bad.mag - off, "x", ms=3, color=c, alpha=0.5)
    ax.invert_yaxis()
    title = str(sid)
    if tri is not None and int(sid) in tri.index:
        r = tri.loc[int(sid)]
        title += f"  G={r.g_mag:.1f} BP-RP={r.bp_rp:.2f}  P?={r.best_period:.1f}d pw={r.best_power:.2f}"
    ax.set_title(title, fontsize=7)
    ax.tick_params(labelsize=6)
axes.flat[0].legend(fontsize=6)
for ax in list(axes.flat)[n:]:
    ax.axis("off")
fig.tight_layout()
fig.savefig(out, dpi=90)
