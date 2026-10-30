"""r2: re-fetch ZTF (IRSA nph_light_curves, all catflags kept, 2" radius; cuts are applied later) and pull the NEOWISE
visit light curves from the sky3lens run (~/oddsky-runs/h0008/lightcurves). Outside the Oddsky tools: raw requests/pandas."""
import io, os, sys, time
import pandas as pd, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import TARGETS
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LC = os.path.expanduser("~/oddsky-runs/h0008/lightcurves")
EV = os.path.expanduser("~/oddsky-runs/h0008/events")
for k, (name, ra, dec, t, pix) in TARGETS.items():
    u = (f"https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves?POS=CIRCLE%20{ra}%20{dec}%200.000556&FORMAT=csv")
    r = requests.get(u, timeout=300)
    z = pd.read_csv(io.StringIO(r.text))
    z.to_csv(f"{D}/ztf_{k}.csv", index=False)
    lc = pd.read_parquet(f"{LC}/pixel={pix}.parquet")
    ev = pd.read_parquet(f"{EV}/pixel={pix}.parquet")
    e = ev[ev.t.sub(t).abs() < 0.01]
    cn = int(e.allwise_cntr.iloc[0])
    lc[lc.allwise_cntr == cn].to_csv(f"{D}/neowise_{k}.csv", index=False)
    print(k, "ZTF rows", len(z), "oids", z.oid.nunique() if len(z) else 0, "catflags0", int((z.catflags == 0).sum()) if len(z) else 0,
          "| NEOWISE visits", int((lc.allwise_cntr == cn).sum()))
    time.sleep(2)
