"""H-0012: ADS full-text novelty check for OS-0030 (the NGC 3239 infrared transient) and the other infrared-only leads.

Reads the ADS API token from ~/.config/oddsky/ads-token (never printed). For each target: full-text searches for the host galaxy
with transient/infrared terms, the coordinates in common formats, and a read of the WISE/NEOWISE transient papers by De et al.
(and SPIRITS) for any mention of the host. Writes hunts/H-0012/work/ads_novelty.json. Read-only.
usage: uv run python hunts/H-0012/scripts/ads_novelty.py
"""

import json
import time
from pathlib import Path

import httpx

TOKEN = (Path.home() / ".config/oddsky/ads-token").read_text().strip()
API = "https://api.adsabs.harvard.edu/v1/search/query"
H = {"Authorization": f"Bearer {TOKEN}"}
TARGETS = {
    "OS-0030 NGC 3239": ["NGC 3239", "NGC3239", "Arp 263", "UGC 5637"],
    "NGC 4945 lead": ["NGC 4945"],
    "M81 lead": ["M81 infrared transient", "NGC 3031 infrared transient"],
    "NGC 55 lead": ["NGC 55 infrared"],
    "IC 342 lead": ["IC 342 transient"],
}
COORDS = ['"10:25:09.9" "+17:09:49"', '"102509.89+170949.6"', '"156.2912 17.1638"', '"J102509"']
CONTEXT = '(transient OR "luminous red nova" OR LRN OR ILRT OR "infrared transient" OR "obscured supernova" OR NEOWISE OR WISE OR JWST)'


def q(query, rows=50, fl="bibcode,title,year,author"):
    for attempt in range(4):
        r = httpx.get(API, headers=H, params={"q": query, "rows": rows, "fl": fl, "sort": "date desc"}, timeout=60)
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()["response"]
    raise RuntimeError("ADS rate-limited")


out = {}
for label, names in TARGETS.items():
    res = {}
    for n in names:
        resp = q(f'full:"{n}" AND full:{CONTEXT} AND year:2020-2026')
        res[n] = {"numFound": resp["numFound"], "docs": [{k: d.get(k) for k in ("bibcode", "title", "year")} for d in resp["docs"]]}
        time.sleep(1)
    out[label] = res
coords = {}
for c in COORDS:
    resp = q(f"full:{c}")
    coords[c] = {"numFound": resp["numFound"], "docs": [{k: d.get(k) for k in ("bibcode", "title", "year")} for d in resp["docs"]]}
    time.sleep(1)
out["OS-0030 coordinates"] = coords
# the WISE/NEOWISE transient and SPIRITS papers: do they mention NGC 3239?
surveys = q('(author:"De, Kishalay" AND (title:WISE OR title:NEOWISE OR title:"infrared transient" OR title:"mid-infrared"))'
            ' OR (title:SPIRITS) OR (title:"WISE" AND title:"transients" AND title:"nearby galaxies")', rows=200)
hits = []
for d in surveys["docs"]:
    r = q(f'bibcode:"{d["bibcode"]}" AND full:("NGC 3239" OR NGC3239 OR "Arp 263")', rows=1)
    if r["numFound"]:
        hits.append({k: d.get(k) for k in ("bibcode", "title", "year")})
    time.sleep(0.5)
out["survey papers mentioning NGC 3239"] = {"n_survey_papers_checked": surveys["numFound"], "hits": hits}
Path("hunts/H-0012/work/ads_novelty.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: ({n: v["numFound"] for n, v in vv.items()} if k != "survey papers mentioning NGC 3239" else vv)
                  for k, vv in out.items()}, indent=1))
