"""r6: local novelty checks for the five targets: nearest entries in the investigators' reference catalogue (any time),
every Gaia Science Alert (hunts/H-0005/alerts.csv, any class, any date) within 30", and the KMTNet/OGLE footprints
(nearest event of each year)."""
import os, sys
import numpy as np, pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from targets import TARGETS
ROOT = f"{HERE}/../../../.."
ref = pd.read_csv(f"{HERE}/../../ext/reference_lenses.csv")
a = pd.read_csv(f"{ROOT}/hunts/H-0005/alerts.csv", skipinitialspace=True)
a.columns = [c.strip("# ") for c in a.columns]
rc = SkyCoord(ref.ra.values * u.deg, ref.dec.values * u.deg)
ac = SkyCoord(a.RaDeg.values * u.deg, a.DecDeg.values * u.deg)
for k, (name, ra, dec, t, pix) in TARGETS.items():
    c = SkyCoord(ra * u.deg, dec * u.deg)
    s = rc.separation(c).arcsec
    o = np.argsort(s)[:3]
    print(f"== {name} (l,b = {c.galactic.l.deg:.2f}, {c.galactic.b.deg:.2f})")
    for j in o:
        print(f"   ref: {ref.name.iloc[j]} ({ref.source.iloc[j]}) {s[j]/60:.1f}' t0 {ref.t0_mjd.iloc[j]}")
    for src in ("KMTNet", "OGLE"):
        m = (ref.source == src).values
        print(f"   nearest {src} event: {s[m].min()/60:.1f}'")
    sa = ac.separation(c).arcsec
    for j in np.where(sa < 30)[0]:
        print(f"   Gaia alert {a.Name.iloc[j]} {sa[j]:.1f}\" {a.Date.iloc[j]} class={a.Class.iloc[j]} mag {a.AlertMag.iloc[j]} hist {a.HistoricMag.iloc[j]} | {a.Comment.iloc[j]}")
