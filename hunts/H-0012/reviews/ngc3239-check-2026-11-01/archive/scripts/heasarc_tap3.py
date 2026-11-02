import sys, time, httpx, io
from astropy.io.votable import parse_single_table
out = sys.argv[1]
TAP = "https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync"
qs = {
 "swiftlsxps": "SELECT *, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',156.2910,17.1639))*3600 AS dist_arcsec FROM swiftlsxps WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.05))=1",
 "erass1hard": "SELECT *, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',156.2910,17.1639))*3600 AS dist_arcsec FROM erass1hard WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.0167))=1",
 "erassmastr": "SELECT *, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',156.2910,17.1639))*3600 AS dist_arcsec FROM erassmastr WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.0167))=1",
}
with httpx.Client(timeout=120, headers={"User-Agent":"oddsky-review/1.0"}) as c:
    for name,q in qs.items():
        r = c.post(TAP, data={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable","QUERY":q})
        try:
            t = parse_single_table(io.BytesIO(r.content)).to_table()
            f=open(f"{out}/heasarc_{name}.csv","w"); f.write(f"# ADQL: {q}\n# HTTP {r.status_code} nrows={len(t)}\n"); t.write(f,format="csv"); f.close()
            print("==",name,r.status_code,"nrows",len(t))
            for row in t:
                print({k:str(row[k]) for k in t.colnames if str(row[k]) not in ('--','','nan')})
        except Exception as e:
            print("==",name,r.status_code,"PARSEFAIL",r.text[:600])
        if r.status_code==429: break
        time.sleep(2)
