"""p7: does Gaia's photometric processing flag strongly brightened transits as rejected_by_photometry (which the Oddsky
grader drops)? Empirical test on Gaia DR3 vari_microlensing events: 25 high-magnification events (smallest
paczynski0_u0, peak inside the DR3 span), their DR3 epoch photometry via oddsky.data.gaia_epoch.fetch, and for each the
fraction of transits flagged by photometry / variability, split by how far the transit is above the baseline."""
import io
import os
import sys

import httpx
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import HERE  # noqa: E402

from oddsky.data import gaia_epoch  # noqa: E402

TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
adql = ("SELECT TOP 25 m.source_id, m.paczynski0_u0, m.paczynski0_te, m.paczynski0_tmax, g.phot_g_mean_mag FROM "
        "gaiadr3.vari_microlensing AS m JOIN gaiadr3.gaia_source AS g USING (source_id) WHERE m.paczynski0_tmax BETWEEN 1700 AND 2650 "
        "AND m.paczynski0_te > 20 ORDER BY m.paczynski0_u0 ASC")
p = os.path.join(HERE, "dr3_ml_sample.csv")
if not os.path.exists(p):
    r = httpx.post(TAP, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=adql), timeout=240)
    open(p, "w").write(r.text)
ml = pd.read_csv(p, dtype={"source_id": str})
print(ml.to_string())
lcs = gaia_epoch.fetch([int(s) for s in ml.source_id], releases=("Gaia DR3",))
rows = []
for sid, df in lcs.items():
    g = df[df.band == "G"].dropna(subset=["mag"])
    base = np.median(g.mag[g.flag == ""])
    dm = g.mag - base
    for lo, hi in ((-99, -1.0), (-1.0, -0.3), (-0.3, -0.1), (-0.1, 99)):
        s = (dm > lo) & (dm <= hi)
        rows.append(dict(sid=sid, bin=f"{lo}..{hi}", n=int(s.sum()), rej_phot=int((g.flag[s] == "rejected_by_photometry").sum()),
                         rej_var=int((g.flag[s] == "rejected_by_variability").sum())))
    nan = df[(df.band == "G") & df.mag.isna()]
    print(f"{sid}: {len(g)} G transits with mag ({int((g.flag == 'rejected_by_photometry').sum())} rej_phot, "
          f"{int((g.flag == 'rejected_by_variability').sum())} rej_var); {len(nan)} without mag; brightest dm {dm.min():+.2f}")
r = pd.DataFrame(rows)
print(r.groupby("bin")[["n", "rej_phot", "rej_var"]].sum())
r.to_csv(os.path.join(HERE, "p7_flag_test.csv"), index=False)
