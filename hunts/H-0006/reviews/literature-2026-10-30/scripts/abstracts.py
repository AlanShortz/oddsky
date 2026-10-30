import sys, requests
out = open(sys.argv[1], "a")
tok = requests.get("https://ui.adsabs.harvard.edu/v1/accounts/bootstrap", headers={"User-Agent": "Mozilla/5.0"}, timeout=30).json()["access_token"]
for b in sys.argv[2:]:
    r = requests.get("https://api.adsabs.harvard.edu/v1/search/query", headers={"Authorization": f"Bearer {tok}"},
                     params={"q": f'bibcode:"{b}"', "fl": "bibcode,title,author,abstract,pub,doi,identifier", "rows": 1}, timeout=60).json()
    docs = r.get("response", {}).get("docs", [])
    s = f"\n=== {b}\n" + (f"{docs[0].get('title',[''])[0]} | {', '.join(docs[0].get('author',[])[:4])} | {docs[0].get('pub','')}\n{docs[0].get('abstract','(no abstract)')}\n" if docs else "NOT FOUND\n")
    print(s); out.write(s)
