import sys, time
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
out = sys.argv[1]
c = SkyCoord(156.2910, 17.1639, unit='deg')
jobs = [
 ("VIII/92/first14", 10), ("VIII/65/nvss", 10), ("J/A+A/659/A1", 10),
 ("J/ApJS/255/30", 10), ("J/A+A/682/A34", 30), ("IX/58", 30),  # 2SXPS
 ("IX/69", 30), # 4XMM-DR13?
 ("J/ApJS/220/30", 60),
]
v = Vizier(columns=["**","_r"], row_limit=50)
v.VIZIER_SERVER = "vizier.cfa.harvard.edu"
v.TIMEOUT = 60
log = open(f"{out}/vizier_results.txt","w")
for cat, r in jobs:
    try:
        res = v.query_region(c, radius=r*u.arcsec, catalog=cat)
        log.write(f"=== {cat} r={r}arcsec : {len(res)} tables\n")
        for t in res:
            log.write(f"--- {t.meta.get('name')} nrows={len(t)}\n")
            t.write(log, format='ascii.fixed_width', overwrite=True) if len(t) else None
    except Exception as e:
        log.write(f"=== {cat} ERROR {e!r}\n")
    log.flush(); time.sleep(1.5)
log.close()
