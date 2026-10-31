"""p8: noise-free G model (dG vs true quiescent G) at every GOST transit within -250..+300 d of the event for targets 1-2,
per referee reduction variant, with k = 0.65 / 0.85 / 1.10."""
import os
import sys

import numpy as np
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gaialib import gost  # noqa: E402
from models import T0PAR, lens_A, ref_fits  # noqa: E402
from targets import T  # noqa: E402

for k in ("J163539", "J173150"):
    t = gost(k)
    tg = T[k]
    sel = (t > T0PAR[k] - 250) & (t < T0PAR[k] + 300)
    ts = t[sel]
    print(f"== {k}: transits (MJD, date, days from t0par {T0PAR[k]}):")
    print("   " + "  ".join(f"{x:.1f}" for x in ts))
    print("   " + "  ".join(f"{Time(x, format='mjd').iso[5:10]}" for x in ts))
    fits = ref_fits(k)
    for v, f in fits.items():
        A = lens_A(ts, tg["ra"], tg["dec"], f["p"], T0PAR[k])
        for kk in (0.65, 1.10):
            dm = -2.5 * np.log10(1 + kk * f["fs_o"] * (A - 1))
            print(f"   {v:16s} tE {f['p'][1]:5.0f} fs_o {f['fs_o']:.2f} k {kk:.2f}: " + " ".join(f"{x:+.2f}" for x in dm))
