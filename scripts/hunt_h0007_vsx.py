"""H-0007: VSX (B/vsx/vsx) within 6" through a VizieR mirror (CDS and www.aavso.org unreachable 2026-10-29)."""

import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

MIRRORS = [
    "https://vizier.idia.ac.za/viz-bin/asu-tsv",
    "https://vizier.cds.unistra.fr/viz-bin/asu-tsv",
]
a = pd.read_csv(sys.argv[1], dtype={"g_source_id": str})  # 19-digit Gaia ids: keep as text, or they round-trip as float


def lookup(r):
    for m in MIRRORS:
        try:
            t = requests.get(m, params={"-source": "B/vsx/vsx", "-c": f"{r.ra} {r.dec}", "-c.rs": 6, "-out": "_r Name Type Period max min",
                                        "-sort": "_r"}, timeout=60).text
            rows = [ln for ln in t.splitlines() if ln and not ln.startswith("#")]
            return "; ".join("|".join(x.strip() for x in ln.split("\t")) for ln in rows[3:]) if len(rows) > 3 else ""
        except Exception:  # noqa: BLE001
            continue
    return "ERR"


with ThreadPoolExecutor(4) as ex:
    out = list(ex.map(lookup, a.itertuples()))
a["vsx"] = out
a.to_csv(sys.argv[1], index=False)
print(a[["designation", "vsx"]].to_string())
