"""H-0016 fades: ZTF DR light curve at each position (IRSA), then: the ZTF magnitude within +-10 d of the NEOWISE fade visit versus
the star's median elsewhere; the number of ZTF nights fainter than 0.3 mag below the median, and whether the deep points fold on a
period (eclipse_period-style phase clustering, 0.3-400 d). usage: ztf_check.py IN_CSV OUT_CSV"""
import io
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

x = pd.read_csv(sys.argv[1])

def fetch(ra, dec):
    t = requests.get(f"https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves?POS=CIRCLE%20{ra}%20{dec}%200.0006&FORMAT=csv", timeout=300).text
    z = pd.read_csv(io.StringIO(t))
    return z[(z.catflags == 0)]

def phase_cluster(t, p_grid):
    """fraction of deep points that fall within 0.05 phase of each other, maximised over phase; crude eclipse test"""
    best = (0.0, np.nan)
    for p in p_grid:
        ph = (t / p) % 1
        h, _ = np.histogram(ph, bins=20, range=(0, 1))
        frac = h.max() / len(t)
        if frac > best[0]:
            best = (frac, p)
    return best

def one(r):
    try:
        z = fetch(r.ra, r.dec)
    except Exception:  # noqa: BLE001
        return dict(cntr=r.cntr, ztf_status="fetch_error")
    out = dict(cntr=r.cntr, ztf_status="ok", ztf_n=len(z))
    if len(z) < 20:
        out["ztf_status"] = "few"
        return out
    for f in ("zg", "zr"):
        b = z[z.filtercode == f]
        if len(b) < 20:
            continue
        med = b.mag.median()
        mad = 1.4826 * (b.mag - med).abs().median()
        w = b[(b.mjd - r.t).abs() < 10]
        out[f"{f}_n"] = len(b)
        out[f"{f}_med"] = float(med)
        out[f"{f}_mad"] = float(mad)
        out[f"{f}_win_n"] = len(w)
        out[f"{f}_win_d"] = float(w.mag.median() - med) if len(w) else np.nan
        deep = b[b.mag - med > max(0.3, 5 * mad)]
        nights = np.unique(np.floor(deep.mjd))
        out[f"{f}_deep_nights"] = len(nights)
        out[f"{f}_deep_max"] = float((deep.mag - med).max()) if len(deep) else 0.0
        if len(nights) >= 4:
            frac, p = phase_cluster(deep.mjd.to_numpy(), np.exp(np.linspace(np.log(0.3), np.log(400), 20000)))
            out[f"{f}_fold_frac"], out[f"{f}_fold_p"] = float(frac), float(p)
    return out

with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(one, x.itertuples()))
x = x.merge(pd.DataFrame(res), on="cntr", how="left")
x.to_csv(sys.argv[2], index=False)
print(x.ztf_status.value_counts().to_dict())
