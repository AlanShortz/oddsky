"""s3: Gaia DR3 epoch photometry (oddsky.data.gaia_epoch.fetch_report, releases=("Gaia DR3",), <= 50 ids per request) for every
source within 4" of a strong event, not only those flagged as having it, so the flag is checked empirically. Writes
data/epoch/<source_id>.csv and data/epoch_report.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, EPOCH, cones  # noqa: E402

from oddsky.data import gaia_epoch  # noqa: E402

os.makedirs(EPOCH, exist_ok=True)
ids = sorted(cones().source_id.unique())
got, rep = gaia_epoch.fetch_report([int(s) for s in ids], chunk=50, releases=("Gaia DR3",))
for sid, df in got.items():
    df.to_csv(os.path.join(EPOCH, f"{sid}.csv"), index=False)
rep["source_release"] = {str(k): v for k, v in rep["source_release"].items()}
rep["requested"] = len(ids)
json.dump(rep, open(os.path.join(DATA, "epoch_report.json"), "w"), indent=1)
print(f"requested {len(ids)}; epoch photometry for {len(got)}: {sorted(str(k) for k in got)}")
print(rep["releases"])
