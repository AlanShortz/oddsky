"""Plot ZTF DR light curves (from ztf_neowise.py) with the WISE difference light curves of the same lead.

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/ztf_plot.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
W = pd.read_csv(HERE / "leads_lc.csv")
leads = ["NGC3239 obs#33", "M81 obs#9", "NGC2976 fsn#5", "IC342 obs#26", "HolmII obs#21", "M101 obs#19", "UGCA127 obs#30"]
fig, ax = plt.subplots(len(leads), 1, figsize=(10, 2.6 * len(leads)))
for a, lab in zip(ax, leads):
    tag = lab.replace(" ", "_").replace("#", "")
    p = HERE / f"ztf_{tag}.csv"
    z = pd.read_csv(p) if p.exists() else pd.DataFrame()
    if len(z):
        z = z[z.flag.isna() | (z.flag == "")] if "flag" in z else z
        for b, c in (("ZTF_g", "g"), ("ZTF_r", "r"), ("ZTF_i", "m")):
            s = z[z.band == b]
            a.plot(2000 + (s.t_mjd - 51544.5) / 365.25, s.mag, ".", color=c, ms=2, label=b)
        a.invert_yaxis()
    a.set_ylabel("ZTF mag")
    a2 = a.twinx()
    for bnd, c in ((1, "C0"), (2, "C3")):
        s = W[(W.lead == lab) & (W.band == bnd)]
        a2.plot(2000 + (s.mjd - 51544.5) / 365.25, s.df_ujy, "s-", color=c, ms=3, lw=0.6, label=f"W{bnd} dF")
    a2.set_ylabel("WISE dF (uJy)")
    a.set_xlim(2017.5, 2025.9)
    a.set_title(lab, fontsize=8)
    a.legend(fontsize=6, loc="upper left"); a2.legend(fontsize=6, loc="lower left")
fig.tight_layout()
fig.savefig(HERE / "ztf_vs_wise.png", dpi=75)
