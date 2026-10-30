"""H-0008 step 3: how many known microlensing events should NEOWISE have caught, and how many did the survey recover?

NEOWISE scans along the terminator, so a star is observed for ~1-2 days whenever the Sun's ecliptic longitude is 90 degrees
from its own (twice a year). For every event in a reference catalogue (KMTNet 2016-2024, Gaia DR3 vari_microlensing) with a
point-lens t0, tE and u0, predict the magnification on those days (up to the end of NEOWISE, 2024 Aug 8). An event is
"catchable" if a NEOWISE day has A >= 1.6 (0.5 mag, unblended) and the star is bright (MAG_COL <= MAG_MAX). Recovered = a
vetted brightening within 3" and within max(2 tE, 30 d) of t0. In the crowded bulge WISE's 6" beam blends many stars, so
detected amplitudes are diluted: the recovered fraction is this survey's efficiency there, not NEOWISE's in general.
usage: hunt_h0008_efficiency.py REF_CSV NAME_COL MAG_COL MAG_MAX VETTED_CSV OUT_CSV
"""

import sys

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord, get_sun
from astropy.time import Time

from oddsky.analysis.lensing import magnification

ref, name_col, mag_col, mag_max, vetted, out = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5], sys.argv[6]
k = pd.read_csv(ref, dtype={name_col: str})
k = k[k.t0_mjd.between(56600, 60531) & k.tE.notna() & k.u0.notna() & (k.tE > 0)].copy()
days = np.arange(56600, 60531, 1.0)
sun_lon = get_sun(Time(days, format="mjd")).transform_to(GeocentricTrueEcliptic()).lon.deg
kc = SkyCoord(k.ra.to_numpy() * u.deg, k.dec.to_numpy() * u.deg)
lam = kc.transform_to(GeocentricTrueEcliptic()).lon.deg
v = pd.read_csv(vetted)
vc = SkyCoord(v.ra.to_numpy() * u.deg, v.dec.to_numpy() * u.deg)
rows = []
for j, r in enumerate(k.itertuples()):
    dl = (sun_lon - lam[j] + 180) % 360 - 180
    seen = days[np.abs(np.abs(dl) - 90) < 1.0]
    near = seen[np.abs(seen - r.t0_mjd) < 3 * r.tE + 5]
    amax = float(magnification(np.hypot((near - r.t0_mjd) / r.tE, r.u0)).max()) if len(near) else 1.0
    sep = vc.separation(kc[j]).arcsec
    hit = (sep < 3) & (np.abs(v.t.to_numpy() - r.t0_mjd) <= max(2 * r.tE, 30))
    rows.append({"name": getattr(r, name_col), "ra": r.ra, "dec": r.dec, "t0_mjd": r.t0_mjd, "tE": r.tE, "u0": r.u0,
                 "mag": getattr(r, mag_col), "A_at_neowise": round(amax, 3), "recovered": bool(hit.any()),
                 "recovered_as": "; ".join(v.designation[hit].astype(str)) if hit.any() else ""})
e = pd.DataFrame(rows)
e["catchable"] = (e.A_at_neowise >= 1.6) & (e.mag <= mag_max)
e.to_csv(out, index=False)
cat = e[e.catchable]
print(f"{ref}: {len(e)} events with fits; catchable (A >= 1.6 on a NEOWISE day, {mag_col} <= {mag_max}): {len(cat)}; "
      f"recovered: {int(cat.recovered.sum())}; recovered although not 'catchable': {int((e.recovered & ~e.catchable).sum())}")
