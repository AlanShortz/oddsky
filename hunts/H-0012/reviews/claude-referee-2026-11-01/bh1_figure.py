"""Figure: BH1's 2010 -> NEOWISE statistic against 1,392 / 1,376 real sources and 713 positions near
BH1 (same method), and BH1's WISE light curve against the published Spitzer IRAC changes.

    uv run python hunts/H-0012/reviews/claude-referee-2026-11-01/bh1_figure.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "bh1_step_test.json").read_text())
# Spitzer IRAC (Adams et al. 2017a Table 5; Basinger et al. 2021 Table 1), Vega mag -> uJy
ZP = {1: 280.9, 2: 179.7}
irac = {1: [(55769.9, 16.96), (56002.0, 17.49), (56742.6, 17.95), (57408.2, 18.67)],
        2: [(55769.9, 16.34), (56002.0, 16.68), (56916, 17.07), (56945, 17.26), (57281.9, 17.50), (57294.0, 17.35),
            (57322.1, 17.39), (57408.2, 17.42), (58381, 18.01)]}
fig, axs = plt.subplots(2, 2, figsize=(12, 7.5), facecolor="#fcfcfb")
for k, b in enumerate((1, 2)):
    ax = axs[0, k]
    s = np.array([x["dneo_sig"] for x in d["sources"][f"W{b}"]])
    g = np.array([x["dneo_sig"] for x in d["grid"][f"W{b}"]])
    bh = d["variants"]["pipeline"][f"W{b}"]["dneo_sig"]
    bins = np.arange(-11, 6, 0.5)
    ax.hist(s, bins, color="#2a78d6", alpha=0.7, label=f"{s.size} reference sources in the NGC 6946 window")
    ax.hist(g, bins, color="#eb6834", alpha=0.5, label=f"{g.size} positions within 2.5' of BH1")
    ax.axvline(bh, color="#0b0b0b", lw=2)
    ax.text(bh, ax.get_ylim()[1] * 0.9, f" BH1 {bh:+.1f}σ", fontsize=9)
    ax.set_yscale("log")
    ax.set_xlabel(f"W{b}: (NEOWISE mean − 2010-11 mean) / error")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax = axs[1, k]
    mjd = None
    lc = np.array(d["variants"]["pipeline"][f"W{b}"]["lc_ujy"])
    meta = json.loads((Path.home() / f"oddsky-runs/imaging/work/NGC6946/3090p605/w{b}/meta.json").read_text())
    mjd = np.array(meta["mjd"])
    ax.plot(1858.87 + mjd / 365.25, lc, "o-", color="#2a78d6", label=f"WISE W{b} at BH1 (H-0012 method), change since 2010")
    t, m = np.array(irac[b]).T
    fl = ZP[b] * 10 ** (-m / 2.5) * 1e6
    off = np.interp(55546, mjd, lc)  # none: Spitzer has no 2010 point; anchor its first epoch on the WISE curve
    ax.plot(1858.87 + t / 365.25, fl - fl[0] + np.interp(t[0], mjd, lc), "s", mfc="none", color="#eb6834",
            label=f"Spitzer IRAC {'3.6' if b == 1 else '4.5'} µm (Adams+17, Basinger+21), shifted to match at 2011.6")
    ax.axhline(0, color="#52514e", lw=0.6)
    ax.set_ylabel("µJy")
    ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(HERE / "bh1_step_test.png", dpi=130)
print("wrote", HERE / "bh1_step_test.png")
