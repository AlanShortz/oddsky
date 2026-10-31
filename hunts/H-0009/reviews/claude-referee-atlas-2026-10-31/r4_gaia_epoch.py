"""r4: Gaia DR3 epoch photometry (2014-07 to 2017-05; published only for sources Gaia flagged VARIABLE) for the Gaia stars of the
ten events and the VARIABLE neighbours within 3" of the AllWISE positions. Two of the 2015 events fall inside DR3's span:
J180402 (target flagged VARIABLE) and J172057 (the Gaia star 0.59" from the AllWISE position, not the one matched at 2.2", is
flagged VARIABLE). Also the DR3 variability classification (I/358/vclassre) of those sources."""
import io
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, mjd2date, neowise, targets  # noqa: E402

from oddsky.data import gaia_epoch  # noqa: E402

pd.set_option("display.width", 250)
T = targets()
IDS = {"J180402": [4143495279954502016], "J172057": [5959812622743175552, 5959812622743175808],
       "J170153": [5966156701720599680], "J173349": [4061588260756165632]}
got, rep = gaia_epoch.fetch_report([i for v in IDS.values() for i in v], releases=("Gaia DR3",))
print("report:", rep["releases"])
for k, ids in IDS.items():
    t = T[k]
    for sid in ids:
        df = got.get(sid)
        if df is None or df.empty:
            print(f"== {k} {sid}: no DR3 epoch photometry")
            continue
        df.to_csv(os.path.join(DATA, f"r4_gaia_{sid}.csv"), index=False)
        g = df[(df.band == "G") & (df.flag != "rejected_by_photometry")].copy()
        g = g[np.isfinite(g.mag)]
        med = g.mag.median()
        rob = 1.4826 * np.median(np.abs(g.mag - med))
        print(f"== {k} Gaia DR3 {sid}: {len(g)} G transits {mjd2date(g.t_mjd.min())}..{mjd2date(g.t_mjd.max())}; median G {med:.3f}, "
              f"robust scatter {rob:.3f}, range {g.mag.min():.2f}..{g.mag.max():.2f}")
        near = g[np.abs(g.t_mjd - t["tvis"]) < 120].copy()
        near["dt"] = near.t_mjd - t["tvis"]
        near["dG"] = near.mag - med
        near["ratio"] = 10 ** (-0.4 * near.dG)
        print(f"   transits within 120 d of the NEOWISE visit ({mjd2date(t['tvis'])}, W1 x{10 ** (-0.4 * t['dw1']):.2f}):")
        print(near[["t_mjd", "dt", "mag", "err", "dG", "ratio", "flag"]].round(3).to_string(index=False) if len(near) else "   none")
        for b in ("BP", "RP"):
            x = df[(df.band == b) & (df.flag != "rejected_by_photometry") & np.isfinite(df.mag)]
            xn = x[np.abs(x.t_mjd - t["tvis"]) < 120]
            if len(x):
                print(f"   {b}: median {x.mag.median():.3f}; within 120 d: " + ", ".join(f"{r.t_mjd - t['tvis']:+.1f}d {r.mag - x.mag.median():+.3f}"
                                                                                 for r in xn.itertuples()))
        # brightest transits overall
        print("   five brightest G transits:", ", ".join(f"{mjd2date(r.t_mjd)} {r.mag - med:+.2f}" for r in g.nsmallest(5, "mag").itertuples()))
# DR3 variability class
for sid in [i for v in IDS.values() for i in v]:
    q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={"-source": "I/358/vclassre", "Source": sid, "-out": "**"},
                     timeout=120)
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    print(sid, "vclassre:", lines[3:4] if len(lines) > 3 else "none", lines[0][:200] if lines else "")
