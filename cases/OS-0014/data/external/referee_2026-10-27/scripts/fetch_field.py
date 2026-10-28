import sys, requests
ra, dec, rad, out, cat = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
cols = sys.argv[6] if len(sys.argv) > 6 else None
p = dict(catalog=cat, spatial="cone", radius=rad, radunits="arcsec", objstr=f"{ra} {dec}", outfmt=1)
if cols: p["selcols"] = cols
for i in range(4):
    r = requests.get("https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query", params=p, timeout=900)
    if "ERROR" not in r.text[:1000] and r.status_code == 200:
        break
    print("retry", r.text[:300])
open(out, "w").write(r.text)
print(len(r.text.splitlines()))
