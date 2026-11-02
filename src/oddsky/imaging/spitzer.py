"""Spitzer/IRAC archival light curves at fixed positions (2004-2019), for the H-0013 recurrence test.

Method (as in hunts/H-0012/reviews/h0012b-referee/spitzer_ngc2403.py, made reusable): every IRAC
post-BCD mosaic (`*_maic.fits`, from the Spitzer Heritage Archive via IRSA's SIA service) that covers
a position is resampled bilinearly onto a common small tangent-plane grid centred on it; per band the
reference is the median of all epochs; the light curve is a 2.4"-radius aperture on (epoch -
reference) after removing the median of a 6-15" annulus, with an aperture correction (IRAC handbook,
2.4" radius: 1.213 at 3.6 um, 1.234 at 4.5 um). The error is empirical: the scatter of the same
aperture at 12 positions 10" away. The position of the variable is the centroid of (mean of the
brightest epochs - mean of the faintest).

Politeness: IRSA does not serve byte ranges or cutouts for SHA files, so each mosaic (~13 MB) is
downloaded once, sampled at every requested position in it, and deleted; only the small grids are
kept. Requests are sequential with a pause; every failure is recorded as an error, never as a
missing epoch.
"""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import numpy as np

SIA_URL = "https://irsa.ipac.caltech.edu/SIA"
UA = "oddsky/0.1 (+https://github.com/AlanShortz/oddsky; open-source astronomy; polite)"
N_GRID, PX = 61, 0.6  # 61 x 61 px at 0.6" = 36.6" boxes
AP_R, SKY_R = 2.4, (6.0, 15.0)
APCORR = {"I1": 1.213, "I2": 1.234}
BANDS = {"IRAC1": "I1", "IRAC2": "I2"}


def grid_radec(ra: float, dec: float, n: int = N_GRID, px: float = PX):
    yy, xx = np.mgrid[:n, :n]
    dx = (xx - n // 2) * px / 3600
    dy = (yy - n // 2) * px / 3600
    return ra - dx / np.cos(np.radians(dec)), dec + dy  # x increases to the west


def sia_query(ra: float, dec: float, radius_deg: float = 0.001, client=None, timeout: float = 180) -> tuple[str, list[dict]]:
    """IRAC 3.6/4.5 um post-BCD mosaics covering (ra, dec). Returns (status, rows); status 'ok' or
    'ERR ...' (a failed query is not 'no data')."""
    import httpx
    import pandas as pd

    params = dict(COLLECTION="spitzer_sha", POS=f"circle {ra} {dec} {radius_deg}", RESPONSEFORMAT="CSV")
    try:
        c = client or httpx.Client(headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True)
        r = c.get(SIA_URL, params=params)
        r.raise_for_status()
        if not r.text.startswith("s_ra") and "access_url" not in r.text[:5000]:
            return f"ERR unexpected response: {r.text[:120]!r}", []
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}: {e}"[:300], []
    status = "ok"
    try:
        d = pd.read_csv(io.StringIO(r.text))
    except pd.errors.ParserError:
        # IRSA occasionally returns a row with an unquoted comma; keep the others and say how many were dropped
        d = pd.read_csv(io.StringIO(r.text), on_bad_lines="skip")
        n_lines = r.text.count("\n") - 1
        status = f"ok ({n_lines - len(d)} malformed rows skipped)"
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}: {e}"[:300], []
    d = d[d.access_url.astype(str).str.endswith("_maic.fits") & d.energy_bandpassname.isin(list(BANDS))]
    rows = [dict(url=u, band=BANDS[b], t_min=float(t), proposal=str(p), size_kb=float(s))
            for u, b, t, p, s in zip(d.access_url, d.energy_bandpassname, d.t_min, d.get("proposal_id", [""] * len(d)),
                                     d.access_estsize, strict=False)]
    return status, rows


def sample_mosaic(path_or_hdul, positions: dict) -> dict:
    """{label: (ra, dec)} -> {label: (grid image (MJy/sr) or None if not fully covered, mjd)}."""
    from astropy.io import fits
    from astropy.time import Time
    from astropy.wcs import WCS
    from scipy import ndimage

    out = {}
    h = fits.open(path_or_hdul, memmap=True) if not isinstance(path_or_hdul, fits.HDUList) else path_or_hdul
    try:
        hd = h[0].header
        data = h[0].data
        w = WCS(hd)
        mjd = hd.get("MJD_OBS") or Time(hd["DATE_OBS"]).mjd
        for lab, (ra, dec) in positions.items():
            gra, gdec = grid_radec(ra, dec)
            x, y = w.all_world2pix(gra, gdec, 0)
            if x.min() < 2 or y.min() < 2 or x.max() > data.shape[1] - 3 or y.max() > data.shape[0] - 3:
                out[lab] = (None, float(mjd))
                continue
            x0, x1 = int(x.min()) - 2, int(x.max()) + 3
            y0, y1 = int(y.min()) - 2, int(y.max()) + 3
            sub = np.asarray(data[y0:y1, x0:x1], float)
            im = ndimage.map_coordinates(sub, [y - y0, x - x0], order=1, mode="nearest")
            c = N_GRID // 2
            if not np.isfinite(im[c - 8:c + 9, c - 8:c + 9]).all():
                im = None
            out[lab] = (im, float(mjd))
    finally:
        if not isinstance(path_or_hdul, fits.HDUList):
            h.close()
    return out


def fetch_samples(rows: list[dict], positions: dict, cache: Path, pause: float = 2.0, local_dirs=(),
                  client=None, max_retries: int = 3, log=print) -> tuple[dict, list[dict]]:
    """Download each mosaic once (or use a local copy from `local_dirs`), sample it at every position,
    delete it. Samples are cached per (file, label) as npz under `cache`. Returns
    ({label: [(band, mjd, image, fname)]}, errors)."""
    import httpx

    cache.mkdir(parents=True, exist_ok=True)
    tmp = cache / "_tmp"
    tmp.mkdir(exist_ok=True)
    c = client or httpx.Client(headers={"User-Agent": UA}, timeout=300, follow_redirects=True)
    res = {lab: [] for lab in positions}
    errors = []
    for k, r in enumerate(rows):
        fname = r["url"].rsplit("/", 1)[-1]
        todo = {}
        for lab, pos in positions.items():
            cp = cache / f"{lab}__{fname}.npz"
            if cp.exists():
                z = np.load(cp)
                if z["ok"]:
                    res[lab].append((r["band"], float(z["mjd"]), z["im"], fname))
            else:
                todo[lab] = pos
        if not todo:
            continue
        local = next((Path(d) / fname for d in local_dirs if (Path(d) / fname).exists()), None)
        path = local
        if path is None:
            path = tmp / fname
            ok = False
            for attempt in range(max_retries):
                try:
                    with c.stream("GET", r["url"]) as resp:
                        if resp.status_code in (429, 500, 502, 503, 504):
                            raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
                        resp.raise_for_status()
                        with open(path, "wb") as fh:
                            for chunk in resp.iter_bytes(1 << 20):
                                fh.write(chunk)
                    ok = True
                    break
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"[:200]
                    time.sleep(pause * (4 ** attempt))
            time.sleep(pause)
            if not ok:
                errors.append(dict(url=r["url"], error=f"ERR download: {err}"))
                log(f"  ERR {fname}: {err}")
                path.unlink(missing_ok=True)
                continue
        try:
            s = sample_mosaic(str(path), todo)
        except Exception as e:  # noqa: BLE001  (truncated / corrupt file)
            errors.append(dict(url=r["url"], error=f"ERR read: {type(e).__name__}: {e}"[:200]))
            s = {}
        finally:
            if local is None:
                path.unlink(missing_ok=True)
        for lab, (im, mjd) in s.items():
            np.savez_compressed(cache / f"{lab}__{fname}.npz", im=im if im is not None else np.zeros(1), mjd=mjd,
                                ok=im is not None)
            if im is not None:
                res[lab].append((r["band"], mjd, im, fname))
        if (k + 1) % 10 == 0:
            log(f"  {k + 1}/{len(rows)} mosaics")
    return res, errors


def difference_lightcurve(samples: list, band: str) -> dict | None:
    """samples: [(band, mjd, image, fname)] -> light curve of one band (uJy change vs the median of
    all epochs), the variable's centroid offset and the per-epoch files."""
    from scipy import ndimage

    rows = sorted([s for s in samples if s[0] == band], key=lambda s: s[1])
    if len(rows) < 3:
        return None
    cube = np.array([s[2] for s in rows])
    mjd = np.array([s[1] for s in rows])
    ref = np.nanmedian(cube, 0)
    diff = cube - ref
    n = N_GRID
    yy, xx = np.mgrid[:n, :n]
    r = np.hypot(xx - n // 2, yy - n // 2)
    ap = r <= AP_R / PX
    sky = (r > SKY_R[0] / PX) & (r < SKY_R[1] / PX)
    conv = 1e6 * (PX / 206265) ** 2 * 1e6  # MJy/sr per px -> uJy
    lc = []
    for i in range(len(diff)):
        d = diff[i] - np.nanmedian(diff[i][sky])
        offs = []
        for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            cx, cy = n // 2 + 10 / PX * np.cos(a), n // 2 + 10 / PX * np.sin(a)
            offs.append(np.nansum(d[np.hypot(xx - cx, yy - cy) <= AP_R / PX]))
        lc.append((float(mjd[i]), float(np.nansum(d[ap]) * conv * APCORR[band]), float(np.nanstd(offs) * conv * APCORR[band])))
    lc = np.array(lc)
    hi = lc[:, 1] >= np.nanpercentile(lc[:, 1], 80)
    lo = lc[:, 1] <= np.nanpercentile(lc[:, 1], 30)
    dm = np.nanmean(diff[hi], 0) - np.nanmean(diff[lo], 0)
    dm = dm - np.nanmedian(dm[sky])
    c = n // 2
    win = dm[c - 8:c + 9, c - 8:c + 9]
    jy, jx = np.unravel_index(np.nanargmax(ndimage.gaussian_filter(np.nan_to_num(win), 1.5)), win.shape)
    jy, jx = int(np.clip(jy, 3, win.shape[0] - 4)), int(np.clip(jx, 3, win.shape[1] - 4))
    sy, sx = slice(jy - 3, jy + 4), slice(jx - 3, jx + 4)
    wgt = np.clip(win[sy, sx], 0, None)
    cyy, cxx = np.mgrid[sy, sx]
    if wgt.sum() > 0:
        cy = (cyy * wgt).sum() / wgt.sum() + c - 8
        cx = (cxx * wgt).sum() / wgt.sum() + c - 8
    else:
        cy = cx = float(c)
    return dict(mjd=lc[:, 0].tolist(), dflux=lc[:, 1].tolist(), err=lc[:, 2].tolist(), files=[s[3] for s in rows],
                var_offset_arcsec=float(np.hypot(cx - c, cy - c) * PX), var_dx_px=float(cx - c), var_dy_px=float(cy - c),
                bright_minus_faint=dm.astype(np.float32), reference=ref.astype(np.float32))


def to_json(lcs: dict) -> str:
    return json.dumps({b: {k: v for k, v in d.items() if k not in ("bright_minus_faint", "reference")}
                       for b, d in lcs.items() if d is not None}, indent=1)
