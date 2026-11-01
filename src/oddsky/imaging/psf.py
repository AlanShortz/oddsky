"""Point-spread functions: Gaussian (tests, fallback) and empirical (median of isolated stars).

The unWISE PSF is ~6.1" (W1) / 6.8" (W2) FWHM, i.e. ~2.2-2.5 px, with a three-fold pattern from the
secondary-mirror supports that rotates 180 deg between the two visit seasons; an empirical PSF
built per tile, band and season from the image itself captures both without a model."""

from __future__ import annotations

import numpy as np
from scipy import ndimage

SIZE = 25  # px; 69" stamp, enough for the core and first Airy ring


def gaussian_psf(fwhm_px: float, size: int = SIZE) -> np.ndarray:
    s = fwhm_px / 2.3548
    r = np.arange(size) - size // 2
    g = np.exp(-0.5 * (r[None, :] ** 2 + r[:, None] ** 2) / s**2)
    return (g / g.sum()).astype(np.float64)


def shifted(psf: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """PSF centred at (+dx, +dy) px from the stamp centre (cubic spline), renormalised."""
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return psf
    p = ndimage.shift(psf, (dy, dx), order=3, mode="constant", prefilter=True)
    return p * (psf.sum() / p.sum())


def fwhm(psf: np.ndarray) -> float:
    """FWHM from the second moment, assuming a Gaussian core (px)."""
    c = psf.shape[0] // 2
    core = psf[c - 4 : c + 5, c - 4 : c + 5].clip(0)
    yy, xx = np.mgrid[-4:5, -4:5]
    var = (core * (xx**2 + yy**2)).sum() / core.sum() / 2
    return float(2.3548 * np.sqrt(var))


def centroid(img: np.ndarray, x: float, y: float, box: int = 2, iters: int = 3) -> tuple[float, float]:
    """Iterative first-moment centroid in a (2*box+1)^2 window, background = window minimum."""
    ny, nx = img.shape
    for _ in range(iters):
        xi, yi = int(round(x)), int(round(y))
        if xi - box < 0 or yi - box < 0 or xi + box >= nx or yi + box >= ny:
            break
        w = img[yi - box : yi + box + 1, xi - box : xi + box + 1]
        w = (w - w.min()).clip(0)
        s = w.sum()
        if s <= 0:
            break
        yy, xx = np.mgrid[-box : box + 1, -box : box + 1]
        x, y = xi + (w * xx).sum() / s, yi + (w * yy).sum() / s
    return float(x), float(y)


def find_stars(img: np.ndarray, ivar: np.ndarray, mask: np.ndarray | None = None, snr_min: float = 50,
               flux_max: float | None = None, isolation: int = 10, nmax: int = 300,
               size: int = SIZE) -> np.ndarray:
    """Bright, unsaturated, isolated point sources: (N, 2) array of x, y (px).

    A star qualifies if it is a local maximum with peak S/N > snr_min, no brighter peak lies within
    `isolation` px, and no other peak above 10% of its height lies within size//2 px."""
    sig = np.where(ivar > 0, 1 / np.sqrt(np.maximum(ivar, 1e-30)), np.inf)
    sm = ndimage.uniform_filter(img, 3)
    bkg = ndimage.median_filter(img[::4, ::4], size=16)
    bkg = ndimage.zoom(bkg, (img.shape[0] / bkg.shape[0], img.shape[1] / bkg.shape[1]), order=1)
    bkg = bkg[: img.shape[0], : img.shape[1]]
    peak = (sm == ndimage.maximum_filter(sm, size=2 * isolation + 1)) & ((img - bkg) / sig > snr_min)
    h = size // 2 + 2
    peak[:h, :] = peak[-h:, :] = False
    peak[:, :h] = peak[:, -h:] = False
    if mask is not None:
        peak &= ~ndimage.binary_dilation(mask, iterations=3)
    ys, xs = np.nonzero(peak)
    hts = (img - bkg)[ys, xs]
    if flux_max is not None:
        ok = hts < flux_max
        ys, xs, hts = ys[ok], xs[ok], hts[ok]
    # secondary peaks: any local max (3x3) above 10% of the star's height within the stamp
    loc = (sm == ndimage.maximum_filter(sm, size=3)) & ((img - bkg) / sig > 5)
    ly, lx = np.nonzero(loc)
    lh = (img - bkg)[ly, lx]
    out = []
    order = np.argsort(-hts)
    for i in order:
        d2 = (lx - xs[i]) ** 2 + (ly - ys[i]) ** 2
        near = (d2 > 4) & (d2 < (size // 2) ** 2) & (lh > 0.1 * hts[i])
        if not near.any():
            out.append((xs[i], ys[i]))
        if len(out) >= nmax:
            break
    return np.array(out, dtype=float).reshape(-1, 2)


def stamp(img: np.ndarray, x: float, y: float, size: int = SIZE) -> np.ndarray | None:
    h = size // 2
    xi, yi = int(round(x)), int(round(y))
    if xi - h < 0 or yi - h < 0 or xi + h + 1 > img.shape[1] or yi + h + 1 > img.shape[0]:
        return None
    return img[yi - h : yi + h + 1, xi - h : xi + h + 1]


def build_psf(img: np.ndarray, stars: np.ndarray, size: int = SIZE, clip: float = 3.0) -> np.ndarray:
    """Median of background-subtracted, recentred, flux-normalised star stamps; one rejection pass
    drops stamps that disagree with the first median (neighbours, cosmic junk)."""
    h = size // 2
    yy, xx = np.mgrid[-h : h + 1, -h : h + 1]
    rr = np.hypot(xx, yy)
    ann = (rr >= h - 3) & (rr <= h)
    stamps = []
    for x, y in stars:
        cx, cy = centroid(img, x, y)
        s = stamp(img, cx, cy, size + 4)
        if s is None:
            continue
        s = ndimage.shift(s.astype(np.float64), (round(cy) - cy, round(cx) - cx), order=3)[2:-2, 2:-2]
        s = s - np.median(s[ann])
        tot = s[rr <= h - 3].sum()
        if tot <= 0:
            continue
        stamps.append(s / tot)
    if len(stamps) < 5:
        raise ValueError(f"only {len(stamps)} usable PSF stars")
    S = np.array(stamps)
    med = np.median(S, axis=0)
    core = rr <= 4
    resid = np.sqrt(((S - med)[:, core] ** 2).sum(axis=1))
    good = resid < clip * np.median(resid)
    psf = np.median(S[good], axis=0) if good.sum() >= 5 else med
    psf[rr > h] = 0
    return psf / psf.sum()
