"""r4: every NEOWISE-R single exposure (IRSA TAP, neowiser_p1bs_psd) within 8" of the Gaia position of the candidates that
have NEOWISE coverage (J174618, J173332, J072830, J200958, J175414, J182124), all epochs 2013-2024, all detections (not only
those associated with the AllWISE source), so that merged/unextracted neighbours can be seen. Untrusted downloads -> data/frames/.
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r4_neowise_fetch.py"""
import io, os, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd, requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "frames")
C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str})
WANT = ["J174618", "J173332", "J072830", "J200958", "J175414", "J182124"]
COLS = ("mjd,ra,dec,sigra,sigdec,w1mpro,w1sigmpro,w1snr,w2mpro,w2sigmpro,w2snr,w1mag,w1sigm,w2mag,w2sigm,w1flux,w1sigflux,"
        "w2flux,w2sigflux,w1rchi2,w2rchi2,nb,na,w1sat,w2sat,cc_flags,ph_qual,qual_frame,qi_fact,saa_sep,moon_masked,sso_flg,"
        "w1x,w1y,scan_id,frame_num,source_id,allwise_cntr,r_allwise,w1sky,w1mpro_allwise,w2mpro_allwise")


def fetch(c):
    path = os.path.join(OUT, f"{c.source_id}.csv")
    if os.path.exists(path):
        return c.name, "cached"
    q = f"SELECT {COLS} FROM neowiser_p1bs_psd WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{c.ra},{c.dec},{8 / 3600}))=1"
    err = ""
    for attempt in range(3):
        try:
            r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=1200)
            if r.status_code == 200 and r.text.startswith("mjd"):
                d = pd.read_csv(io.StringIO(r.text), dtype={"cc_flags": str, "ph_qual": str, "moon_masked": str,
                                                            "allwise_cntr": "Int64", "source_id": str, "scan_id": str})
                d.to_csv(path, index=False)
                return c.name, len(d)
            err = f"HTTP {r.status_code} {r.text[:120]!r}"
        except Exception as e:  # noqa: BLE001
            err = str(e)[:120]
        time.sleep(20 * (attempt + 1))
    return c.name, "FAILED " + err


rows = [c for c in C.itertuples() if c.name[:7] in WANT]
with ThreadPoolExecutor(6) as ex:
    for name, res in ex.map(fetch, rows):
        print(name, res, flush=True)
