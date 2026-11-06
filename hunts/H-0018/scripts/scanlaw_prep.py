"""Reduce the Gaia commanded scan law (EDR3/DR3 span) to one point per 30 s per field of view."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

src = f"{hd.RUNS}/data/scanlaw/CommandedScanLaw_001.csv.gz"
cols = ["bjd_fov1", "bjd_fov2", "obmt_time", "ra_fov1", "dec_fov1", "scan_angle_fov1", "ra_fov2", "dec_fov2", "scan_angle_fov2"]
parts = []
total = 0
for ch in pd.read_csv(src, usecols=cols, chunksize=1_000_000, dtype={"obmt_time": "int64"}):
    total += len(ch)
    keep = (ch.obmt_time // 10_000_000_000) % 3 == 0
    parts.append(ch[keep])
d = pd.concat(parts)
print("rows", total, "kept", len(d), "bjd range", d.bjd_fov1.min(), d.bjd_fov1.max())
np.savez_compressed(
    f"{hd.RUNS}/data/scanlaw/scan30s.npz",
    t=np.concatenate([d.bjd_fov1.values, d.bjd_fov2.values]),
    ra=np.concatenate([d.ra_fov1.values, d.ra_fov2.values]).astype(float),
    dec=np.concatenate([d.dec_fov1.values, d.dec_fov2.values]).astype(float),
    psi=np.concatenate([d.scan_angle_fov1.values, d.scan_angle_fov2.values]).astype(float),
    fov=np.concatenate([np.ones(len(d), "int8"), np.full(len(d), 2, "int8")]),
)
