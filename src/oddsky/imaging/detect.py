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


def fine_scatter(snr: np.ndarray, mask: np.ndarray | None, fine: np.ndarray, box: int = 16,
                 floor: float = 0.8) -> np.ndarray:
    """local_scatter at a finer box, computed only over the bounding box of `fine` (padded by 2 boxes):
    the high-surface-brightness parts of a galaxy (bulges, starburst cores, released unWISE 'star'
    footprints) where subtraction residuals vary on scales far below the 64-px default. NaN outside."""
    out = np.full(snr.shape, np.nan, np.float32)
    if not fine.any():
        return out
    ys, xs = np.nonzero(fine)
    y0, y1 = max(0, ys.min() - 2 * box), min(snr.shape[0], ys.max() + 2 * box + 1)
    x0, x1 = max(0, xs.min() - 2 * box), min(snr.shape[1], xs.max() + 2 * box + 1)
    sub_mask = None if mask is None else mask[y0:y1, x0:x1]
    out[y0:y1, x0:x1] = local_scatter(snr[y0:y1, x0:x1], sub_mask, box=box, floor=floor)
    return out


def snr_map(D, S, psf, mask=None, box: int = 64, fine: np.ndarray | None = None, fine_box: int = 16):
    """Calibrated S/N map plus (F, E_cal, scatter) for forced photometry. Where `fine` is set the noise
    factor is max(box-scale, fine_box-scale scatter): never smaller than the default, larger where the
    residuals are structured on small scales."""
    F, E = flux_maps(D, S, psf)
    snr = F / E
    c = local_scatter(snr, mask, box=box)
    if fine is not None and fine.any():
        cf = fine_scatter(snr, mask, fine, box=fine_box)
        c = np.where(fine & np.isfinite(cf), np.fmax(c, cf), c).astype(np.float32)
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


def dipole_test(stamp: np.ndarray, fwhm_px: float = 2.4, r_fit: float = 6.0, step: float = 0.5, reach: float = 4.0,
                sigma: float | None = None) -> dict:
    """Is a late-minus-early difference stamp (candidate at its centre pixel) a moving star's dipole?

    Compares two models fitted within r_fit px, both with a constant: (1) ONE point source of either sign
    at a free sub-pixel position (grid of `step` px within `reach` px); (2) a positive AND a negative point
    source at two free grid positions. A proper-motion star leaves a +/- pair of similar amplitude; a real
    fade or brightening is one PSF, which model 2 cannot improve on much. Returns
      dchi2   chi2(1) - chi2(2) (noise from the stamp's outer pixels unless `sigma` is given)
      balance min(|A+|, |A-|) / max(|A+|, |A-|) of model 2 (1 = a pure dipole)
      sep_px  separation of the two lobes
      dipole  dchi2 >= 25 and balance >= 0.5 and 1 <= sep_px <= 2.5
    (calibrated on h0012a: the 10" pair-flagged dipoles have lobes 1-1.6 px apart and balance ~0.95; lobes 3-4
    px apart are two neighbouring sources, e.g. the nova AT 2023lyd and the LRN AT 2021biy, not a moving star)
    Gaussian PSF (the test needs the lobes, not the exact profile)."""
    st = np.asarray(stamp, float)
    c = st.shape[0] // 2
    yy, xx = np.mgrid[: st.shape[0], : st.shape[1]] - c
    rr = np.hypot(xx, yy)
    fit = (rr <= r_fit) & np.isfinite(st)
    if sigma is None:
        out_px = st[(rr > r_fit + 4) & np.isfinite(st)]
        if out_px.size < 30:
            return dict(dchi2=np.nan, balance=np.nan, sep_px=np.nan, dipole=False)
        sigma = 1.4826 * np.median(np.abs(out_px - np.median(out_px)))
    if not sigma or not np.isfinite(sigma) or fit.sum() < 20:
        return dict(dchi2=np.nan, balance=np.nan, sep_px=np.nan, dipole=False)
    d = st[fit] / sigma
    s2 = (fwhm_px / 2.3548) ** 2
    g = np.arange(-reach, reach + 1e-9, step)
    px, py = np.meshgrid(g, g)
    px, py = px.ravel(), py.ravel()
    T = np.exp(-0.5 * ((xx[fit][None, :] - px[:, None]) ** 2 + (yy[fit][None, :] - py[:, None]) ** 2) / s2)
    T /= T.sum(axis=1, keepdims=True)
    n = d.size
    # model 1: a*T_k + c
    tt, t1, td = (T * T).sum(1), T.sum(1), T @ d
    det = tt * n - t1**2
    a1 = (td * n - t1 * d.sum()) / det
    c1 = (tt * d.sum() - t1 * td) / det
    chi1 = ((d[None, :] - a1[:, None] * T - c1[:, None]) ** 2).sum(1)
    chi2_1 = float(chi1.min())
    # model 2: A*T_i + B*T_j + c, all pairs (vectorised 3x3 normal equations)
    G = T @ T.T
    m = len(px)
    M = np.empty((m, m, 3, 3))
    M[..., 0, 0] = tt[:, None]
    M[..., 1, 1] = tt[None, :]
    M[..., 0, 1] = M[..., 1, 0] = G
    M[..., 0, 2] = M[..., 2, 0] = t1[:, None]
    M[..., 1, 2] = M[..., 2, 1] = t1[None, :]
    M[..., 2, 2] = n
    rhs = np.stack([np.broadcast_to(td[:, None], (m, m)), np.broadcast_to(td[None, :], (m, m)),
                    np.full((m, m), d.sum())], -1)
    M[np.eye(m, dtype=bool)] += np.eye(3) * 1e-6  # i == j is degenerate
    p = np.linalg.solve(M, rhs[..., None])[..., 0]
    # chi2 = d.d - 2 p.rhs + p.M.p
    chi2 = (d @ d) - 2 * (p * rhs).sum(-1) + np.einsum("...i,...ij,...j->...", p, M, p)
    ok = (p[..., 0] > 0) & (p[..., 1] < 0)
    ok &= ~np.eye(m, dtype=bool)
    if not ok.any():
        return dict(dchi2=0.0, balance=0.0, sep_px=0.0, dipole=False)
    chi2 = np.where(ok, chi2, np.inf)
    i, j = np.unravel_index(int(np.argmin(chi2)), chi2.shape)
    A, B = p[i, j, 0], p[i, j, 1]
    dchi2 = chi2_1 - float(chi2[i, j])
    bal = float(min(abs(A), abs(B)) / max(abs(A), abs(B)))
    sep = float(np.hypot(px[i] - px[j], py[i] - py[j]))
    return dict(dchi2=dchi2, balance=bal, sep_px=sep, dipole=bool(dchi2 >= 25 and bal >= 0.5 and 1.0 <= sep <= 2.5))
