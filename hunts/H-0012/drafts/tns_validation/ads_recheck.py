"""OS-0030 TNS pre-filing check: re-query ADS (token from ~/.config/oddsky/ads-token, never printed) for anything
on NGC 3239 / its aliases / the position entered since 2026-10-01, and for TNS reports (bibstem TNSTR/TNSAN) naming
NGC 3239.

    uv run python hunts/H-0012/drafts/tns_validation/ads_recheck.py
Output: ~/oddsky-runs/imaging/scratch/tns-validation-os0030/ads/ads_recheck.json
"""
import json
from pathlib import Path

import requests

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-validation-os0030/ads"
OUT.mkdir(parents=True, exist_ok=True)
TOKEN = (Path.home() / ".config/oddsky/ads-token").read_text().strip()
API = "https://api.adsabs.harvard.edu/v1/search/query"
Q = {
    "recent_NGC3239": 'full:("NGC 3239" OR "NGC3239" OR "Arp 263" OR "UGC 5637") entdate:[2026-10-01 TO *]',
    "tns_reports_NGC3239": 'full:("NGC 3239" OR "NGC3239") bibstem:(TNSTR OR TNSAN OR TNSCR)',
    "atel_NGC3239": 'full:("NGC 3239" OR "NGC3239") bibstem:ATel',
    "infrared_transient_NGC3239_2020plus": 'full:("NGC 3239" OR "NGC3239") full:(transient OR outburst OR NEOWISE) year:2020-2026',
    "position_strings": 'full:("10 25 09.9" OR "10:25:09.9" OR "102509.9" OR "J102509.89" OR "156.2912")',
}
res = {}
for k, q in Q.items():
    r = requests.get(API, params={"q": q, "fl": "bibcode,title,year,entdate", "rows": 200, "sort": "date desc"},
                     headers={"Authorization": f"Bearer {TOKEN}"}, timeout=60)
    if r.status_code != 200:
        res[k] = {"query": q, "error": f"HTTP {r.status_code}"}
    else:
        d = r.json()["response"]
        res[k] = {"query": q, "numFound": d["numFound"],
                  "docs": [{"bibcode": x["bibcode"], "title": (x.get("title") or [""])[0], "entdate": x.get("entdate")}
                           for x in d["docs"]]}
    print(k, res[k].get("numFound", res[k].get("error")))
    for x in res[k].get("docs", [])[:40]:
        print("   ", x["bibcode"], x["entdate"], x["title"][:110])
(OUT / "ads_recheck.json").write_text(json.dumps(res, indent=1))
