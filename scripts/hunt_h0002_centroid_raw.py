"""Per-visit NEOWISE centroid of one AllWISE source from the raw Parquet on AWS (no IRSA needed), measured along the
line from its Gaia position to a neighbour. A brightening on the star leaves the centroid put; a neighbour that flares
drags it toward the neighbour.

python scripts/hunt_h0002_centroid_raw.py <allwise_cntr> <healpix_k5_pixel> <ra> <dec> <neighbour_ra> <neighbour_dec>
"""
import sys

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

from oddsky.sky import neowise_pixel as npx

cntr, pixel = int(sys.argv[1]), int(sys.argv[2])
gra, gde, nra, nde = map(float, sys.argv[3:7])  # Gaia epoch 2016; proper motion is negligible at this precision

fs = npx.s3()
rows = []
for rel in npx.RELEASES:
    path = (f"{npx.BUCKET}/{rel}/neowiser-healpix_k5-{rel}.parquet/healpix_k0={pixel >> 10}/"
            f"healpix_k5={pixel}/part0.snappy.parquet")
    try:
        pf = pq.ParquetFile(fs.open_input_file(path))
    except (FileNotFoundError, OSError):
        continue
    for batch in pf.iter_batches(batch_size=2_000_000, columns=[*npx.COLUMNS, "ra", "dec"]):
        mask = pc.fill_null(pc.equal(batch["allwise_cntr"], cntr), False)
        if pc.any(mask).as_py():
            rows.append(batch.filter(mask).to_pandas())

d = pd.concat(rows)
d = d[npx.quality(d, "w1") | npx.quality(d, "w2")].sort_values("mjd")
d["visit"] = (d.mjd.diff() > npx.VISIT_GAP).cumsum()
cosd = np.cos(np.radians(gde))
d["dx"] = (d.ra - gra) * cosd * 3600
d["dy"] = (d.dec - gde) * 3600
ux, uy = (nra - gra) * cosd * 3600, (nde - gde) * 3600
sep = np.hypot(ux, uy)
d["along"] = (d.dx * ux + d.dy * uy) / sep  # arcsec toward the neighbour


def robust_err(x):
    return 1.4826 * np.median(np.abs(x - x.median())) / np.sqrt(len(x))


v = d.groupby("visit").agg(t=("mjd", "median"), n=("mjd", "size"), w2=("w2mpro", "median"),
                           along=("along", "median"), along_err=("along", robust_err),
                           dx=("dx", "median"), dy=("dy", "median"))
v["offset"] = np.hypot(v.dx, v.dy)
print(f'neighbour at {sep:.2f}"')
print(v.drop(columns=["dx", "dy"]).round(3).to_string())
