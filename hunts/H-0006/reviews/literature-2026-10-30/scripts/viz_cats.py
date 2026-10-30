"""Cone (r arcsec) in each listed VizieR catalogue at vizier.idia.ac.za. Records hits, zero-row results, and errors separately."""
import sys, warnings, time
warnings.filterwarnings("ignore")
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
outf, rad = sys.argv[1], float(sys.argv[2]); cats = sys.argv[3:]
c = SkyCoord(241.785503, -32.016950, unit="deg")
v = Vizier(columns=["**", "+_r"], row_limit=20, vizier_server="vizier.idia.ac.za", timeout=180)
out = open(outf, "a")
for cat in cats:
    for attempt in range(2):
        try:
            res = v.query_region(c, radius=rad * u.arcsec, catalog=cat)
            break
        except Exception as e:
            res = e; time.sleep(3)
    if isinstance(res, Exception):
        s = f"\n## {cat}: ERROR (not checked) {res!r}"[:300]
    elif len(res) == 0:
        s = f"\n## {cat}: 0 rows within {rad}\""
    else:
        s = ""
        for k in res.keys():
            t = res[k]
            s += f"\n## {cat} -> {k} ({t.meta.get('description','')}) rows={len(t)}\n" + "\n".join(t.pformat(max_lines=-1, max_width=-1))
    print(s.split("\n")[1][:200]); out.write(s + "\n"); out.flush()
