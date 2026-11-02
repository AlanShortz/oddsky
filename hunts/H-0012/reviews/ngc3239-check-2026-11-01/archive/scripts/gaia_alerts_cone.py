import sys, csv, numpy as np
from astropy.coordinates import SkyCoord
rows = list(csv.reader(open(sys.argv[1], newline='')))
hdr = [h.strip().lstrip('#') for h in rows[0]]; data = [r for r in rows[1:] if len(r)>=4]
ra = np.array([float(r[2]) for r in data]); de = np.array([float(r[3]) for r in data])
c = SkyCoord(156.2910,17.1639,unit='deg'); s = SkyCoord(ra,de,unit='deg').separation(c).arcsec
print(f"Gaia alerts total={len(data)}; date range {min(r[1] for r in data)} .. {max(r[1] for r in data)}")
for lim in (60, 600):
    idx = np.where(s<lim)[0]; print(f"within {lim}\": {len(idx)}")
    for i in idx: print("  ", f"{s[i]:.1f}\"", data[i])
print("nearest:", f"{s.min():.1f}\"", data[int(np.argmin(s))])
