"""Why is each of the 37 'new in h0012b' survivors new? For each: was there any h0012a candidate (any class) within 6"
(then it is a re-classification / re-ranking), was it inside the h0012a nucleus circle (old UNGC centre and radius),
or on a released-core (low-confidence) pixel?

    uv run python hunts/H-0012/reviews/h0012b-referee/why_new.py
Writes why_new.csv next to this script.
"""
import json
import subprocess
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
W = HERE.parents[1] / "work"
NEW = pd.read_csv(W / "new_in_h0012b.csv", dtype={"gaia_id": str})
RA_ = Path("~/oddsky-runs/h0012a").expanduser()
old_t = pd.read_csv(StringIO(subprocess.run(["git", "show", "9c695f5:hunts/H-0012/work/targets_10mpc.csv"], capture_output=True,
                                            text=True, cwd=HERE).stdout))
new_t = pd.read_csv(W / "targets_10mpc.csv")
# h0012a nucleus radii: report.json per tile records them
rows = []
for _, r in NEW.iterrows():
    gal, tile = r.galaxy, r.tile
    near_a = None
    cdir = RA_ / tile / gal / "candidates.csv"
    if cdir.exists():
        c = pd.read_csv(cdir, low_memory=False)
        d = np.hypot((c.ra - r.ra) * np.cos(np.radians(r.dec)), c.dec - r.dec) * 3600
        k = int(np.argmin(d)) if len(d) else None
        near_a = (float(d.iloc[k]), c.cls.iloc[k], float(c.var_sig.iloc[k])) if k is not None else None
    nuc_old = None
    rep = RA_ / tile / "report.json"
    if rep.exists():
        g = json.loads(rep.read_text()).get("galaxies", {}).get(gal, {})
        if "centre" in g:
            ra0, de0 = g["centre"]
            sep = float(np.hypot((r.ra - ra0) * np.cos(np.radians(de0)), r.dec - de0) * 3600)
            nuc_old = (round(sep, 1), g.get("nucleus_mask_arcsec"))
    rows.append(dict(galaxy=gal, ra=r.ra, dec=r.dec, rank_fsn=r.rank_fsn, rank_obs=r.rank_obs, what=str(r.what)[:40],
                     low_conf=r.low_confidence, mask_code=r.mask_code, cls=r.cls, var_sig=round(r.var_sig, 2),
                     h0012a_nearest_sep=None if near_a is None else round(near_a[0], 1),
                     h0012a_nearest_cls=None if near_a is None else near_a[1],
                     h0012a_nearest_var_sig=None if near_a is None else round(near_a[2], 2),
                     h0012a_dir=cdir.exists(), old_centre_sep_and_nucleus_radius=nuc_old))
out = pd.DataFrame(rows)
out.to_csv(HERE / "why_new.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(out.drop(columns=["what"]).to_string())
