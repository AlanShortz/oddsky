"""r5: the FULL Zhai et al. 2024 (ApJ 978, 76) ZTF DR17 microlensing list from the journal's machine-readable tables
(content.cld.iop.org/journals/0004-637X/978/1/76/revision1/apjad94e7t{2,3}_mrt.txt; t2 = high-confidence, t3 = possible),
matched against (a) the five review targets and (b) all 661 clean H-0008 events (6", |t - t0| <= max(2 tE, 30 d)).
t0 in the MRT is HJD - 2450000 (MJD = t0 + 49999.5)."""
import os, sys
import numpy as np, pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from targets import TARGETS
D = f"{HERE}/data/zhai2024_mrt"
rows = []
for f, conf in (("apjad94e7t2_mrt.txt", "high"), ("apjad94e7t3_mrt.txt", "possible")):
    for ln in open(f"{D}/{f}"):
        if not ln.startswith("ZTF"):
            continue
        rows.append({"id": ln[0:14].strip(), "gaia": ln[15:24].strip(), "ra": float(ln[25:35]), "dec": float(ln[36:46]),
                     "t0_mjd": float(ln[47:54]) + 49999.5, "u0": float(ln[65:70] if conf == "high" else ln[68:72]),
                     "tE": float(ln[81:88] if conf == "high" else ln[83:90]), "conf": conf})
z = pd.DataFrame(rows).drop_duplicates("id")  # first row per event = the static fit
z.to_csv(f"{HERE}/r5_zhai_full.csv", index=False)
print("Zhai+2024 events:", len(z), z.conf.value_counts().to_dict())
inv = pd.read_csv(f"{HERE}/../../ext/ztf_zhai2024.csv")
print("investigators' parsed list:", len(inv), "| in full list:", int(inv.name.isin(z.id).sum()))
zc = SkyCoord(z.ra.values * u.deg, z.dec.values * u.deg)
for k, (name, ra, dec, t, pix) in TARGETS.items():
    sep = zc.separation(SkyCoord(ra * u.deg, dec * u.deg)).arcsec
    j = np.argmin(sep)
    print(f"{name}: nearest Zhai event {z.id.iloc[j]} ({z.conf.iloc[j]}) at {sep[j]:.1f}\" t0 {z.t0_mjd.iloc[j]:.1f} tE {z.tE.iloc[j]}")
c = pd.read_csv(f"{HERE}/../../work/sky3_classified.csv", dtype={"g_source_id": str})
cc = SkyCoord(c.ra.values * u.deg, c.dec.values * u.deg)
idx, sep, _ = cc.match_to_catalog_sky(zc)
m = (sep.arcsec < 6) & (np.abs(c.t.values - z.t0_mjd.values[idx]) <= np.maximum(2 * z.tE.values[idx], 30))
out = c[m][["designation", "t", "dw1", "class", "known_lens"]].assign(zhai=z.id.values[idx][m], conf=z.conf.values[idx][m],
                                                                     sep=sep.arcsec[m].round(2), zt0=z.t0_mjd.values[idx][m].round(1))
print(out.to_string())
print("matched:", len(out), "| previously classified as known microlensing:", int((out["class"] == "microlensing (known)").sum()))
# How many Zhai events are 'NEOWISE-catchable' by position alone? (W1 brightness unknown here)
