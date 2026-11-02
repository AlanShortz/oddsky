"""Absolute astrometry of each HST visit drc against Gaia DR3 (proper-motion propagated to the visit epoch).

    uv run python -I hunts/H-0012/reviews/ngc3239-check-2026-11-01/hst_gaia_tie.py <hst dir>
Writes hst_gaia_tie.json: per image the median (dRA*cosDec, dDec) of HST - Gaia in mas, robust scatter, N.
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hst_lib as L  # noqa: E402

D = Path(sys.argv[1])
gaia = pd.read_csv(HERE / "cat" / "gaia_dr3_12arcmin.csv")
g = gaia[(gaia.phot_g_mean_mag < 20.7) & (gaia.phot_g_mean_mag > 15) & gaia.pmra.notna() & (gaia.ruwe < 1.6)].copy()
res = {}
for f in sorted(D.glob("hst_*_drc.fits")):
    name = f.name
    if any(k in name for k in ("hc_", "hg_", "hb_", "he_", "le_", "lf_")):
        continue
    with fits.open(f, memmap=True) as h:
        sci = h["SCI"].data
        w = WCS(h["SCI"].header)
        mjd = h[0].header["EXPSTART"]
    yr = 2000 + (mjd - 51544.5) / 365.25
    dt = yr - 2016.0
    ra = g.ra + g.pmra * dt / 3.6e6 / np.cos(np.radians(g.dec))
    de = g.dec + g.pmdec * dt / 3.6e6
    x, y = w.all_world2pix(np.c_[ra, de], 0).T
    rows = []
    for xi, yi, gid, gm in zip(x, y, g.source_id, g.phot_g_mean_mag):
        if not (20 < xi < sci.shape[1] - 20 and 20 < yi < sci.shape[0] - 20):
            continue
        st = sci[int(yi) - 12:int(yi) + 13, int(xi) - 12:int(xi) + 13]
        if not np.isfinite(st).all() or st.max() <= 0:
            continue
        cx, cy = L.centroid(sci, xi, yi, box=4)
        if not np.isfinite(cx) or np.hypot(cx - xi, cy - yi) > 12:
            continue
        fit = L.gauss2d_fit(sci, cx, cy, box=5)
        if fit is None:
            continue
        fx, fy, fl, sg, b = fit
        if sg > 2.5 or fl <= 0:  # extended (HII knot / cluster / galaxy)
            continue
        r_, d_ = w.all_pix2world([[fx, fy]], 0)[0]
        dra = (r_ - ra[g.source_id == gid].values[0]) * np.cos(np.radians(d_)) * 3.6e6
        dde = (d_ - de[g.source_id == gid].values[0]) * 3.6e6
        rows.append((str(gid), float(gm), dra, dde, float(sg)))
    if not rows:
        res[name] = dict(n=0)
        continue
    a = np.array([[r[2], r[3]] for r in rows])
    med = np.median(a, 0)
    for _ in range(3):
        rr = np.hypot(*(a - med).T)
        ok = rr < max(3 * 1.4826 * np.median(rr), 20)
        med = np.median(a[ok], 0)
    sc = 1.4826 * np.median(np.abs(a[ok] - med), 0)
    res[name] = dict(n=int(len(rows)), n_used=int(ok.sum()), dra_mas=float(med[0]), ddec_mas=float(med[1]),
                     scatter_mas=[float(sc[0]), float(sc[1])], err_mean_mas=[float(sc[0] / np.sqrt(ok.sum())), float(sc[1] / np.sqrt(ok.sum()))],
                     wcsname=fits.getheader(f, "SCI").get("WCSNAME"), stars=rows)
    print(name, res[name]["n"], res[name]["n_used"], round(med[0], 1), round(med[1], 1), np.round(sc, 1), res[name]["wcsname"], flush=True)
json.dump(res, open(HERE / "hst_gaia_tie.json", "w"), indent=1)
