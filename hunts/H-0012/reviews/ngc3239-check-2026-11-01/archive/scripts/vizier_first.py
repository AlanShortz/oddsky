import sys
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
out=sys.argv[1]; srv=sys.argv[2]
c = SkyCoord(156.2910, 17.1639, unit='deg')
v = Vizier(columns=["_r","FIRST","RAJ2000","DEJ2000","Fpeak","Fint","Rms","Maj","Min","PA","c1","c2"], row_limit=200); v.VIZIER_SERVER=srv; v.TIMEOUT=120
res = v.query_region(c, radius=600*u.arcsec, catalog="VIII/92/first14")
with open(f"{out}/vizier_first14_r600.txt","w") as f:
    f.write(f"# VizieR {srv} VIII/92/first14 r=600\" around 156.2910 +17.1639\n")
    for t in res:
        t.sort('_r'); f.write(f"nrows={len(t)}\n"); t[:15].write(f, format='ascii.fixed_width')
    if not len(res): f.write("no rows\n")
print(open(f"{out}/vizier_first14_r600.txt").read())
