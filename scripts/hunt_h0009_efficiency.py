"""H-0009: how many catchable known lenses each pass finds, strict (sky3lens, H-0008) against long (sky4long).

Reference events and their magnification at the real NEOWISE visit dates come from the H-0008 referee (r12_eff.csv: every
KMTNet, OGLE, Gaia DR3 and Zhai+2024 event, A at the visits from template stars' real visit dates; r13_zhai_w1.csv: the Zhai
disk events with an AllWISE counterpart and its W1). Catchable: A >= 1.6 at a non-edge visit (catchable_v2). A pass recovers an
event if one of its clean events lies within 6" and its visit block is within max(2 tE, 30 d) of t0.
usage: hunt_h0009_efficiency.py STRICT_CLEAN_CSV LONG_CLEAN_CSV   (the *_clean.csv tables written by hunt_h0008_events.py)
"""

import os
import sys

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hunts", "H-0008", "reviews", "claude-referee-2026-10-30")
e = pd.read_csv(os.path.join(R, "r12_eff.csv"))
w1 = pd.read_csv(os.path.join(R, "r13_zhai_w1.csv"))[["name", "w1mpro"]]
e = e.merge(w1, on="name", how="left")
ec = SkyCoord(e.ra.values * u.deg, e.dec.values * u.deg)
win = np.where(e.tE.notna(), np.maximum(2 * e.tE.fillna(0), 30), 100)


def recovered(path):
    c = pd.read_csv(path)
    if "t_first" not in c:
        c["t_first"] = c["t_last"] = c["t"]
    cc = SkyCoord(c.ra.values * u.deg, c.dec.values * u.deg)
    hit = np.zeros(len(e), bool)
    ci, ei, _, _ = ec.search_around_sky(cc, 6 * u.arcsec)  # ci: index into cc, ei: into ec
    for a, b in zip(ci, ei, strict=True):
        if c.t_first.iloc[a] - win[b] <= e.t0.iloc[b] <= c.t_last.iloc[a] + win[b]:
            hit[b] = True
    return hit


e["strict"] = recovered(sys.argv[1])
e["long"] = recovered(sys.argv[2])
cat = e[e.catchable_v2.astype(bool)]
rows = []
for lab, s in (("all catchable", cat), ("not inner bulge", cat[~cat.inner_bulge.astype(bool)]),
               ("inner bulge", cat[cat.inner_bulge.astype(bool)]), ("Zhai disk, AllWISE W1 <= 15", cat[cat.w1mpro <= 15]),
               ("tE > 100 d", cat[cat.tE > 100]), ("tE <= 100 d", cat[cat.tE <= 100])):
    rows.append({"sample": lab, "n": len(s), "strict": int(s.strict.sum()), "long": int(s.long.sum()),
                 "either": int((s.strict | s.long).sum())})
t = pd.DataFrame(rows)
print(t.to_string(index=False))
out = os.path.join(os.path.dirname(R), "..", "..", "H-0009", "work")
e[e.catchable_v2.astype(bool) | e.strict | e.long].to_csv(os.path.join(out, "efficiency_events.csv"), index=False)
t.to_csv(os.path.join(out, "efficiency.csv"), index=False)
