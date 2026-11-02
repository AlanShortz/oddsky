"""ATLAS difference-image forced photometry (task 5280891) at 156.2910 +17.1639: 30-day weighted bins per filter, and
weighted means in windows around the WISE event.

    uv run python -I hunts/H-0012/reviews/ngc3239-check-2026-11-01/atlas_check.py
"""
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
txt = (HERE / "atlas" / "atlas_5280891.txt").read_text()
d = pd.read_csv(io.StringIO(txt.lstrip("#")), sep=r"\s+")
n0 = len(d)
d = d[(d.duJy > 0) & (d.duJy < 150) & (d["chi/N"] < 5) & (d.err == 0) & (d.x > 50) & (d.x < 10510) & (d.y > 50) & (d.y < 10510)]
print("kept", len(d), "of", n0)


def wmean(g):
    w = 1 / g.duJy ** 2
    m = np.sum(w * g.uJy) / np.sum(w)
    e = 1 / np.sqrt(np.sum(w))
    # inflate by reduced chi2 if > 1
    chi = np.sum(w * (g.uJy - m) ** 2) / max(len(g) - 1, 1)
    return m, e * np.sqrt(max(chi, 1)), len(g)


wins = {"baseline 2015.5-2020.3": (57200, 58970), "2020 May-Jun (pre-conjunction, onset window start)": (58970, 59030),
        "2020 Oct 1-Nov 30 (WISE peak 11-23)": (59123, 59183), "2020 Dec-2021 Jan": (59184, 59245),
        "2021 Feb-Mar (HST 02-16)": (59246, 59304), "2021 Apr-Jun": (59305, 59395), "2021 Oct-2022 Jun": (59490, 59760),
        "2022.8-2025": (59850, 61000)}
res = {}
for f in ("c", "o"):
    g = d[d.F == f]
    res[f] = {}
    for k, (a, b) in wins.items():
        s = g[(g.MJD >= a) & (g.MJD < b)]
        if len(s) == 0:
            res[f][k] = None
            continue
        m, e, n = wmean(s)
        lim = m + 3 * e if m > 0 else 3 * e
        res[f][k] = dict(n=int(n), uJy=float(m), err=float(e), lim3_uJy=float(lim), lim3_AB=float(23.9 - 2.5 * np.log10(lim)),
                         mjd_range=[float(s.MJD.min()), float(s.MJD.max())])
    print(f, json.dumps(res[f], indent=1))
# gaps: nightly coverage between 2020-04-01 and 2021-06-30
g = d[(d.MJD > 58940) & (d.MJD < 59400)].sort_values("MJD")
nights = np.unique(np.floor(g.MJD))
gaps = [(float(a), float(b)) for a, b in zip(nights[:-1], nights[1:]) if b - a > 20]
res["gaps_gt20d_2020_2021"] = gaps
print("gaps > 20 d:", gaps)
json.dump(res, open(HERE / "atlas_check.json", "w"), indent=1)
fig, ax = plt.subplots(figsize=(9, 4))
for f, c in (("c", "teal"), ("o", "orange")):
    g = d[d.F == f].copy()
    g["bin"] = (g.MJD // 30).astype(int)
    b = g.groupby("bin").apply(lambda s: pd.Series(dict(zip(("m", "e", "n"), wmean(s)), mjd=s.MJD.mean())), include_groups=False)
    ax.errorbar(b.mjd, b.m, b.e, fmt="o", ms=3, color=c, label=f"ATLAS {f} (30-d bins)")
ax.axvline(59176.4, color="r", ls="--", label="WISE peak 2020-11-23")
ax.axvline(59261.8, color="g", ls=":", label="HST 2021-02-16")
ax.axvspan(58967.3, 59176.4, color="r", alpha=0.08, label="onset window")
ax.axhline(0, color="k", lw=0.5)
ax.set_ylim(-60, 60); ax.set_xlabel("MJD"); ax.set_ylabel("difference flux (uJy)")
ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(HERE / "atlas_check.png", dpi=110)
