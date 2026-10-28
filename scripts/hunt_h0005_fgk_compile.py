"""Hunt H-0005: every archival measurement of Gaia20fgk (Gaia DR3 523457286761045120) on one table, as depth below each
band's bright-state level, plus the figure.

Inputs in hunts/H-0005/data/: Gaia alert light curve, ZTF, NEOWISE visits, ATLAS, and the WISE 2010 single-exposure
median (cached in Gaia20fgk_wise2010.csv; re-queried from IRSA if the file is missing). Pan-STARRS DR2 detections are
fetched from MAST. Writes data/Gaia20fgk_photometry.csv and figures/Gaia20fgk_lightcurve.png.
"""
import io
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import requests

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RA, DEC = 17.13953, 64.14006
D = Path("hunts/H-0005/data")
PS1 = "https://catalogs.mast.stsci.edu/api/v0.1/panstarrs/dr2/detection.csv"


def year(mjd):
    return (mjd - 51544.5) / 365.25 + 2000


def wise_2010() -> pd.DataFrame:
    cache = D / "Gaia20fgk_wise2010.csv"
    if cache.exists():
        return pd.read_csv(cache)
    q = ("SELECT mjd, w1mpro, w1sigmpro FROM allsky_3band_p1bs_psd "
         f"WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{RA},{DEC},0.0011))=1")
    w = pd.read_csv(io.StringIO(requests.post("https://irsa.ipac.caltech.edu/TAP/sync",
                                              data={"FORMAT": "csv", "QUERY": q}, timeout=300).text))
    out = pd.DataFrame({"mjd": [w.mjd.median()], "w1": [w.w1mpro.median()],
                        "w1_err": [w.w1sigmpro.median() / np.sqrt(len(w))], "n": [len(w)]})
    out.to_csv(cache, index=False)
    return out


rows = []
g = pd.read_csv(D / "Gaia20fgk_gaia_alerts.csv", skiprows=1)
g.columns = ["date", "jd", "mag"]
g["mag"] = pd.to_numeric(g.mag, errors="coerce")  # "untrusted" points become NaN
for r in g.dropna().itertuples():
    rows.append(("Gaia", "G", r.jd - 2400000.5, r.mag, np.nan, False))
z = pd.read_csv(D / "Gaia20fgk_ztf.csv")
for r in z[z.flag.isna()].itertuples():
    rows.append(("ZTF", r.band[-1], r.t_mjd, r.mag, r.err, False))
p = pd.read_csv(io.StringIO(requests.get(PS1, timeout=120, params={
    "ra": RA, "dec": DEC, "radius": 1.5 / 3600, "columns": "[obsTime,filterID,psfFlux,psfFluxErr,psfQfPerfect]"}).text))
for r in p[p.psfQfPerfect > 0.85].itertuples():
    rows.append(("Pan-STARRS", "grizy"[r.filterID - 1], r.obsTime, -2.5 * np.log10(r.psfFlux) + 8.90,
                 1.0857 * r.psfFluxErr / r.psfFlux, False))
n = pd.read_csv(D / "Gaia20fgk_neowise.csv")
for r in n[n.band == "W1"].itertuples():
    rows.append(("WISE", "W1", r.t_mjd, r.mag, r.err, False))
for r in wise_2010().itertuples():
    rows.append(("WISE", "W1", r.mjd, r.w1, r.w1_err, False))
a = pd.read_csv(D / "Gaia20fgk_atlas.csv")
for r in a[a.flag.fillna("") == ""].itertuples():  # 5-sigma upper limits are left out of the depth plot
    rows.append(("ATLAS", r.band[-1], r.t_mjd, r.mag, r.err, False))
# Non-detections (lower limits on depth): 2MASS 1999-01-03 (field complete to J ~16.5), WISE 2010-02 (field to W1 ~15.6)
rows.append(("2MASS", "J", 2451186.5 - 2400000.5, 16.5, np.nan, True))
rows.append(("WISE", "W1", 55230.5, 15.6, np.nan, True))

d = pd.DataFrame(rows, columns=["survey", "band", "mjd", "mag", "err", "fainter_than"])
d["year"] = year(d.mjd)
# Baselines: medians in the bright states (2015.5-2020.3, 2024.2+); PS1 g/r/i use ZTF's, z/y and J are colour estimates
bright = d[~d.fainter_than & (((d.year > 2015.5) & (d.year < 2020.3)) | (d.year > 2024.2))]
base = bright.groupby(["survey", "band"]).mag.median().to_dict()
base.update({("Pan-STARRS", b): base.get(("ZTF", b)) for b in "gri"})
base.update({("Pan-STARRS", "z"): base[("ZTF", "i")] - 0.15, ("Pan-STARRS", "y"): base[("ZTF", "i")] - 0.25,
             ("2MASS", "J"): 14.8})
d["baseline"] = [base.get((s, b)) for s, b in zip(d.survey, d.band, strict=True)]
d["depth"] = d.mag - d.baseline
d.to_csv(D / "Gaia20fgk_photometry.csv", index=False)
print({f"{k[0]}:{k[1]}": round(v, 2) for k, v in base.items() if v})
ztf = d[d.survey == "ZTF"]
post = ztf[ztf.year > 2024.2].groupby("band").mag.median()
pre = ztf[ztf.year < 2020.3].groupby("band").mag.median()
print("ZTF post-2024.2 minus pre-2020.3:", (post - pre).round(3).to_dict())

# One axis (depth below baseline, down = fainter); marker shape and colour per survey, plus a legend.
style = {"Pan-STARRS": ("#2a78d6", "o"), "ZTF": ("#eb6834", "s"), "Gaia": ("#1baf7a", "D"),
         "WISE": ("#eda100", "^"), "2MASS": ("#e87ba4", "v"), "ATLAS": ("#008300", "P")}
fig, ax = plt.subplots(figsize=(11, 4.6), dpi=160)
for s, (c, m) in style.items():
    x = d[(d.survey == s) & ~d.fainter_than]
    ax.scatter(x.year, x.depth, s=14, c=c, marker=m, lw=0, label=s, zorder=3)
    for r in d[(d.survey == s) & d.fainter_than].itertuples():
        ax.annotate("", xy=(r.year, r.depth + 0.9), xytext=(r.year, r.depth),
                    arrowprops={"arrowstyle": "-|>", "color": c, "lw": 2}, zorder=3)
        ax.scatter([r.year], [r.depth], s=40, c=c, marker="_", lw=2, zorder=3)
for x0, x1, label in [(2010.0, 2015.6, "low state <=2010.1-2015.6"), (2020.4, 2023.9, "low state 2020.4-2023.9")]:
    ax.axvspan(x0, x1, color="#ec4899", alpha=0.07, lw=0)
    ax.text((x0 + x1) / 2, -0.55, label, ha="center", color="#555", fontsize=9)
ax.text(1999.0, 2.95, "2MASS: not detected", ha="center", fontsize=8, color="#555")
ax.set_ylim(6.2, -0.8)
ax.set_xlim(1997.5, 2026.6)
ax.set_ylabel("magnitudes below bright-state level")
ax.set_xlabel("year")
ax.set_title("Gaia20fgk (Gaia DR3 523457286761045120): an H-alpha emitting star that spends years 3-5 mag fainter",
             loc="left", fontsize=11)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
ax.grid(axis="y", color="#e5e5e5", lw=0.6)
ax.legend(frameon=False, ncol=6, loc="lower left", fontsize=8)
fig.text(0.01, 0.005, "Depth per band vs its own baseline (PS1 z,y and 2MASS J baselines estimated from colours). "
         "Arrows: non-detections (lower limits). Data: Pan-STARRS DR2, ZTF DR (IRSA), Gaia Science Alerts, "
         "ATLAS forced photometry, WISE/NEOWISE, 2MASS.", fontsize=6.5, color="#666")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig("hunts/H-0005/figures/Gaia20fgk_lightcurve.png")
