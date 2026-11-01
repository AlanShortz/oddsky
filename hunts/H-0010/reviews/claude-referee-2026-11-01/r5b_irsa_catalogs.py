"""r5b: AllWISE (allwise_p3as_psd) and 2MASS PSC (fp_psc) within 15" of the candidates with NEOWISE data, from IRSA TAP (CDS VizieR
was timing out on 2026-11-01). Offsets dx (east), dy (north) in arcsec from the Gaia DR3 position. Writes data/irsa_<sid>.csv.
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r5b_irsa_catalogs.py"""
import io, os
import numpy as np, pandas as pd, requests

HERE = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str}).set_index("source_id")
pd.set_option("display.width", 250)
Q = {"allwise": "SELECT ra,dec,w1mpro,w1sigmpro,w2mpro,w2sigmpro,w3mpro,w4mpro,cc_flags,ext_flg,nb,na,ph_qual,cntr FROM allwise_p3as_psd",
     "2mass": "SELECT ra,dec,j_m,h_m,k_m,ph_qual,cc_flg,bl_flg FROM fp_psc"}
for sid in ["4067152339419332992", "5958944416543307648", "5620272814897694848", "2054828730840779520", "4096047127002546560"]:
    c = C.loc[sid]
    print(f"\n=== {c['name']}")
    for lab, q in Q.items():
        p = os.path.join(HERE, "data", f"irsa_{lab}_{sid}.csv")
        if not os.path.exists(p):
            qq = q + f" WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{c.ra},{c.dec},{15/3600}))=1"
            r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": qq, "FORMAT": "csv"}, timeout=600)
            open(p, "w").write(r.text)
        t = pd.read_csv(p)
        t["dx"] = (t.ra - c.ra) * np.cos(np.radians(c.dec)) * 3600
        t["dy"] = (t.dec - c.dec) * 3600
        t["r"] = np.hypot(t.dx, t.dy)
        print(lab); print(t.drop(columns=["ra", "dec"]).sort_values("r").round(2).to_string(index=False))
