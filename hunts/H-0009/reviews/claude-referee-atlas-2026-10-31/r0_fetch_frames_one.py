"""r0 (function only, imported by r14): NEOWISE single exposures (IRSA TAP, neowiser_p1bs_psd) within 6" of every strong unexplained event (122) and every
known-lens recovery (118) of H-0009, all epochs. One CSV per AllWISE cntr in data/frames/ (untrusted downloads; read as data).
Slow (~80-100 s per cone at IRSA); runs 6 cones in parallel and skips files already present."""
import io
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
W9 = os.path.abspath(os.path.join(HERE, "..", "..", "work"))
OUT = os.path.join(HERE, "data", "frames")
os.makedirs(OUT, exist_ok=True)
COLS = ("mjd,ra,dec,sigra,sigdec,w1mpro,w1sigmpro,w1snr,w2mpro,w2sigmpro,w2snr,w1mag,w1sigm,w2mag,w2sigm,w1flux,w1sigflux,"
        "w2flux,w2sigflux,w1rchi2,w2rchi2,nb,na,w1sat,w2sat,cc_flags,ph_qual,qual_frame,qi_fact,saa_sep,moon_masked,sso_flg,"
        "w1x,w1y,scan_id,frame_num,source_id,allwise_cntr,r_allwise,w1sky,w1mpro_allwise,w2mpro_allwise")


def fetch(row):
    cntr, ra, dec = row
    path = os.path.join(OUT, f"{cntr}.csv")
    if os.path.exists(path):
        return cntr, "cached"
    q = (f"SELECT {COLS} FROM neowiser_p1bs_psd WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{6 / 3600}))=1")
    for attempt in range(3):
        try:
            r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=900)
            if r.status_code == 200 and r.text.startswith("mjd"):
                d = pd.read_csv(io.StringIO(r.text), dtype={"cc_flags": str, "ph_qual": str, "moon_masked": str,
                                                            "allwise_cntr": "Int64", "source_id": str, "scan_id": str})
                d.to_csv(path + ".tmp", index=False)
                os.replace(path + ".tmp", path)
                return cntr, len(d)
            err = f"HTTP {r.status_code} {r.text[:120]!r}"
        except Exception as e:  # noqa: BLE001
            err = str(e)[:120]
        time.sleep(20 * (attempt + 1))
    return cntr, "FAILED " + err


s = pd.read_csv(os.path.join(W9, "sky4_strong.csv"))
k = pd.read_csv(os.path.join(W9, "sky4_classified.csv"))
