"""H-0007 pass 3: NEOWISE single exposures for the faint candidates (W1 13-15), one 3" Gator cone per star.

The sky2 pass stored visit light curves only for W1 < 13. For 13 <= W1 < 15, sky2_features still records per-star W1/W2 peak-to-peak,
so the candidates are the stars with W1 and W2 swings >= 0.4 mag, stellar colours (|W1-W2| < 0.4) and a quiet first three visits
(bq export -> cands.csv; positions from AllWISE -> cands_pos.csv). Resumable: one parquet per star in OUT/exp/.
usage: hunt_h0007_faint_fetch.py CANDS_POS_CSV OUT_DIR [threads]
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from astropy.io import ascii as aascii

from oddsky.data.http import request

GATOR = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
COLS = ("ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qual_frame,qi_fact,saa_sep,moon_masked,cc_flags,ph_qual,nb,na,"
        "w1rchi2,w2rchi2,allwise_cntr,r_allwise,sso_flg,w1sat,w2sat")
cands = pd.read_csv(sys.argv[1])
out = Path(sys.argv[2]) / "exp"
out.mkdir(parents=True, exist_ok=True)
threads = int(sys.argv[3]) if len(sys.argv) > 3 else 6


def one(r):
    f = out / f"{r.cntr}.parquet"
    if f.exists():
        return "skip"
    p = dict(catalog="neowiser_p1bs_psd", spatial="cone", radius=3, radunits="arcsec", objstr=f"{r.ra} {r.dec}",
             outfmt=1, selcols=COLS)
    try:
        t = request("GET", GATOR, params=p, timeout=300).text
        df = aascii.read(t.splitlines(), format="ipac").to_pandas() if "|" in t[:20000] else pd.DataFrame()
    except Exception as e:  # noqa: BLE001
        return f"err {r.cntr} {str(e)[:80]}"
    df.to_parquet(f, index=False)
    return "ok"


with ThreadPoolExecutor(threads) as ex:
    for i, res in enumerate(ex.map(one, cands.itertuples())):
        if res.startswith("err") or i % 200 == 0:
            print(i, res, flush=True)
print("done", flush=True)
