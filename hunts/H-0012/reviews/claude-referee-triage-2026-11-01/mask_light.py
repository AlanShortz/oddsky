"""Fraction of each bright galaxy's W1 light (inside the runner's 1.2 x a26/2 search circle, on the tile holding
the centre) that falls on pixels the runner masks (unWISE ARTIFACT_BITS dilated 2 px + nucleus circle).
Uses ONE neo11 epoch image (img-m, W1, e013 or the nearest available) per galaxy - not a reference stack.

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/mask_light.py
Writes mask_light.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "infra" / "gcp"))
from imaging_tile import galaxy_from_row  # noqa: E402

from oddsky.imaging import PIXSCALE, fetch, tiles  # noqa: E402

T = pd.read_csv(ROOT / "hunts/H-0012/work/targets_10mpc.csv").set_index("Name", drop=False)
GALS = ["NGC4945", "NGC5128", "NGC0253", "MESSIER081", "IC0342", "NGC6946", "NGC5236", "NGC4736", "NGC5102",
        "MESSIER082", "NGC5194", "MESSIER101", "NGC2403", "NGC4258", "NGC1068" if "NGC1068" in T.index else "NGC5055"]
rows = []
for g in GALS:
    r = T.loc[g]
    gal = galaxy_from_row(r)
    tl = [t for t in str(r.tiles).split(",") if t]
    best = None
    for t in tl:
        x, y = tiles.wcs_for(t).all_world2pix([[gal.ra, gal.dec]], 0)[0]
        e = min(x, y, 2047 - x, 2047 - y)
        if best is None or e > best[0]:
            best = (e, t, x, y)
    _, tile, xc, yc = best
    img = None
    for ep in (13, 12, 14, 11, 15):
        try:
            p = fetch.download(f"{fetch.BASE}/{fetch.rel_path(tile, 1, ep, 'img-m')}", fetch.local_path(tile, 1, ep, "img-m"))
            img = fits.getdata(p).astype(float)
            break
        except Exception:  # noqa: BLE001
            continue
    msk = fits.getdata(fetch.fetch_mask(tile)).astype(np.int64)
    yy, xx = np.mgrid[:2048, :2048]
    w = tiles.wcs_for(tile)
    rr = np.hypot(xx - xc, yy - yc) * PIXSCALE / 60  # arcmin
    search = rr <= gal.search_scale * gal.d25_arcmin / 2
    art = ndimage.binary_dilation((msk & fetch.ARTIFACT_BITS) != 0, iterations=2)
    nuc = rr * 60 <= gal.nucleus_mask_arcsec
    m = art | nuc
    sky = np.median(img[(rr > gal.search_scale * gal.d25_arcmin / 2) & (rr < gal.search_scale * gal.d25_arcmin / 2 + 3) & ~art])
    light = np.clip(img - sky, 0, None) * search
    rows.append(dict(galaxy=g, tile=tile, search_area_masked=float((m & search).sum() / search.sum()),
                     light_masked=float((light * m).sum() / light.sum()),
                     light_masked_bits_only=float((light * art).sum() / light.sum()),
                     light_masked_nucleus_only=float((light * (nuc & ~art)).sum() / light.sum())))
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(HERE / "mask_light.csv", index=False)
