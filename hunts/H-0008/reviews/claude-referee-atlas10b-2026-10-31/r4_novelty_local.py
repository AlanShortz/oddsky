"""r4: novelty against the local reference lists (hunts/H-0008/ext) and the Gaia alerts index (hunts/H-0005/alerts.csv).
 - nearest event of each list, and per year, within 60';
 - OGLE EWS season coverage: t0 range of the 2022 events in the local list (OGLE was paused 2020-2022);
 - KMT event density around each star per year (proxy for whether the star lies in a KMT field, and its cadence)."""
import os
import sys

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import H8, mjd2date, targets  # noqa: E402

pd.set_option("display.width", 250)
T = targets()
ext = os.path.join(H8, "ext")
ROOT = os.path.abspath(os.path.join(H8, "..", ".."))
lists = {f: pd.read_csv(os.path.join(ext, f)) for f in ("ogle_events.csv", "kmt_events.csv", "ogle_gvs_mroz2020.csv",
                                                        "gaia_dr3_microlensing.csv", "reference_lenses.csv", "ztf_zhai2024.csv",
                                                        "ztf_older.csv", "tns_reported.csv")}
o = lists["ogle_events.csv"]
o["yr"] = o.name.str.split("-").str[1].astype(int)
for y in (2019, 2022, 2023):
    d = o[(o.yr == y) & o.t0_mjd.between(50000, 70000)]
    print(f"OGLE EWS {y} in the local list: {len(d)} events, t0 {mjd2date(d.t0_mjd.min())} .. {mjd2date(d.t0_mjd.max())}; "
          f"t0 before 2022-06-01: {(d.t0_mjd < 59731).sum()}")
print("OGLE years present:", sorted(o.yr.unique()))
k_ = lists["kmt_events.csv"]
k_["yr"] = k_.name.str.split("-").str[1].astype(int)
print("KMT years present:", sorted(k_.yr.unique()))

a = pd.read_csv(os.path.join(ROOT, "hunts", "H-0005", "alerts.csv"), skipinitialspace=True)
a.columns = [c.strip("# ") for c in a.columns]
print(f"Gaia alerts index: {len(a)} alerts, last {a.Date.max()}")
ac = SkyCoord(a.RaDeg.values * u.deg, a.DecDeg.values * u.deg)

for k, t in T.items():
    c = SkyCoord(t["ra"] * u.deg, t["dec"] * u.deg)
    print("=" * 30, k, t["name"])
    for f, d in lists.items():
        d = d[d.ra.notna()].copy()
        if "name" not in d.columns:
            d["name"] = d.iloc[:, 0].astype(str)
        s = SkyCoord(d.ra.values * u.deg, d.dec.values * u.deg).separation(c).arcmin
        i = np.argsort(s)[:3]
        extra = ""
        if "t0_mjd" in d.columns:
            extra = " | " + "; ".join(f"{d.name.iloc[j]} {s[j]:.1f}' t0 {mjd2date(d.t0_mjd.iloc[j]) if 50000 < d.t0_mjd.iloc[j] < 70000 else '-'}"
                                       for j in i)
        else:
            extra = " | " + "; ".join(f"{d.name.iloc[j]} {s[j]:.1f}'" for j in i)
        print(f"  {f:28s} within 1': {(s < 1).sum()}, within 10': {(s < 10).sum()}, within 30': {(s < 30).sum()}, within 60': "
              f"{(s < 60).sum()}{extra}")
        if f in ("ogle_events.csv", "kmt_events.csv"):
            d = d.assign(sep=s)
            d["yr"] = d.name.str.split("-").str[1].astype(int)
            near = d[d.sep < 30]
            print(f"      per year within 30': {near.groupby('yr').size().to_dict()}; within 30' and t0 in 2022: "
                  f"{near[(near.t0_mjd > 59580) & (near.t0_mjd < 59945)][['name', 'sep', 't0_mjd']].round(1).values.tolist()}")
    s = ac.separation(c).arcsec
    near = np.where(s < 60)[0]
    print(f"  Gaia alerts within 60\": {len(near)}; nearest: " +
          "; ".join(f"{a.Name.iloc[j]} {s[j] / 60:.1f}' {a.Date.iloc[j][:10]} {a.Class.iloc[j]}" for j in np.argsort(s)[:3]))
    m = (s < 3600) & (a.Date.str[:4] == "2022").values
    print(f"  Gaia alerts in 2022 within 60': {m.sum()}: " + "; ".join(f"{a.Name.iloc[j]} {s[j] / 60:.1f}' {a.Date.iloc[j][:10]} "
                                                                       f"{a.Class.iloc[j]}" for j in np.where(m)[0]))
