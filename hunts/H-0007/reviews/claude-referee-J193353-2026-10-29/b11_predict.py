"""b11: best-fit point-lens predictions (b7: t0 58949.5, tE 55.6, u0 0.575; tE range 48-62 d via the profile endpoints) at the
Gaia GOST transits (gost_2019oct-2020dec.csv) and for an ATLAS/ASAS-SN check of the peak. Own code, outside the Oddsky tools."""
import numpy as np
import pandas as pd
from astropy.time import Time

A = lambda t, t0, tE, u0: (lambda u: (u * u + 2) / (u * np.sqrt(u * u + 4)))(np.hypot(u0, (t - t0) / tE))
sols = {"best": (58949.5, 55.6, 0.575), "t0=Apr 2": (58942.0, 59.0, 0.56), "t0=Apr 17": (58957.0, 51.0, 0.565)}
g = pd.read_csv("hunts/H-0007/reviews/claude-referee-J193353-2026-10-29/gost_2019oct-2020dec.csv", skipinitialspace=True)
g["mjd"] = Time(list(g.iloc[:, 0].str.replace("T", " ")), format="iso").mjd
g["day"] = np.floor(g.mjd)
for lab, p in sols.items():
    g[lab] = -2.5 * np.log10(A(g.mjd, *p))
print("predicted dG at Gaia transits (mag):")
print(g.groupby("day").agg(date=(g.columns[0], "first"), n=("mjd", "size"), **{k: (k, "mean") for k in sols}).round(3).to_string())
print("\npredicted dm for ATLAS / ASAS-SN (achromatic, fs = 1):")
for d in ["2020-01-20", "2020-02-15", "2020-03-01", "2020-03-15", "2020-04-01", "2020-04-10", "2020-04-20", "2020-05-01", "2020-05-15", "2020-06-01", "2020-06-18"]:
    t = Time(d).mjd
    print(d, "  ".join(f"{k}: {-2.5*np.log10(A(t, *p)):+.2f}" for k, p in sols.items()))
