import sys, time, httpx, io
from astropy.io.votable import parse_single_table
out = sys.argv[1]
TAP = "https://heasarc.gsfc.nasa.gov/xamin/vo/tap/sync"
qs = {
 "swiftmastr": "SELECT obsid,target_name,ra,dec,start_time,xrt_exposure,uvot_exposure, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',156.2910,17.1639))*60 AS dist_arcmin FROM swiftmastr WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.2))=1 ORDER BY start_time",
 "chanmaster": "SELECT obsid,name,ra,dec,time,exposure,detector,status, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',156.2910,17.1639))*60 AS dist_arcmin FROM chanmaster WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.3))=1",
 "xmmmaster": "SELECT obsid,name,ra,dec,time,duration,status, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',156.2910,17.1639))*60 AS dist_arcmin FROM xmmmaster WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.3))=1",
 "numaster": "SELECT obsid,name,ra,dec,time,exposure_a,status, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',156.2910,17.1639))*60 AS dist_arcmin FROM numaster WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.2))=1",
 "nicermastr": "SELECT obsid,name,ra,dec,time,exposure FROM nicermastr WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.1))=1",
 "lsxps": "SELECT * FROM lsxps WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.0167))=1",
 "erass1main": "SELECT * FROM erass1main WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',156.2910,17.1639,0.0167))=1",
}
with httpx.Client(timeout=120, headers={"User-Agent":"oddsky-review/1.0"}) as c:
    for name,q in qs.items():
        try:
            r = c.post(TAP, data={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable","QUERY":q})
            try:
                t = parse_single_table(io.BytesIO(r.content)).to_table()
                f=open(f"{out}/heasarc_{name}.csv","w"); f.write(f"# ADQL: {q}\n# HTTP {r.status_code} nrows={len(t)}\n"); t.write(f,format="csv"); f.close()
                print("==",name,r.status_code,"nrows",len(t)); t.pprint(max_lines=60,max_width=250)
            except Exception as e:
                open(f"{out}/heasarc_{name}.txt","w").write(f"# ADQL: {q}\n# HTTP {r.status_code}\n"+r.text)
                print("==",name,r.status_code,"PARSEFAIL",repr(e)[:200], r.text[:600])
            if r.status_code==429: break
        except Exception as e:
            print("==",name,"ERR",repr(e))
        time.sleep(2)
