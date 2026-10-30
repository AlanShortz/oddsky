"""r18b: point-lens fit of J183040.98-220950.3 (ZTF catflags=0 nightly + NEOWISE sky3lens visits), same recipe as r4, plus
baseline behaviour in the other ZTF seasons (robust scatter per season, largest excursion)."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import targets
x = pd.read_csv(f"{HERE}/../../work/sky3_classified.csv", dtype={"g_source_id": str})
r = x[x.designation == "J183040.98-220950.3"].iloc[0]
lc = pd.read_parquet(os.path.expanduser(f"~/oddsky-runs/h0008/lightcurves/pixel={int(r.pixel)}.parquet"))
lc[lc.allwise_cntr == r.allwise_cntr].to_csv(f"{HERE}/data/neowise_J183040.csv", index=False)
targets.TARGETS["J183040"] = ("J183040.98-220950.3", r.ra, r.dec, r.t, int(r.pixel))
import r4_fits
r4_fits.TARGETS["J183040"] = targets.TARGETS["J183040"]
df = r4_fits.series_for("J183040")
res = r4_fits.fit_variants("J183040", df)
for k in ("static_noblend", "static_blend", "parallax_blend"):
    print(k, {a: b for a, b in res[k].items() if a != "chi2_by_series"})
print("asym", r4_fits.asym(df, res["static_noblend"]["t0"], res["static_noblend"]["tE"], res["static_noblend"]["u0"]), "coverage", res["coverage"])
from lib import ztf
z = ztf("J183040")
z["season"] = np.floor((z.mjd - 58119) / 365.25) + 2018
for (s, band), d in z.groupby(["season", "band"]):
    base = z[(z.band == band) & ((z.mjd - r.t).abs() > 200)].mag.median()
    print(int(s), band, len(d), "median offset", round(d.mag.median() - base, 3), "min", round(d.mag.min() - base, 2), "max", round(d.mag.max() - base, 2))
