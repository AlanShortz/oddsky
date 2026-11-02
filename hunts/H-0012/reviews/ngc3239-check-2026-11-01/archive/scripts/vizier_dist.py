import sys, time
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
out=sys.argv[1]; srv=sys.argv[2]
c = SkyCoord(156.270475, 17.16363, unit='deg')  # NED centre
v = Vizier(columns=["**","_r"], row_limit=20); v.VIZIER_SERVER=srv; v.TIMEOUT=120
f=open(f"{out}/vizier_distance_catalogues.txt","w")
for cat in ["J/ApJ/944/94","J/AJ/145/101","J/AJ/146/86","J/AJ/152/50","VII/237"]:
    try:
        res = v.query_region(c, radius=90*u.arcsec, catalog=cat)
        f.write(f"=== {cat} (r=90\" around NED centre): {[(t.meta.get('name'),len(t)) for t in res]}\n")
        for t in res:
            f.write(f"--- {t.meta.get('name')}\n")
            for row in t:
                for k in t.colnames: f.write(f"  {k:12s}= {row[k]}  [{t[k].unit}] {(t[k].description or '')[:70]}\n")
                f.write("\n")
    except Exception as e:
        f.write(f"=== {cat} ERROR {e!r}\n")
    f.flush(); time.sleep(2)
f.close(); print(open(f"{out}/vizier_distance_catalogues.txt").read()[:9000])
