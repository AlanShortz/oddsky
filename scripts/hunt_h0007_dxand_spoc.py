"""H-0007 side result: DX And's photometric period from the official TESS SPOC 2-minute light curves (TIC 428055818).

Per sector: PDCSAP flux, quality == 0, trends longer than a day removed with a 721-point (1-day) running mean; sector 57 starts
after the 2022 outburst has decayed (MJD > 58858). Lomb-Scargle near 2/P_orb; prints each sector's peak and the combined 2P.
"""

import io
import json

import numpy as np
import requests
from astropy.io import fits
from astropy.timeseries import LombScargle

API = "https://mast.stsci.edu/api/v0/invoke"
CAT = 2 / 0.440502  # catalogue (VSX / Ritter & Kolb) orbital period, as the ellipsoidal frequency


def mast(service, params):
    req = {"service": service, "params": params, "format": "json", "pagesize": 500}
    return requests.post(API, data={"request": json.dumps(req)}, timeout=120).json()["data"]


obs = [o for o in mast("Mast.Caom.Cone", {"ra": 352.4444462, "dec": 43.7510794, "radius": 0.003})
       if o.get("obs_collection") == "TESS" and o.get("dataproduct_type") == "timeseries"]
ts, fs = [], []
for o in obs:
    lc = next(p for p in mast("Mast.Caom.Products", {"obsid": o["obsid"]}) if p["productFilename"].endswith("_lc.fits"))
    raw = requests.get("https://mast.stsci.edu/api/v0.1/Download/file?uri=" + lc["dataURI"], timeout=300).content
    h = fits.open(io.BytesIO(raw))
    d, sec = h[1].data, h[0].header["SECTOR"]
    ok = (d["QUALITY"] == 0) & np.isfinite(d["PDCSAP_FLUX"])
    t = d["TIME"][ok] + 2457000 - 2400000.5
    f = d["PDCSAP_FLUX"][ok] / np.nanmedian(d["PDCSAP_FLUX"][ok])
    if sec == 57:
        m = t > 59858
        t, f = t[m], f[m]
    f = f - np.convolve(f, np.ones(721) / 721, mode="same")
    t, f = t[400:-400], f[400:-400]
    grid = np.linspace(4.52, 4.55, 30001)
    pw = LombScargle(t, f).power(grid)
    k = int(np.argmax(pw))
    at_cat = LombScargle(t, f).power(np.array([CAT]))[0]
    print(f"S{sec}: n={len(t)} peak f={grid[k]:.5f} c/d (2P={2 / grid[k]:.6f} d), power {pw[k]:.3f}; at catalogue {at_cat:.3f}")
    ts.append(t)
    fs.append(f)
t, f = np.concatenate(ts), np.concatenate(fs)
grid = np.linspace(4.53, 4.545, 150001)
pw = LombScargle(t, f).power(grid)
k = int(np.argmax(pw))
print(f"combined: 2P = {2 / grid[k]:.7f} d; power {pw[k]:.3f}; at catalogue {LombScargle(t, f).power(np.array([CAT]))[0]:.3f}")
