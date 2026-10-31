"""r5b: parse the live KMTNet 2022 event page saved by r5 (data/page_KMTNet_2022.html): nearest events to each star, their
KMT field (cadence group), and the coverage of fields around the star; also the OGLE EWS 2022 page: season start and fields."""
import os
import re
import sys

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, mjd2date, targets  # noqa: E402

T = targets()
t = open(os.path.join(DATA, "page_KMTNet_2022.html")).read().replace("&nbsp;", " ")
rows = re.findall(r"event=(KMT-2022-BLG-\d+)'.*?</td>\s*<td>\s*(\S+)\s*</td>.*?<td>\s*(\d{2}:\d{2}:\d{2}\.\d+)\s*</td>\s*<td>\s*"
                  r"([+-]?\d{2}:\d{2}:\d{2}\.\d+)\s*</td>\s*<td>\s*([\d.]+)\s*</td>", t, re.S)
k_ = pd.DataFrame(rows, columns=["name", "field", "ra", "dec", "t0"])
print(f"KMTNet 2022 live page: {len(k_)} events parsed")
kc = SkyCoord(k_.ra.values, k_.dec.values, unit=(u.hourangle, u.deg))
k_["l"], k_["b"] = kc.galactic.l.wrap_at(180 * u.deg).deg, kc.galactic.b.deg
k_["fld"] = k_.field.str[:5]
for key, tt in T.items():
    c = SkyCoord(tt["ra"] * u.deg, tt["dec"] * u.deg)
    s = kc.separation(c).arcmin
    j = np.argsort(s)[:5]
    print(f"{key} (l {tt['l']:.2f} b {tt['b']:+.2f}): nearest " + "; ".join(
        f"{k_.name.iloc[i]} {s[i]:.1f}' field {k_.field.iloc[i]} t0 {mjd2date(float(k_.t0.iloc[i]) + 50000)}" for i in j))
    lw = ((tt["l"] + 180) % 360) - 180
    box = k_[(np.abs(k_.l - lw) < 1.5) & (np.abs(k_.b - tt["b"]) < 1.5)]
    print(f"   events within +-1.5 deg box: {len(box)}; fields: {box.fld.value_counts().to_dict()}; their l range "
          f"{box.l.min() if len(box) else np.nan:.2f}..{box.l.max() if len(box) else np.nan:.2f}, b range "
          f"{box.b.min() if len(box) else np.nan:.2f}..{box.b.max() if len(box) else np.nan:.2f}")
print("KMT 2022 events l range overall: %.2f..%.2f, b %.2f..%.2f" % (k_.l.min(), k_.l.max(), k_.b.min(), k_.b.max()))

o = open(os.path.join(DATA, "page_OGLE_EWS_2022.html")).read()
txt = re.sub(r"<[^>]+>", " ", o)
ev = re.findall(r"(\d{4}-BLG-\d{4})\s+(BLG\d+\.\d+)\s+\d+\s+(\d{2}:\d{2}:\d{2}\.\d+)\s+([+-]?\d{2}:\d{2}:\d{2}\.\d+)\s+([\d.]+)", txt)
print(f"OGLE EWS 2022 live page: {len(ev)} events parsed")
if ev:
    e = pd.DataFrame(ev, columns=["name", "field", "ra", "dec", "tmax"])
    e["tmax"] = e.tmax.astype(float)
    print("  first events:", e.head(3).values.tolist())
    print(f"  tmax (HJD-2450000) range {e.tmax.min():.1f}..{e.tmax.max():.1f}; tmax before 2022-06-01 (HJD 2459731.5): {(e.tmax < 2459731.5).sum()}; earliest tmax {e.sort_values("tmax").head(3)[["name","tmax"]].values.tolist()}; event numbers 0001-0003 tmax {e.tmax.iloc[:3].round(1).tolist()}")
    oc = SkyCoord(e.ra.values, e.dec.values, unit=(u.hourangle, u.deg))
    for key, tt in T.items():
        s = oc.separation(SkyCoord(tt["ra"] * u.deg, tt["dec"] * u.deg)).arcmin
        j = np.argsort(s)[:3]
        print(f"  {key}: nearest " + "; ".join(f"{e.name.iloc[i]} {s[i]:.1f}' {e.field.iloc[i]}" for i in j))
else:
    i = txt.find("2022-BLG-0001")
    print("  unparsed; snippet:", re.sub(r"\s+", " ", txt[i - 100:i + 400]))
