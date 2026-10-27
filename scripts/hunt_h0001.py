"""Hunt H-0001, step 1: the Gaia candidate list. Writes hunts/H-0001/candidates.csv.

Anonymous Gaia TAP queries are cut off after 60 s, so the sky is split into source_id ranges
(source_id encodes HEALPix position, and is indexed) and queried in chunks.
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from oddsky.data.gaia import adql

here = Path("hunts/H-0001")
parts = here / "parts"
parts.mkdir(exist_ok=True)
base = (here / "query.adql").read_text()
base = "\n".join(line for line in base.splitlines() if not line.strip().startswith("--"))
MAX_ID = 6917529027641081856
N = 192
edges = [int(MAX_ID * i / N) for i in range(N + 1)]


def run(i):
    f = parts / f"{i:03d}.csv"
    if f.exists():
        return i, "cached"
    q = base + f"\n  AND v.source_id BETWEEN {edges[i]} AND {edges[i + 1] - 1}"
    for attempt in range(3):
        try:
            df = adql(q, timeout=120)
            df.to_csv(f, index=False)
            return i, len(df)
        except Exception as e:  # noqa: BLE001
            err = str(e)[:120]
            time.sleep(5)
    return i, f"FAILED {err}"


t = time.time()
with ThreadPoolExecutor(3) as ex:
    for i, res in ex.map(run, range(N)):
        print(i, res, f"{time.time() - t:.0f}s", flush=True)
frames = [pd.read_csv(p) for p in sorted(parts.glob("*.csv")) if p.stat().st_size > 0]
df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
df.to_csv(here / "candidates.csv", index=False)
print(len(df), "candidates;", len(list(parts.glob("*.csv"))), "of", N, "chunks", flush=True)
sys.exit(0)
