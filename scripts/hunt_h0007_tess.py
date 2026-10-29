"""H-0007: simple-aperture TESS FFI photometry from TESScut cubes (3x3 px aperture on the target, median background
from pixels > 4 px away). usage: hunt_h0007_tess.py CUTOUT_DIR OUT_PREFIX"""

import glob
import sys

import matplotlib
import numpy as np
import pandas as pd
from astropy.io import fits

matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows = []
files = sorted(glob.glob(f"{sys.argv[1]}/*.fits"))
fig, axs = plt.subplots(len(files), 1, figsize=(14, 3 * len(files)))
for ax, f in zip(np.atleast_1d(axs), files, strict=True):
    h = fits.open(f)
    d = h[1].data
    sec = h[0].header.get("SECTOR")
    cube = d["FLUX"]
    ny, nx = cube.shape[1:]
    cy, cx = ny // 2, nx // 2
    yy, xx = np.mgrid[:ny, :nx]
    r = np.hypot(yy - cy, xx - cx)
    ap = (np.abs(yy - cy) <= 1) & (np.abs(xx - cx) <= 1)
    bkg = np.nanmedian(cube[:, r > 4], axis=1)
    flux = np.nansum(cube[:, ap], axis=1) - ap.sum() * bkg
    ok = (d["QUALITY"] == 0) & np.isfinite(flux) & np.isfinite(d["TIME"])
    t = d["TIME"][ok] + 2457000 - 2400000.5  # BTJD -> MJD
    fl = flux[ok]
    med = np.nanmedian(fl)
    rows.append(
        pd.DataFrame({"sector": sec, "mjd": t, "flux": fl, "bkg": bkg[ok], "rel": fl / med})
    )
    ax.plot(t, fl / med, ".", ms=1)
    ax.set_title(f"sector {sec}  median aperture flux {med:.0f} e/s")
out = pd.concat(rows)
out.to_csv(f"{sys.argv[2]}.csv", index=False)
plt.tight_layout()
plt.savefig(f"{sys.argv[2]}.png", dpi=70)
print(
    out.groupby("sector").agg(
        n=("mjd", "size"),
        t0=("mjd", "min"),
        t1=("mjd", "max"),
        rel_min=("rel", "min"),
        rel_max=("rel", "max"),
        med=("flux", "median"),
    )
)
