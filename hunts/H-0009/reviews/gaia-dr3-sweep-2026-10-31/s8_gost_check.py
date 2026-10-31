"""s8: does GOST's predicted scanning match the transits Gaia DR3 actually published? For the three sources with epoch photometry,
the fraction of predicted FoV transits in the DR3 span with a published G transit within 0.05 d, and the reverse."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, DR3_T0, DR3_T1, EPOCH  # noqa: E402

gost = pd.read_csv(os.path.join(DATA, "gost_transits.csv"))
for d, sid in (("J172057.02-414201.2", "5959812622743175552"), ("J180402.28-181847.5", "4143495279954502016"),
               ("J180839.93-151910.5", "4145977633638478336")):
    g = gost[(gost.designation == d) & (gost.mjd > DR3_T0) & (gost.mjd < DR3_T1)].mjd.values
    e = pd.read_csv(os.path.join(EPOCH, f"{sid}.csv"))
    o = e[e.band == "G"].t_mjd.values
    hit = np.array([np.min(np.abs(o - x)) < 0.05 for x in g])
    rev = np.array([np.min(np.abs(g - x)) < 0.05 for x in o])
    print(f"{d}: GOST {len(g)} predicted FoV transits in DR3 span, {hit.sum()} published ({hit.mean():.0%}); "
          f"published {len(o)}, {rev.sum()} predicted")
