import sys, io, requests, numpy as np, pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
src, ra, dec, rad = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
r = requests.get("https://vizier.cds.unistra.fr/viz-bin/asu-tsv", params={"-source": src, "-c": f"{ra} {dec}", "-c.rs": rad, "-out.max": 200}, timeout=200)
lines = [l for l in r.text.splitlines() if l and not l.startswith("#")]
if not lines: print("no rows"); sys.exit()
hdr = lines[0].split("\t"); rows = [l.split("\t") for l in lines[3:]]
d = pd.DataFrame(rows, columns=hdr)
rc = [c for c in hdr if c.startswith("RA")][0]; dc = [c for c in hdr if c.startswith("DE")][0]
d["sep"] = np.hypot((d[rc].astype(float) - ra) * np.cos(np.radians(dec)), d[dc].astype(float) - dec) * 3600
keep = [c for c in sys.argv[5].split(",")] if len(sys.argv) > 5 else hdr
print(d.sort_values("sep")[keep + ["sep"]].to_string())
