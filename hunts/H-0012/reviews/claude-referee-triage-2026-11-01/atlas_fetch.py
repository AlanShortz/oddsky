"""Fetch finished ATLAS forced-photometry results (difference images) recorded in atlas_tasks.json, bin them
(60-day bins, per filter, chi/N > 0 and |uJy err| < 200 only), and plot them with the WISE difference light curves.

    set -a; . ~/.config/oddsky/atlas.env; set +a
    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/atlas_fetch.py
"""
import io
import json
from pathlib import Path

import httpx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from oddsky.data import atlas

HERE = Path(__file__).resolve().parent
W = pd.read_csv(HERE / "leads_lc.csv")
tasks = json.loads((HERE / "atlas_tasks.json").read_text())
done = []
for t in tasks:
    tag = t["lead"].replace(" ", "_").replace("#", "")
    p = HERE / f"atlas_{tag}.txt"
    if not p.exists():
        st = atlas.status(t["task_url"])
        if not st.get("result_url"):
            print(t["lead"], "not finished"); continue
        r = httpx.get(st["result_url"], headers=atlas._headers(), timeout=120)
        p.write_text(r.text)
    d = pd.read_csv(io.StringIO(p.read_text().lstrip("#")), sep=r"\s+")
    d = d[(d.duJy > 0) & (d.duJy < 200) & (d.err == 0) if "err" in d else (d.duJy > 0) & (d.duJy < 200)]
    d["bin"] = (d.MJD // 60).astype(int)
    b = d.groupby(["F", "bin"]).apply(lambda g: pd.Series(dict(
        mjd=g.MJD.mean(), f=np.average(g.uJy, weights=1 / g.duJy**2), e=1 / np.sqrt(np.sum(1 / g.duJy**2)), n=len(g))),
        include_groups=False).reset_index()
    done.append((t["lead"], b))
    summ = {}
    for F_, g in b.groupby("F"):
        k = np.argmax(g.f / g.e)
        summ[F_] = dict(n_bins=len(g), max_snr=round(float((g.f / g.e).max()), 1), mjd_max=round(float(g.mjd.iloc[k])),
                        f_max=round(float(g.f.iloc[k]), 1), e_max=round(float(g.e.iloc[k]), 1),
                        median_f=round(float(g.f.median()), 1), robust_sd=round(float(1.4826 * np.median(np.abs(g.f - g.f.median()))), 1))
    print(t["lead"], json.dumps(summ))
fig, ax = plt.subplots(len(done), 1, figsize=(10, 2.8 * max(len(done), 1)), squeeze=False)
for a, (lab, b) in zip(ax[:, 0], done):
    for F_, c in (("c", "c"), ("o", "orange")):
        g = b[b.F == F_]
        a.errorbar(2000 + (g.mjd - 51544.5) / 365.25, g.f, g.e, fmt="o", ms=3, color=c, label=f"ATLAS {F_} diff (60-d bins)")
    a.axhline(0, color="k", lw=0.5)
    a.set_ylabel("ATLAS uJy"); a.set_title(lab, fontsize=8)
    a2 = a.twinx()
    for bnd, c in ((1, "C0"), (2, "C3")):
        s = W[(W.lead == lab) & (W.band == bnd)]
        a2.plot(2000 + (s.mjd - 51544.5) / 365.25, s.df_ujy, "s-", color=c, ms=3, lw=0.6, label=f"W{bnd}")
    a2.set_ylabel("WISE dF uJy"); a.set_xlim(2015.3, 2026.0)
    a.legend(fontsize=6, loc="upper left"); a2.legend(fontsize=6, loc="lower right")
fig.tight_layout(); fig.savefig(HERE / "atlas_vs_wise.png", dpi=75)
