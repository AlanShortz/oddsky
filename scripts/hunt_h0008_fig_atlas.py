"""H-0008: figure of the two candidates' ATLAS + ZTF + NEOWISE light curves with the parallax point-lens fit
(work/atlas_fit_<k>.csv and atlas_fits.json from hunt_h0008_atlas_fit.py), and the residuals. J180624 (blend fractions
well measured) is shown as the source's magnification, (flux ratio - 1 + fs) / fs per series, so one curve fits all. J183040's
blend fraction is unconstrained (the ATLAS referee), so it is shown as observed flux ratios with no adopted model.
Output: figures/candidates_atlas.png, and one panel per case as cases/<case>/figures/event.png."""

import os

import matplotlib

matplotlib.use("Agg")
import json  # noqa: E402

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from astropy.time import Time  # noqa: E402

from oddsky.analysis.lensing import Problem  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hunts", "H-0008")
FITS = json.load(open(os.path.join(ROOT, "work", "atlas_fits.json")))
COORD = {"J180624": (271.603281, -9.069857), "J183040": (277.670788, -22.163984)}
MAGNIFY = {"J180624": True, "J183040": False}
CASES = {"J180624": "OS-0018", "J183040": "OS-0019"}
NAMES = {"J180624": "J180624.78-090411.4", "J183040": "J183040.98-220950.3"}
COL = {"ATLAS_o": "#e08a2c", "ATLAS_c": "#2aa1b3", "ZTF_g": "#2e9e44", "ZTF_r": "#c0392b", "ZTF_i": "#7f3c8d",
       "NEOWISE_W1": "#2836d9", "NEOWISE_W2": "#d6338a"}


def draw(k, ax, rx):
    name = NAMES[k]
    d = pd.read_csv(os.path.join(ROOT, "work", f"atlas_fit_{k}.csv"))
    d = d[(d.t > 59550) & (d.t < 60150)]
    fp = FITS[k]["parallax"]
    for g, s in d.groupby("g"):
        key = next(c for c in COL if g.startswith(c))
        fs = fp["fs"][g] if MAGNIFY[k] else 1.0
        ax.errorbar(Time(s.t, format="mjd").datetime, (s.f - 1 + fs) / fs, s.e / fs, fmt="o", ms=3 if "NEOWISE" not in g else 6,
                    lw=0.6, color=COL[key], label=key, alpha=0.8, zorder=3 if "NEOWISE" in g else 2)
        if MAGNIFY[k]:
            rx.plot(Time(s.t, format="mjd").datetime, (s.f - s.model) / s.e, "o", ms=2, color=COL[key], alpha=0.7)
    if not MAGNIFY[k]:
        rx.text(0.5, 0.5, "no adopted model: tE and the blend are unconstrained", transform=rx.transAxes, ha="center",
                va="center", fontsize=8)
    grid = np.arange(59550, 60150, 1.0)
    pr = Problem(grid, np.ones_like(grid), np.ones_like(grid), np.array(["x"] * len(grid)), ra=COORD[k][0], dec=COORD[k][1],
                 parallax=True, blend=False, t0par=fp["t0par"])
    if MAGNIFY[k]:
        ax.plot(Time(grid, format="mjd").datetime, pr.model([fp["t0"], fp["tE"], fp["u0"], *fp["piE"]]), color="k", lw=1.0,
                zorder=4, label="point lens")
    h, lab = ax.get_legend_handles_labels()
    keep = dict(zip(lab, h, strict=True))
    ax.legend(keep.values(), keep.keys(), fontsize=7, loc="upper left", frameon=False)
    ax.set_title(name, fontsize=10)
    ax.set_ylabel("source magnification" if MAGNIFY[k] else "flux / baseline")
    rx.axhline(0, color="k", lw=0.5)
    rx.set_ylim(-6, 6)
    rx.set_ylabel("residual (σ)")
    rx.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    rx.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

fig, axes = plt.subplots(2, 2, figsize=(12, 6.4), gridspec_kw={"height_ratios": [3, 1]}, sharex="col")
for col, k in enumerate(NAMES):
    draw(k, axes[0, col], axes[1, col])
fig.suptitle("H-0008: J180624, a microlensing event (point lens with annual parallax, blending per series), and J183040, "
             "a candidate", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(ROOT, "figures", "candidates_atlas.png"), dpi=130)

for k, case in CASES.items():
    f1, (ax, rx) = plt.subplots(2, 1, figsize=(7, 5.6), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    draw(k, ax, rx)
    f1.suptitle(f"{case}: ATLAS, ZTF and NEOWISE" + (", point lens with annual parallax" if MAGNIFY[k] else ""), fontsize=10)
    f1.tight_layout()
    f1.savefig(os.path.join(ROOT, "..", "..", "cases", case, "figures", "event.png"), dpi=130)
