"""TNS packet 2026-11: read the ADS abstracts of the hits that could concern the candidates (token from
~/.config/oddsky/ads-token, never printed).

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/ads_abstracts.py BIBCODE [BIBCODE ...]
Output: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/archives/ads_abstracts.json (appended)
"""
import json
import sys
import time
from pathlib import Path

import requests

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/archives/ads_abstracts.json"
tok = (Path.home() / ".config/oddsky/ads-token").read_text().strip()
have = json.loads(OUT.read_text()) if OUT.exists() else {}
for b in sys.argv[1:]:
    time.sleep(1.5)
    r = requests.get("https://api.adsabs.harvard.edu/v1/search/query",
                     params={"q": f"bibcode:{b}", "fl": "bibcode,title,author,abstract,pubdate"},
                     headers={"Authorization": f"Bearer {tok}"}, timeout=60)
    if r.status_code != 200:
        have[b] = {"error": f"HTTP {r.status_code} (not a null result)"}
    else:
        docs = r.json()["response"]["docs"]
        have[b] = docs[0] if docs else {"error": "no document returned (not a null result)"}
    d = have[b]
    print("==", b, d.get("pubdate"), (d.get("title") or [""])[0], "|", "; ".join((d.get("author") or [])[:6]))
    print(d.get("abstract", d.get("error")))
OUT.write_text(json.dumps(have, indent=1))
