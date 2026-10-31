"""r11: Gaia's scanning law (GOST; predicted transit times, dead time not modelled) for J174401 during its 2021 event, and the
brightening Gaia would have seen at each transit (ATLAS o, PSF-corrected nightly excess against a 370 uJy baseline, log-linear
interpolation between nights < 20 d apart). Gaia Science Alerts trigger roughly at >= 1 mag above the historic mean."""
import os
import re
import sys

import numpy as np
import pandas as pd
import requests
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, mjd2date, targets  # noqa: E402

T = targets()
k = "J174401"
p = os.path.join(DATA, f"gost_{k}.xml")
if not os.path.exists(p):
    s = requests.Session()
    s.get("https://gaia.esac.esa.int/gost/index.jsp", timeout=60)
    r = s.get("https://gaia.esac.esa.int/gost/GostServlet", params={"ra": T[k]["ra"], "dec": T[k]["dec"], "service": 1, "srcname": k,
              "inputmode": "single"}, timeout=300)
    open(p, "w").write(r.text)
x = open(p).read()
ev = re.findall(r"<kind>(\w+)</kind>.*?<fov>(\w+)</fov>.*?<eventUtcDate>([\d\-T:.]+)</eventUtcDate>", x, re.S)
d = pd.DataFrame(ev, columns=["kind", "fov", "utc"])
if d.empty:
    print("GOST returned nothing:", x[:300])
    sys.exit()
d["mjd"] = Time(list(d.utc), scale="utc").mjd
d = d.sort_values("mjd")
d["tr"] = (d.mjd.diff().fillna(1) > 0.02).cumsum()
tr = d.groupby("tr").agg(mjd=("mjd", "min"), fov=("fov", "first"), n=("kind", "size")).reset_index(drop=True)
nt = pd.read_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"))
o = nt[(nt.F == "o") & nt.cam.isin(["01a", "02a", "03a", "04a"])].copy()
o["x"] = (o.exc_psf + (o.ubase - 370)) / 370  # PSF-corrected excess, referred to a common 370 uJy baseline
o.loc[o.cam == "01a", "x"] = (o.ujy[o.cam == "01a"] - 366 - (-200.9) * (o.maj[o.cam == "01a"] - 2.5)) / 370  # 01a: 2020 baseline (PSF 2.5)
o = o.sort_values("t")
w = tr[(tr.mjd > 59250) & (tr.mjd < 59650)]
print(f"{len(tr)} FOV transits in the GOST span; {len(w)} between 2021 Feb and 2022 Mar:")
for _, r in w.iterrows():
    bef, aft = o[o.t <= r.mjd], o[o.t > r.mjd]
    if len(bef) and len(aft) and aft.t.iloc[0] - bef.t.iloc[-1] < 20:
        a, c = bef.iloc[-1], aft.iloc[0]
        f = (r.mjd - a.t) / (c.t - a.t)
        xa, xc = max(a.x, 1e-3), max(c.x, 1e-3)
        xx = np.exp(np.log(xa) + f * (np.log(xc) - np.log(xa)))
        est = f"ATLAS o x{1 + xx:.2f} (dG ~ {-2.5 * np.log10(1 + xx):+.2f} if Gaia's G sees the same fraction)"
    else:
        est = "no ATLAS night within 20 d on both sides"
    print(f"  {mjd2date(r.mjd)} MJD {r.mjd:.2f} {r.fov} ({r.n} CCD crossings): {est}")
