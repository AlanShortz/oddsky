"""NGC 55 fsn#7 (and neighbours) in the two cryogenic Spitzer/IRAC epochs (2003-12 and 2005-12): was the mid-IR
source already fading before WISE? Small-aperture photometry (r = 2 px = 2.4", sky 2-6 px, IRAC aperture corrections)
on the post-BCD mosaics downloaded to ~/oddsky-runs/imaging/scratch/h0012b-referee/spitzer_ngc55/, with the
epoch-to-epoch ratio of ~stars in the field as a calibration control.

    uv run python -I hunts/H-0012/reviews/h0012b-referee/spitzer_ngc55.py
Writes spitzer_ngc55.json and spitzer_ngc55.png next to this script.
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
D = Path("~/oddsky-runs/imaging/scratch/h0012b-referee/spitzer_ngc55").expanduser()
FILES = {("I1", 2003.96): "SPITZER_I1_5056000_0000_7_E8348429_maic.fits",
         ("I2", 2003.96): "SPITZER_I2_5056000_0000_7_E8348614_maic.fits",
         ("I1", 2005.97): "SPITZER_I1_14478592_0479_5_E8625232_maic.fits",
         ("I2", 2005.97): "SPITZER_I2_14478592_0479_5_E8622364_maic.fits"}
APCOR = {"I1": 1.213, "I2": 1.234}  # IRAC handbook, r = 2 px, sky 2-6 px
POS = {"fsn7": (3.80788, -39.2148), "obs184": (3.79288, -39.2126), "obs299": (3.79834, -39.2132),
       "fsn13": (3.7601, -39.2179)}


def phot(img, w, ra, dec, pxas):
    x, y = w.all_world2pix(ra, dec, 0)
    yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
    r = np.hypot(xx - x, yy - y)
    ap = r <= 2.4 / pxas
    sk = (r > 2.4 / pxas) & (r <= 7.2 / pxas) & np.isfinite(img)
    if not np.isfinite(img[ap]).all() or sk.sum() < 10:
        return np.nan, np.nan
    s = np.nanmedian(img[sk])
    f = np.nansum(img[ap] - s)
    e = np.nanstd(img[sk]) * np.sqrt(ap.sum())
    return f, e


def main():
    out = {}
    stamps = {}
    for (band, ep), fn in FILES.items():
        p = D / fn
        if not p.exists():
            print("missing", fn, file=sys.stderr)
            continue
        h = fits.open(p, memmap=True)
        img = h[0].data
        w = WCS(h[0].header)
        pxas = abs(h[0].header.get("PXSCAL1", -1.2))
        conv = 1e6 * (pxas / 206265) ** 2 * 1e6  # MJy/sr * px -> uJy
        res = {}
        for lab, (ra, dec) in POS.items():
            x, y = w.all_world2pix(ra, dec, 0)
            x, y = int(round(float(x))), int(round(float(y)))
            if not (20 < x < img.shape[1] - 20 and 20 < y < img.shape[0] - 20):
                res[lab] = None
                continue
            sub = img[y - 20:y + 21, x - 20:x + 21].astype(float)
            sw = w[y - 20:y + 21, x - 20:x + 21]
            f, e = phot(sub, sw, ra, dec, pxas)
            res[lab] = dict(ujy=float(f * conv * APCOR[band]), err=float(e * conv * APCOR[band]))
            if lab == "fsn7":
                sub2 = img[y - 25:y + 26, x - 25:x + 26].astype(float)
                stamps[(band, ep)] = sub2
        out[f"{band}_{ep}"] = dict(file=fn, pxscale=pxas, **res)
        h.close()
    # calibration control: bright compact sources in a 2' box around fsn7, matched between epochs
    ctrl = {}
    for band in ("I1", "I2"):
        try:
            h0 = fits.open(D / FILES[(band, 2003.96)]); h1 = fits.open(D / FILES[(band, 2005.97)])
        except FileNotFoundError:
            continue
        w0, w1 = WCS(h0[0].header), WCS(h1[0].header)
        i0, i1 = h0[0].data.astype(float), h1[0].data.astype(float)
        px0 = abs(h0[0].header.get("PXSCAL1", -1.2)); px1 = abs(h1[0].header.get("PXSCAL1", -1.2))
        x0, y0 = w0.all_world2pix(*POS["fsn7"], 0)
        x0, y0 = int(round(float(x0))), int(round(float(y0)))
        half = int(90 / px0)
        box = i0[max(y0 - half, 0):y0 + half, max(x0 - half, 0):x0 + half]
        from scipy import ndimage
        mx = ndimage.maximum_filter(np.nan_to_num(box), size=7)
        pk = np.argwhere((box == mx) & (box > np.nanpercentile(box, 99.0)))
        ratios = []
        for (py, pxx) in pk[:80]:
            ra, dec = w0.all_pix2world(pxx + max(x0 - half, 0), py + max(y0 - half, 0), 0)
            f0, _ = phot(i0[max(y0 - half, 0):y0 + half, max(x0 - half, 0):x0 + half], w0[max(y0 - half, 0):y0 + half, max(x0 - half, 0):x0 + half], ra, dec, px0)
            xx1, yy1 = w1.all_world2pix(ra, dec, 0)
            xx1, yy1 = int(round(float(xx1))), int(round(float(yy1)))
            if not (20 < xx1 < i1.shape[1] - 20 and 20 < yy1 < i1.shape[0] - 20):
                continue
            f1, _ = phot(i1[yy1 - 20:yy1 + 21, xx1 - 20:xx1 + 21], w1[yy1 - 20:yy1 + 21, xx1 - 20:xx1 + 21], ra, dec, px1)
            if np.isfinite(f0) and np.isfinite(f1) and f0 > 0:
                ratios.append(f1 / f0 * (px1 / px0) ** 2)
        ratios = np.array(ratios)
        ctrl[band] = dict(n=int(ratios.size), median_ratio_2005_over_2003=float(np.median(ratios)) if ratios.size else None,
                          robust_sd=float(1.4826 * np.median(np.abs(ratios - np.median(ratios)))) if ratios.size else None)
    out["control"] = ctrl
    (HERE / "spitzer_ngc55.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    if stamps:
        fig, ax = plt.subplots(1, len(stamps), figsize=(3 * len(stamps), 3))
        for a, (k, im) in zip(np.atleast_1d(ax), stamps.items()):
            v0, v1 = np.nanpercentile(im, [5, 99.5])
            a.imshow(np.arcsinh((im - v0) / max(v1 - v0, 1e-3) * 10), origin="lower", cmap="gray")
            a.plot(25, 25, "+", color="lime", ms=12)
            a.set_title(f"IRAC {k[0]} {k[1]}", fontsize=8); a.set_xticks([]); a.set_yticks([])
        fig.suptitle("NGC 55 fsn#7, Spitzer/IRAC cryogenic epochs (61\" boxes)", fontsize=9)
        fig.tight_layout(); fig.savefig(HERE / "spitzer_ngc55.png", dpi=90)


if __name__ == "__main__":
    main()
