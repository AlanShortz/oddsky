"""b9: is the ZTF 2020 tail real? Comparison stars in the same field/CCD/quadrant (285/15/2) from IRSA ZTF DR light curves
(b3), catflags = 0. Per epoch (expid): median offset of comparison stars from their own medians, overall and for stars of
similar colour (g-r within 0.25 of the target's 0.77) and magnitude. Writes per-epoch offsets for b7.
Outside the Oddsky tools (pandas)."""
import numpy as np
import pandas as pd
from astropy.time import Time

pd.set_option("display.width", 250)
RA, DEC = 293.471115, -21.3037472
z = pd.read_csv("/tmp/j1933ref/ztf_cone.csv")
z = z[(z.catflags == 0) & (z.field == 285)].copy()
z["sep"] = 3600 * np.hypot((z.ra - RA) * np.cos(np.radians(DEC)), z.dec - DEC)
pos = z.groupby("oid").agg(ra=("ra", "median"), dec=("dec", "median"), n=("mjd", "size"), med=("mag", "median"), band=("filtercode", "first"))
pos["sep"] = 3600 * np.hypot((pos.ra - RA) * np.cos(np.radians(DEC)), pos.dec - DEC)
tgt = pos[pos.sep < 1.5]
print("target oids:", tgt.round(3).to_string())
# colour: match g and r oids by position (1")
g = pos[pos.band == "zg"]
r = pos[pos.band == "zr"]
col = {}
for oid, row in r.iterrows():
    d = 3600 * np.hypot((g.ra - row.ra) * np.cos(np.radians(DEC)), g.dec - row.dec)
    if len(d) and d.min() < 1.0:
        col[oid] = g.loc[d.idxmin(), "med"] - row.med
        col[d.idxmin()] = col[oid]
pos["gr"] = pd.Series(col)
z = z.merge(pos[["med", "gr"]], left_on="oid", right_index=True)
z["d"] = z.mag - z.med
z["tgt"] = z.oid.isin(tgt.index)
z["date"] = Time(z.mjd.values, format="mjd").iso
z["yr"] = Time(z.mjd.values, format="mjd").decimalyear
tgr = 16.116 - 15.343
cmp_all = z[(~z.tgt) & (pos.loc[z.oid, "n"].values > 150)]
cmp_col = cmp_all[(cmp_all.gr - tgr).abs() < 0.25]
print("comparison oids: all", cmp_all.oid.nunique(), " colour-matched", cmp_col.oid.nunique())
ep_all = cmp_all.groupby(["expid", "filtercode"]).d.agg(["median", "size"]).rename(columns={"median": "c_all", "size": "n_all"})
ep_col = cmp_col.groupby(["expid", "filtercode"]).d.agg(["median", "size", lambda x: 1.4826 * np.median(np.abs(x - np.median(x)))])
ep_col.columns = ["c_col", "n_col", "mad_col"]
T = z[z.tgt].set_index(["expid", "filtercode"])[["date", "mjd", "yr", "d", "airmass", "magzprms"]].join(ep_all).join(ep_col)
T["d_corr"] = T.d - T.c_col
w = T[(T.yr > 2019.6) & (T.yr < 2021.0)].sort_values("mjd")
print(w.round(3).to_string())
T["y"] = T.yr.astype(int)
T["summer"] = ((T.yr % 1) * 365.25).between(160, 215)
print("\nJun 9 - Aug 3 window, per year: target raw and comparison-corrected offsets")
print(T[T.summer].groupby(["y", "filtercode"]).agg(n=("d", "size"), raw=("d", "median"), comp=("c_col", "median"), corr=("d_corr", "median"),
                                                  corr_sd=("d_corr", "std")).round(3).to_string())
# distribution of 2020 June-July offsets for every comparison star: is the target an outlier?
win = (z.mjd > 59010) & (z.mjd < 59055)
s = z[win & (pos.loc[z.oid, "n"].values > 150)].groupby(["oid", "filtercode"]).d.median().reset_index()
s = s.merge(pos[["med", "gr", "sep"]], left_on="oid", right_index=True)
for f in ["zg", "zr"]:
    q = s[s.filtercode == f]
    print(f"\n{f}: {len(q)} stars, 2020 Jun 9-Jul 23 median offset: median {q.d.median():+.3f}, MAD {1.4826*np.median(np.abs(q.d-q.d.median())):.3f};"
          f" stars <= -0.08: {(q.d <= -0.08).sum()}")
    print(q.nsmallest(6, "d").round(3).to_string())
T.reset_index()[["mjd", "filtercode", "c_col"]].rename(columns={"c_col": "zoff"}).to_csv("/tmp/j1933ref/ztf_zoff.csv", index=False)
