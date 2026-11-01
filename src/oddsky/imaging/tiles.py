"""The unWISE tile scheme: 18,240 tiles of 2048 x 2048 px at 2.75"/px (1.56 deg) on the WISE Atlas
tile centres, TAN projection about the tile centre, CRPIX 1024.5."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from astropy.table import Table
from astropy.wcs import WCS

from ..data.http import request
from . import PIXSCALE
from .fetch import cache_root

TILES_URL = "https://portal.nersc.gov/project/cosmo/data/unwise/allwise/unwise-coadds/fulldepth/tiles.fits"
NPIX = 2048


@lru_cache(maxsize=1)
def tile_table() -> Table:
    p = cache_root() / "meta" / "tiles.fits"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(request("GET", TILES_URL).content)
    t = Table.read(p)
    t["coadd_id"] = [str(c).strip() for c in t["coadd_id"]]
    return t


def tile_wcs(ra0: float, dec0: float) -> WCS:
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra0, dec0]
    w.wcs.crpix = [1024.5, 1024.5]
    w.wcs.cd = np.array([[-PIXSCALE / 3600, 0], [0, PIXSCALE / 3600]])
    return w


def wcs_for(coadd_id: str) -> WCS:
    t = tile_table()
    r = t[t["coadd_id"] == coadd_id][0]
    return tile_wcs(float(r["ra"]), float(r["dec"]))


def tiles_covering(ra: np.ndarray, dec: np.ndarray, margin_px: int = 0) -> list[str]:
    """Tiles whose pixel area (shrunk by margin_px) contains any of the given points.

    A point usually lies in 1-2 tiles (tiles overlap by ~0.03 deg at the equator, more at high Dec)."""
    ra, dec = np.atleast_1d(ra), np.atleast_1d(dec)
    t = tile_table()
    # candidate tiles within 1.5 deg (cheap pre-filter on the sphere)
    out = []
    cosd = np.cos(np.radians(dec.mean()))
    near = np.hypot((((t["ra"] - ra.mean() + 180) % 360) - 180) * cosd, t["dec"] - dec.mean())
    span = float(np.max(np.hypot((ra - ra.mean()) * cosd, dec - dec.mean()))) if ra.size > 1 else 0.0
    for r in t[near < span + 1.5]:
        x, y = tile_wcs(float(r["ra"]), float(r["dec"])).all_world2pix(ra, dec, 0)
        inside = (x >= margin_px - 0.5) & (x <= NPIX - 0.5 - margin_px) & (y >= margin_px - 0.5) & (y <= NPIX - 0.5 - margin_px)
        if inside.any():
            out.append(str(r["coadd_id"]))
    return sorted(out)


def primary_tile(ra: float, dec: float) -> str:
    """The tile whose centre is nearest (unWISE's own convention for de-duplicating overlaps)."""
    t = tile_table()
    d = np.hypot((((t["ra"] - ra + 180) % 360) - 180) * np.cos(np.radians(dec)), t["dec"] - dec)
    return str(t["coadd_id"][int(np.argmin(d))])


def tile_dir(coadd_id: str) -> Path:
    return Path(coadd_id[:3]) / coadd_id
