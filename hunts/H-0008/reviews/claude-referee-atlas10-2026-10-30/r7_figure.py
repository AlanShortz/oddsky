"""r7: figure of the seven light curves in excess flux normalised by each series' fitted source flux (parallax lens, default
reduction, r3), i.e. (A - 1) if the lens is right: achromatic data then fall on one curve. ATLAS c and o, NEOWISE, Gaia, ZTF.
For J185846, J182120 and J075219 (no usable lens fit) the panels show the raw excess relative to each series' event-window maximum."""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import Fitter  # noqa: E402
from lib import DATA, HERE, targets  # noqa: E402

KEYS = ["J163539", "J173150", "J174440", "J191120", "J075219", "J185846", "J182120"]
TPK = {"J163539": 57980.0, "J075219": 58208.0, "J174440": 60010.0, "J191120": 59294.0, "J173150": 58311.0,
       "J185846": 57485.0, "J182120": 57472.0}
WIN = {"J191120": (-60, 150), "J075219": (-60, 80), "J185846": (-400, 400), "J182120": (-400, 400)}
COL = {"ATLAS_c": "#2aa1b3", "ATLAS_o": "#e08a2c", "NEOWISE_W1": "#2836d9", "NEOWISE_W2": "#d6338a", "GAIA_G": "#222222",
       "ZTF_r": "#b22222", "ZTF_g": "#2e8b57", "ZTF_i": "#8b4513"}
fig, axes = plt.subplots(4, 2, figsize=(12, 13))
for ax, k in zip(axes.flat, KEYS, strict=False):
    p = os.path.join(DATA, f"r3_{k}_series.csv")
    if not os.path.exists(p):
        ax.set_title(f"{k}: no fit yet")
        continue
    s = pd.read_csv(p)
    jp = os.path.join(DATA, f"r3_{k}.json")
    jp = jp if os.path.exists(jp) else jp.replace(".json", "_quick.json")
    js = json.load(open(jp))["default"]["res"]
    lens = k not in ("J185846", "J182120", "J075219")
    amp = js["parallax"]["amp"]
    lo, hi = WIN.get(k, (-300, 300))
    w = s[(s.t - TPK[k] > lo) & (s.t - TPK[k] < hi)]
    for g, d in w.groupby("g"):
        key = next((c for c in COL if g.startswith(c)), None)
        if key is None:
            continue
        if lens:
            A = amp[g]
            if abs(A) < 1e-9:
                continue
            y, e = d.d / A, d.e / abs(A)
        else:
            A = max(np.nanmax(np.abs(d.d)), 1e-9)
            y, e = d.d / A, d.e / A
        ax.errorbar(d.t - TPK[k], y, e, fmt="o", ms=2.5 if g.startswith("ATLAS") else 5, lw=0.4, c=COL[key], alpha=0.75,
                    label=key)
    if lens:
        tt = np.linspace(TPK[k] + lo, TPK[k] + hi, 1500)
        tg = targets()[k]
        F = Fitter(pd.DataFrame({"t": tt, "d": 0.0, "e": 1.0, "g": "x"}), ra=tg["ra"], dec=tg["dec"], t0par=round(TPK[k]))
        ax.plot(tt - TPK[k], F.lens(js["parallax"]["p"], True), c="k", lw=0.8, label="parallax lens (A-1)")
        ax.set_ylabel("excess / fitted source flux  (= A-1)", fontsize=7)
        if k == "J191120":
            ax.set_yscale("symlog", linthresh=1)
    else:
        ax.set_ylabel("excess / max |excess| (no lens fit)", fontsize=7)
    h, lab = ax.get_legend_handles_labels()
    uniq = dict(zip(lab, h, strict=False))
    ax.legend(uniq.values(), uniq.keys(), fontsize=6, loc="upper right")
    ax.set_title(k, fontsize=9)
    ax.set_xlabel(f"days from MJD {TPK[k]:.0f}", fontsize=7)
    ax.tick_params(labelsize=7)
for ax in list(axes.flat)[len(KEYS):]:
    ax.axis("off")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "r7_lightcurves.png"), dpi=110)
print("wrote r7_lightcurves.png")
