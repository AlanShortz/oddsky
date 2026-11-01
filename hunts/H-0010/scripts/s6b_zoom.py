"""s6b: zoomed views (+-250 d) of the events of the 39 sources with no catalogued lens match: Delta mag per band (G black, BP
blue, RP red) and NEOWISE visits as open squares. Diagnostics for the verdicts.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s6b_zoom.py
Writes hunts/H-0010/data/zoom_<k>.png."""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import CASES, DATA, NW, epoch, targets  # noqa: E402
from s3_lightcurves import ratio_series  # noqa: E402

x = pd.read_csv(os.path.join(DATA, "xmatch.csv"), dtype={"source_id": str})
known = set(x[x.ref_intime.notna() | x.gaia_alert.notna()].source_id)
T = targets()
T = T[~T.source_id.isin(known)].reset_index(drop=True)
lc = pd.read_csv(os.path.join(DATA, "lc_metrics.csv"), dtype={"source_id": str}).set_index("source_id")
print(len(T))
for part in range(0, len(T), 12):
    sub = T.iloc[part:part + 12]
    fig, ax = plt.subplots(4, 3, figsize=(18, 16))
    ax = ax.ravel()
    for i, r in enumerate(sub.itertuples()):
        d, _ = epoch(r.source_id)
        df, base = ratio_series(d)
        tp = lc.loc[r.source_id].t_peak
        if not np.isfinite(tp):
            tp = lc.loc[r.source_id].static_t0
        for b, c in (("G", "k"), ("BP", "tab:blue"), ("RP", "tab:red")):
            y = df[(df.g == b) & (np.abs(df.t - tp) < 250)]
            ax[i].errorbar(y.t - tp, y.dm, np.hypot(y.err, y.sig), fmt="o", color=c, ms=3, lw=0.6)
        vp = os.path.join(NW, f"{r.source_id}_visits.csv")
        if os.path.getsize(vp) > 5:
            v = pd.read_csv(vp)
            v = v[v["mode"] == "long"]
            for b, c in (("W1", "orange"), ("W2", "purple")):
                y = v[v.band == b]
                if len(y) >= 5:
                    z = y[np.abs(y.t - tp) < 250]
                    ax[i].plot(z.t - tp, z.mag - y.mag.median(), "s", color=c, ms=6, mfc="none")
        ax[i].invert_yaxis()
        ax[i].axhline(0, color="0.7", lw=0.5)
        ax[i].set_title(f"{r.source_id} {CASES.get(r.source_id, '')} G{r.phot_g_mean_mag:.1f} l{r.l:.1f} b{r.b:.1f} "
                        f"peak {lc.loc[r.source_id].t_peak_date}", fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(DATA, f"zoom_{part // 12}.png"), dpi=55)
    plt.close()
