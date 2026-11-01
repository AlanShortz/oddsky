"""Reference images, PSF-matching kernels and difference images.

Choices (see hunts/H-0012/README.md):
- One reference per visit season (= scan direction): the median of that season's epochs. The WISE
  PSF's three-fold pattern rotates 180 deg between seasons, so mixing them leaves dipoles round
  every star. A median of ~12 epochs is ~3.5x deeper than one epoch, so the difference noise is
  dominated by the epoch itself; and a star that changes for a few years still has a reference
  that represents its typical state.
- Kernel: a small (5x5 px) delta-function basis plus a constant background, fitted by weighted least
  squares on signal-bearing pixels in blocks of `block` px (spatial variation, astrometric
  jitter, photometric scale). It is a minimal Alard & Lupton (1998) / Bramich (2008) scheme;
  the PSFs of epochal unWISE coadds differ only slightly within a season, so 5x5 is ample.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage


def masked_median(img: np.ndarray, ivar: np.ndarray, rows: int = 256) -> tuple[np.ndarray, np.ndarray]:
    """Per-pixel median over epochs (axis 0) ignoring ivar == 0, and the variance of that median
    ((pi/2) * mean variance / N). Processed in row chunks to bound memory."""
    n, ny, nx = img.shape
    med = np.zeros((ny, nx), np.float32)
    var = np.full((ny, nx), np.inf, np.float32)
    for y0 in range(0, ny, rows):
        sl = slice(y0, min(ny, y0 + rows))
        im = img[:, sl].astype(np.float32, copy=True)
        iv = ivar[:, sl]
        good = iv > 0
        im[~good] = np.nan
        with np.errstate(all="ignore"):
            m = np.nanmedian(im, axis=0)
            ng = good.sum(axis=0)
            v = np.where(good, 1 / np.where(good, iv, 1), 0).sum(axis=0) / np.maximum(ng, 1)
            eff = np.where(ng > 2, np.pi / 2, 1.0)
            vv = eff * v / np.maximum(ng, 1)
        med[sl] = np.where(ng > 0, m, 0)
        var[sl] = np.where(ng > 0, vv, np.inf)
    return med, var


def references(img: np.ndarray, ivar: np.ndarray, season: np.ndarray, mjd: np.ndarray | None = None,
               mjd_max: float | None = None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """{season: (ref, ref_var)}. With mjd_max, only epochs before it build the reference (De et al.
    used the 2010-2011 WISE coadds); otherwise all epochs of the season."""
    out = {}
    for s in np.unique(season):
        sel = season == s
        if mjd_max is not None:
            sel &= mjd < mjd_max
        if not sel.any():
            sel = season == s
        out[int(s)] = masked_median(img[sel], ivar[sel])
    return out


def residual_floor(ref: np.ndarray, eps: float = 0.03, size: int = 9, spread: int = 7) -> np.ndarray:
    """Per-pixel systematic error from imperfect subtraction of point sources: eps times the
    reference's compact (high-pass) structure, spread over `spread` px (the residual of a 1-3%
    PSF/astrometry mismatch lands on the PSF wings, not just the core). Bright stars are
    down-weighted where their residuals exceed the photon noise; smooth galaxy light is not."""
    hp = np.clip(ref - ndimage.median_filter(ref, size=size, mode="nearest"), 0, None)
    return (eps * ndimage.maximum_filter(hp, size=spread)).astype(np.float32)


def loo_medians(img: np.ndarray, ivar: np.ndarray, rows: int = 128) -> np.ndarray:
    """Leave-one-out medians: out[i] = per-pixel median of all epochs EXCEPT i (ignoring ivar == 0).

    One sort per pixel column, then order statistics: removing the element of rank r from n sorted
    valid values leaves k = n - 1, whose median sits at remaining positions (k-1)//2 and k//2, i.e.
    sorted positions p (p < r) or p + 1 (p >= r). An uncovered epoch gets the plain median."""
    n, ny, nx = img.shape
    out = np.zeros((n, ny, nx), np.float32)
    for y0 in range(0, ny, rows):
        sl = slice(y0, min(ny, y0 + rows))
        v = img[:, sl].astype(np.float32, copy=True)
        good = ivar[:, sl] > 0
        v[~good] = np.inf  # invalid sorts last
        order = np.argsort(v, axis=0, kind="stable")
        srt = np.take_along_axis(v, order, axis=0)
        rank = np.empty_like(order)
        np.put_along_axis(rank, order, np.arange(n)[:, None, None].repeat(order.shape[1], 1).repeat(order.shape[2], 2), axis=0)
        nv = good.sum(axis=0)
        for i in range(n):
            gi = good[i]
            k = np.where(gi, nv - 1, nv)  # values remaining after leaving i out
            r = rank[i]
            p1, p2 = (k - 1) // 2, k // 2
            i1 = np.where(gi & (p1 >= r), p1 + 1, p1).clip(0, n - 1)
            i2 = np.where(gi & (p2 >= r), p2 + 1, p2).clip(0, n - 1)
            m = 0.5 * (np.take_along_axis(srt, i1[None], 0)[0] + np.take_along_axis(srt, i2[None], 0)[0])
            out[i, sl] = np.where((k > 0) & np.isfinite(m), m, 0)
    return out


def _shift_index(h: int):
    return [(dy, dx) for dy in range(-h, h + 1) for dx in range(-h, h + 1)]


def fit_kernel(ref: np.ndarray, img: np.ndarray, w: np.ndarray, use: np.ndarray | None = None,
               half: int = 2, nmax: int = 150_000, snr_min: float = 3.0, clip: float = 5.0,
               rng: np.random.Generator | None = None) -> tuple[np.ndarray, float]:
    """Fit img ~ K (x) ref + b over pixels with weight w > 0 (and `use`, if given).

    Pixels are drawn preferentially where the reference carries signal (ref * sqrt(w) > snr_min),
    where the kernel shape is constrained; one sigma-clipping pass removes variables, artefacts
    and saturated cores. Returns (kernel[(2h+1),(2h+1)], b); model = correlate(ref, K) + b."""
    rng = rng or np.random.default_rng(0)
    ny, nx = ref.shape
    ok = (w > 0) & np.isfinite(ref) & np.isfinite(img)
    if use is not None:
        ok &= use
    ok[:half, :] = ok[-half:, :] = False
    ok[:, :half] = ok[:, -half:] = False
    sig = ok & (ref * np.sqrt(np.maximum(w, 0)) > snr_min)
    iy, ix = np.nonzero(sig)
    if iy.size > nmax:
        k = rng.choice(iy.size, nmax, replace=False)
        iy, ix = iy[k], ix[k]
    # plus some sky pixels to pin the background
    sy, sx = np.nonzero(ok & ~sig)
    if sy.size:
        k = rng.choice(sy.size, min(sy.size, max(nmax // 5, 1000)), replace=False)
        iy, ix = np.concatenate([iy, sy[k]]), np.concatenate([ix, sx[k]])
    if iy.size < 50:
        k0 = np.zeros((2 * half + 1, 2 * half + 1))
        k0[half, half] = 1
        return k0, 0.0
    shifts = _shift_index(half)
    A = np.empty((iy.size, len(shifts) + 1))
    for j, (dy, dx) in enumerate(shifts):
        A[:, j] = ref[iy + dy, ix + dx]
    A[:, -1] = 1.0
    b = img[iy, ix].astype(np.float64)
    sw = np.sqrt(w[iy, ix]).astype(np.float64)
    keep = np.ones(iy.size, bool)
    for _ in range(2):
        p, *_ = np.linalg.lstsq(A[keep] * sw[keep, None], b[keep] * sw[keep], rcond=None)
        r = (b - A @ p) * sw
        mad = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep])))
        keep = np.abs(r) < clip * max(mad, 1e-12)
    K = p[:-1].reshape(2 * half + 1, 2 * half + 1)
    return K, float(p[-1])


def apply_kernel(ref: np.ndarray, ref_var: np.ndarray, K: np.ndarray, b: float):
    model = ndimage.correlate(ref.astype(np.float64), K, mode="nearest") + b
    mvar = ndimage.correlate(np.where(np.isfinite(ref_var), ref_var, 0).astype(np.float64), K**2, mode="nearest")
    return model, mvar


def blocks(ny: int, nx: int, block: int):
    """Non-overlapping (y0, y1, x0, x1) blocks covering the image (last row/col absorb remainders)."""
    ys = list(range(0, max(ny - block // 2, 1), block)) or [0]
    xs = list(range(0, max(nx - block // 2, 1), block)) or [0]
    for i, y0 in enumerate(ys):
        y1 = ny if i == len(ys) - 1 else ys[i + 1]
        for j, x0 in enumerate(xs):
            x1 = nx if j == len(xs) - 1 else xs[j + 1]
            yield y0, y1, x0, x1


def difference(img: np.ndarray, ivar: np.ndarray, ref: np.ndarray, ref_var: np.ndarray,
               use: np.ndarray | None = None, half: int = 2, block: int = 512, margin: int = 24,
               floor: np.ndarray | None = None, kernels: list | None = None):
    """One epoch minus its PSF-matched reference. Returns (D, sigma, kernels) with D, sigma float32
    and NaN where the epoch has no coverage. sigma is the nominal per-pixel noise (epoch + matched
    reference, plus `floor` in quadrature, see residual_floor); crowding and correlated-noise
    corrections are applied downstream on the S/N map. Passing `kernels` (from an earlier call on
    the same image) reuses them instead of refitting: used to subtract a leave-one-out reference
    with the kernel fitted against the full-season reference."""
    given = {k[0]: (k[1], k[2]) for k in kernels} if kernels is not None else None
    ny, nx = img.shape
    D = np.full((ny, nx), np.nan, np.float32)
    S = np.full((ny, nx), np.nan, np.float32)
    kernels = []
    for y0, y1, x0, x1 in blocks(ny, nx, block):
        fy0, fy1 = max(0, y0 - margin), min(ny, y1 + margin)
        fx0, fx1 = max(0, x0 - margin), min(nx, x1 + margin)
        sl = (slice(fy0, fy1), slice(fx0, fx1))
        w = ivar[sl]
        if not (w > 0).any():
            continue
        if given is not None and (y0, y1, x0, x1) in given:
            K, b = given[(y0, y1, x0, x1)]
        else:
            K, b = fit_kernel(ref[sl], img[sl], w, None if use is None else use[sl], half=half)
        kernels.append(((y0, y1, x0, x1), K, b))
        model, mvar = apply_kernel(ref[sl], ref_var[sl], K, b)
        iy, ix = slice(y0 - fy0, y1 - fy0), slice(x0 - fx0, x1 - fx0)
        wi = w[iy, ix]
        good = wi > 0
        d = (img[sl][iy, ix] - model[iy, ix]).astype(np.float32)
        v = 1 / np.where(good, wi, 1) + mvar[iy, ix]
        if floor is not None:
            v = v + floor[y0:y1, x0:x1].astype(np.float64) ** 2
        s = np.sqrt(v).astype(np.float32)
        D[y0:y1, x0:x1] = np.where(good, d, np.nan)
        S[y0:y1, x0:x1] = np.where(good, s, np.nan)
    return D, S, kernels


def background_mesh(D: np.ndarray, S: np.ndarray, box: int = 24, clip: float = 3.0) -> np.ndarray:
    """Smooth background of a difference image: sigma-clipped medians in box x box cells (the clip
    removes point sources, which cover ~20 of a cell's 576 px), bilinear interpolation. unWISE subtracts a
    per-frame sky that eats a varying fraction of a big galaxy's extended light, leaving arcminute-
    scale residuals in the difference that a per-block constant cannot remove; point sources
    (FWHM ~2.5 px) are untouched at box = 24 px (66")."""
    ny, nx = D.shape
    nby, nbx = max(1, ny // box), max(1, nx // box)
    grid = np.full((nby, nbx), np.nan)
    ye = np.linspace(0, ny, nby + 1).round().astype(int)  # uniform cells, matching the zoom below
    xe = np.linspace(0, nx, nbx + 1).round().astype(int)
    for i in range(nby):
        y0, y1 = ye[i], ye[i + 1]
        for j in range(nbx):
            x0, x1 = xe[j], xe[j + 1]
            v = D[y0:y1, x0:x1]
            sg = S[y0:y1, x0:x1]
            ok = np.isfinite(v) & np.isfinite(sg)
            if ok.sum() < 0.3 * v.size:
                continue
            v = v[ok]
            for _ in range(3):
                m = np.median(v)
                mad = 1.4826 * np.median(np.abs(v - m))
                if mad <= 0:
                    break
                v = v[np.abs(v - m) < clip * mad]
            grid[i, j] = np.median(v)
    if np.isnan(grid).all():
        return np.zeros_like(D)
    idx = ndimage.distance_transform_edt(np.isnan(grid), return_distances=False, return_indices=True)
    grid = grid[tuple(idx)]  # empty cells take their nearest neighbour
    full = ndimage.zoom(grid, (ny / nby, nx / nbx), order=1, mode="nearest", grid_mode=True)[:ny, :nx]
    return full.astype(np.float32)
