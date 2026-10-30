"""r18: a lens-like event the investigators did not single out: J183040.98-220950.3 (achromatic to 0.005 mag, ZTF r brighter by
0.50 mag on the one night within 10 d vs W1 0.47). Nearest catalogued lenses / Gaia alerts and its ZTF light curve."""
import io, os
import numpy as np, pandas as pd, requests
import astropy.units as u
from astropy.coordinates import SkyCoord
HERE = os.path.dirname(os.path.abspath(__file__))
x = pd.read_csv(f"{HERE}/../../work/sky3_classified.csv", dtype={"g_source_id": str})
r = x[x.designation == "J183040.98-220950.3"].iloc[0]
print(r[["ra", "dec", "t", "dw1", "dw2", "w1_med", "l", "b", "g_phot_g_mean_mag", "g_bp_rp", "g_parallax", "n_gaia_3as", "vsx", "ztf_dr", "ztf_n_window"]].to_dict())
ref = pd.read_csv(f"{HERE}/../../ext/reference_lenses.csv")
s = SkyCoord(ref.ra.values * u.deg, ref.dec.values * u.deg).separation(SkyCoord(r.ra * u.deg, r.dec * u.deg)).arcmin
for src in ref.source.unique():
    m = (ref.source == src).values
    j = np.argmin(np.where(m, s, 1e9))
    print(f"  nearest {src}: {ref.name.iloc[j]} {s[j]:.1f}' t0 {ref.t0_mjd.iloc[j]}")
t = requests.get(f"https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves?POS=CIRCLE%20{r.ra}%20{r.dec}%200.000556&FORMAT=csv", timeout=300).text
z = pd.read_csv(io.StringIO(t)); z.to_csv(f"{HERE}/data/ztf_J183040.csv", index=False)
z = z[z.catflags == 0]
for (f, fld), d in z.groupby(["filtercode", "field"]):
    base = d[(d.mjd - r.t).abs() > 200].mag.median()
    w = d[(d.mjd - r.t).abs() < 120].sort_values("mjd")
    print(f, fld, len(d), "baseline", round(base, 3), "robust sd", round(1.4826 * (d.mag - d.mag.median()).abs().median(), 3))
    print("   window:", [(round(a, 1), round(b - base, 2)) for a, b in zip(w.mjd, w.mag)][:40])
