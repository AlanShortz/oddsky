"""Point-source detection on difference images.

The detection statistic is the PSF-fit flux at every pixel divided by its error (the matched
filter, i.e. ZOGY's S_corr without the PSF-matching term):

    F = corr(D / s^2, P) / corr(1 / s^2, P^2),   E = 1 / sqrt(corr(1 / s^2, P^2)),   S/N = F / E

The nominal E ignores two things that dominate in a nearby galaxy: pixel-to-pixel noise
correlation from unWISE's resampling, and subtraction residuals from crowding and the galaxy's
bright, structured background. Both are absorbed by dividing the S/N map by its own local robust
scatter (box of `box` px), so a 5-sigma peak means 5 times the local empirical noise.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.signal import fftconvolve
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree


def _corr(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    return fftconvolve(a, k[::-1, ::-1], mode="same")


def flux_maps(D: np.ndarray, S: np.ndarray, psf: np.ndarray):
    """(F, E): PSF-fit flux and its nominal error at every pixel. NaN pixels carry no weight."""
    good = np.isfinite(D) & np.isfinite(S) & (S > 0)
    w = np.where(good, 1 / np.where(good, S, 1) ** 2, 0.0)
    num = _corr(np.where(good, D, 0) * w, psf)
    den = _corr(w, psf**2)
    with np.errstate(all="ignore"):
        F = num / den
        E = 1 / np.sqrt(den)
    cover = _corr(good.astype(float), psf) > 0.7  # most of the PSF footprint covered
    F[~cover] = np.nan
    E[~cover] = np.nan
    return F.astype(np.float32), E.astype(np.float32)


def local_scatter(snr: np.ndarray, mask: np.ndarray | None = None, box: int = 64,
                  floor: float = 0.8) -> np.ndarray:
    """Robust (MAD) scatter of the S/N map in boxes, bilinearly interpolated to full size.
    Masked/NaN pixels and |S/N| > 8 (real sources) are excluded from the estimate. The factor is
    never below `floor` (0.8): it may shrink nominal errors a little where the 3% residual floor
    overestimates them, but never by 2x in a sparse box whose MAD is accidentally small."""
    ny, nx = snr.shape
    nby, nbx = max(1, ny // box), max(1, nx // box)
    grid = np.full((nby, nbx), np.nan)
    ye = np.linspace(0, ny, nby + 1).round().astype(int)  # uniform cells, matching the zoom below
    xe = np.linspace(0, nx, nbx + 1).round().astype(int)
    for i in range(nby):
        y0, y1 = ye[i], ye[i + 1]
        for j in range(nbx):
            x0, x1 = xe[j], xe[j + 1]
            v = snr[y0:y1, x0:x1]
            ok = np.isfinite(v)
            if mask is not None:
                ok &= ~mask[y0:y1, x0:x1]
            v = v[ok]
            v = v[np.abs(v) < 8 * max(1.0, 1.4826 * np.median(np.abs(v)))] if v.size else v
            if v.size > 0.1 * box * box:
                grid[i, j] = 1.4826 * np.median(np.abs(v - np.median(v)))
    if np.isnan(grid).all():
        return np.ones_like(snr, dtype=np.float32)
    # fill empty boxes with the nearest filled one
    idx = ndimage.distance_transform_edt(np.isnan(grid), return_distances=False, return_indices=True)
    grid = grid[tuple(idx)]
    grid = np.maximum(grid, floor)
    full = ndimage.zoom(grid, (ny / nby, nx / nbx), order=1, mode="nearest", grid_mode=True)
    return full[:ny, :nx].astype(np.float32)


def snr_map(D, S, psf, mask=None, box: int = 64):
    """Calibrated S/N map plus (F, E_cal, scatter) for forced photometry."""
    F, E = flux_maps(D, S, psf)
    snr = F / E
    c = local_scatter(snr, mask, box=box)
    return snr / c, F, E * c, c


def find_peaks(snr: np.ndarray, thresh: float = 5.0, mask: np.ndarray | None = None, size: int = 5,
               border: int = 3):
    """Local extrema of |S/N| above thresh, both signs, at least `border` px from the edge.
    Returns arrays x, y (sub-pixel), snr."""
    a = np.where(np.isfinite(snr), snr, 0)
    a[:border, :] = a[-border:, :] = 0
    a[:, :border] = a[:, -border:] = 0
    out = []
    for sign in (1, -1):
        s = sign * a
        pk = (s == ndimage.maximum_filter(s, size=size)) & (s > thresh)
        if mask is not None:
            pk &= ~mask
        ys, xs = np.nonzero(pk)
        for y, x in zip(ys, xs, strict=True):
            # quadratic sub-pixel refinement
            dx = dy = 0.0
            if 0 < x < s.shape[1] - 1:
                lo, c, hi = s[y, x - 1], s[y, x], s[y, x + 1]
                den = lo - 2 * c + hi
                dx = 0.5 * (lo - hi) / den if den < 0 else 0.0
            if 0 < y < s.shape[0] - 1:
                lo, c, hi = s[y - 1, x], s[y, x], s[y + 1, x]
                den = lo - 2 * c + hi
                dy = 0.5 * (lo - hi) / den if den < 0 else 0.0
            out.append((x + np.clip(dx, -0.5, 0.5), y + np.clip(dy, -0.5, 0.5), a[y, x]))
    if not out:
        return np.zeros(0), np.zeros(0), np.zeros(0)
    o = np.array(out)
    return o[:, 0], o[:, 1], o[:, 2]


def bright_star_mask(ref: np.ndarray, ref_var: np.ndarray, flux_thresh: float, base_r: float = 4.0,
                     r_per_mag: float = 5.0, r_max: float = 40.0) -> np.ndarray:
    """Circles round reference sources brighter than flux_thresh, radius growing 5 px per magnitude
    above the threshold (WISE PSF wings, saturation artefacts, latent-image ghosts)."""
    sm = ndimage.uniform_filter(ref, 3)
    pk = (sm == ndimage.maximum_filter(sm, 7)) & (ref > flux_thresh)
    ys, xs = np.nonzero(pk)
    m = np.zeros(ref.shape, bool)
    if ys.size == 0:
        return m
    dm = 2.5 * np.log10(ref[ys, xs] / flux_thresh)
    rad = np.clip(base_r + r_per_mag * dm, base_r, r_max)
    yy, xx = np.ogrid[: ref.shape[0], : ref.shape[1]]
    for y, x, r in zip(ys, xs, rad, strict=True):
        r_i = int(np.ceil(r))
        y0, y1, x0, x1 = max(0, y - r_i), min(ref.shape[0], y + r_i + 1), max(0, x - r_i), min(ref.shape[1], x + r_i + 1)
        m[y0:y1, x0:x1] |= (yy[y0:y1] - y) ** 2 + (xx[:, x0:x1] - x) ** 2 <= r * r
    return m


def circle_mask(shape, x: float, y: float, r: float) -> np.ndarray:
    yy, xx = np.ogrid[: shape[0], : shape[1]]
    return (yy - y) ** 2 + (xx - x) ** 2 <= r * r


def group(ra: np.ndarray, dec: np.ndarray, radius_arcsec: float = 3.5) -> np.ndarray:
    """Friends-of-friends labels for detections on the sky (linking length radius_arcsec)."""
    n = len(ra)
    if n == 0:
        return np.zeros(0, int)
    xyz = np.c_[np.cos(np.radians(dec)) * np.cos(np.radians(ra)),
                np.cos(np.radians(dec)) * np.sin(np.radians(ra)), np.sin(np.radians(dec))]
    tree = cKDTree(xyz)
    pairs = tree.query_pairs(np.radians(radius_arcsec / 3600), output_type="ndarray")
    g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n)) if len(pairs) else coo_matrix((n, n))
    _, labels = connected_components(g, directed=False)
    return labels
