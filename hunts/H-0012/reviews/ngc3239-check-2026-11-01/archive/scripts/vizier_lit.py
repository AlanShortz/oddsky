import sys, time
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
out=sys.argv[1]; srv=sys.argv[2]
c = SkyCoord(156.2910, 17.1639, unit='deg')
v = Vizier(columns=["**","_r"], row_limit=50); v.VIZIER_SERVER=srv; v.TIMEOUT=120
f=open(f"{out}/vizier_literature_catalogues.txt","w")
# also list catalogue metadata to confirm which tables exist
for cat in ["J/ApJ/839/88","J/ApJS/252/32","J/ApJ/880/L20"]:
    try:
        tl = v.get_catalogs(cat)
        f.write(f"### {cat} tables: {[(t.meta.get('name'),len(t)) for t in tl]}  (first 50 rows fetched for existence check)\n")
    except Exception as e: f.write(f"### {cat} meta ERROR {e!r}\n")
    time.sleep(2)
    try:
        res = v.query_region(c, radius=300*u.arcsec, catalog=cat)
        f.write(f"=== {cat} cone r=300\": {[(t.meta.get('name'),len(t)) for t in res]}\n")
        for t in res: t.write(f, format='ascii.fixed_width')
    except Exception as e: f.write(f"=== {cat} ERROR {e!r}\n")
    f.flush(); time.sleep(2)
f.close(); print(open(f"{out}/vizier_literature_catalogues.txt").read()[:5000])
