"""r10b: every GOST transit 2021-2023 and in the DR4 sub-windows, with the noise-free lens dG, to choose resolvable windows."""
import os
import sys

import numpy as np
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r10_gaia_predictions import MODELS, gost, lens_ratio, mjd  # noqa: E402

for k in ("J180624", "J183040"):
    t = gost(k)
    p, fss = list(MODELS[k].values())[-1]
    dm = -2.5 * np.log10(lens_ratio(k, t, p, fss[-1]))
    sel = (t > mjd("2021-01-01")) & (t < mjd("2023-12-31"))
    print(k, "transits 2021-2023 (date, model dG):", [(Time(x, format="mjd").iso[:16], round(float(d), 2)) for x, d in zip(t[sel], dm[sel], strict=True)])
    for a, b in (("2014-07-25", "2016-06-30"), ("2018-01-01", "2020-01-20"), ("2015-01-01", "2021-12-31")):
        s = (t >= mjd(a)) & (t <= mjd(b) + 1)
        print(f"   {a}..{b}: {s.sum()} transits on {len(np.unique(np.floor(t[s])))} nights")
