"""r1: re-fetch Gaia DR3 epoch photometry for the 21 H-0010 candidates, independently of the investigators' files.
(a) through oddsky.data.gaia_epoch.fetch_report(ids, releases=("Gaia DR3",)) -> data/epoch/<sid>.csv (normalised series);
(b) the raw datalink CSV (all columns, incl. transit_id, other flags, flux_over_error) -> data/epoch_raw/<sid>.csv.
Then compares (a) with the investigators' hunts/H-0010/data/epoch/<sid>.csv (same transits, same magnitudes).
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r1_gaia_epoch.py"""
import io, json, os, zipfile
import numpy as np, pandas as pd
from oddsky.data.gaia_epoch import fetch_report, DATALINK
from oddsky.data.http import request

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
os.makedirs(os.path.join(D, "epoch"), exist_ok=True)
os.makedirs(os.path.join(D, "epoch_raw"), exist_ok=True)
C = pd.read_csv(os.path.join(D, "candidates21.csv"), dtype={"source_id": str})
ids = [int(s) for s in C.source_id]

got, rep = fetch_report(ids, releases=("Gaia DR3",))
print("fetch_report:", json.dumps(rep["releases"]))
for sid, df in got.items():
    df.to_csv(os.path.join(D, "epoch", f"{sid}.csv"), index=False)

r = request("POST", DATALINK, timeout=300, retries=3, data=dict(RETRIEVAL_TYPE="EPOCH_PHOTOMETRY", ID=",".join(map(str, ids)),
            FORMAT="csv", DATA_STRUCTURE="DATAMODEL_STANDARD", RELEASE="Gaia DR3", VALID_DATA="false"))
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    for name in z.namelist():
        raw = pd.read_csv(io.StringIO(z.read(name).decode()), comment="#")
        if raw.empty:
            continue
        raw.to_csv(os.path.join(D, "epoch_raw", f"{raw.source_id.iloc[0]}.csv"), index=False)
print("raw columns:", list(raw.columns))

INV = os.path.join(HERE, "..", "..", "data", "epoch")
for c in C.itertuples():
    sid = int(c.source_id)
    a = got.get(sid)
    if a is None:
        print(c.name, "NO DATA"); continue
    b = pd.read_csv(os.path.join(INV, f"{sid}.csv"), dtype={"camera": str})
    m = a.merge(b, on=["camera", "band"], suffixes=("", "_inv"), how="outer", indicator=True)
    both = m[m._merge == "both"]
    dmag = np.nanmax(np.abs(both.mag - both.mag_inv)) if len(both) else np.nan
    print(f"{c.name} {sid}: mine {len(a)} rows, investigators {len(b)}, matched {len(both)}, max |dmag| {dmag:.2e}, "
          f"only-mine {int((m._merge=='left_only').sum())}, only-theirs {int((m._merge=='right_only').sum())}")
