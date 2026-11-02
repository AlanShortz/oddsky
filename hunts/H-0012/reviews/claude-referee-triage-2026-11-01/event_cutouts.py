"""Per-epoch W1/W2 difference cutouts (41x41 px, 2.75"/px) for selected leads, from the runner's cutouts.npz.

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/event_cutouts.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUN = Path("~/oddsky-runs/h0012a").expanduser()
L = {d["lead"]: d for d in json.loads((HERE / "leads.json").read_text())}
SEL = ["NGC3239 obs#33", "NGC4945 obs#3", "M81 obs#9", "NGC55 obs#14", "IC342 fsn#1", "NGC2976 fsn#5", "M101 obs#19",
       "UGCA127 obs#30", "NGC1744 obs#32", "IC342 obs#26"]
for lab in SEL:
    d = L[lab]
    gal, tile, gid = d["uid"].split("|")
    z = np.load(RUN / tile / gal / "cutouts.npz")
    lc = pd.read_parquet(RUN / tile / gal / "lightcurves.parquet")
    lc = lc[(lc.group == int(gid)) & (lc.band == 1)].sort_values("epoch")
    keys = [f"{gid}_w1_diff", f"{gid}_w2_diff"]
    if keys[0] not in z:
        print(lab, "no cutouts"); continue
    n = z[keys[0]].shape[0]
    fig, ax = plt.subplots(2, n, figsize=(1.1 * n, 2.6))
    for b, k in enumerate(keys):
        cube = z[k]
        v = np.nanpercentile(np.abs(cube[:, 10:31, 10:31]), 99.5)
        for i in range(n):
            ax[b, i].imshow(cube[i, 8:33, 8:33], origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
            ax[b, i].set_xticks([]); ax[b, i].set_yticks([])
            if b == 0 and i < len(lc):
                ax[b, i].set_title(f"{2000 + (lc.mjd.iloc[i] - 51544.5) / 365.25:.1f}", fontsize=6)
    fig.suptitle(f"{lab} W1 (top) / W2 difference per epoch, 25x25 px", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / f"epochs_{lab.split()[0]}_{lab.split()[1].replace('#', '')}.png", dpi=90)
    plt.close(fig)
    print(lab, "ok", n)
