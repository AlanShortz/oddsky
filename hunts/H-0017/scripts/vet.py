"""H-0017: ask the Librarian about every source (is it already published, and as what?), one row per source with the
status of each lookup. usage: vet.py NUCLEI_CSV(designation, ra, dec, side) OUT_CSV"""
import os
import sys

import pandas as pd

from oddsky.librarian import prior_art

x = pd.read_csv(sys.argv[1])
out = sys.argv[2]
rows = pd.read_csv(out).to_dict("records") if os.path.exists(out) else []
seen = {r["designation"] for r in rows if r.get("complete")}
rows = [r for r in rows if r["designation"] in seen]
for r in x.itertuples():
    if r.designation in seen:
        continue
    pa = prior_art(r.ra, r.dec, 5.0, "transient")
    top = pa.get("topical") or pa.get("topical_papers") or []
    sim, ned = pa.get("simbad") or {}, pa.get("ned") or {}
    rows.append(dict(designation=r.designation, side=r.side, verdict=pa["verdict"], complete=pa["complete"],
                     status="/".join(f"{k}:{v.get('status')}" for k, v in pa["sources"].items()),
                     simbad=sim.get("main_id"), simbad_otype=sim.get("otype"), ned=ned.get("prefname") or ned.get("name"),
                     ned_type=ned.get("type"), z=ned.get("z"), n_papers=pa.get("n_papers"), n_topical=len(top),
                     newest_topical=(top[0]["bibcode"] if top else None), newest_title=(top[0]["title"][:140] if top else None),
                     topical_bibcodes=";".join(p["bibcode"] for p in top[:8]),
                     shelves=";".join(h["shelf"] for h in pa.get("shelf_hits", []))))
    pd.DataFrame(rows).to_csv(out, index=False)
    print(r.designation, rows[-1]["verdict"], rows[-1]["complete"], rows[-1]["n_papers"], rows[-1]["n_topical"], rows[-1]["shelves"], flush=True)
o = pd.DataFrame(rows)
print(o.groupby(["side", "verdict"]).size().to_string())
print("incomplete:", int((~o.complete.astype(bool)).sum()))
