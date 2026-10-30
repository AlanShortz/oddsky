"""r19: why were bright, well-magnified Zhai+2024 events missed? AllWISE cntr for the Zhai events with W1 <= 13.2 and A >= 2.3 at a
real NEOWISE visit, then: is the star in the raw sky3lens event table (any kind, before cleaning), or in the brightening table?"""
import glob, io, os, time
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
names = ["ZTF19abagvae", "ZTF21abmnkml", "ZTF21abrgqfr", "ZTF21aawqeqn", "ZTF21acqomnw", "ZTF18absrimp", "ZTF22abcfjfp", "ZTF22aaajzoi"]
z = pd.read_csv(f"{HERE}/r12_eff.csv").set_index("name").loc[names]
rows = []
for n, r in z.iterrows():
    q = (f"SELECT cntr, designation, w1mpro, w2mpro, ra, dec FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {r.ra}, {r.dec}, {3/3600}))=1")
    for _ in range(4):
        d = pd.read_csv(io.StringIO(requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=300).text))
        if "cntr" in d:
            break
        time.sleep(15)
    d["sep"] = np.hypot((d.ra - r.ra) * np.cos(np.radians(r.dec)), d.dec - r.dec) * 3600
    d = d.sort_values("sep").head(1)
    rows.append({"name": n, "t0": r.t0, "tE": r.tE, "A": r.A_real_visits, **(d.iloc[0].to_dict() if len(d) else {})})
m = pd.DataFrame(rows)
ev = pd.concat([pd.read_parquet(f) for f in glob.glob(os.path.expanduser("~/oddsky-runs/h0008/events/*.parquet"))], ignore_index=True)
ev = ev[ev.allwise_cntr.isin(set(m.cntr.dropna().astype("int64")))]
b = pd.read_csv(f"{HERE}/../../work/sky3_brighten.csv")
pd.set_option("display.width", 250)
print(m.to_string(index=False))
print("in raw event table:", ev[["allwise_cntr", "kind", "edge", "t", "dw1", "dw2", "w1_med", "w2_med", "ccfrac_event", "ccfrac_other", "rchi_ratio", "n_visits"]].to_string(index=False))
print("in brighten table:", b[b.allwise_cntr.isin(set(m.cntr.dropna().astype("int64")))][["allwise_cntr", "t", "dw1", "clean", "w1w2", "rchi_ratio"]].to_string(index=False))
