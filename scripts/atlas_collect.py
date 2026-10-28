"""Collect an already-queued ATLAS forced-photometry task into a case (no resubmission).
python scripts/atlas_collect.py OS-0014 https://fallingstar-data.com/forcedphot/queue/5262171/"""
import json
import sys

from oddsky.case.store import CaseStore
from oddsky.data import atlas

case, url = sys.argv[1], sys.argv[2]
s = CaseStore.find(case)
text = atlas.download(atlas.wait(url, poll_s=120, max_wait_s=12 * 3600))
(s.data / "external").mkdir(exist_ok=True)
(s.data / "external" / "atlas_forced_reduced.txt").write_text(text)
raw = atlas.parse(text)
df = atlas.to_series(raw)
s.write_series("atlas", df)
pr = s.provenance()
pr["atlas"] = {"archive": "ATLAS forced photometry (fallingstar-data.com), reduced images", "status": "ok",
               "rows_raw": int(len(raw)), "rows_kept": int((df.flag == "").sum()), "cuts": [], "query": {"task": url},
               "notes": ["cite Tonry+2018, Heinze+2018, Smith+2020, Shingles+2021"]}
s.write_provenance(pr)
print(json.dumps({"case": case, "rows": len(raw), "good": int((df.flag == "").sum())}))
