"""b1: target NEOWISE single exposures (3" cone parquet from the hunt): per-visit table, event-visit exposures, centroid, slope.
Runs outside the Oddsky tools (pandas on the parquet). uv run python hunts/H-0007/reviews/claude-referee-J193353-2026-10-29/b1_target.py"""
import os

import numpy as np
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
RA, DEC = 293.471115, -21.3037472
PMRA, PMDEC = 0.0, 0.0  # filled below from Gaia if given
ex = pd.read_parquet(os.path.expanduser("~/oddsky-runs/h0007/faint/exp/2938021301351037214.parquet"))
ex["dra"] = 3600 * (ex.ra - RA) * np.cos(np.radians(DEC))
ex["ddec"] = 3600 * (ex.dec - DEC)
ex["sep"] = np.hypot(ex.dra, ex.ddec)
ex = ex.sort_values("mjd").reset_index(drop=True)
# visits: gap > 20 d
ex["visit"] = (ex.mjd.diff() > 20).cumsum()
ex["c"] = ex.w1mpro - ex.w2mpro
t = ex[ex.sep < 2.5].copy()
print("rows", len(ex), "within 2.5\"", len(t), "; other detections in 3\" cone:", len(ex) - len(t))
g = t.groupby("visit").agg(t0=("mjd", "min"), t1=("mjd", "max"), n=("mjd", "size"), w1=("w1mpro", "median"), w1s=("w1mpro", "std"),
                           w2=("w2mpro", "median"), w2s=("w2mpro", "std"), c=("c", "median"), dra=("dra", "mean"), ddec=("ddec", "mean"),
                           r1=("w1rchi2", "median"), r2=("w2rchi2", "median"), qf=("qual_frame", lambda x: ",".join(map(str, sorted(set(x))))),
                           nb=("nb", "max"), na=("na", "max"), sso=("sso_flg", "max"), moon=("moon_masked", lambda x: ",".join(sorted(set(map(str, x))))),
                           cc=("cc_flags", lambda x: ",".join(sorted(set(map(str, x))))), ph=("ph_qual", lambda x: ",".join(sorted(set(map(str, x))))),
                           saa=("saa_sep", "min"), w1sat=("w1sat", "max"))
print(g.round(3).to_string())
ev = g.index[(g.t0 < 58950) & (g.t1 > 58948)][0]
base = g.drop(ev)
for b in ["w1", "w2", "c"]:
    print(f"{b}: baseline median {base[b].median():.3f} visit-scatter {base[b].std():.3f} robust {1.4826*np.median(np.abs(base[b]-base[b].median())):.3f}; event {g.loc[ev, b]:.3f}; delta {g.loc[ev, b]-base[b].median():+.3f}")
e = ex[ex.visit == ev].copy()
print("\nEvent visit, all rows in 3\" cone:")
print(e[["mjd", "w1mpro", "w1sigmpro", "w2mpro", "w2sigmpro", "c", "dra", "ddec", "sep", "w1rchi2", "w2rchi2", "qual_frame", "qi_fact", "nb", "na",
         "cc_flags", "ph_qual", "moon_masked", "sso_flg", "saa_sep"]].round(3).to_string())
et = e[e.sep < 2.5]
print("event centroid mean dra %.3f+-%.3f ddec %.3f+-%.3f; baseline-visit dra %.3f+-%.3f ddec %.3f+-%.3f" % (
    et.dra.mean(), et.dra.std() / np.sqrt(len(et)), et.ddec.mean(), et.ddec.std() / np.sqrt(len(et)), base.dra.mean(), base.dra.std(), base.ddec.mean(), base.ddec.std()))
core = et[et.mjd < 58951]
for b in ["w1mpro", "w2mpro", "c"]:
    p, cov = np.polyfit(core.mjd - core.mjd.mean(), core[b], 1, cov=True)
    print(f"{b} in-visit slope {p[0]:+.4f} +- {np.sqrt(cov[0, 0]):.4f} mag/d (n={len(core)})")
print("flux ratio W1 %.3f W2 %.3f" % (10 ** (-0.4 * (core.w1mpro.median() - base.w1.median())), 10 ** (-0.4 * (core.w2mpro.median() - base.w2.median()))))
t.to_parquet("/tmp/j1933ref/target_exp.parquet")
