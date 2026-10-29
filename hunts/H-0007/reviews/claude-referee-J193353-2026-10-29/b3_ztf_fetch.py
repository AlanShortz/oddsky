"""b3: fetch IRSA ZTF DR light curves of all objects with 14.3 < mag < 16.8 within 3.6' of J193353 (g and r), for comparison
stars in the same field/CCD/quadrant. Outside the Oddsky tools (raw IRSA nph_light_curves). Writes /tmp/j1933ref/ztf_cone.csv."""
from oddsky.data.http import request

API = "https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves"
p = {"POS": "CIRCLE 293.471115 -21.3037472 0.06", "BANDNAME": "g,r", "MAG": "14.3 16.8", "FORMAT": "csv"}
r = request("GET", API, params=p, timeout=1200)
open("/tmp/j1933ref/ztf_cone.csv", "w").write(r.text)
print(len(r.text.splitlines()), "lines")
