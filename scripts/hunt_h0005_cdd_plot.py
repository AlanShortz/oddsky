"""Hunt H-0005: Gaia20cdd (Gaia DR3 1624711296862985472) light curve, 2014-2026: ZTF g/r/i (catflags = 0), Gaia alert G
and ATLAS o, each as depth below its own median. Inputs in hunts/H-0005/data/; writes figures/Gaia20cdd_lightcurve.png.
"""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

D = Path("hunts/H-0005/data")


def year(mjd):
    return (mjd - 51544.5) / 365.25 + 2000


z = pd.read_csv(D / "Gaia20cdd_ztf.csv")
z = z[z.flag.isna()].copy()
z["d"] = z.mag - z.groupby("band").mag.transform("median")
g = pd.read_csv(D / "Gaia20cdd_gaia_alerts.csv", skiprows=1)
g.columns = ["date", "jd", "mag"]
g["mag"] = pd.to_numeric(g.mag, errors="coerce")
g = g.dropna().assign(t_mjd=lambda x: x.jd - 2400000.5)
g["d"] = g.mag - g.mag.median()
a = pd.read_csv(D / "Gaia20cdd_atlas.csv")
a = a[(a.flag.fillna("") == "") & (a.band == "ATLAS_o")].copy()
a["d"] = a.mag - a.mag.median()

series = [("ZTF g", z[z.band == "ZTF_g"], "#2a78d6", "o", 6), ("ZTF r", z[z.band == "ZTF_r"], "#eb6834", "s", 6),
          ("ZTF i", z[z.band == "ZTF_i"], "#1baf7a", "^", 6), ("ATLAS o", a, "#eda100", "P", 7),
          ("Gaia G", g, "#6250d6", "D", 16)]
fig, ax = plt.subplots(figsize=(12, 4.4), dpi=160)
for name, d, c, m, size in series:
    ax.scatter(year(d.t_mjd), d.d, s=size, c=c, marker=m, lw=0, label=name, zorder=3 if name == "Gaia G" else 2)
ax.set_ylim(3.9, -0.4)
ax.set_xlim(2014.6, 2027.0)
ax.grid(axis="y", color="#e5e5e5", lw=0.6)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
ax.set_xlabel("year")
ax.set_ylabel("magnitudes below median")
ax.set_title("Gaia20cdd (Gaia DR3 1624711296862985472): an old K dwarf with warm dust that keeps going dark",
             loc="left", fontsize=11)
ax.legend(frameon=False, ncol=5, loc="lower left", fontsize=8)
fig.text(0.01, 0.005, "Events before 2016 (CRTS 2007-2016, Pan-STARRS 2010-2014) are in the referee report. A 392.2-day period "
         "we proposed was retracted. Data: ZTF DR via IRSA, ATLAS forced photometry, Gaia Science Alerts.",
         fontsize=6.5, color="#666")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig("hunts/H-0005/figures/Gaia20cdd_lightcurve.png")
