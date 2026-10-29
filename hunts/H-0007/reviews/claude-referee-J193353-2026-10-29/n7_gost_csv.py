"""Referee J193353: reduce the raw GOST csv export (/tmp/j1933nov/gost/export_raw.csv) to the format of the first
referee's gost_2017jun-oct.csv, add MJD, and list transits. uv run python -I .../n7_gost_csv.py <raw> <out.csv>"""
import csv, sys
from datetime import datetime

raw, out = sys.argv[1], sys.argv[2]
rows = list(csv.reader(open(raw, encoding="utf-8")))
hdr = [h.strip() for h in rows[0]]
it, ic, ifov = hdr.index("ObservationTimeAtGaia[UTC]"), hdr.index("CcdRow[1-7]"), hdr.index("Fov[FovP=preceding/FovF=following]")
data = [(r[it].strip(), r[ic].strip(), r[ifov].strip()) for r in rows[1:] if len(r) > ifov]
with open(out, "w", encoding="utf-8") as f:
    f.write(" ObservationTimeAtGaia[UTC], CcdRow[1-7], Fov[FovP=preceding/FovF=following]\n")
    for t, c, v in data:
        f.write(f"{t},{c},{v}\n")
mjd0 = datetime(1858, 11, 17)
print(f"{len(data)} transits (FoV crossings)")
for t, c, v in data:
    dt = datetime.fromisoformat(t)
    mjd = (dt - mjd0).total_seconds() / 86400
    flag = "  <-- 2020 Jan-Aug" if "2020-01" <= t[:7] <= "2020-08" else ""
    print(f"  {t}  MJD {mjd:.4f}  row {c} {v}{flag}")
