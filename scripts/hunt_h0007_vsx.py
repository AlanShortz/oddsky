"""H-0007: VSX (B/vsx/vsx) within 6" through a VizieR mirror (CDS and www.aavso.org unreachable 2026-10-29)."""
import sys, io, time
import pandas as pd, requests
MIRRORS = ["https://vizier.idia.ac.za/viz-bin/asu-tsv", "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"]
a = pd.read_csv(sys.argv[1])
out = []
for r in a.itertuples():
    res = "ERR"
    for m in MIRRORS:
        try:
            t = requests.get(m, params={"-source": "B/vsx/vsx", "-c": f"{r.ra} {r.dec}", "-c.rs": 6, "-out": "_r Name Type Period max min", "-sort": "_r"}, timeout=60).text
            rows = [l for l in t.splitlines() if l and not l.startswith("#")]
            res = "; ".join("|".join(x.strip() for x in l.split("\t")) for l in rows[3:]) if len(rows) > 3 else ""
            break
        except Exception:  # noqa: BLE001
            continue
    out.append(res)
    time.sleep(0.3)
a["vsx"] = out
a.to_csv(sys.argv[1], index=False)
print(a[["designation", "vsx"]].to_string())
