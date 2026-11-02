"""Masked search area per galaxy for the H-0012a run, from the unWISE full-depth bitmasks alone
(the same ARTIFACT_BITS, 2-px dilation, and the runner's nucleus circle and 1.2 x a26 search circle).
The bright-reference-peak circles are not included (they need the images; in M51/M82 they add <0.2%).

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/mask_census.py [--fetch]

--fetch downloads the ~150 kB bitmask of every run tile (2 connections). Writes mask_census.csv:
per galaxy, the masked fraction of the search area, of the inner region (r < 0.25 x a26/2), the
fraction flagged by bits 0-5 (bright star / saturation) inside r < 0.25, and whether the galaxy
centre itself is flagged as a "bright star" (bits 0-3).
"""
import concurrent.futures as cf
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
from oddsky.imaging.pipeline import Config, galaxy_tiles, window_for  # noqa: E402

T = pd.read_csv(ROOT / "hunts/H-0012/work/targets_10mpc.csv")
T = T[~T.separate_project.astype(bool)]
TILES = (ROOT / "hunts/H-0012/work/tiles_h0012.txt").read_text().split()
if "--fetch" in sys.argv:
    with cf.ThreadPoolExecutor(2) as ex:
        list(ex.map(lambda t: fetch.fetch_mask(t), TILES))
cfg = Config()
BR = sum(1 << b for b in (0, 1, 2, 3, 4, 5))
rows = []
for _, r in T.iterrows():
    gal = galaxy_from_row(r)
    tot = dict(search=0, masked=0, inner=0, inner_masked=0, inner_bright=0)
    centre_star = False
    for tile in [t for t in str(r.tiles).split(",") if t]:
        win = window_for(gal, tile, cfg.margin)
        if win is None:
            continue
        y0, y1, x0, x1 = win
        p = fetch.cache_root() / "cache" / "unwise-fulldepth" / f"unwise-{tile}-msk.fits.gz"
        if not p.exists():
            continue
        msk = fits.getdata(p)[y0:y1, x0:x1].astype(np.int64)
        w = tiles.wcs_for(tile)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        ra, dec = w.all_pix2world(xx.ravel(), yy.ravel(), 0)
        rn = gal.ellipse_r(ra, dec).reshape(xx.shape)  # in units of a26/2 (circle)
        # primary pixels only (bit 6 = centre of pixel not primary): count each sky pixel once across tiles
        prim = (msk >> 6 & 1) == 0
        search = (rn <= gal.search_scale) & prim
        inner = (rn <= 0.25) & prim
        art = ndimage.binary_dilation((msk & fetch.ARTIFACT_BITS) != 0, iterations=2)
        xc, yc = w.all_world2pix([[gal.ra, gal.dec]], 0)[0]
        nuc = (xx - xc) ** 2 + (yy - yc) ** 2 <= (gal.nucleus_mask_arcsec / PIXSCALE) ** 2
        m = art | nuc
        tot["search"] += search.sum(); tot["masked"] += (m & search).sum()
        tot["inner"] += inner.sum(); tot["inner_masked"] += (m & inner).sum()
        tot["inner_bright"] += (((msk & BR) != 0) & inner).sum()
        xi, yi = int(round(xc)) - x0, int(round(yc)) - y0
        if 0 <= xi < msk.shape[1] and 0 <= yi < msk.shape[0] and prim[yi, xi]:
            centre_star = bool(msk[yi, xi] & 0b1111)
    if tot["search"] == 0:
        continue
    rows.append(dict(galaxy=r.Name, dist=r.Dist, a26=r.a26, nucleus_mask_arcsec=gal.nucleus_mask_arcsec,
                     search_px=int(tot["search"]), masked_frac=tot["masked"] / tot["search"],
                     inner_masked_frac=tot["inner_masked"] / max(tot["inner"], 1),
                     inner_bright_frac=tot["inner_bright"] / max(tot["inner"], 1), centre_flagged_star=centre_star,
                     masked_arcmin2=tot["masked"] * (PIXSCALE / 60) ** 2))
out = pd.DataFrame(rows).sort_values("masked_frac", ascending=False)
out.to_csv(HERE / "mask_census.csv", index=False)
print(len(out), "galaxies; median masked", out.masked_frac.median().round(4),
      "; >10%:", (out.masked_frac > 0.1).sum(), "; centre flagged as bright star:", out.centre_flagged_star.sum(),
      "; inner region >50% masked:", (out.inner_masked_frac > 0.5).sum())
print(out.head(40).round(3).to_string())
