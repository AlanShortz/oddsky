"""ATLAS forced photometry (reduced images, 2015-) for the H-0002 survivors; raw table kept as provenance."""
import json

from oddsky.case.store import CaseStore
from oddsky.data import atlas

for case in ("OS-0014", "OS-0013"):
    s = CaseStore.find(case)
    t = s.load().target
    url = atlas.submit(t.ra, t.dec, use_reduced=True)
    print(case, "task", url, flush=True)
    res = atlas.wait(url, max_wait_s=5400)
    text = atlas.download(res)
    (s.data / "external").mkdir(exist_ok=True)
    (s.data / "external" / "atlas_forced_reduced.txt").write_text(text)
    raw = atlas.parse(text)
    df = atlas.to_series(raw)
    s.write_series("atlas", df)
    pr = s.provenance()
    pr["atlas"] = {"archive": "ATLAS forced photometry (fallingstar-data.com), reduced images", "status": "ok",
                   "rows_raw": int(len(raw)), "rows_kept": int((df.flag == "").sum()), "cuts": [],
                   "notes": ["cite Tonry+2018, Heinze+2018, Smith+2020, Shingles+2021"]}
    s.write_provenance(pr)
    print(case, json.dumps({"rows": len(raw), "good": int((df.flag == '').sum()), "mjd": [float(df.t_mjd.min()), float(df.t_mjd.max())] if len(df) else None}), flush=True)
