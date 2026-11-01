"""All epochs of one tile and band as a single array on the tile's pixel grid."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from . import fetch

HALF_YEAR = 365.25 / 2


@dataclass
class EpochStack:
    tile: str
    band: int
    epochs: np.ndarray  # epoch numbers (eNNN)
    mjd: np.ndarray  # mid-epoch MJD
    img: np.ndarray  # (n, ny, nx) float32, Vega nanomaggies
    ivar: np.ndarray  # (n, ny, nx) float32, 0 where uncovered
    wcs: WCS  # of the window
    window: tuple[int, int, int, int] = (0, 2048, 0, 2048)  # y0, y1, x0, x1 in tile pixels
    season: np.ndarray = field(default=None)  # 0/1: absolute visit season (= WISE scan direction)
    builds: list = field(default_factory=list)  # UNW_VER per epoch (the neo11 epochs mix code builds)

    def __post_init__(self):
        if self.season is None:
            ra0, dec0 = self.wcs.wcs.crval if self.wcs is not None else (None, None)
            self.season = seasons(self.mjd, ra0, dec0)

    @property
    def n(self) -> int:
        return len(self.epochs)


def sun_ecliptic_longitude(mjd) -> np.ndarray:
    """Apparent ecliptic longitude of the Sun (deg), low-precision formula (Astronomical Almanac;
    better than 0.01 deg, far finer than needed here)."""
    n = np.asarray(mjd, float) - 51544.5
    L = (280.460 + 0.9856474 * n) % 360
    g = np.radians((357.528 + 0.9856003 * n) % 360)
    return (L + 1.915 * np.sin(g) + 0.020 * np.sin(2 * g)) % 360


def ecliptic_longitude(ra: float, dec: float) -> float:
    import astropy.units as u
    from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord

    return float(SkyCoord(ra * u.deg, dec * u.deg).transform_to(GeocentricTrueEcliptic()).lon.deg)


def seasons(mjd: np.ndarray, ra: float | None = None, dec: float | None = None) -> np.ndarray:
    """Visit season, 0 or 1, i.e. which side of the Sun WISE was looking from.

    WISE scans great circles through the ecliptic poles at ~90 deg solar elongation, so a field is
    seen twice a year: once with the Sun ~90 deg behind it in ecliptic longitude (label 0) and once
    with the Sun ~90 deg ahead (label 1). The scan direction across the field, and hence the PSF
    orientation, flips between the two. Given the field's (ra, dec) the label is ABSOLUTE: the same
    for every tile and epoch numbering. Without coordinates it falls back to tile-relative timing
    (alternating half-years from the first epoch), for synthetic tests only."""
    mjd = np.asarray(mjd, float)
    if ra is None or dec is None:
        k = np.round((mjd - mjd.min()) / HALF_YEAR).astype(int)
        return (k % 2).astype(np.int8)
    dlon = (sun_ecliptic_longitude(mjd) - ecliptic_longitude(ra, dec) + 180) % 360 - 180
    return (dlon > 0).astype(np.int8)


def epoch_mjd(header) -> float:
    return 0.5 * (float(header["MJDMIN"]) + float(header["MJDMAX"]))


def window_wcs(wcs: WCS, y0: int, x0: int) -> WCS:
    w = wcs.deepcopy()
    w.wcs.crpix = [wcs.wcs.crpix[0] - x0, wcs.wcs.crpix[1] - y0]
    return w


def load_stack(tile: str, band: int, epochs=None, window=None, min_nexp: int = 2) -> EpochStack:
    """Read img-m / invvar-m / n-m for each epoch (from the cache). Pixels with fewer than
    `min_nexp` exposures get ivar = 0. Epochs whose window is entirely uncovered are dropped."""
    epochs = fetch.list_epochs(tile) if epochs is None else list(epochs)
    y0, y1, x0, x1 = window or (0, 2048, 0, 2048)
    imgs, ivars, mjds, keep, builds = [], [], [], [], []
    wcs = None
    for e in epochs:
        p_img = fetch.local_path(tile, band, e, "img-m")
        if not p_img.exists():
            continue
        with fits.open(p_img, memmap=True) as h:
            hdr = h[0].header
            im = np.array(h[0].data[y0:y1, x0:x1], dtype=np.float32)
        if wcs is None:
            wcs = WCS(hdr)
        iv = fits.getdata(fetch.local_path(tile, band, e, "invvar-m"))[y0:y1, x0:x1].astype(np.float32)
        nn = fits.getdata(fetch.local_path(tile, band, e, "n-m"))[y0:y1, x0:x1]
        bad = (nn < min_nexp) | ~np.isfinite(im) | ~np.isfinite(iv)
        iv[bad] = 0
        im[bad] = 0
        if not (iv > 0).any():
            continue
        imgs.append(im)
        ivars.append(iv)
        mjds.append(epoch_mjd(hdr))
        keep.append(e)
        builds.append(f"{hdr.get('UNW_VER', '?')}|{hdr.get('UNW_DATE', '?')[:10]}")
    if not imgs:
        raise FileNotFoundError(f"no cached epochs for {tile} W{band}")
    return EpochStack(
        tile=tile, band=band, epochs=np.array(keep), mjd=np.array(mjds),
        img=np.stack(imgs), ivar=np.stack(ivars), wcs=window_wcs(wcs, y0, x0), window=(y0, y1, x0, x1),
        builds=builds,
    )
