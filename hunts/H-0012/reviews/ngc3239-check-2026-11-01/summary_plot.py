"""One-panel summary: everything measured at the position vs time (log flux density)."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
HERE = Path(__file__).resolve().parent
lc = pd.read_csv(HERE / "wise_lc.csv")
H = json.load(open(HERE / "hst_diff.json"))["phot"]
J = json.load(open(HERE / "jwst_check.json"))
S = json.load(open(HERE / "spitzer_check.json"))["measured"]
A = json.load(open(HERE / "atlas_check.json"))
fig, ax = plt.subplots(figsize=(10, 5))
for b, c in ((1, "C0"), (2, "C3")):
    g = lc[lc.band == b]
    det = g.uJy > 3 * g.e_uJy
    ax.errorbar(g.mjd[det], g.uJy[det], g.e_uJy[det], fmt="o", color=c, label=f"WISE W{b} (difference)")
    ax.plot(g.mjd[~det], np.maximum(g.uJy[~det], 0) + 3 * g.e_uJy[~det], "v", color=c, alpha=0.35, ms=5)
t21, t22, t25 = 59261.8, 59925.0, 60684.6
ax.errorbar([t21], [H["DIFF F606W21-ACSF606W22"]["flux_uJy"]], [H["DIFF F606W21-ACSF606W22"]["err"]], fmt="s", color="g", label="HST F606W")
ax.errorbar([t21], [H["DIFF F814W21-F814W25"]["flux_uJy"]], [H["DIFF F814W21-F814W25"]["err"]], fmt="D", color="darkred", label="HST F814W")
ax.plot([t22], [max(H["ACS_F606W_2022"]["flux_uJy"], 0) + 3 * H["ACS_F606W_2022"]["err_stat"]], "v", color="g", ms=8)
ax.plot([t25], [3 * H["F555W_2025"]["err_local"]], "v", color="limegreen", ms=8, label="HST F555W 2025 (3$\\sigma$)")
ax.plot([t25], [3 * H["F814W_2025"]["err_stat"]], "v", color="darkred", ms=8)
for k, m, c in (("F300M_2024-04", "^", "purple"), ("F300M_2024-05", "^", "purple"), ("F335M_2024-04", "*", "m")):
    ax.plot([60424.4 if "04" in k else 60452.3], [J[k]["flux_uJy"]], m, color=c, ms=10, label=f"JWST {k[:5]}" if "05" not in k else None)
ax.plot([60424.4, 60452.3], [J["F150W_2024-04"]["lim3_uJy"], J["F150W_2024-05"]["lim3_uJy"]], "v", color="orange", ms=8, label="JWST F150W (3$\\sigma$)")
ax.plot([54461], [3 * S["irac1"]["err_conf_uJy"] + max(S["irac1"]["flux_uJy"], 0)], "v", color="C0", ms=9, mfc="none", label="Spitzer 2008 3.6/4.5 um (3$\\sigma$)")
ax.plot([54461], [3 * S["irac2"]["err_conf_uJy"] + max(S["irac2"]["flux_uJy"], 0)], "v", color="C3", ms=9, mfc="none")
for k, v in A["o"].items():
    if v and "baseline" not in k:
        ax.plot([np.mean(v["mjd_range"])], [v["lim3_uJy"]], "v", color="gold", alpha=0.7, ms=6)
ax.plot([], [], "v", color="gold", label="ATLAS o window (3$\\sigma$)")
ax.axvspan(58967.3, 59176.4, color="r", alpha=0.07)
ax.set_yscale("log"); ax.set_ylim(0.02, 1000); ax.set_xlim(54200, 61100)
ax.set_xlabel("MJD"); ax.set_ylabel("flux density (uJy)")
sec = ax.secondary_xaxis("top", functions=(lambda m: 1858.87 + m / 365.25, lambda y: (y - 1858.87) * 365.25)); sec.set_xlabel("year")
ax.legend(fontsize=7, ncol=2, loc="upper left")
ax.set_title("NGC 3239 156.29122 +17.16378: WISE transient, HST 2021 counterpart, JWST 2024 dust source (independent check)", fontsize=9)
fig.tight_layout(); fig.savefig(HERE / "summary.png", dpi=110)
