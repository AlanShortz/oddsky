"""s13: how good are Gaia-DR3-only lens parameters? For the catalogued lenses among the 67, compare this hunt's fitted t0 and tE
(BIC-preferred model, and the brightest transit) with the survey values (OGLE preferred, else KMTNet) from
hunts/H-0008/ext/reference_lenses.csv. Run from the repo root: uv run python -I hunts/H-0010/scripts/s13_calibrate.py
Writes hunts/H-0010/data/calibration.csv."""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, WORK  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
t = pd.read_csv(os.path.join(WORK, "gaia_ml_unpub.csv"), dtype={"source_id": str})
ref = pd.read_csv(os.path.join(REPO, "hunts/H-0008/ext/reference_lenses.csv")).set_index("name")
rows = []
for r in t[(t.verdict == "known lens") & t.ref_intime.notna()].itertuples():
    names = re.findall(r"((?:OGLE|KMT)-\d{4}-BLG-\d{4})", r.ref_intime)
    names = sorted(names, key=lambda n: not n.startswith("OGLE"))
    if not names:
        continue
    x = ref.loc[names[0]]
    x = x.iloc[0] if isinstance(x, pd.DataFrame) else x
    fj = json.load(open(os.path.join(DATA, "fits", f"{r.source_id}.json")))
    lab = "parallax" if fj["fit"]["parallax"]["bic"] < fj["fit"]["static"]["bic"] else "static"
    f = fj["fit"][lab]
    rows.append(dict(source_id=r.source_id, ref=names[0], t0_ref=x.t0_mjd, tE_ref=x.tE, t0_fit=f["t0"], tE_fit=f["tE"],
                     tE_static=fj["fit"]["static"]["tE"], t_peak=r.t_peak, dt0_fit=f["t0"] - x.t0_mjd,
                     dt0_peak=r.t_peak - x.t0_mjd, tE_ratio_static=fj["fit"]["static"]["tE"] / x.tE))
c = pd.DataFrame(rows)
for col in ("dt0_fit", "dt0_peak"):
    v = c[col].dropna().abs()
    print(f"|{col}| median {v.median():.1f} d, 80th pct {v.quantile(0.8):.1f} d, n {len(v)}")
v = np.log10(c.tE_ratio_static.dropna())
print(f"static tE / survey tE: median {10 ** v.median():.2f}, 16-84% {10 ** v.quantile(0.16):.2f}-{10 ** v.quantile(0.84):.2f}")
c.round(2).to_csv(os.path.join(DATA, "calibration.csv"), index=False)
print(c[["ref", "dt0_fit", "dt0_peak", "tE_ref", "tE_static", "tE_fit"]].round(1).to_string())
