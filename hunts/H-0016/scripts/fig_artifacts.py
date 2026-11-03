"""H-0016 figure: (a) AllWISE aperture-minus-profile magnitude against the catalogue step, for the clean stellar candidates, coloured
by the unWISE image verdict; (b) measured unWISE flux ratio R against the ratio a real step predicts."""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[1]
v = pd.read_csv(Path.home() / "oddsky-runs/h0016/steps_unwise_verdict.csv")
m = pd.read_csv(Path.home() / "oddsky-runs/h0016/steps_master.csv")[["designation", "w1mag", "w1mpro", "w1snr"]]
x = v.merge(m, on="designation")
w = pd.read_csv(Path.home() / "oddsky-runs/h0016/steps_wide_unwise_verdict.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
col = {"REAL in images": "C3", "catalogue artifact": "C0", "partial": "C1"}
for k, g in x.groupby("verdict"):
    ax[0].scatter(g.d1, g.w1mag - g.w1mpro, c=col.get(k, "k"), s=28, label=f"{k} ({len(g)})")
ax[0].plot([-2, 1.5], [2, -1.5], "k:", lw=0.8, label="aperture = NEOWISE")
ax[0].axhline(0, color="k", lw=0.5)
ax[0].set_xlabel("catalogue step  W1(NEOWISE 2014-15) − W1(AllWISE profile fit)  [mag]")
ax[0].set_ylabel("AllWISE aperture − profile-fit W1  [mag]")
ax[0].set_title("Clean, isolated stars with a > 0.4 mag step", fontsize=10)
ax[0].legend(fontsize=8)
allv = pd.concat([x.assign(src="main"), w.assign(src="wide").replace({"verdict": {"REAL": "REAL in images", "artifact": "catalogue artifact"}})])
for k, g in allv.groupby("verdict"):
    ax[1].scatter(g.R_pred, (g.w1_R + g.w2_R) / 2, c=col.get(k, "k"), s=28, label=f"{k} ({len(g)})")
ax[1].plot([0.2, 2.6], [0.2, 2.6], "k:", lw=0.8, label="real step")
ax[1].axhline(1, color="k", lw=0.5)
ax[1].set_xscale("log")
ax[1].set_yscale("log")
ax[1].set_xlabel("flux ratio 2010 coadd / 2010-2020 coadd predicted from the catalogue step")
ax[1].set_ylabel("measured in unWISE images (W1, W2 mean)")
ax[1].set_title("Image test of every clean stellar step", fontsize=10)
ax[1].legend(fontsize=8)
fig.tight_layout()
fig.savefig(HERE / "figures" / "allwise_artifacts.png", dpi=120)
print("saved")
