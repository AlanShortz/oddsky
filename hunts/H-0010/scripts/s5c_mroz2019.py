"""s5c: OGLE-IV bulge events 2010-2015 from Mroz et al. (2019, ApJS 244, 29; VizieR J/ApJS/244/29/table3), which include events
the EWS never alerted and which hunts/H-0008/ext/reference_lenses.csv does not hold. 6" cones on the vizier.idia.ac.za mirror.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s5c_mroz2019.py. Writes hunts/H-0010/data/mroz2019.csv."""
import io
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, targets  # noqa: E402

rows = []
for r in targets().itertuples():
    val = "ERR"
    for _ in range(3):
        try:
            q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", timeout=120, params={
                "-source": "J/ApJS/244/29/table3", "-c": f"{r.ra} {r.dec}", "-c.rs": 6,
                "-out": "Name,t0-best,tE-best,EWS", "-out.add": "_r"})
            q.raise_for_status()
            lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
            if len(lines) < 3:
                val = "none"
            else:
                d = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t")
                val = "; ".join(f"{x['Name'].strip()} (t0 HJD {x['t0-best']}, tE {x['tE-best']}, EWS {str(x['EWS']).strip()}, "
                                f"{float(x['_r']):.1f}\")" for x in d.to_dict("records"))
            break
        except Exception as e:  # noqa: BLE001
            val = f"ERR {type(e).__name__}"
            time.sleep(10)
    rows.append(dict(source_id=r.source_id, mroz2019=val))
    if val != "none":
        print(r.source_id, val, flush=True)
out = pd.DataFrame(rows)
out.to_csv(os.path.join(DATA, "mroz2019.csv"), index=False)
print("none:", (out.mroz2019 == "none").sum(), "errors:", out.mroz2019.str.startswith("ERR").sum())
