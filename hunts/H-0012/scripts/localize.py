"""H-0012: where exactly is the flux change? Stack (NEOWISE epochs) - (2010-11 epochs) of the
difference images, matched-filter it, and report the extreme peak near a position.

    uv run python hunts/H-0012/scripts/localize.py NGC6946 3090p605 308.864833 60.135636 [radius_arcsec]

Within each season the reference cancels in the subtraction, so the stack is reference-free.
"""

from __future__ import annotations

import json
import sys

import numpy as np
from astropy.wcs import WCS

from oddsky.imaging import PIXSCALE, detect, fetch, flux_to_mjy
from oddsky.imaging.metrics import EARLY_MJD
from oddsky.imaging.pipeline import tile_dir


def wmean(D, S, sel, sl):
    """Inverse-variance mean of the selected epochs of a difference stack over a stamp."""
    dd = np.array(D[sel][:, sl[0], sl[1]], float)
    ww = 1 / np.array(S[sel][:, sl[0], sl[1]], float) ** 2
    ok = np.isfinite(dd) & np.isfinite(ww)
    num = np.where(ok, dd * ww, 0).sum(0)
    den = np.where(ok, ww, 0).sum(0)
    return num / den, 1 / np.sqrt(den)


def main(galaxy, tile, ra, dec, radius=12.0):
    wd = fetch.cache_root() / "work" / galaxy
    out = {}
    for band in (1, 2):
        d = tile_dir(wd, tile, band)
        meta = json.loads((d / "meta.json").read_text())
        wcs = WCS(meta["wcs"])
        x0, y0 = wcs.all_world2pix([[ra, dec]], 0)[0]
        h = 40
        xi, yi = int(round(x0)), int(round(y0))
        sl = (slice(yi - h, yi + h + 1), slice(xi - h, xi + h + 1))
        D = np.load(d / "D.npy", mmap_mode="r")
        S = np.load(d / "S.npy", mmap_mode="r")
        mjd = np.array(meta["mjd"])
        season = np.array(meta["season"])
        stacks = []
        for s in (0, 1):
            early = (season == s) & (mjd < EARLY_MJD)
            neo = (season == s) & (mjd > 56600)
            if early.any() and neo.any():
                a, ea = wmean(D, S, neo, sl)
                b, eb = wmean(D, S, early, sl)
                stacks.append((a - b, np.hypot(ea, eb)))
        num = sum(st[0] / st[1] ** 2 for st in stacks)
        den = sum(1 / st[1] ** 2 for st in stacks)
        diff, err = num / den, 1 / np.sqrt(den)
        psf = np.load(d / "psf_s0.npy")
        snr, F, E, c = detect.snr_map(diff.astype(np.float32), err.astype(np.float32), psf, box=40)
        yy, xx = np.mgrid[-h : h + 1, -h : h + 1]
        near = np.hypot(xx - (x0 - xi), yy - (y0 - yi)) * PIXSCALE < radius
        v = np.where(near & np.isfinite(snr), snr, 0)
        j = np.unravel_index(np.argmin(v), v.shape)  # most negative = faded
        px, py, pv = detect.find_peaks(np.where(near, -np.nan_to_num(snr), 0), 3.0)
        k = int(np.argmax(pv)) if pv.size else None
        if k is not None:
            fx, fy = px[k] + xi - h, py[k] + yi - h
            pra, pdec = wcs.all_pix2world([[fx, fy]], 0)[0]
            off = np.hypot((pra - ra) * np.cos(np.radians(dec)), pdec - dec) * 3600
        else:
            pra = pdec = off = np.nan
        # positional uncertainty ~ FWHM / (2.35 * S/N) for a PSF fit
        fwhm = 2.3 * PIXSCALE if band == 1 else 2.5 * PIXSCALE
        out[f"W{band}"] = dict(min_snr_within=float(v[j]), flux_change_mjy=float(flux_to_mjy(F[j], band)),
                               peak_ra=float(pra), peak_dec=float(pdec), offset_arcsec=float(off),
                               pos_err_arcsec=float(fwhm / (2.35 * abs(v[j]))) if v[j] else None,
                               snr_at_target=float(snr[h + int(round(y0 - yi)), h + int(round(x0 - xi))]))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], float(a[3]), float(a[4]), float(a[5]) if len(a) > 5 else 12.0)
