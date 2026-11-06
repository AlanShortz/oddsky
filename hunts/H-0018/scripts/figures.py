"""Figures for the H-0018 dossier, from the frozen held-out outputs."""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
from nss_rv_test import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
DATA, MODEL = "#2836d9", "#eb6834"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
                     "figure.dpi": 150, "savefig.bbox": "tight", "legend.frameon": False})


def period_axis(ax):
    ax.set_xscale("log")
    ax.set_xlim(45, 3000)
    ax.set_xticks([50, 100, 182.6, 365.25, 730.5, 1461, 2922], ["50", "100", "½ yr", "1 yr", "2 yr", "4 yr", "8 yr"])
    ax.minorticks_off()
    for x in (182.6, 365.25, 730.5):
        ax.axvline(x, color=MUTED, lw=0.8, zorder=0)


t = pd.read_csv(ROOT / "work/nss_by_period_heldout.csv")
mid = np.sqrt(t.lo * t.hi)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 6.4), sharex=True)
a1.errorbar(mid, t.A, yerr=t.A_se, fmt="o", ms=5, color=DATA, lw=1.5, label="Gaia DR3 orbits, held-out 70%")
a1.plot(mid, t.A_model, "-", color=MODEL, lw=2, label="forward model, frozen before opening them")
a1.axhline(0, color=MUTED, lw=1)
a1.set_ylim(-0.36, 0.34)
a1.set_ylabel("Handedness A\n(below 0: Earth-sense orbits missing)")
a1.legend(loc="upper right")
period_axis(a1)
a2.errorbar(mid, t.ratio, yerr=t.ratio_se, fmt="o", ms=5, color=DATA, lw=1.5)
a2.plot(mid, t.ratio_model, "-", color=MODEL, lw=2)
a2.axhline(1, color=MUTED, lw=1)
a2.set_ylabel("Parallax error, Earth-sense\nover opposite-sense orbits")
a2.set_xlabel("Orbital period (days)")
period_axis(a2)
fig.savefig(ROOT / "figures/handedness_by_period.png")

# Which element carries the sense
names = {"all free": ("sim_ko_none", DATA, "-"), "e fixed": ("sim_ko_e", "#1baf7a", "-"), "P fixed": ("sim_ko_P", MODEL, "-"), "P, T and e fixed": ("sim_ko_all", "#6250d6", "--")}
edges = [100, 150, 170, 200, 250, 300, 340, 390, 450, 500, 600, 700, 800, 900, 1000, 1300, 1600, 3000]
fig, ax = plt.subplots(figsize=(7.2, 3.6))
for k, (f, c, ls) in names.items():
    d = pd.read_parquet(f"{hd.RUNS}/{f}.parquet", columns=["P", "s_plx_plus", "s_plx_minus"])
    y = [np.nanmedian(d[(d.P >= a) & (d.P < b)].s_plx_plus) / np.nanmedian(d[(d.P >= a) & (d.P < b)].s_plx_minus) for a, b in zip(edges[:-1], edges[1:])]
    ax.plot(np.sqrt(np.array(edges[:-1]) * np.array(edges[1:])), y, ls, color=c, lw=2, label=k)
ax.axhline(1, color=MUTED, lw=1)
ax.set_ylabel("Parallax error ratio, model")
ax.set_xlabel("Orbital period (days)")
period_axis(ax)
ax.set_xlim(100, 3000)
ax.legend(ncols=2, loc="upper right")
fig.savefig(ROOT / "figures/which_element.png")

# The channel: A against the margin over the parallax cut
a = load(True)
a = a[a.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"]) & (a.period >= 600) & (a.period < 900)].copy()
ref = a[a.sense < 0].groupby(pd.cut(a[a.sense < 0].phot_g_mean_mag, np.arange(5, 19)), observed=True).parallax_error.median()
a["m"] = a.parallax / pd.cut(a.phot_g_mean_mag, np.arange(5, 19)).map(ref).astype(float) * a.period / 20000
f = pd.read_parquet(f"{hd.RUNS}/sim_field2.parquet")
f = f[(f.P >= 600) & (f.P < 900)]
f = f.assign(m=f.plx / f.s_plx_minus * f.P / 20000)
bins = [(0, 1.5), (1.5, 2.5), (2.5, 5), (5, 10), (10, 1e9)]
labels = ["< 1.5", "1.5–2.5", "2.5–5", "5–10", "> 10"]
ya, ye, ym = [], [], []
for lo, hi in bins:
    x, s = a[(a.m >= lo) & (a.m < hi)], f[(f.m >= lo) & (f.m < hi)]
    ya.append(x.sense.mean())
    ye.append(np.sqrt((1 - x.sense.mean() ** 2) / len(x)))
    ym.append((s.acc_plus.sum() - s.acc_minus.sum()) / (s.acc_plus.sum() + s.acc_minus.sum()))
fig, ax = plt.subplots(figsize=(6.2, 3.4))
ax.errorbar(range(5), ya, yerr=ye, fmt="o", ms=6, color=DATA, lw=1.5, label="Gaia DR3, held-out, P 600–900 d")
ax.plot(range(5), ym, "-", color=MODEL, lw=2, label="forward model")
ax.axhline(0, color=MUTED, lw=1)
ax.set_xticks(range(5), labels)
ax.set_xlabel("Margin over the cut ϖ/σ > 20000/P, with an error blind to sense")
ax.set_ylabel("Handedness A")
ax.legend(loc="lower right")
fig.savefig(ROOT / "figures/channel_margin.png")

# Wide pairs against the registered threshold
j = json.loads((ROOT / "work/final_heldout.json").read_text())
b = [x for x in j["wb_bins"] if x["N"] >= 500]
fig, ax = plt.subplots(figsize=(6.2, 3.2))
xs = [np.sqrt(x["lo"] * x["hi"]) for x in b]
ax.errorbar(xs, [100 * x["Dz"] for x in b], yerr=[100 * x["Dz_se"] for x in b], fmt="o", ms=6, color=DATA, lw=1.5)
ax.axhline(0, color=MUTED, lw=1)
ax.set_xscale("log")
ax.set_xlabel("Projected separation (au)")
ax.set_ylabel("Galactic dipole $D_Z$ (%)\n(below 0: prograde)")
fig.savefig(ROOT / "figures/wide_pairs_dipole.png")
print("ok")
