"""r1: ATLAS forced photometry (reduced images) for the five targets, raw server text cached in data/atlas_<key>.txt.
Run with the ATLAS credentials sourced (~/.config/oddsky/atlas.env)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import TARGETS
from oddsky.data import atlas
keys = sys.argv[1:] or list(TARGETS)
for k in keys:
    name, ra, dec, t, pix = TARGETS[k]
    df, prov = atlas.lightcurve(ra, dec, mjd_min=57200, raw_cache=os.path.join(os.path.dirname(os.path.abspath(__file__)), f"data/atlas_{k}.txt"), max_wait_s=5400)
    print(k, prov.status, len(df), prov.notes, flush=True)
