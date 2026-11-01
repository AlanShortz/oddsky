"""r1b: Gaia DR3 epoch-photometry g_other_flags during brightenings. In the five best candidates the bright transits carry
g_other_flags with bits 2-10 set (value 1023 + extras) while quiet transits carry 1. ESA's (historical) datalink help describes
bits 1-10 as 'SM / AF1-AF9 transit rejected by photometric processing'. If catalogued lenses show the same pattern, the flag is a
generic response to a large brightening and not an artifact marker. Raw DR3 data for 6 catalogued lenses among the 67.
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r1b_other_flags.py"""
import io, os, zipfile
import numpy as np, pandas as pd
from oddsky.data.gaia_epoch import DATALINK
from oddsky.data.http import request

HERE = os.path.dirname(os.path.abspath(__file__))
known = [4043458241772263936, 4062840084877907712, 4063409292521568640, 4056368634256485504, 4039699492609592704, 2032454944878107008]
cand = [4067152339419332992, 5958944416543307648, 5893807634053861120, 5620272814897694848, 2054828730840779520]
r = request("POST", DATALINK, timeout=300, retries=3, data=dict(RETRIEVAL_TYPE="EPOCH_PHOTOMETRY", ID=",".join(map(str, known)), FORMAT="csv",
            DATA_STRUCTURE="DATAMODEL_STANDARD", RELEASE="Gaia DR3", VALID_DATA="false"))
tabs = {}
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    for n in z.namelist():
        d = pd.read_csv(io.StringIO(z.read(n).decode()), comment="#")
        if len(d):
            tabs[int(d.source_id.iloc[0])] = ("known", d)
for s in cand:
    tabs[s] = ("candidate", pd.read_csv(os.path.join(HERE, "data", "epoch_raw", f"{s}.csv")))
for s, (lab, d) in tabs.items():
    d = d[np.isfinite(d.g_transit_flux)]
    f = d.g_transit_flux / np.median(d.g_transit_flux)
    af = (d.g_other_flags.astype("int64") & 0b1111111110) != 0
    br = f > 1.3
    print(f"{lab:9s} {s}: transits {len(d)}; bright (>x1.3) {int(br.sum())}, of which AF-bit flagged {int((af & br).sum())}; "
          f"quiet (<x1.05) {int((f < 1.05).sum())}, of which flagged {int((af & (f < 1.05)).sum())}")
