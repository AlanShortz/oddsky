"""Hunt H-0003, step 1: Gaia + AllWISE candidate list for R CrB-like fades (chunked by source_id)."""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from oddsky.data.gaia import adql

here = Path("hunts/H-0003")
parts = here / "parts"
parts.mkdir(exist_ok=True)
base = "\n".join(ln for ln in (here / "query.adql").read_text().splitlines() if not ln.strip().startswith("--"))
MAX_ID, N = 6917529027641081856, 192
edges = [int(MAX_ID * i / N) for i in range(N + 1)]


def run(i):
    f = parts / f"{i:03d}.csv"
    if f.exists():
        return i, "cached"
    q = base + f"\n  AND v.source_id BETWEEN {edges[i]} AND {edges[i + 1] - 1}"
    err = ""
    for _ in range(3):
        try:
            adql(q, timeout=120).to_csv(f, index=False)
            return i, "ok"
        except Exception as e:  # noqa: BLE001
            err = str(e)[:120]
            time.sleep(5)
    return i, f"FAILED {err}"


t = time.time()
with ThreadPoolExecutor(3) as ex:
    for i, res in ex.map(run, range(N)):
        if res != "ok":
            print(i, res, flush=True)
frames = [pd.read_csv(p) for p in sorted(parts.glob("*.csv")) if p.stat().st_size > 5]
df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
df.to_csv(here / "candidates.csv", index=False)
print(len(df), "candidates from", len(list(parts.glob('*.csv'))), "chunks in", round(time.time() - t), "s", flush=True)
sys.exit(0)
