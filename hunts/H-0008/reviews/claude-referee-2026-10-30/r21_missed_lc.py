"""r21: NEOWISE light curves (oddsky.data.neowise.lightcurve, IRSA single exposures) at two bright Zhai+2024 events that the survey
missed although an unblended source would have passed the detector (r20): what did NEOWISE actually see at the predicted visit?"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
from oddsky.data import neowise
from oddsky.analysis.lensing import magnification
e = pd.read_csv(f"{HERE}/r12_eff.csv").set_index("name")
for n in sys.argv[1:] or ["ZTF21acqomnw", "ZTF19abagvae"]:
    r = e.loc[n]
    df, prov = neowise.lightcurve(r.ra, r.dec)
    df.to_csv(f"{HERE}/data/neowise_{n}.csv", index=False)
    print(n, prov.status, len(df), "t0", r.t0, "tE", r.tE, "u0", r.u0)
    for b, d in df.groupby("band"):
        d = d.sort_values("t_mjd")
        med = d.mag.median()
        pred = 2.5 * np.log10(magnification(np.hypot((d.t_mjd - r.t0) / r.tE, r.u0)))
        print("  ", b, [(round(t, 1), round(m - med, 2), round(p, 2)) for t, m, p in zip(d.t_mjd, d.mag, pred)])
