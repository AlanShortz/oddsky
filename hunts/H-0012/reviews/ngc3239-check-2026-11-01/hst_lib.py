"""Small HST helpers for the NGC 3239 check (fresh code; no drizzlepac/photutils needed).

Images are HAP single-visit drizzled (drc) products in e-/s. Everything is put on the pixel grid of a reference
cutout (WFC3/UVIS 2021-02-16 F606W, 0.04"/px) by WCS mapping + a star-based affine correction, resampled with a
cubic spline (flux per pixel rescaled by the pixel-area ratio), and converted to uJy per pixel.
"""
from __future__ import annotations

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy import ndimage, optimize

C_AA = 2.99792458e18  # speed of light, Angstrom/s


def to_ujy_factor(hdr) -> float:
    """e-/s -> uJy: f_lambda = PHOTFLAM * rate; f_nu = f_lambda * lam^2 / c (erg/s/cm2/Hz) -> uJy."""
    fl, lam = hdr["PHOTFLAM"], hdr["PHOTPLAM"]
    return fl * lam ** 2 / C_AA * 1e29


def ab(ujy):
    ujy = np.asarray(ujy, float)
    return np.where(ujy > 0, 23.9 - 2.5 * np.log10(np.where(ujy > 0, ujy, 1)), np.nan)


def load_drc(path):
    h = fits.open(path, memmap=True)
    sci = h["SCI"]
    wht = h["WHT"] if "WHT" in h else None
    return h, sci, wht


def cutout(path, ra, dec, half_px):
    """Slice the drc around (ra, dec) without resampling; returns data (uJy/px), weight, WCS, header, date."""
    h, sci, wht = load_drc(path)
    w = WCS(sci.header)
    x, y = w.all_world2pix([[ra, dec]], 0)[0]
    xi, yi = int(round(x)), int(round(y))
    y0, y1, x0, x1 = yi - half_px, yi + half_px + 1, xi - half_px, xi + half_px + 1
    ny, nx = sci.data.shape
    if y0 < 0 or x0 < 0 or y1 > ny or x1 > nx:
        pad = True
    else:
        pad = False
    data = np.full((2 * half_px + 1, 2 * half_px + 1), np.nan, np.float32)
    wd = np.zeros_like(data)
    sy0, sy1, sx0, sx1 = max(y0, 0), min(y1, ny), max(x0, 0), min(x1, nx)
    data[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = sci.data[sy0:sy1, sx0:sx1]
    if wht is not None:
        wd[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = wht.data[sy0:sy1, sx0:sx1]
    ww = w.deepcopy()
    ww.wcs.crpix = [w.wcs.crpix[0] - x0, w.wcs.crpix[1] - y0]
    if ww.sip is not None:
        ww.sip = None  # drc products have no SIP; guard anyway
    f = to_ujy_factor(sci.header)
    out = dict(data=data * f, wht=wd / f ** 2, wcs=ww, factor=f, date=h[0].header.get("DATE-OBS"),
               expstart=h[0].header.get("EXPSTART"), filt=h[0].header.get("FILTER") or h[0].header.get("FILTER1"),
               inst=h[0].header.get("INSTRUME"), wcsname=sci.header.get("WCSNAME"), exptime=h[0].header.get("EXPTIME"),
               pixscale=float(np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix))) * 3600), padded=pad)
    h.close()
    return out


def find_peaks(img, nsig=8.0, fwhm=2.0, border=12, sat=None):
    """Local maxima of a Gaussian-smoothed, background-subtracted image above nsig x robust sigma."""
    bkg = ndimage.median_filter(np.nan_to_num(img), size=25)
    r = np.nan_to_num(img) - bkg
    sm = ndimage.gaussian_filter(r, fwhm / 2.355)
    s = 1.4826 * np.median(np.abs(sm - np.median(sm)))
    pk = (sm == ndimage.maximum_filter(sm, 5)) & (sm > nsig * s)
    pk[:border] = pk[-border:] = False
    pk[:, :border] = pk[:, -border:] = False
    ys, xs = np.nonzero(pk)
    return xs.astype(float), ys.astype(float), sm[ys, xs] / s, r


def centroid(img, x, y, box=3, iters=4):
    for _ in range(iters):
        xi, yi = int(round(x)), int(round(y))
        if xi - box < 0 or yi - box < 0 or xi + box + 1 > img.shape[1] or yi + box + 1 > img.shape[0]:
            return np.nan, np.nan
        w = img[yi - box:yi + box + 1, xi - box:xi + box + 1]
        w = np.nan_to_num(w - np.nanmedian(w)).clip(0)
        s = w.sum()
        if s <= 0:
            return np.nan, np.nan
        yy, xx = np.mgrid[-box:box + 1, -box:box + 1]
        x, y = xi + (w * xx).sum() / s, yi + (w * yy).sum() / s
    return float(x), float(y)


def gauss2d_fit(img, x, y, box=4):
    """Fit an elliptical-free circular Gaussian + constant; returns x, y, flux, sigma, bkg."""
    xi, yi = int(round(x)), int(round(y))
    st = img[yi - box:yi + box + 1, xi - box:xi + box + 1]
    if st.shape != (2 * box + 1, 2 * box + 1) or not np.isfinite(st).all():
        return None
    yy, xx = np.mgrid[-box:box + 1, -box:box + 1]

    def m(p):
        dx, dy, f, s, b = p
        return f / (2 * np.pi * s ** 2) * np.exp(-((xx - dx) ** 2 + (yy - dy) ** 2) / (2 * s ** 2)) + b

    p0 = [x - xi, y - yi, max(st.sum() - st.min() * st.size, 1e-3), 1.0, np.median(st)]
    try:
        r = optimize.least_squares(lambda p: (m(p) - st).ravel(), p0, bounds=([-box, -box, -np.inf, 0.3, -np.inf], [box, box, np.inf, 5, np.inf]))
    except Exception:
        return None
    dx, dy, f, s, b = r.x
    return xi + dx, yi + dy, f, s, b


def resample(src, src_wcs, ref_wcs, shape, affine=None, order=3):
    """Map src onto the ref grid: for each ref pixel, world coords -> src pixel (+ optional affine correction applied
    in src pixel space), cubic-spline interpolation; multiply by (ref pix area / src pix area) to conserve flux."""
    ny, nx = shape
    yy, xx = np.mgrid[:ny, :nx].astype(float)
    ra, dec = ref_wcs.all_pix2world(xx.ravel(), yy.ravel(), 0)
    sx, sy = src_wcs.all_world2pix(ra, dec, 0)
    if affine is not None:
        a = affine
        sx, sy = a[0] + a[1] * sx + a[2] * sy, a[3] + a[4] * sx + a[5] * sy
    good = np.isfinite(src)
    filled = np.where(good, src, 0.0)
    out = ndimage.map_coordinates(filled, [sy, sx], order=order, mode="constant", cval=np.nan, prefilter=True)
    msk = ndimage.map_coordinates(good.astype(float), [sy, sx], order=1, mode="constant", cval=0.0)
    out = out.reshape(shape)
    out[msk.reshape(shape) < 0.99] = np.nan
    area = abs(np.linalg.det(ref_wcs.pixel_scale_matrix)) / abs(np.linalg.det(src_wcs.pixel_scale_matrix))
    return out * area


def fit_affine(x_pred, y_pred, x_meas, y_meas, clip=3.0, iters=5):
    """Affine map from predicted src-pixel positions to measured ones (6 params), sigma-clipped."""
    ok = np.isfinite(x_meas) & np.isfinite(y_meas)
    for _ in range(iters):
        A = np.c_[np.ones(ok.sum()), x_pred[ok], y_pred[ok]]
        px, *_ = np.linalg.lstsq(A, x_meas[ok], rcond=None)
        py, *_ = np.linalg.lstsq(A, y_meas[ok], rcond=None)
        rx = x_meas - (px[0] + px[1] * x_pred + px[2] * y_pred)
        ry = y_meas - (py[0] + py[1] * x_pred + py[2] * y_pred)
        rr = np.hypot(rx, ry)
        s = 1.4826 * np.nanmedian(rr[ok])
        new = np.isfinite(rr) & (rr < clip * max(s, 0.02))
        if (new == ok).all():
            break
        ok = new
    return np.r_[px, py], ok, float(np.nanstd(rx[ok])), float(np.nanstd(ry[ok]))


def fit_kernel(img, ref, mask, half=5, reg=0.0):
    """img ~ K (x) ref + b with a (2h+1)^2 delta-basis kernel (least squares over mask)."""
    cols = []
    for dy in range(-half, half + 1):
        for dx in range(-half, half + 1):
            cols.append(np.roll(np.roll(ref, dy, 0), dx, 1))
    ok = mask & np.isfinite(img) & np.isfinite(ref)
    ok[:half + 1] = ok[-half - 1:] = False
    ok[:, :half + 1] = ok[:, -half - 1:] = False
    A = np.stack([np.nan_to_num(c[ok]) for c in cols] + [np.ones(ok.sum())], 1)
    AtA = A.T @ A
    if reg:
        AtA[:-1, :-1] += reg * np.eye(AtA.shape[0] - 1) * np.trace(AtA) / AtA.shape[0]
    sol = np.linalg.solve(AtA, A.T @ img[ok])
    K = sol[:-1].reshape(2 * half + 1, 2 * half + 1)
    conv = ndimage.convolve(np.nan_to_num(ref), K[::-1, ::-1], mode="constant") + sol[-1]
    conv[~np.isfinite(ref)] = np.nan
    return conv, K, sol[-1]


def build_psf(img, xs, ys, size=15, ov=1):
    """Median of normalised, recentred star stamps (no oversampling)."""
    h = size // 2
    st = []
    for x, y in zip(xs, ys):
        xi, yi = int(round(x)), int(round(y))
        s = img[yi - h - 2:yi + h + 3, xi - h - 2:xi + h + 3]
        if s.shape != (size + 4, size + 4) or not np.isfinite(s).all():
            continue
        s = ndimage.shift(s.astype(float), (yi - y, xi - x), order=3)[2:-2, 2:-2]
        yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
        rr = np.hypot(xx, yy)
        s = s - np.median(s[rr >= h - 1])
        t = s[rr <= h - 1].sum()
        if t <= 0:
            continue
        st.append(s / t)
    if len(st) < 3:
        raise ValueError("too few PSF stars")
    S = np.array(st)
    med = np.median(S, 0)
    res = np.sqrt(((S - med)[:, h - 2:h + 3, h - 2:h + 3] ** 2).sum((1, 2)))
    good = res < 2.5 * np.median(res)
    psf = np.median(S[good], 0) if good.sum() >= 3 else med
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    psf[np.hypot(xx, yy) > h] = 0
    return psf / psf.sum(), int(good.sum())


def psf_phot(img, var, psf, x, y, free=False, rad=4.0, fit_bkg=True):
    """PSF-fit flux (and optionally position) with a constant background; returns dict with flux, err, x, y, chi2."""
    h = psf.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    d = img[yi - h:yi + h + 1, xi - h:xi + h + 1]
    v = var[yi - h:yi + h + 1, xi - h:xi + h + 1]
    if d.shape != psf.shape:
        return None
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]

    def lin(dx, dy):
        P = ndimage.shift(psf, (dy, dx), order=3, mode="constant")
        ok = (np.hypot(xx - dx, yy - dy) <= rad) & np.isfinite(d) & np.isfinite(v) & (v > 0)
        A = np.c_[P[ok], np.ones(ok.sum())] if fit_bkg else P[ok][:, None]
        wgt = 1 / v[ok]
        cov = np.linalg.inv(A.T @ (A * wgt[:, None]))
        p = cov @ (A.T @ (d[ok] * wgt))
        chi2 = (((d[ok] - A @ p) ** 2) * wgt).sum()
        return p, cov, chi2, ok.sum()

    dx, dy = x - xi, y - yi
    if free:
        r = optimize.minimize(lambda q: lin(q[0], q[1])[2], [dx, dy], method="Nelder-Mead",
                              options=dict(xatol=1e-3, fatol=1e-3))
        dx, dy = r.x
    p, cov, chi2, n = lin(dx, dy)
    return dict(flux=float(p[0]), err=float(np.sqrt(cov[0, 0])), x=float(xi + dx), y=float(yi + dy),
                bkg=float(p[1]) if fit_bkg else 0.0, chi2nu=float(chi2 / max(n - 2 - 2 * free, 1)))
