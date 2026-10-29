"""H-0007 figure for J193353.06-211813.4: NEOWISE single exposures 2014-2024; ATLAS nightly 2020 with the point-lens fit,
NEOWISE and the ZTF tail; ZTF r June-July of every year (2020 against the other seasons)."""

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.time import Time

RA, DEC, CNTR = 293.471115, -21.3037472, 2938021301351037214
d = pd.read_parquet(f"{__import__('os').path.expanduser('~')}/oddsky-runs/h0007/faint/exp/{CNTR}.parquet")
d["sep"] = 3600 * np.hypot((d.ra - RA) * np.cos(np.radians(DEC)), d.dec - DEC)
d = d[(d.sep < 2.5) & (d.qual_frame > 0) & (d.nb == 1) & (d.cc_flags.astype(str).str.zfill(4).str[:2] == "00")]
d["yr"] = Time(d.mjd.values, format="mjd").decimalyear
z = pd.read_csv("hunts/H-0007/work/ztf_J193353.csv")
z = z[z.catflags == 0].copy()
z["d"] = z.mag - z.groupby("filtercode").mag.transform("median")
z["year"] = Time(z.mjd.values, format="mjd").decimalyear
z["doy"] = (z.year % 1) * 365.25
fig, ax = plt.subplots(1, 3, figsize=(20, 5), gridspec_kw={"width_ratios": [3, 3, 2]})
ax[0].plot(d.yr, d.w1mpro, ".", ms=3, label="W1 (single exposures)")
ax[0].plot(d.yr, d.w2mpro + 0.5, ".", ms=3, label="W2 + 0.5")
ax[0].invert_yaxis()
ax[0].set_xlabel("year")
ax[0].set_ylabel("mag")
ax[0].legend(fontsize=8)
ax[0].set_title("J193353.06-211813.4 (Gaia DR3 6772245406602788608): NEOWISE 2014-2024")
a = pd.read_csv("hunts/H-0007/work/atlas_J193353_nightly.csv")
a = a[(a.mjd > 58880) & (a.mjd < 59160)]
for F, col in (("o", "darkorange"), ("c", "teal")):
    g = a[a.F == F]
    ax[1].plot(g.mjd, g.A, "o", ms=4, color=col, label=f"ATLAS {F} (nightly)")
m = a.sort_values("mjd")
tt = np.linspace(58880, 59160, 600)
t0, tE, u0 = 58925.6, 62.7, 0.434
uu = np.sqrt(u0**2 + ((tt - t0) / tE) ** 2)
ax[1].plot(tt, (uu**2 + 2) / (uu * np.sqrt(uu**2 + 4)), "k-", lw=1, label="point lens, no parallax (leaves an asymmetry; see J193353.md)")
ax[1].plot([58949.4], [1.98], "*", ms=16, color="crimson", label="NEOWISE W1 = W2 (Apr 9-10)")
ax[1].plot([59018.4, 59048.0], [10 ** (0.4 * 0.17), 10 ** (0.4 * 0.09)], "s", ms=7, color="purple", label="ZTF r, comparison-corrected")
ax[1].set_xlabel("MJD (2020)")
ax[1].set_ylabel("flux / baseline")
ax[1].legend(fontsize=8)
ax[1].set_title("2020: ATLAS, NEOWISE and ZTF")
for yr in range(2018, 2026):
    w = z[(z.year // 1 == yr) & (z.doy > 150) & (z.doy < 215) & (z.filtercode == "zr")]
    if len(w):
        ax[2].plot(w.doy, w.d, "o-" if yr == 2020 else ".", ms=5 if yr == 2020 else 3,
                   color="crimson" if yr == 2020 else "0.6", label="2020" if yr == 2020 else (None if yr > 2018 else "2018-2025"))
ax[2].axvline(Time("2020-04-10").decimalyear % 1 * 365.25, color="crimson", ls=":", label="NEOWISE visit (Apr 10)")
ax[2].invert_yaxis()
ax[2].set_xlim(90, 215)
ax[2].set_xlabel("day of year")
ax[2].set_ylabel("ZTF r minus its median (mag)")
ax[2].legend(fontsize=8)
ax[2].set_title("ZTF r in June-July: 2020 against every other year")
plt.tight_layout()
plt.savefig("hunts/H-0007/figures/J193353.png", dpi=90)
