import sys, time
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
out = sys.argv[1]
c = SkyCoord(156.2910, 17.1639, unit='deg')
v = Vizier(columns=["**","_r"], row_limit=500); v.VIZIER_SERVER="vizier.cfa.harvard.edu"; v.TIMEOUT=90
log = open(f"{out}/vizier_coverage_and_details.txt","w")
# coverage check: big radius, report count + nearest few
for cat, r in [("VIII/92/first14",600),("VIII/65/nvss",600),("J/A+A/659/A1",900),("J/ApJS/255/30",600),("J/A+A/682/A34",600)]:
    try:
        res = v.query_region(c, radius=r*u.arcsec, catalog=cat)
        log.write(f"=== COVERAGE {cat} r={r}\": {[ (t.meta.get('name'),len(t)) for t in res]}\n")
        for t in res:
            t.sort('_r')
            keep=[k for k in t.colnames][:14]
            t[keep][:6].write(log, format='ascii.fixed_width')
    except Exception as e:
        log.write(f"=== {cat} ERROR {e!r}\n")
    log.flush(); time.sleep(2)
# details transposed
for cat, r in [("J/A+A/682/A34",30),("IX/58",30)]:
    res = v.query_region(c, radius=r*u.arcsec, catalog=cat)
    for t in res:
        log.write(f"=== DETAIL {t.meta.get('name')}\n")
        for row in t:
            for k in t.colnames:
                log.write(f"  {k:20s} = {row[k]}   [{t[k].unit}] {t[k].description or ''}\n")
    time.sleep(2)
log.close()
