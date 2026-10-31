"""r12: figure. Top rows: light curves as flux ratio to baseline (ATLAS o/c nightly, PSF-corrected against the baseline at the
event-season PSF; NEOWISE W1/W2 visits; Gaia DR3 G transits). Bottom row: flag fractions of the event visit for known lenses
against strong unexplained events (r9). Colours: validated categorical palette; marker shapes carry identity as well."""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, HERE, neowise, targets  # noqa: E402

C = {"o": "#eb6834", "c": "#1baf7a", "W1": "#2a78d6", "W2": "#e87ba4", "G": "#eda100"}
MK = {"o": "o", "c": "s", "W1": "D", "W2": "v", "G": "*"}
T = targets()
plt.rcParams.update({"font.size": 8, "axes.edgecolor": "#888", "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.5})
fig, axes = plt.subplots(3, 3, figsize=(13, 10.5))
PAN = [("J174401", (59100, 59850)), ("J025145", (58400, 60300)), ("J064439", (58600, 59700)), ("J185035", (57600, 59300)),
       ("J170153", (56900, 57900)), ("J182621", (58700, 59200))]


def atlas_ratio(k, F):
    nt = pd.read_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"))
    d = nt[(nt.F == F) & nt.ubase.notna()].copy()
    if k == "J174401":  # 01a pre-2020 baseline taken with a wide PSF: use 02a-04a as the common baseline (370 / 118 uJy)
        b = 370.0 if F == "o" else 118.0
        d["r"] = (d.ujy - (d.exc - d.exc_psf)) / b
        d.loc[d.cam == "01a", "r"] = (d.ujy[d.cam == "01a"] + 200.9 * (d.maj[d.cam == "01a"] - 2.5) * (F == "o")) / b
        return d
    d["r"] = 1 + d.exc_psf / d.ubase
    return d


for ax, (k, (t0, t1)) in zip(axes.flat[:6], PAN, strict=True):
    t = T[k]
    for F in ("o", "c"):
        d = atlas_ratio(k, F)
        d = d[(d.t > t0) & (d.t < t1)]
        err = d.ujy_err / (370.0 if (k == "J174401" and F == "o") else 118.0) if k == "J174401" else d.e2 / d.ubase.abs().clip(lower=1)
        ax.errorbar(d.t, d.r, yerr=err, fmt=MK[F], ms=3, color=C[F], elinewidth=0.5, alpha=0.8,
                    label=f"ATLAS {F}")
    lc = neowise(k, t, raw=True)
    blk = (lc.t >= t["t_first"] - 1) & (lc.t <= t["t_last"] + 1)
    for b in ("w1", "w2"):
        r = 10 ** (-0.4 * (lc[b] - np.median(lc[b][~blk])))
        sel = (lc.t > t0) & (lc.t < t1)
        ax.plot(lc.t[sel], r[sel], MK[b.upper()], ms=7, color=C[b.upper()], mec="white", mew=0.8, label=b.upper(), zorder=5)
    ax.axvline(t["tvis"], color="#999", lw=0.8, ls=":")
    ax.set_title(f"{t['name']} (G {t['G']:.1f})", fontsize=9)
    ax.set_xlabel("MJD")
    ax.set_ylabel("flux / baseline")
    ax.legend(fontsize=6.5, loc="upper left", frameon=False)
# Gaia DR3 cases
ax = axes.flat[6]
for k, sid, col in (("J172057", 5959812622743175552, None), ("J180402", 4143495279954502016, None)):
    t = T[k]
    g = pd.read_csv(os.path.join(DATA, f"r4_gaia_{sid}.csv"))
    g = g[(g.band == "G") & (g.flag != "rejected_by_photometry") & np.isfinite(g.mag)]
    r = 10 ** (-0.4 * (g.mag - g.mag.median()))
    lc = neowise(k, t, raw=True)
    rw = 10 ** (-0.4 * (lc.w1 - lc.w1.median()))
    off = 0 if k == "J172057" else 6
    lab = "J172057 (Gaia 0.59\" source)" if k == "J172057" else "J180402 (+6 offset)"
    ax.plot(g.t_mjd - t["tvis"], r + off, MK["G"], ms=7, color=C["G"], label=f"Gaia G, {lab}")
    ax.plot(lc.t - t["tvis"], rw + off, MK["W1"], ms=6, color=C["W1"], mec="white", label=f"W1, {k}")
ax.set_xlim(-300, 300)
ax.set_xlabel("days from the NEOWISE peak visit")
ax.set_ylabel("flux / median")
ax.set_title("Gaia DR3 epoch photometry (2015 events)", fontsize=9)
ax.legend(fontsize=6.5, frameon=False)
# flag histograms
p = os.path.join(DATA, "r9_metrics.csv")
if os.path.exists(p):
    m = pd.read_csv(p)
    for ax, (col, lab) in zip(axes.flat[7:9], (("frac_hd_ev", "share of event frames flagged h/d"),
                                                ("frac_nb_ev", "share of event frames deblended (nb > 1)")), strict=True):
        bins = np.linspace(0, 1, 11)
        for grp, cc, hatch in (("known", C["W1"], None), ("strong", C["o"], "//")):
            x = m[m.grp == grp][col].dropna()
            ax.hist(x, bins=bins, histtype="step", lw=2, color=cc, hatch=hatch,
                    label=f"{'known lenses' if grp == 'known' else 'strong unexplained'} (n {len(x)})", density=False)
        ax.set_xlabel(lab)
        ax.set_ylabel("events")
        ax.legend(fontsize=7, frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "r12_figure.png"), dpi=130)
print("wrote r12_figure.png")
