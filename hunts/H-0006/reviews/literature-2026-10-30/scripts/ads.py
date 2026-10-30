"""ADS search with anonymous bootstrap token. usage: ads.py outfile 'raw query 1' 'raw query 2' ... (raw ADS syntax)"""
import sys, time, json, requests
out = open(sys.argv[1], "a")
def p(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n")
tok = None
for url in ("https://ui.adsabs.harvard.edu/v1/accounts/bootstrap", "https://api.adsabs.harvard.edu/v1/accounts/bootstrap"):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        tok = r.json()["access_token"]; p(f"# token from {url}: ok"); break
    except Exception as e:
        p(f"# token from {url}: FAIL {e!r}")
rows = int(__import__("os").environ.get("ROWS", "25"))
for q in sys.argv[2:]:
    try:
        r = requests.get("https://api.adsabs.harvard.edu/v1/search/query", headers={"Authorization": f"Bearer {tok}"},
                         params={"q": q, "fl": "bibcode,title,year,first_author", "rows": rows, "sort": "date desc"}, timeout=60)
        d = r.json()
        n = d.get("response", {}).get("numFound", f"ERR {r.status_code} {str(d)[:200]}")
    except Exception as e:
        n, d = f"ERR {e!r}", {}
    p(f"\nQUERY {q}  ->  numFound={n}")
    for doc in d.get("response", {}).get("docs", []):
        p("   ", doc["bibcode"], "|", (doc.get("first_author") or ""), "|", (doc.get("title") or [""])[0][:140])
    time.sleep(1)
