"""H-0008 step 5: the strongest unexplained events. Keeps unclassified, achromatic (|dW1 - dW2| <= 0.08), >= 0.4 mag
brightenings, then looks each up in TNS (60") and in every Gaia Science Alert (any class, 10", within 200 d).
usage: hunt_h0008_vet.py CLASSIFIED_CSV GAIA_ALERTS_CSV OUT_CSV"""

import io
import sys
import time

import astropy.units as u
import numpy as np
import pandas as pd
import requests
from astropy.coordinates import SkyCoord

x = pd.read_csv(sys.argv[1], dtype={"g_source_id": str})
x["ach"] = (x.dw1 - x.dw2).abs()
c = x[(x["class"] == "unclassified") & (x.ach <= 0.08) & (x.dw1 <= -0.4)].copy()
a = pd.read_csv(sys.argv[2], skipinitialspace=True)
a.columns = [col.strip("# ") for col in a.columns]
a["t"] = pd.to_datetime(a.Date).map(lambda d: d.to_julian_date()) - 2400000.5
ac = SkyCoord(a.RaDeg.to_numpy() * u.deg, a.DecDeg.to_numpy() * u.deg)
tns, gal = [], []
for r in c.itertuples():
    sep = ac.separation(SkyCoord(r.ra * u.deg, r.dec * u.deg)).arcsec
    ok = (sep < 10) & (np.abs(a.t.to_numpy() - r.t) < 200)
    gal.append("; ".join(f"{n} ({cl}, {cm})" for n, cl, cm in zip(a.Name[ok], a.Class[ok], a.Comment[ok], strict=True)))
    try:
        resp = requests.get("https://www.wis-tns.org/search", params={"ra": r.ra, "decl": r.dec, "radius": 60, "coords_unit": "arcsec",
                            "format": "csv"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        if resp.status_code != 200:  # 429 = rate limited: an error, never "nothing there"
            tns.append(f"ERR HTTP {resp.status_code}")
            time.sleep(30)
            continue
        d = pd.read_csv(io.StringIO(resp.text)) if resp.text.strip() else pd.DataFrame()
        if "Name" not in d:
            tns.append("")
            continue
        tns.append("; ".join(f"{n} ({ty}, {dt})" for n, ty, dt in zip(d["Name"], d["Obj. Type"], d["Discovery Date (UT)"], strict=True)))
    except Exception as e:  # noqa: BLE001
        tns.append(f"ERR {str(e)[:60]}")
    time.sleep(8)
c["gaia_alert"] = gal
c["tns"] = tns
c.sort_values("dw1").to_csv(sys.argv[3], index=False)
print(len(c), "strong unexplained events;", int((c.gaia_alert != "").sum()), "with a Gaia alert,", int((c.tns.str.len() > 0).sum() - c.tns.str.startswith("ERR").sum()), "with TNS objects;",
      int(c.tns.str.startswith("ERR").sum()), "TNS lookups failed")
