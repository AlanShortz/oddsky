"""a2: per-unit, per-band nightly light curve with per-unit baselines (2015-2018 and 2021+ only, so the 2019 wing is not in it).
Quality cut: o/c only, dujy < 150, mag5sig >= 17.5 (frames shallower than this listed separately). Writes /tmp/j1933atl/nightly_ref.csv.
Prints: season boundaries 2019-2020, every night with |A-1| > 0.06 outside 2020 Feb-Oct, and calendar-window comparisons.
usage: a2_nightly.py ATLAS_TXT"""
import sys, os
import numpy as np
import pandas as pd
from oddsky.data import atlas

pd.set_option("display.width", 200, "display.max_rows", 500)
r = atlas.parse(open(sys.argv[1]).read())
r = r[r.F.isin(["c", "o"]) & (r.dujy > 0)].copy()
r["unit"] = r.obs.str[:3]
r["date"] = pd.to_datetime(r.mjd - 40587, unit="D")
base_mask = (r.mjd < 58400) | (r.mjd > 59300)          # exclude 2018 Oct - 2021 Mar entirely
good = (r.dujy < 150) & (r.mag5sig >= 17.5)
print("frames failing quality:", (~good).sum(), "of", len(r))
B = r[base_mask & good].groupby(["F", "unit"]).ujy.median()
print("per-unit baselines:\n", B.round(0).to_string())
r["A"] = r.ujy / pd.Series([B.get((f, u), np.nan) for f, u in zip(r.F, r.unit)], index=r.index)
r["night"] = np.floor(r.mjd - 0.3).astype(int)
g = r[good]
n = g.groupby(["F", "unit", "night"]).agg(mjd=("mjd", "mean"), A=("A", "median"), sd=("A", "std"), k=("A", "size"),
                                          m5=("mag5sig", "median"), chi=("chi_n", "median")).reset_index()
n["date"] = pd.to_datetime(n.mjd - 40587, unit="D").dt.strftime("%Y-%m-%d")
os.makedirs("/tmp/j1933atl", exist_ok=True)
n.to_csv("/tmp/j1933atl/nightly_ref.csv", index=False)
bl = n[(n.mjd < 58400) | (n.mjd > 59300)]
print("\nbaseline nightly scatter (1.4826 MAD) by F/unit:")
print(bl.groupby(["F", "unit"]).A.agg(lambda x: 1.4826 * np.median(np.abs(x - 1))).round(4).to_string())
print("\nseason edges: last nights before 2020 Mar 11 and around")
print(n[(n.mjd > 58700) & (n.mjd < 58925)][["date", "F", "unit", "A", "k", "m5", "chi"]].round(3).to_string())
ev = (n.mjd > 58880) & (n.mjd < 59140)
out = n[~ev & ((n.A - 1).abs() > 0.06)]
print(f"\nnights outside 2020 Feb-Oct with |A-1|>0.06 (good frames only): {len(out)} of {len(n[~ev])}")
print(out[["date", "F", "unit", "A", "sd", "k", "m5", "chi"]].round(3).to_string())
bad = r[~good & ((r.A - 1).abs() > 0.15) & ~((r.mjd > 58880) & (r.mjd < 59140))]
print(f"\nrejected frames outside the event with |A-1|>0.15: {len(bad)}; their mag5sig range {bad.mag5sig.min()}-{bad.mag5sig.max()}, dujy median {bad.dujy.median()}")
# calendar-window systematics: Oct 1 - Nov 30 and Jul 1 - Aug 31 each year
for lab, m1, m2 in [("Oct-Nov", 10, 11), ("Jun 15-Aug 31", 6, 8), ("Mar-Apr", 3, 4)]:
    w = n[(pd.to_datetime(n.date).dt.month >= m1) & (pd.to_datetime(n.date).dt.month <= m2)]
    if lab.startswith("Jun"):
        w = w[~((pd.to_datetime(w.date).dt.month == 6) & (pd.to_datetime(w.date).dt.day < 15))]
    w = w.assign(yr=pd.to_datetime(w.date).dt.year)
    print(f"\n{lab}: median A by year/band (nights)")
    print(w.groupby(["yr", "F"]).A.agg(["median", "size"]).round(3).unstack("F").to_string())
