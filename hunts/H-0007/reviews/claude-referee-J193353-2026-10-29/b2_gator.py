"""b2: fetch NEOWISE single-exposure photometry (neowiser_p1bs_psd) in a 20' cone around J193353 for the event visit
(2020 Apr 9-14) and the adjacent visits (2019 Oct, 2020 Sep), plus 1 deg cone of bright stars (W1 < 6) in the event visit.
Outside the Oddsky tools (raw IRSA Gator). Writes /tmp/j1933ref/wide.parquet and /tmp/j1933ref/bright1deg.parquet."""
import pandas as pd
from astropy.io import ascii as aascii

from oddsky.data.http import request

G = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
COLS = ("ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qual_frame,qi_fact,nb,na,w1rchi2,w2rchi2,allwise_cntr,r_allwise,scan_id,frame_num,"
        "cc_flags,ph_qual,sso_flg,moon_masked,saa_sep,w1sat,w2sat")
OBJ = "293.471115 -21.3037472"


def gator(radius, constraints):
    p = dict(catalog="neowiser_p1bs_psd", spatial="cone", radius=radius, radunits="arcsec", objstr=OBJ, outfmt=1, selcols=COLS,
             constraints=constraints)
    r = request("GET", G, params=p, timeout=1200)
    return aascii.read(r.text.splitlines(), format="ipac").to_pandas()


out = []
for lo, hi, lab in [(58948.5, 58954.5, "ev"), (58748.5, 58750.3, "pre"), (59112.5, 59118.5, "post")]:
    d = gator(1200, f"mjd between {lo} and {hi} and w1mpro < 15.0")
    d["lab"] = lab
    out.append(d)
    print(lab, len(d), d.mjd.min(), d.mjd.max(), "scans", sorted(d.scan_id.unique()))
pd.concat(out).to_parquet("/tmp/j1933ref/wide.parquet")
b = gator(3600, "mjd between 58948.5 and 58954.5 and w1mpro < 7.5")
b.to_parquet("/tmp/j1933ref/bright1deg.parquet")
print("bright (W1<7.5) detections within 1 deg in event visit:", len(b))
