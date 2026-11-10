"""Figures for the H-0019 dossier. Cobalt = stars above the tip (the measurement); orange = Magellanic Cloud reference;
grey = controls. One axis per panel, direct labels."""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parents[1]
FIG = HERE / "figures"; FIG.mkdir(exist_ok=True)
COBALT, ORANGE, GREY, INK = "#2836d9", "#c2570c", "#6b7280", "#1f2430"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#9aa0a6",
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "savefig.dpi": 170, "savefig.bbox": "tight"})
gal = pd.read_csv(HERE / "work/galaxies.csv"); tests = json.loads((HERE / "work/tests.json").read_text())
ref = tests["reference"]["E03"]

# Figure 1: one number per galaxy
g = gal.sort_values("E03").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(7.2, 0.33 * len(g) + 1.6))
y = np.arange(len(g))
clean = g.sd_long_rgb < 0.05
ax.axvspan(tests["T1"]["E03"] - tests["T1"]["se"], tests["T1"]["E03"] + tests["T1"]["se"], color=COBALT, alpha=0.10, lw=0)
for name, v in (("LMC", ref["lmc"]), ("SMC", ref["smc"])):
    ax.axvline(v, color=ORANGE, lw=1.2); ax.text(v + 0.0008, -0.75, name + " (OGLE)", color=INK, ha="left", va="center", fontsize=8.5)
ax.axvline(0, color="#9aa0a6", lw=0.8)
ax.errorbar(g.E03[clean], y[clean], xerr=g.eE03[clean], fmt="o", color=COBALT, ms=6, lw=1.5, label="clean fields (control scatter < 0.05 mag)")
ax.errorbar(g.E03[~clean], y[~clean], xerr=g.eE03[~clean], fmt="o", mfc="#fcfcfb", color=COBALT, ms=6, lw=1.5, label="crowded or noisy fields")
ax.set_yticks(y); ax.set_yticklabels([f"{n}  ({int(k)} stars)" for n, k in zip(g.name, g.n_long_agb)])
ax.set_xlabel("excess fraction changing by more than 0.3 mag between two visits\n(stars 0-1 mag above the red-giant tip, minus stars just below it)")
ax.legend(frameon=False, loc="center right", fontsize=8.5); ax.set_ylim(-1.2, len(g) - 0.4)
ax.set_title("Two Hubble visits per star, 100 days to 13 years apart (band: all galaxies pooled)", loc="left", color=INK, fontsize=10.5)
fig.savefig(FIG / "fig1_excess_by_galaxy.png"); plt.close(fig)

CLEAN = set(gal.name[gal.sd_long_rgb < 0.05])
# Figure 2: the distribution of the change, above and below the tip, against the Clouds
import glob
P = pd.concat([pd.read_parquet(f).assign(gal=pathlib.Path(f).stem) for f in glob.glob(str(HERE / "work/pairs/*.parquet"))
               if pathlib.Path(f).stem.replace("_", " ") in CLEAN or pathlib.Path(f).stem in CLEAN])
xs = np.linspace(0.1, 1.2, 60)
fig, ax = plt.subplots(figsize=(6.6, 4.2))
def tail(d): return [(np.abs(d) > x).mean() for x in xs]
L = P[P.kind == "long"]; S = P[P.kind == "short"]
ax.plot(xs, tail(L[L.box == "agb"].d), color=COBALT, lw=2); ax.plot(xs, tail(L[L.box == "rgb"].d), color=GREY, lw=2)
ax.plot(xs, tail(S[S.box == "agb"].d), color=GREY, lw=1.2, ls=":")
import sys; sys.path.insert(0, str(HERE.parents[1] / "src"))
from oddsky.analysis import twopoint
for cloud, tip, ls in (("lmc", 14.60, "-"), ("smc", 15.00, "--")):
    pop = pd.read_csv(HERE / f"work/{cloud}_population.csv")
    mean, d = twopoint.simulate_two_visits(pop.I.values, pop[["P1", "P2", "P3"]].values, pop[["A1", "A2", "A3"]].values, 1000.0, seed=5)
    sel = (mean - tip >= -1) & (mean - tip < 0)
    ax.plot(xs, [(np.abs(d[sel]) > x).mean() for x in xs], color=ORANGE, lw=1.4, ls=ls)
    ax.text(1.0, (np.abs(d[sel]) > 1.0).mean() * (1.25 if cloud == "lmc" else 0.62), f"{cloud.upper()}, above tip" + (" (dashed)" if cloud == "smc" else ""), color=ORANGE, fontsize=8.5)
ax.set_yscale("log"); ax.set_ylim(5e-4, 0.5); ax.set_xlim(0.1, 1.2)
ax.text(0.62, tail(L[L.box == "agb"].d)[28] * 1.6, "Hubble, above the tip, visits > 100 d apart", color=COBALT, fontsize=9)
ax.text(0.30, 1.5e-3, "Hubble, just below the tip, same images (grey)", color=INK, fontsize=9)
ax.text(0.12, 7e-4, "above the tip, visits < 10 d apart (dotted)", color=INK, fontsize=8.5)
ax.set_xlabel("change between two visits exceeds x (mag)"); ax.set_ylabel("fraction of stars")
ax.set_title(f"Clean fields pooled: {', '.join(sorted(CLEAN))}", loc="left", color=INK, fontsize=10)
fig.savefig(FIG / "fig2_change_distribution.png"); plt.close(fig)

# Figure 3: rediscovery in M33
r = pd.read_csv(HERE / "work/rediscovery_m33.csv"); rj = json.loads((HERE / "work/rediscovery_m33.json").read_text())
fig, ax = plt.subplots(figsize=(6.6, 3.8))
ax.scatter(r.amp, r.d.abs(), s=28, color=COBALT, edgecolor="#fcfcfb", lw=0.8, zorder=3)
a = np.linspace(0.6, r.amp.max() + 0.1, 20)
ax.plot(a, a, color=GREY, lw=1); ax.text(a[-1], a[-1], " largest possible\n (peak to peak)", color=INK, fontsize=8.5, va="top", ha="right")
ax.axhline(0.3, color=GREY, lw=0.8, ls=":"); ax.text(a[0], 0.33, "0.3 mag", color=INK, fontsize=8.5)
ax.set_xlabel("published I amplitude of the Mira, peak to peak (Yuan+ 2017)"); ax.set_ylabel("|change| between two Hubble visits (mag)")
ax.set_title(f"M33: {rj['n_used']} published Miras, never shown to the pipeline. {rj['x0.3']['observed']} change by > 0.3 mag\n"
             f"(one sinusoid of the published amplitude predicts {rj['x0.3']['expected_frac']*rj['n_used']:.0f} ± {rj['x0.3']['expected_sd']*rj['n_used']:.0f}; other stars of the same brightness: {rj['x0.3']['control_frac']*100:.1f}%)",
             loc="left", color=INK, fontsize=9.5)
fig.savefig(FIG / "fig3_m33_rediscovery.png"); plt.close(fig)
print("figures written")
