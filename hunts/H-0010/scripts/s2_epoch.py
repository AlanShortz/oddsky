"""s2: Gaia DR3 epoch photometry (G, BP, RP per transit) for the 67 sources and for every Gaia DR3 neighbour within 6"
that has published epoch photometry. gaia_epoch.fetch_report, DR3 only, <= 50 ids per request.

Run from the repo root: uv run python -I hunts/H-0010/scripts/s2_epoch.py [--neighbours]
Writes hunts/H-0010/data/epoch/<source_id>.csv and epoch_report*.json."""
import json
import os
import sys

import pandas as pd

from oddsky.data import gaia_epoch

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
EP = os.path.join(DATA, "epoch")
os.makedirs(EP, exist_ok=True)


def main():
    neigh = "--neighbours" in sys.argv
    if neigh:
        nb = pd.read_csv(os.path.join(DATA, "neighbours.csv"), dtype={"nb_source_id": str, "target": str})
        ids = sorted(set(nb[nb.has_epoch_photometry.astype(str).str.lower() == "true"].nb_source_id))
        tag = "neighbours"
    else:
        ids = pd.read_csv(os.path.join(DATA, "unpub.csv"), dtype={"source_id": str}).source_id.tolist()
        tag = "targets"
    ids = [s for s in ids if not os.path.exists(os.path.join(EP, f"{s}.csv"))]
    print(f"{tag}: fetching {len(ids)}")
    if not ids:
        return
    got, rep = gaia_epoch.fetch_report([int(s) for s in ids], releases=("Gaia DR3",))
    rep["source_release"] = {str(k): v for k, v in rep["source_release"].items()}
    with open(os.path.join(DATA, f"epoch_report_{tag}.json"), "w") as f:
        json.dump(rep, f, indent=1)
    for sid, df in got.items():
        df.to_csv(os.path.join(EP, f"{sid}.csv"), index=False)
    missing = sorted(set(ids) - {str(k) for k in got})
    print(f"got {len(got)}; missing {len(missing)}: {missing}")
    print(rep["releases"])


if __name__ == "__main__":
    main()
