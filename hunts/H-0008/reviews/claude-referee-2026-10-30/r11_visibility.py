"""r11: claim 3. Is hunt_h0008_efficiency.py's NEOWISE visibility model right? For the 661 clean events, the Sun-target
ecliptic-longitude offset at the actual NEOWISE visit (the investigators' model requires ||dl| - 90| < 1 deg)."""
import os
import numpy as np, pandas as pd
import astropy.units as u
from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord, get_sun
from astropy.time import Time
HERE = os.path.dirname(os.path.abspath(__file__))
c = pd.read_csv(f"{HERE}/../../work/sky3_classified.csv", dtype={"g_source_id": str})
sun = get_sun(Time(c.t.values, format="mjd")).transform_to(GeocentricTrueEcliptic())
tgt = SkyCoord(c.ra.values * u.deg, c.dec.values * u.deg).transform_to(GeocentricTrueEcliptic())
dl = (sun.lon.deg - tgt.lon.deg + 180) % 360 - 180
off = np.abs(np.abs(dl) - 90)
c["vis_off_deg"] = off
c["ecl_lat"] = tgt.lat.deg
print("||dl|-90| at the real NEOWISE visit (deg): percentiles 50/90/99/max:", np.percentile(off, [50, 90, 99]).round(2), off.max().round(2))
print("fraction outside the model's 1-deg window:", round(float(np.mean(off >= 1)), 3))
# same for a known missed recovery
for name, t0, ra, dec in (("KMT-2018-BLG-0262 visit", 58361.078735, 268.66892, -23.34361),):
    days = np.arange(t0 - 15, t0 + 15, 0.25)
    s = get_sun(Time(days, format="mjd")).transform_to(GeocentricTrueEcliptic()).lon.deg
    l = SkyCoord(ra * u.deg, dec * u.deg).transform_to(GeocentricTrueEcliptic()).lon.deg
    d = np.abs(np.abs((s - l + 180) % 360 - 180) - 90)
    print(name, "days within 1 deg:", days[d < 1].min() if (d < 1).any() else None, "-", days[d < 1].max() if (d < 1).any() else None)
# NEOWISE pointing: in the real data the visit centre sits at |dl| ~ 90 +- x; fit a typical offset
print("median signed |dl|-90:", np.median(np.abs(dl) - 90).round(2))
# where are the off-window visits?  by ecliptic latitude and by year
c["absb"] = np.abs(c.ecl_lat)
c["yr"] = np.floor((c.t - 51544.5) / 365.25 + 2000)
print(c.groupby(pd.cut(c.absb, [0, 10, 30, 50, 70, 90])).vis_off_deg.describe().round(2))
print(c.groupby("yr").vis_off_deg.median().round(2).to_dict())
# Elongation (true angular distance Sun-target) at the visit
el = SkyCoord(c.ra.values * u.deg, c.dec.values * u.deg).separation(get_sun(Time(c.t.values, format="mjd")).transform_to("icrs")).deg
print("solar elongation at the visit: percentiles 1/50/99", np.percentile(el, [1, 50, 99]).round(2))
