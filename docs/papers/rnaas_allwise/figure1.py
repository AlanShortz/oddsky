"""Figure 1 of the AllWISE profile-fit note, from the tables in this directory. Run from the repo root."""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from oddsky.data.allwise import expected_w1snr  # noqa: E402

D = "docs/papers/rnaas_allwise/"
stars = pd.read_csv(D + "dbf_48_unflagged_stars.csv")
listed = pd.read_csv(D + "dbf_631_listed_sources.csv")
control = pd.read_csv(D + "data/control_cone.csv")
control = control[control.nb == 1]
rej = pd.read_csv(D + "data/reject_entries_48.csv")
cat = pd.read_csv(D + "data/catalog_tiles_48.csv").set_index("designation")
neo = rej.target.map(stars.set_index("designation").w1_neowise)
dup = set(rej[(rej.w1snr > 25) & ((rej.w1mpro - neo).abs() < 0.25) & (rej.sep < 5) & (rej.coadd_id == rej.target.map(cat.coadd_id))].target)
stars["dup"] = stars.designation.isin(dup)

LABEL = {"catalog error, close pair": "catalog error, second Gaia star within 8.5″", "catalog error, isolated": "catalog error, none within 8.5″",
         "real change": "real change"}
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.4))
x, y = stars.w1_neowise_minus_allwise, stars.w1mag - stars.w1mpro
style = {"catalog error, close pair": ("s", "tab:orange"), "catalog error, isolated": ("o", "tab:blue"), "real change": ("*", "tab:red")}
for k, (mk, col) in style.items():
    m = stars.klass == k
    a.scatter(x[m], y[m], marker=mk, c=col, s=110 if mk == "*" else 38, zorder=3, label=f"{LABEL[k]} ({m.sum()})")
m = stars.dup
a.scatter(x[m], y[m], marker="o", facecolors="none", edgecolors="k", s=120, linewidths=0.9, zorder=4,
          label=f"correct duplicate in the Reject Table ({m.sum()})")
a.plot([-2, 1.5], [-2, 1.5], "k:", lw=1, label="aperture = NEOWISE")
a.axhline(0, color="k", lw=0.6)
a.set_xlabel("W1(NEOWISE 2014–15) − W1(AllWISE profile fit)  [mag]")
a.set_ylabel("AllWISE aperture − profile-fit W1  [mag]")
a.legend(fontsize=8, loc="upper left")
a.set_title("(a)", loc="left", fontsize=10)

err, real = stars[stars.klass != "real change"], stars[stars.klass == "real change"]
b.scatter(control.w1mpro, control.w1snr, s=5, c="0.6", label=f"control sample ({len(control)})")
b.scatter(listed.w1mpro, listed.w1snr, s=7, c="tab:orange", alpha=0.7, label=f"listed sources ({len(listed)})")
b.scatter(err.w1mpro, err.w1snr, s=38, c="tab:blue", zorder=3, label=f"the {len(err)} catalog errors")
b.scatter(real.w1mpro, real.w1snr, marker="*", s=110, c="tab:red", zorder=3, label=f"the {len(real)} real changes")
w = np.linspace(8, 14.5, 100)
b.plot(w, [0.5 * expected_w1snr(v) for v in w], "k--", lw=1, label="half the median SNR")
b.set_xlabel("AllWISE profile-fit W1  [mag]")
b.set_ylabel("profile-fit W1 signal-to-noise (w1snr)")
b.set_ylim(0, 55)
b.legend(fontsize=8, loc="center left")
b.set_title("(b)", loc="left", fontsize=10)
fig.tight_layout()
fig.savefig(D + "figure1.png", dpi=200)
fig.savefig(D + "figure1.pdf")
print("duplicates ringed:", int(stars.dup.sum()))
