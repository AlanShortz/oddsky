"""s6: Gaia's scanning law (GOST predicted field-of-view transits, dead time not modelled) at every strong event and at the
calibration known lenses (s5). Writes data/gost_transits.csv (one row per predicted FoV transit: designation, mjd, fov) so that
s4 can count transits within +-30 and +-90 d of each NEOWISE event, inside the DR3 (to 2017-05-28) and DR4 (to 2020-01-20) spans."""
import os
import re
import sys
import time

import pandas as pd
import requests
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, events  # noqa: E402

p = os.path.join(DATA, "gost_transits.csv")
done = set(pd.read_csv(p).designation) if os.path.exists(p) else set()
e = events()[["designation", "ra", "dec"]]
k = pd.read_csv(os.path.join(DATA, "calib_known.csv"))[["designation"]]
kk = pd.read_csv(os.path.join(DATA, "..", "..", "..", "work", "sky4_classified.csv"), usecols=["designation", "ra", "dec"])
k = k.merge(kk.drop_duplicates("designation"), on="designation")
todo = pd.concat([e, k], ignore_index=True).drop_duplicates("designation")
s = requests.Session()
s.get("https://gaia.esac.esa.int/gost/index.jsp", timeout=60)
for r in todo.itertuples():
    if r.designation in done:
        continue
    for i in range(4):
        try:
            x = s.get("https://gaia.esac.esa.int/gost/GostServlet", params={"ra": r.ra, "dec": r.dec, "service": 1, "srcname": "t",
                      "inputmode": "single"}, timeout=300).text
            if "<eventUtcDate>" in x:
                break
        except Exception as ex:  # noqa: BLE001
            print("retry", r.designation, ex)
        time.sleep(10 * (i + 1))
        s = requests.Session()
        s.get("https://gaia.esac.esa.int/gost/index.jsp", timeout=60)
    ev = re.findall(r"<fov>(\w+)</fov>.*?<eventUtcDate>([\d\-T:.]+)</eventUtcDate>", x, re.S)
    if not ev:
        print("GOST returned nothing for", r.designation, x[:200])
        continue
    d = pd.DataFrame(ev, columns=["fov", "utc"])
    d["mjd"] = Time(list(d.utc), scale="utc").mjd
    d = d.sort_values("mjd")
    d["tr"] = (d.mjd.diff().fillna(1) > 0.02).cumsum()
    tr = d.groupby("tr").agg(mjd=("mjd", "min"), fov=("fov", "first")).reset_index(drop=True)
    tr.insert(0, "designation", r.designation)
    tr.to_csv(p, mode="a", header=not os.path.exists(p), index=False)
    print(r.designation, len(tr), "transits", flush=True)
    time.sleep(1)
