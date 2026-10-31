"""r10: Gaia's scanning law (GOST, gaia.esac.esa.int/gost, fetched 2026-10-31; predicted times ~hours; dead time not modelled):
FOV transits during each event, and the brightening Gaia would have seen at each (from the ATLAS o light curve, nightly,
log-linear interpolation of the excess). Gaia Science Alerts trigger on brightening of a known source by roughly >= 1 mag
(plus significance), which bounds what could have been alerted."""
import os
import re
import sys

import numpy as np
import pandas as pd
import requests
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, targets  # noqa: E402

T = targets()
TP = {"J175634": 59661.3, "J174744": 59654.4}
WIN = {"J175634": (59630, 59700), "J174744": (59380, 59950)}
for k in KEYS:
    p = os.path.join(DATA, f"gost_{k}.xml")
    if not os.path.exists(p):
        s = requests.Session()
        s.get("https://gaia.esac.esa.int/gost/index.jsp", timeout=60)
        r = s.get("https://gaia.esac.esa.int/gost/GostServlet", params={"ra": T[k]["ra"], "dec": T[k]["dec"], "service": 1,
                  "srcname": k, "inputmode": "single"}, timeout=300)
        open(p, "w").write(r.text)
    x = open(p).read()
    span = re.search(r"<startTime>(.*?)</startTime><endTime>(.*?)</endTime>", x)
    ev = re.findall(r"<kind>(\w+)</kind>.*?<fov>(\w+)</fov>.*?<eventUtcDate>([\d\-T:.]+)</eventUtcDate>", x, re.S)
    d = pd.DataFrame(ev, columns=["kind", "fov", "utc"])
    d["mjd"] = Time(list(d.utc), scale="utc").mjd
    d = d.sort_values("mjd")
    d["tr"] = (d.mjd.diff().fillna(1) > 0.02).cumsum()
    tr = d.groupby("tr").agg(mjd=("mjd", "min"), fov=("fov", "first"), n=("kind", "size")).reset_index(drop=True)
    print(f"== {k}: GOST span {span.group(1)} .. {span.group(2)}; {len(tr)} FOV transits")
    nt = pd.read_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"))
    o = nt[nt.F == "o"].copy()
    b = o[np.abs(o.t - TP[k]) > 400].groupby("cam").ujy.median()
    o["x"] = o.ujy / o.cam.map(b) - 1
    o = o.sort_values("t")
    w = tr[(tr.mjd > WIN[k][0]) & (tr.mjd < WIN[k][1])]
    for _, r in w.iterrows():
        bef, aft = o[o.t <= r.mjd], o[o.t > r.mjd]
        a, c = bef.iloc[-1], aft.iloc[0]
        if c.t - a.t < 20:
            f = (r.mjd - a.t) / (c.t - a.t)
            xa, xc = max(a.x, 1e-3), max(c.x, 1e-3)
            x_ = np.exp(np.log(xa) + f * (np.log(xc) - np.log(xa)))
            est = f"ATLAS o x{1 + x_:.2f} (dG ~ {-2.5 * np.log10(1 + x_):+.2f}); bracketing nights {a.t - r.mjd:+.1f}/{c.t - r.mjd:+.1f} d"
        else:
            est = f"no ATLAS night within the gap ({a.t - r.mjd:+.1f}/{c.t - r.mjd:+.1f} d; o x{1 + a.x:.2f} before, x{1 + c.x:.2f} after)"
        print(f"   {Time(r.mjd, format='mjd').iso[:16]}  dt {r.mjd - TP[k]:+7.1f} d  {r.fov}  {est}")
