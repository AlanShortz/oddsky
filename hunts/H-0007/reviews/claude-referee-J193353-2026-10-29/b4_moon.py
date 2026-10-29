"""b4: Moon and Sun geometry for every target exposure; are moon_masked / qual_frame=0 / SAA exposures biased in baseline visits?
Outside the Oddsky tools (astropy get_body). Reads /tmp/j1933ref/target_exp.parquet from b1."""
import numpy as np
import pandas as pd
from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord, get_body
from astropy.time import Time

pd.set_option("display.width", 250)
t = pd.read_parquet("/tmp/j1933ref/target_exp.parquet")
star = SkyCoord(293.471115, -21.3037472, unit="deg")
print("ecliptic lat/lon of star:", star.transform_to(GeocentricTrueEcliptic()).lat.deg.round(2), star.transform_to(GeocentricTrueEcliptic()).lon.deg.round(2))
tt = Time(t.mjd.values, format="mjd")
moon = get_body("moon", tt)
sun = get_body("sun", tt)
t["moon_sep"] = moon.separation(star).deg
t["sun_elong"] = sun.separation(star).deg
t["moon_illum"] = (1 - np.cos(np.radians(get_body("sun", tt).separation(moon).deg))) / 2
vm = t.groupby("visit").w1mpro.transform("median")
t["d1"] = t.w1mpro - vm
t["d2"] = t.w2mpro - t.groupby("visit").w2mpro.transform("median")
print(t[t.visit == 11][["mjd", "w1mpro", "w2mpro", "moon_sep", "moon_illum", "sun_elong", "moon_masked", "qual_frame", "saa_sep"]].round(3).to_string())
nonev = t[t.visit != 11]
for lab, m in [("moon_masked=11", nonev.moon_masked.astype(str) == "11"), ("qual_frame=0", nonev.qual_frame == 0), ("saa_sep<0", nonev.saa_sep < 0),
               ("clean", (nonev.moon_masked.astype(str) == "00") & (nonev.qual_frame > 0))]:
    s = nonev[m]
    print(f"baseline {lab:15s} n={len(s):3d}  W1 - visit median: median {s.d1.median():+.3f} rms {s.d1.std():.3f}  min {s.d1.min():+.3f}; W2 median {s.d2.median():+.3f}")
print("baseline min moon_sep per visit:")
print(t.groupby("visit").agg(t0=("mjd", "min"), msep=("moon_sep", "min"), illum=("moon_illum", "max")).round(2).T.to_string())
