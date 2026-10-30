"""r1: my own ATLAS reduction. Cuts, what each cut removes in and out of the event, nightly binning, per-season medians per
unit, and a full 2015-2026 plot (flux and PSF width) per unit. Writes r1_nightly_<k>.csv."""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import HERE, TARGETS, atlas_raw, clean, nightly  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)

for k, T in TARGETS.items():
    print("=" * 30, k, T["name"])
    r = atlas_raw(k)
    ev = np.abs(r.mjd - T["tpk"]) < 100
    print(f"raw c/o rows {len(r)}; within 100 d of peak {ev.sum()}")
    for lab, m in [("mag5sig<=17.5", r.mag5sig <= 17.5), ("chi/N>=10 (investigators)", r.chi_n >= 10),
                   ("maj>4", r.maj > 4)]:
        print(f"  cut {lab:28s}: removes {m[~ev].mean():.3f} of baseline rows, {m[ev].mean():.3f} of event rows")
    c_rel = clean(r, chi="rel")
    ev2 = np.abs(c_rel.mjd - T["tpk"]) < 100
    print(f"  my relative chi cut keeps {len(c_rel)} ({ev2.sum()} event rows of {ev.sum()})")
    nt = nightly(c_rel)
    nt.to_csv(os.path.join(HERE, f"r1_nightly_{k}.csv"), index=False)
    nt["season"] = np.floor(2000 + (nt.t - 51544.5) / 365.25).astype(int)  # calendar year (the gap is Dec-Jan)
    tab = nt[np.abs(nt.t - T["tpk"]) > 150].groupby(["F", "cam", "season"]).agg(
        nights=("ujy", "size"), med=("ujy", "median"), maj=("maj", "median"), apfit=("apfit", "median"), m5=("m5", "median"))
    # normalise each unit to its own 2023-2026 median (post-event, all four units present)
    ref = nt[(nt.t > 60100)].groupby(["F", "cam"]).ujy.median()
    tab["rel_post"] = [row.med / ref.get((F, c), np.nan) for (F, c, s), row in tab.iterrows()]
    print(tab.round(3).to_string())

    fig, ax = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for (F, cam), d in nt.groupby(["F", "cam"]):
        rr = ref.get((F, cam), np.median(d.ujy))
        ax[0].errorbar(d.t, d.ujy / rr, d.ujy_err / rr, fmt=".", ms=3, lw=0.5, label=f"{F} {cam}")
        ax[1].plot(d.t, d.maj, ".", ms=3)
    ax[0].set_ylim(0.4, 1.6 if k == "J183040" else 1.6)
    ax[0].set_ylabel("flux / unit's 2023-26 median")
    ax[0].legend(ncol=8, fontsize=7)
    ax[1].set_ylabel("PSF major axis (px)")
    ax[1].set_xlabel("MJD")
    ax[0].set_title(f"{T['name']} ATLAS nightly (referee reduction); event clipped at 1.6")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, f"r1_baseline_{k}.png"), dpi=110)
