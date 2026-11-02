"""Mask status (unWISE ARTIFACT_BITS dilated 2 px; the runner's nucleus circle; outside the search circle)
at every benchmark position in work/triage_h0012a_benchmarks.csv, and the census for big galaxies.

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/mask_benchmarks.py
Needs the bitmasks fetched by mask_census.py --fetch. Writes mask_benchmarks.csv.
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
B = pd.read_csv(ROOT / "hunts/H-0012/work/triage_h0012a_benchmarks.csv")
rows = []
for _, b in B.iterrows():
    gal = galaxy_from_row(T.loc[b.galaxy])
    rec = dict(name=b["name"], type=b.type, disc=b.disc, galaxy=b.galaxy, found=b.found, rank_obs=b.rank_obs)
    best = None
    for tile in str(T.loc[b.galaxy].tiles).split(","):
        w = tiles.wcs_for(tile)
        x, y = w.all_world2pix([[b.ra, b.dec]], 0)[0]
        xi, yi = int(round(x)), int(round(y))
        if not (0 <= xi < 2048 and 0 <= yi < 2048):
            continue
        edge = min(xi, yi, 2047 - xi, 2047 - yi)
        if best is None or edge > best[0]:
            best = (edge, tile, xi, yi, w)
    if best is None:
        rows.append(rec | dict(note="not on a run tile")); continue
    edge, tile, xi, yi, w = best
    p = fetch.cache_root() / "cache" / "unwise-fulldepth" / f"unwise-{tile}-msk.fits.gz"
    msk = fits.getdata(p).astype(np.int64)
    sl = (slice(max(yi - 3, 0), yi + 4), slice(max(xi - 3, 0), xi + 4))
    art = ndimage.binary_dilation((msk[sl] & fetch.ARTIFACT_BITS) != 0, iterations=2)
    c = (min(3, yi), min(3, xi))
    xc, yc = w.all_world2pix([[gal.ra, gal.dec]], 0)[0]
    r_nuc = np.hypot(xi - xc, yi - yc) * PIXSCALE
    rec.update(tile=tile, bits=[k for k in range(31) if msk[yi, xi] >> k & 1], artefact_masked=bool(art[c]),
               nucleus_masked=bool(r_nuc <= gal.nucleus_mask_arcsec), sep_centre_arcsec=round(float(r_nuc), 1),
               outside=bool(gal.ellipse_r(b.ra, b.dec) > gal.search_scale))
    rows.append(rec)
out = pd.DataFrame(rows)
out.to_csv(HERE / "mask_benchmarks.csv", index=False)
nn = out[out.type != "Nova"]
print("all benchmarks:", len(out), " masked (artefact or nucleus):", int((out.artefact_masked | out.nucleus_masked).sum()))
print("non-nova:", len(nn), " masked:", int((nn.artefact_masked | nn.nucleus_masked).sum()))
print(nn[["name", "type", "disc", "galaxy", "found", "rank_obs", "bits", "artefact_masked", "nucleus_masked", "sep_centre_arcsec", "outside"]].to_string())
nov = out[out.type == "Nova"]
print("novae:", len(nov), "found", int(nov.found.sum()), "masked", int((nov.artefact_masked | nov.nucleus_masked).sum()))
C = pd.read_csv(HERE / "mask_census.csv")
big = C[C.a26 >= 8].sort_values("masked_frac", ascending=False)
print("\nbig galaxies (a26 >= 8'):", len(big), "median masked", big.masked_frac.median().round(3))
print(big[["galaxy", "dist", "a26", "masked_frac", "inner_masked_frac", "inner_bright_frac", "centre_flagged_star", "masked_arcmin2"]].round(3).to_string())
