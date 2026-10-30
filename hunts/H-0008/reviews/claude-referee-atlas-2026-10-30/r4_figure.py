"""r4: figure of the referee reduction (main variant) for both candidates: per-band flux ratio, the parallax point-lens fit, a
free symmetric Pearson VII bump, and residuals binned in 10-day bins per band. Also prints binned residuals around the event."""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import build  # noqa: E402
from lib import HERE, TARGETS  # noqa: E402

from oddsky.analysis.lensing import Problem  # noqa: E402

COL = {"ATLAS_o": "#e08a2c", "ATLAS_c": "#2aa1b3", "ZTF_g": "#2e9e44", "ZTF_r": "#c0392b", "ZTF_i": "#7f3c8d",
       "NEOWISE_W1": "#2836d9", "NEOWISE_W2": "#d6338a"}
fig, axes = plt.subplots(3, 2, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 1, 1]})
for col, (k, T) in enumerate(TARGETS.items()):
    df = build(k)
    prob = Problem(df.t.values, df.f.values, df.e.values, df.g.values, ra=T["ra"], dec=T["dec"], parallax=True, blend=True, t0par=T["tpk"])
    p, chi2 = prob.fit(t0c=T["tpk"])
    df["model"] = prob.model(p)
    fs = dict(zip(prob.names, p[prob.nlens:], strict=True))
    # magnification of the source: (f - 1 + fs) / fs
    df["A"] = (df.f - 1 + df.g.map(fs)) / df.g.map(fs)
    df["Ae"] = df.e / df.g.map(fs)
    df["Am"] = (df.model - 1 + df.g.map(fs)) / df.g.map(fs)
    df["band"] = df.g.str.rsplit("_", n=1).str[0].where(~df.g.str.startswith("NEOWISE"), df.g)
    ax, axr, axl = axes[0, col], axes[1, col], axes[2, col]
    win = (T["tpk"] - 400, T["tpk"] + 400)
    for b, d in df.groupby("band"):
        d = d[(d.t > win[0]) & (d.t < win[1])]
        ax.errorbar(d.t, d.f, d.e, fmt="o", ms=2.5, lw=0.4, color=COL.get(b, "k"), label=b, alpha=0.7)
        r = (d.f - d.model) / d.e
        axr.plot(d.t, r, ".", ms=2.5, color=COL.get(b, "k"))
        bins = np.arange(win[0], win[1] + 10, 10)
        g = d.assign(r=r, bn=np.digitize(d.t, bins)).groupby("bn")
        axl.plot(g.t.mean(), (g.f.mean() - g.model.mean()), "o-", ms=3, lw=0.8, color=COL.get(b, "k"))
    tt = np.linspace(*win, 2000)
    for g in prob.names:
        if g.startswith("ATLAS_o") or g.startswith("ATLAS_c"):
            q = Problem(tt, np.ones_like(tt), np.ones_like(tt), np.array([g] * len(tt)), ra=T["ra"], dec=T["dec"], parallax=True, blend=True, t0par=T["tpk"])
            m = q.model(np.r_[p[:5], fs[g]])
            ax.plot(tt, m, "-", lw=0.6, color=COL["ATLAS_o" if "_o_" in g else "ATLAS_c"])
    ax.set_title(f"{T['name']}: parallax+blend fit (referee reduction), chi2 {chi2:.0f}/{len(df) - len(p)}, tE {p[1]:.0f} d, u0 {p[2]:+.2f}")
    ax.set_ylabel("flux / baseline")
    ax.legend(fontsize=7, ncol=4)
    axr.axhline(0, color="k", lw=0.5)
    axr.set_ylim(-6, 6)
    axr.set_ylabel("resid / sigma")
    axl.axhline(0, color="k", lw=0.5)
    axl.set_ylabel("10-d binned\nresid (flux ratio)")
    axl.set_xlabel("MJD")
    for a in (ax, axr, axl):
        a.set_xlim(*win)
        a.axvline(T["tvis"], color="grey", lw=0.5, ls=":")
    # residual summary per band in phases
    ph = pd.cut(df.t - p[0], [-400, -150, -60, -20, 20, 60, 150, 400])
    tab = df.assign(r=(df.f - df.model), ph=ph).groupby(["band", "ph"], observed=True).r.agg(["size", "median"]).round(3)
    print(k, "fs", {g: round(float(v), 3) for g, v in fs.items()})
    print(tab.unstack(0).to_string())
fig.tight_layout()
fig.savefig(os.path.join(HERE, "r4_fits.png"), dpi=110)
