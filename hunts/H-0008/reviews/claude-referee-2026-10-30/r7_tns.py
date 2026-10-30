"""r7: TNS cone search (60") for the five targets, one request every 30 s; HTTP 429 or any error = 'unknown', never 'nothing'."""
import io, os, sys, time
import pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from targets import TARGETS
out = []
for k, (name, ra, dec, t, pix) in TARGETS.items():
    try:
        r = requests.get("https://www.wis-tns.org/search", params={"ra": ra, "decl": dec, "radius": 60, "coords_unit": "arcsec", "format": "csv"},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        if r.status_code != 200:
            res = f"UNKNOWN (HTTP {r.status_code})"
        else:
            d = pd.read_csv(io.StringIO(r.text)) if r.text.strip() else pd.DataFrame()
            res = "none" if "Name" not in d or d.empty else "; ".join(f"{n} ({ty}, {dt}, {rep})" for n, ty, dt, rep in zip(d["Name"], d["Obj. Type"], d["Discovery Date (UT)"], d.get("Reporting Group", [""] * len(d))))
    except Exception as e:  # noqa: BLE001
        res = f"UNKNOWN ({str(e)[:80]})"
    print(name, "->", res, flush=True)
    out.append({"target": name, "tns": res})
    time.sleep(30)
pd.DataFrame(out).to_csv(f"{HERE}/r7_tns.csv", index=False)
