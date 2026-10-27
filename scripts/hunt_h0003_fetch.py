"""Hunt H-0003, step 2: Gaia epoch photometry for the non-eclipsing candidates (resumable)."""
from pathlib import Path

import pandas as pd

from oddsky.data import gaia_epoch

here = Path("hunts/H-0003")
cache = here / "epoch"
cache.mkdir(exist_ok=True)
c = pd.read_csv(here / "candidates.csv")
c = c[c.gaia_eb.astype(str).str.lower() != "true"]
todo = [s for s in c.source_id if not (cache / f"{s}.parquet").exists()]
print(len(c), "non-EB;", len(todo), "to fetch", flush=True)
for i in range(0, len(todo), 50):
    for sid, df in gaia_epoch.fetch(todo[i:i + 50]).items():
        df.to_parquet(cache / f"{sid}.parquet", index=False)
    print(f"fetched {min(i + 50, len(todo))}/{len(todo)}", flush=True)
