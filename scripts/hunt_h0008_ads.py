"""H-0008: ADS full-text search for a candidate's names and coordinate strings (anonymous ADS UI token, no account needed).
usage: hunt_h0008_ads.py "query 1" "query 2" ...   (each query is searched as full:"...")"""

import sys
import time

import requests

tok = requests.get("https://api.adsabs.harvard.edu/v1/accounts/bootstrap", headers={"User-Agent": "Mozilla/5.0"},
                   timeout=30).json()["access_token"]
for q in sys.argv[1:]:
    r = requests.get("https://api.adsabs.harvard.edu/v1/search/query", headers={"Authorization": f"Bearer {tok}"},
                     params={"q": f'full:"{q}"', "fl": "bibcode,title,year", "rows": 20}, timeout=60)
    d = r.json()
    n = d.get("response", {}).get("numFound", "ERR " + str(r.status_code))
    print(f'full:"{q}" -> {n}')
    for doc in d.get("response", {}).get("docs", [])[:10]:
        print("   ", doc["bibcode"], (doc.get("title") or [""])[0][:100])
    time.sleep(1)
