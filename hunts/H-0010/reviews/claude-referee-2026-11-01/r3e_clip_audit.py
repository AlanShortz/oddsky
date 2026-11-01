"""r3e: what the investigators' BP/RP clip (scripts/lib.py epoch(): drop BP/RP points departing from the same transit's G by
more than max(1 mag, 5 sigma)) removes inside the event windows of the 21 candidates. A clip conditioned on agreement with G
removes exactly the points that would show chromaticity. Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r3e_clip_audit.py"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from lib import epoch  # noqa: E402  (investigators' code, read-only use)
inv = pd.read_csv(os.path.join(HERE, "..", "..", "work", "gaia_ml_unpub.csv"), dtype={"source_id": str}).set_index("source_id")
C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str})
for c in C.itertuples():
    a, _ = epoch(c.source_id, clip_bp_rp=False)
    b, info = epoch(c.source_id, clip_bp_rp=True)
    r = inv.loc[c.source_id]
    lo, hi = float(r.ep_first) - 40, float(r.ep_last) + 40
    key = lambda d: set(zip(d.camera, d.band))
    gone = key(a) - key(b)
    g = a[a.band == "G"].set_index("camera").dm
    ev = [(cam, band) for cam, band in gone if lo <= a[(a.camera == cam) & (a.band == band)].t_mjd.iloc[0] <= hi]
    det = []
    for cam, band in ev:
        x = a[(a.camera == cam) & (a.band == band)].iloc[0]
        det.append(f"{band} {x.t_mjd:.1f} d{band} {x.dm:+.2f} vs dG {g.get(cam, np.nan) if not hasattr(g.get(cam, np.nan), 'iloc') else g.get(cam).iloc[0]:+.2f}")
    print(f"{c.name}: clipped {info['n_clip_bprp']} BP/RP points in total, {len(ev)} inside the event window: {'; '.join(det)}")
