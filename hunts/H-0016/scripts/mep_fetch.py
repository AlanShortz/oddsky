"""H-0016: AllWISE multi-epoch photometry (allwise_p3as_mep: every 2010-11 frame) for a list of AllWISE cntr ids.
usage: mep_fetch.py IN_CSV(allwise_cntr) OUT_CSV"""
import io
import sys
import time

import pandas as pd
import requests

ids = pd.read_csv(sys.argv[1]).allwise_cntr.astype("int64").unique().tolist()
rows = []
for i in range(0, len(ids), 100):
    q = ("SELECT cntr_mf, mjd, w1mpro_ep, w1sigmpro_ep, w1rchi2_ep, w2mpro_ep, w2sigmpro_ep, w2rchi2_ep, w1flux_ep, w1sigflux_ep, w2flux_ep, w2sigflux_ep, "
         "nb, cc_flags, qi_fact, saa_sep, moon_masked, frame_id FROM allwise_p3as_mep WHERE cntr_mf IN (" + ",".join(map(str, ids[i:i + 100])) + ")")
    for _k in range(4):
        try:
            r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=900)
            r.raise_for_status()
            rows.append(pd.read_csv(io.StringIO(r.text)))
            break
        except Exception as e:  # noqa: BLE001
            print("retry", i, e, file=sys.stderr)
            time.sleep(20)
    print(i, len(ids), flush=True)
pd.concat(rows).to_csv(sys.argv[2], index=False)
