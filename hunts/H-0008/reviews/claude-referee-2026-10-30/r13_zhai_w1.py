"""r13: why the full Zhai+2024 list is mostly not recovered: AllWISE W1 of the 85 events with A >= 1.6 at a real NEOWISE visit
(nearest AllWISE source within 3", IRSA TAP), the expected W1 brightening if the ZTF source flux fraction applied in W1
(unknown: here the upper bound, unblended), and whether the star got into the 661 / the raw event list."""
import io, os, time
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
e = pd.read_csv(f"{HERE}/r12_eff.csv")
z = e[e.source.str.startswith("ZTF") & (e.A_real_visits >= 1.6)].copy()
from concurrent.futures import ThreadPoolExecutor


def one(r):
    q = (f"SELECT designation, w1mpro, w2mpro, ph_qual, nb, ra, dec FROM allwise_p3as_psd "
         f"WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {r.ra}, {r.dec}, {3/3600}))=1")
    d = pd.DataFrame()
    for attempt in range(4):  # IRSA TAP sometimes answers with an error page under load: retry, never read it as 'no source'
        try:
            d = pd.read_csv(io.StringIO(requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=300).text))
        except Exception:  # noqa: BLE001
            d = pd.DataFrame()
        if "w1mpro" in d:
            break
        time.sleep(15)
    if "w1mpro" not in d:
        return {"designation": "ERR bad response"}
    if not len(d):
        return {"designation": None}
    d["sep"] = np.hypot((d.ra - r.ra) * np.cos(np.radians(r.dec)), d.dec - r.dec) * 3600
    return d.sort_values("sep").iloc[0].drop(["ra", "dec"]).to_dict()


with ThreadPoolExecutor(2) as ex:
    w = list(ex.map(one, list(z.itertuples())))
z = pd.concat([z.reset_index(drop=True), pd.DataFrame(w)], axis=1)
z.to_csv(f"{HERE}/r13_zhai_w1.csv", index=False)
print("no AllWISE source within 3\":", int(z.designation.isna().sum()), "of", len(z))
print("W1 distribution (with source):", z.w1mpro.describe().round(2).to_dict())
for lim in (13, 14, 15):
    s = z[z.w1mpro <= lim]
    print(f"W1 <= {lim}: {len(s)}, recovered {int(s.recovered.sum())}")
pd.set_option("display.width", 200)
print(z.sort_values("w1mpro")[["name", "A_real_visits", "w1mpro", "nb", "sep", "b", "recovered"]].head(25).to_string(index=False))
