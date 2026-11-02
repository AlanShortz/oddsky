"""ADS full-text novelty check for the two real h0012b leads: NGC 2403 obs#50 (07:36:54.7 +65:35:53, periodic mid-IR
outbursts) and NGC 55 fsn#7 (00:15:13.9 -39:12:53, fading dusty source). Token from ~/.config/oddsky/ads-token (never
printed). Writes ads_novelty_h0012b.json next to this script. Read-only.
    uv run python hunts/H-0012/reviews/h0012b-referee/ads_novelty_h0012b.py
"""

import json
import time
from pathlib import Path

import httpx

TOKEN = (Path.home() / ".config/oddsky/ads-token").read_text().strip()
API = "https://api.adsabs.harvard.edu/v1/search/query"
H = {"Authorization": f"Bearer {TOKEN}"}
OUT = Path(__file__).with_name("ads_novelty_h0012b.json")
TARGETS = {
    "NGC 2403 obs#50": {
        "coords": ['"07:36:54.7"', '"073654.7"', '"07 36 54.7"', '"114.228"', '"J073654"', '"7:36:54.7"'],
        "topic": ['full:"NGC 2403" full:(periodic OR "colliding wind" OR "dust-forming" OR "WC binary" OR "episodic dust")',
                  'full:"NGC 2403" full:("mid-infrared variable" OR "infrared variable" OR SPIRITS OR "dust-obscured")',
                  'full:"NGC 2403" full:(WISE OR NEOWISE) full:(variable OR outburst)'],
    },
    "NGC 55 fsn#7": {
        "coords": ['"00:15:13.9"', '"001513.9"', '"00 15 13.9"', '"3.8079"', '"J001513"', '"0:15:13.9"'],
        "topic": ['full:"NGC 55" full:("B[e]" OR LBV OR "luminous blue variable" OR "Wolf-Rayet" OR "dusty massive")',
                  'full:"NGC 55" full:("mid-infrared variable" OR "infrared variable" OR SPIRITS OR fading)',
                  'full:"NGC 55" full:(WISE OR NEOWISE OR Spitzer) full:(variable OR dimming)'],
    },
}


def q(query, rows=60):
    for attempt in range(4):
        r = httpx.get(API, headers=H, params={"q": query, "rows": rows, "fl": "bibcode,title,year"}, timeout=60)
        if r.status_code == 200:
            d = r.json()["response"]
            return {"n": d["numFound"], "docs": [{"bibcode": x["bibcode"], "year": x.get("year"),
                                                  "title": (x.get("title") or [""])[0][:140]} for x in d["docs"]]}
        time.sleep(5 * (attempt + 1))
    return {"error": f"HTTP {r.status_code}"}


out = {}
for name, t in TARGETS.items():
    res = {}
    for c in t["coords"]:
        res[f"full:{c}"] = q(f"full:{c}")
        time.sleep(1)
    for s in t["topic"]:
        res[s] = q(s)
        time.sleep(1)
    out[name] = res
    for k, v in res.items():
        print(name, "|", k, "|", v.get("n", v.get("error")))
OUT.write_text(json.dumps(out, indent=1))
