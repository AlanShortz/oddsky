import sys, time, httpx, io
from astropy.io.votable import parse_single_table
out = sys.argv[1]
TAP = "https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync"
qs = {
 "tables_xps": "SELECT table_name, description FROM TAP_SCHEMA.tables WHERE table_name LIKE '%xps%' OR table_name LIKE '%eras%' OR table_name LIKE '%erosita%' OR table_name LIKE '%swiftx%'",
 "swiftmastr": "SELECT obsid,name,ra,dec,start_time,xrt_exposure,uvot_exposure, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',156.2910,17.1639))*60 AS dist_arcmin FROM swiftmastr WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.2))=1 ORDER BY start_time",
 "chanmaster_full": "SELECT * FROM chanmaster WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.3))=1",
}
with httpx.Client(timeout=120, headers={"User-Agent":"oddsky-review/1.0"}) as c:
    for name,q in qs.items():
        r = c.post(TAP, data={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable","QUERY":q})
        try:
            t = parse_single_table(io.BytesIO(r.content)).to_table()
            f=open(f"{out}/heasarc_{name}.csv","w"); f.write(f"# ADQL: {q}\n# HTTP {r.status_code} nrows={len(t)}\n"); t.write(f,format="csv"); f.close()
            print("==",name,r.status_code,"nrows",len(t))
            if name=="chanmaster_full":
                for row in t:
                    print({k:str(row[k]) for k in t.colnames})
            else: t.pprint(max_lines=80,max_width=250)
        except Exception as e:
            print("==",name,r.status_code,"PARSEFAIL",r.text[:600])
        if r.status_code==429: break
        time.sleep(2)
