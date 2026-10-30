"""H-0008 figure: the new microlensing events, each with ZTF (IRSA DR, catflags = 0, nightly medians, flux / baseline), the NEOWISE
visit and a point-source point-lens fit to all of them (oddsky.analysis.lensing; no parallax, no blending).
usage: hunt_h0008_fig_events.py STRONG_CSV OUT_PNG DESIGNATION [...]"""

import io
import sys

import matplotlib
import numpy as np
import pandas as pd
import requests

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.time import Time

from oddsky.analysis import lensing

x = pd.read_csv(sys.argv[1])
names = sys.argv[3:]
fig, axs = plt.subplots(1, len(names), figsize=(5.2 * len(names), 4.2), squeeze=False)
for ax, des in zip(axs[0], names, strict=True):
    r = x[x.designation == des].iloc[0]
    z = pd.read_csv(io.StringIO(requests.get("https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves?POS=CIRCLE%20"
                                             f"{r.ra}%20{r.dec}%200.0006&FORMAT=csv", timeout=300).text))
    z = z[(z.catflags == 0) & z.filtercode.isin(["zg", "zr"])]
    parts = []
    for b, g in z.groupby("filtercode"):
        g = g.assign(night=np.floor(g.mjd)).groupby("night").agg(t=("mjd", "median"), m=("mag", "median"), e=("magerr", "median"))
        base = g[(g.t - r.t).abs() > 200]
        m0, sc = base.m.median(), 1.4826 * np.median(np.abs(base.m - base.m.median()))
        w = g[(g.t - r.t).abs() < 300]
        f = 10 ** (-0.4 * (w.m - m0))
        parts.append(pd.DataFrame({"t": w.t, "f": f, "e": np.sqrt((0.921 * f * w.e) ** 2 + (0.921 * f * sc) ** 2 + (0.01 * f) ** 2), "g": b}))
    d = pd.concat(parts + [pd.DataFrame({"t": [r.t, r.t], "f": [10 ** (-0.4 * r.dw1), 10 ** (-0.4 * r.dw2)], "e": [0.03, 0.04],
                                         "g": ["W1", "W2"]})])
    prob = lensing.Problem(d.t, d.f, d.e, d.g)
    p, chi2 = prob.fit()
    tt = np.linspace(p[0] - 3 * p[1], p[0] + 3 * p[1], 600)
    for b, col in (("zg", "seagreen"), ("zr", "firebrick")):
        g = d[d.g == b]
        ax.errorbar(g.t - p[0], g.f, g.e, fmt="o", ms=3, color=col, label=f"ZTF {b[1]}", alpha=0.8)
    ax.plot([r.t - p[0]], [10 ** (-0.4 * r.dw1)], "*", ms=15, color="k", label="NEOWISE W1/W2")
    ax.plot(tt - p[0], lensing.magnification(np.hypot((tt - p[0]) / p[1], p[2])), "k-", lw=1)
    ax.set_xlim(-3 * p[1], 3 * p[1])
    ax.set_title(f"{des}\nt0 {Time(p[0], format='mjd').iso[:10]}, tE {p[1]:.0f} d, A_max {lensing.magnification(p[2]):.1f}, "
                 f"χ² {chi2:.0f}/{len(d) - 3}", fontsize=9)
    ax.set_xlabel("days from peak")
    ax.legend(fontsize=7)
axs[0][0].set_ylabel("flux / baseline")
plt.tight_layout()
plt.savefig(sys.argv[2], dpi=100)
