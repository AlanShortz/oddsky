"""Forced PSF photometry at fixed positions: difference images (the light curve) and the reference
(the quiescent flux the difference light curve sits on)."""

from __future__ import annotations

import numpy as np

from .psf import shifted


def _stamp_slices(shape, x: float, y: float, h: int):
    xi, yi = int(round(x)), int(round(y))
    y0, y1, x0, x1 = yi - h, yi + h + 1, xi - h, xi + h + 1
    if y0 < 0 or x0 < 0 or y1 > shape[0] or x1 > shape[1]:
        return None
    return (slice(y0, y1), slice(x0, x1)), x - xi, y - yi


def forced_flux(D: np.ndarray, S: np.ndarray, psf: np.ndarray, x: float, y: float,
                scale: float = 1.0, radius: float | None = 7.0, local_bkg: bool = True) -> tuple[float, float]:
    """Weighted PSF-fit flux of a point source at (x, y) on one difference image, and its error.

    flux = sum(P d / s^2) / sum(P^2 / s^2), err = scale / sqrt(sum(P^2 / s^2)); `scale` is the
    local empirical noise correction from the S/N map (detect.local_scatter). With local_bkg a
    constant is fitted jointly (residual galaxy light). Pixels further than `radius` px or NaN
    are ignored."""
    h = psf.shape[0] // 2
    st = _stamp_slices(D.shape, x, y, h)
    if st is None:
        return np.nan, np.nan
    sl, dx, dy = st
    P = shifted(psf, dx, dy)
    d, s = D[sl], S[sl]
    ok = np.isfinite(d) & np.isfinite(s) & (s > 0)
    if radius is not None:
        yy, xx = np.mgrid[-h : h + 1, -h : h + 1]
        ok &= np.hypot(xx - dx, yy - dy) <= radius
    if P[ok].sum() < 0.6:  # most of the PSF must be covered
        return np.nan, np.nan
    w = 1 / s[ok] ** 2
    if local_bkg:
        A = np.c_[P[ok], np.ones(ok.sum())]
        AtA = A.T @ (A * w[:, None])
        try:
            cov = np.linalg.inv(AtA)
        except np.linalg.LinAlgError:
            return np.nan, np.nan
        p = cov @ (A.T @ (d[ok] * w))
        return float(p[0]), float(scale * np.sqrt(cov[0, 0]))
    den = (P[ok] ** 2 * w).sum()
    return float((P[ok] * d[ok] * w).sum() / den), float(scale / np.sqrt(den))


def forced_lightcurve(D, S, psfs, season, x: float, y: float, scales=None):
    """Forced photometry on every epoch of a (n, ny, nx) difference stack. psfs: {season: psf}.
    scales: (n,) local noise factors at (x, y) (default 1)."""
    n = D.shape[0]
    f = np.full(n, np.nan)
    e = np.full(n, np.nan)
    for i in range(n):
        f[i], e[i] = forced_flux(D[i], S[i], psfs[int(season[i])], x, y,
                                 1.0 if scales is None else float(scales[i]))
    return f, e


def reference_flux(ref: np.ndarray, ref_var: np.ndarray, psf: np.ndarray, x: float, y: float,
                   radius: float = 6.0) -> tuple[float, float]:
    """PSF flux + constant local background fitted within `radius` px on the reference image.
    In a crowded field this is an upper bound on the star's own flux (blends add light)."""
    h = psf.shape[0] // 2
    st = _stamp_slices(ref.shape, x, y, h)
    if st is None:
        return np.nan, np.nan
    sl, dx, dy = st
    P = shifted(psf, dx, dy)
    yy, xx = np.mgrid[-h : h + 1, -h : h + 1]
    ok = (np.hypot(xx - dx, yy - dy) <= radius) & np.isfinite(ref[sl]) & np.isfinite(ref_var[sl])
    if ok.sum() < 10:
        return np.nan, np.nan
    A = np.c_[P[ok], np.ones(ok.sum())]
    w = 1 / np.maximum(ref_var[sl][ok], 1e-12)
    AtA = A.T @ (A * w[:, None])
    p = np.linalg.solve(AtA, A.T @ (ref[sl][ok] * w))
    cov = np.linalg.inv(AtA)
    return float(p[0]), float(np.sqrt(cov[0, 0]))
