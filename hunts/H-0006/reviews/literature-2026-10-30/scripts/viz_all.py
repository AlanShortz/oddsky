"""Cone search ALL VizieR catalogues within radius at the idia mirror; print table names + rows."""
import sys, warnings
warnings.filterwarnings("ignore")
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
out = open(sys.argv[1], "w")
ra, dec, rad = 241.785503, -32.016950, float(sys.argv[2])
v = Vizier(columns=["**", "+_r"], row_limit=50, vizier_server="vizier.idia.ac.za", timeout=300)
res = v.query_region(SkyCoord(ra, dec, unit="deg"), radius=rad * u.arcsec)
out.write(f"# VizieR (vizier.idia.ac.za) all-catalogue cone r={rad} arcsec around {ra} {dec}: {len(res)} tables\n")
for k in res.keys():
    t = res[k]
    out.write(f"\n## {k}  ({t.meta.get('description','')})  rows={len(t)}\n")
    t2 = t.copy()
    for c in t2.colnames:
        if t2[c].dtype.kind in "SUO":
            pass
    out.write("\n".join(t2.pformat(max_lines=-1, max_width=-1)) + "\n")
print(len(res))
for k in res.keys(): print(k, len(res[k]), res[k].meta.get('description','')[:110])
