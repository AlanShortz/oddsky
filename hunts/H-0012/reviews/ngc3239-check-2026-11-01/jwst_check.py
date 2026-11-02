"""JWST (programme 3707, 2024-04-24 and 2024-05-22) NIRCam F150W/F300M/F335M and MIRI F770W/F2100W at the HST source.

    uv run python -I hunts/H-0012/reviews/ngc3239-check-2026-11-01/jwst_check.py <jwst dir> <scratch work dir>

Each NIRCam mosaic is registered to the HST 2021 F814W image (on the 2021 F606W grid) with compact sources common to both
(affine fit), then resampled onto a 0.04" grid; forced PSF photometry at the HST source; local-scatter limits.
Writes jwst_check.json and jwst_stamps.png.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hst_lib as L  # noqa: E402

JD = Path(sys.argv[1]); WD = Path(sys.argv[2])
Z = np.load(WD / "registered.npz")
rwcs = WCS(fits.Header.fromstring(str(Z["ref_wcs"])))
F8 = Z["16179_08_wfc3_uvis_f814w_ieb308"].astype(float)
F6 = Z["16179_08_wfc3_uvis_f606w_ieb308"].astype(float)
SRC = json.load(open(HERE / "hst_diff.json"))["source"]
sx, sy = SRC["pix"]
sra, sdec = SRC["ra"], SRC["dec"]
ny, nx = F8.shape
rng = np.random.default_rng(5)

# reference compact sources in HST F814W
xs, ys, snr, _ = L.find_peaks(F8, nsig=15)
ref = []
for x, y in zip(xs, ys):
    f = L.gauss2d_fit(F8, x, y, box=4)
    if f and 0.6 < f[3] < 1.6 and f[2] > 0:
        ref.append(f[:3])
ref = np.array(ref)
rra, rdec = rwcs.all_pix2world(ref[:, 0], ref[:, 1], 0)

files = {"F150W_2024-04": "jw03707-o038_t021_nircam_clear-f150w_i2d.fits", "F150W_2024-05": "jw03707-o138_t021_nircam_clear-f150w_i2d.fits",
         "F300M_2024-04": "jw03707-o038_t021_nircam_clear-f300m_i2d.fits", "F300M_2024-05": "jw03707-o138_t021_nircam_clear-f300m_i2d.fits",
         "F335M_2024-04": "jw03707-o038_t021_nircam_clear-f335m_i2d.fits", "F770W_2024-05": "jw03707-o137_t021_miri_f770w_i2d.fits",
         "F2100W_2024-05": "jw03707-o137_t021_miri_f2100w_i2d.fits"}
res, stamps = {}, {}
for tag, fn in files.items():
    with fits.open(JD / fn, memmap=True) as h:
        s = h["SCI"]; w = WCS(s.header)
        err = h["ERR"].data if "ERR" in h else None
        x0, y0 = w.all_world2pix([[sra, sdec]], 0)[0]
        pixsr = s.header["PIXAR_SR"]
        scale = float(np.sqrt(pixsr) * 206264.806)
        half = int(25 / scale)
        xi, yi = int(round(x0)), int(round(y0))
        sl = (slice(max(yi - half, 0), yi + half + 1), slice(max(xi - half, 0), xi + half + 1))
        img = np.array(s.data[sl], float) * pixsr * 1e12  # uJy / px
        ev = np.array(err[sl], float) * pixsr * 1e12 if err is not None else None
        ww = w.deepcopy(); ww.wcs.crpix = [w.wcs.crpix[0] - sl[1].start, w.wcs.crpix[1] - sl[0].start]
    cover = np.isfinite(img[min(yi, half), min(xi, half)]) if img.size else False
    # nearest finite pixel distance to the source
    fin = np.isfinite(img)
    yyc, xxc = np.nonzero(fin)
    cx, cy = ww.all_world2pix([[sra, sdec]], 0)[0]
    dmin = float(np.min(np.hypot(xxc - cx, yyc - cy)) * scale) if len(xxc) else np.inf
    if not np.isfinite(img[int(round(cy)), int(round(cx))]) if (0 <= int(round(cy)) < img.shape[0] and 0 <= int(round(cx)) < img.shape[1]) else True:
        res[tag] = dict(covered=False, nearest_valid_pixel_arcsec=dmin, pixscale=scale)
        print(tag, "not covered; nearest valid pixel", dmin, '"')
        continue
    # register: predicted positions of HST compact sources, centroid in JWST image
    px, py = ww.all_world2pix(rra, rdec, 0)
    mx, my = np.full(len(px), np.nan), np.full(len(px), np.nan)
    for i, (x, y) in enumerate(zip(px, py)):
        if not (6 < x < img.shape[1] - 7 and 6 < y < img.shape[0] - 7):
            continue
        f = L.gauss2d_fit(img, x, y, box=3 if scale > 0.05 else 4)
        if f is None or not (0.4 < f[3] < 3) or f[2] <= 0 or np.hypot(f[0] - x, f[1] - y) > 3:
            continue
        mx[i], my[i] = f[0], f[1]
    nmatch = int(np.isfinite(mx).sum())
    if nmatch >= 8:
        aff, ok, rx, ry = L.fit_affine(px, py, mx, my)
        shift = [float(np.nanmedian(mx[ok] - px[ok]) * scale * 1000), float(np.nanmedian(my[ok] - py[ok]) * scale * 1000)]
    else:
        aff, ok, rx, ry, shift = None, np.zeros(len(px), bool), np.nan, np.nan, [np.nan, np.nan]
    reg = L.resample(img, ww, rwcs, F8.shape, affine=aff)
    # PSF from the registered image's compact sources (stars matched above)
    good = ok & np.isfinite(mx)
    try:
        P, npsf = L.build_psf(reg, ref[good, 0], ref[good, 1], size=15 if scale < 0.05 else 31)
    except ValueError:
        P, npsf = None, 0
    out = dict(covered=True, pixscale=scale, n_match=nmatch, n_used=int(ok.sum()), reg_rms_mas=[float(rx * scale * 1000), float(ry * scale * 1000)],
               shift_mas=shift, n_psf=npsf)
    if P is not None:
        var = np.full_like(reg, 1.0)
        r = L.psf_phot(reg, var, P, sx, sy, rad=3.5 if scale < 0.05 else 8)
        rf = L.psf_phot(reg, var, P, sx, sy, free=True, rad=3.5 if scale < 0.05 else 8)
        loc = []
        for _ in range(300):
            x0_, y0_ = sx + rng.uniform(-40, 40), sy + rng.uniform(-40, 40)
            if np.hypot(x0_ - sx, y0_ - sy) < 6:
                continue
            q = L.psf_phot(reg, var, P, x0_, y0_, rad=3.5 if scale < 0.05 else 8)
            if q and np.isfinite(q["flux"]):
                loc.append(q["flux"])
        loc = np.array(loc)
        el = float(1.4826 * np.median(np.abs(loc - np.median(loc))))
        out.update(flux_uJy=r["flux"], err_local_uJy=el, snr=r["flux"] / el, mag_AB=float(L.ab(r["flux"])),
                   lim3_uJy=3 * el, lim3_AB=float(L.ab(3 * el)), free_fit_shift_mas=float(np.hypot(rf["x"] - sx, rf["y"] - sy) * 40),
                   free_fit_flux=rf["flux"])
    res[tag] = out
    stamps[tag] = reg[int(sy) - 50:int(sy) + 51, int(sx) - 50:int(sx) + 51]
    print(tag, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}), flush=True)

json.dump(res, open(HERE / "jwst_check.json", "w"), indent=1, default=float)
fig, axs = plt.subplots(1, len(stamps) + 2, figsize=(3 * (len(stamps) + 2), 3.3))
for a, (t, c) in zip(axs, [("HST F606W 2021-02", F6[int(sy) - 50:int(sy) + 51, int(sx) - 50:int(sx) + 51]),
                           ("HST F814W 2021-02", F8[int(sy) - 50:int(sy) + 51, int(sx) - 50:int(sx) + 51])] + list(stamps.items())):
    v0, v1 = np.nanpercentile(c, [5, 99.5])
    a.imshow(c, origin="lower", cmap="gray_r", vmin=v0, vmax=v1)
    a.plot(50 + sx - int(sx), 50 + sy - int(sy), "o", mfc="none", mec="orange", ms=12)
    a.set_title(t, fontsize=8); a.set_xticks([]); a.set_yticks([])
fig.suptitle("4\" boxes at the 2021-only HST source (orange); JWST resampled onto the HST grid", fontsize=9)
fig.tight_layout(); fig.savefig(HERE / "jwst_stamps.png", dpi=95)
