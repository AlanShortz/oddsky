"""a1: raw ATLAS overview: per unit/band counts, baseline, quality columns; every 2020 frame Feb-Nov.
usage: a1_inspect.py ATLAS_TXT"""
import sys
import numpy as np
import pandas as pd
from oddsky.data import atlas

r = atlas.parse(open(sys.argv[1]).read())
r["unit"] = r.obs.str[:3]
print(len(r), "frames; bands", r.F.value_counts().to_dict(), "units", r.unit.value_counts().to_dict())
print("err!=0:", (r.err != 0).sum(), " dujy<=0:", (r.dujy <= 0).sum(), " dujy>2000:", (r.dujy > 2000).sum())
off = (r.mjd < 58800) | (r.mjd > 59200)
g = r[off & (r.dujy > 0) & (r.dujy < 2000)]
print("\nbaseline per unit/band (median uJy, robust scatter, N, median mag5sig, median chi/N):")
print(g.groupby(["F", "unit"]).agg(N=("ujy", "size"), med=("ujy", "median"),
      rs=("ujy", lambda x: 1.4826 * np.median(np.abs(x - x.median()))),
      m5=("mag5sig", "median"), chi=("chi_n", "median")).round(1))
pd.set_option("display.width", 200, "display.max_rows", 500)
e = r[(r.mjd > 58870) & (r.mjd < 59170)].copy()
base = g.groupby("F").ujy.median()
e["A"] = (e.ujy / e.F.map(base)).round(3)
e["date"] = pd.to_datetime(e.mjd - 40587, unit="D").dt.strftime("%Y-%m-%d")
print(e[["mjd", "date", "F", "unit", "ujy", "dujy", "A", "chi_n", "mag5sig", "sky", "apfit", "maj", "x", "y"]].round(3).to_string())
