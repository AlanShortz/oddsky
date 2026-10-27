import time, pyvo, sys
import numpy as np
from astropy.table import Table
from oddsky.data.gaia import adql
stars = adql("""SELECT TOP 300 source_id, ra, dec, phot_g_mean_mag FROM gaiadr3.gaia_source
WHERE random_index < 2000000 AND phot_g_mean_mag BETWEEN 11 AND 13.5 AND bp_rp BETWEEN 0.6 AND 1.3
AND parallax_over_error > 20 AND ruwe < 1.3 AND ABS(b) > 15
AND phot_g_mean_mag + 5*LOG10(parallax/100) BETWEEN 3 AND 7""")
print(len(stars), "stars", flush=True)
W = [(56600, 57400), (57400, 58150), (58150, 58900), (58900, 59650), (59650, 60500)]
rows = []
for i, s in stars.iterrows():
    for k, (lo, hi) in enumerate(W):
        rows.append((i * 10 + k, int(s.source_id) % 2**62, s.ra, s.dec, lo, hi))
up = Table(rows=rows, names=("rid", "gid", "ura", "udec", "tlo", "thi"))
q = """SELECT up.rid, COUNT(*) AS cnt, AVG(nw.w1mpro) AS w1, AVG(nw.w2mpro) AS w2, STDDEV(nw.w1mpro) AS w1sd, STDDEV(nw.w2mpro) AS w2sd
FROM TAP_UPLOAD.up AS up, neowiser_p1bs_psd AS nw
WHERE CONTAINS(POINT('ICRS', nw.ra, nw.dec), CIRCLE('ICRS', up.ura, up.udec, 0.000833)) = 1
AND nw.mjd BETWEEN up.tlo AND up.thi AND nw.qual_frame > 0 AND nw.w1snr > 5 AND nw.w2snr > 5 AND nw.nb = 1 AND nw.saa_sep > 0
GROUP BY up.rid"""
t0 = time.time()
svc = pyvo.dal.TAPService("https://irsa.ipac.caltech.edu/TAP")
r = svc.run_async(q, uploads={"up": up}).to_table().to_pandas()
print("OK", round(time.time() - t0), "s", len(r), "rows", flush=True)
print(r.head(12), flush=True)
