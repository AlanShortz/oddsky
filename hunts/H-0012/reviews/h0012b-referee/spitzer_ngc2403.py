"""NGC 2403 obs#50 in Spitzer/IRAC 2004-2019 (cryogenic + SPIRITS warm mosaics in
~/oddsky-runs/imaging/scratch/h0012b-referee/spitzer_ngc2403/). Each post-BCD mosaic is resampled (bilinear) onto a
common 0.6"/px tangent grid centred on the WISE position; per band a reference is the median of all epochs, and the
light curve is a 2.4"-radius aperture on (epoch - reference). The position of the variable source is the centroid of
(mean of the brightest epochs - mean of the faintest).

    uv run python -I hunts/H-0012/reviews/h0012b-referee/spitzer_ngc2403.py
Writes spitzer_ngc2403.json/.png next to this script.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from scipy import ndimage

HERE = Path(__file__).resolve().parent
D = Path("~/oddsky-runs/imaging/scratch/h0012b-referee/spitzer_ngc2403").expanduser()
RA, DEC = 114.228, 65.598
N, PX = 61, 0.6  # grid: 61 x 61 at 0.6" = 36.6"


def grid_radec():
    yy, xx = np.mgrid[:N, :N]
    dx = (xx - N // 2) * PX / 3600
    dy = (yy - N // 2) * PX / 3600
    dec = DEC + dy
    ra = RA - dx / np.cos(np.radians(DEC))  # east to the left (x increasing = west)
    return ra, dec


def main():
    gra, gdec = grid_radec()
    data = {"I1": [], "I2": []}
    for p in sorted(D.glob("SPITZER_I*_maic.fits")):
        band = "I1" if "_I1_" in p.name else "I2"
        try:
            im, mjd = sample(p, gra, gdec)
        except Exception as e:  # noqa: BLE001  (truncated download etc.)
            print("skip", p.name, str(e)[:80])
            continue
        if im is None:
            continue
        if not np.isfinite(im[N // 2 - 8:N // 2 + 9, N // 2 - 8:N // 2 + 9]).all():
            continue
        data[band].append((float(mjd), im, p.name))
    _finish(data)


def sample(p, gra, gdec):
    if True:
        with fits.open(p, memmap=True) as h:
            hd = h[0].header
            w = WCS(hd)
            x, y = w.all_world2pix(gra, gdec, 0)
            if x.min() < 2 or y.min() < 2 or x.max() > h[0].data.shape[1] - 3 or y.max() > h[0].data.shape[0] - 3:
                return None, None
            x0, x1 = int(x.min()) - 2, int(x.max()) + 3
            y0, y1 = int(y.min()) - 2, int(y.max()) + 3
            sub = np.asarray(h[0].data[y0:y1, x0:x1], float)
            im = ndimage.map_coordinates(sub, [y - y0, x - x0], order=1, mode="nearest", cval=np.nan)
            mjd = hd.get("MJD_OBS") or Time(hd["DATE_OBS"]).mjd
    return im, mjd


def _finish(data):
    conv = 1e6 * (PX / 206265) ** 2 * 1e6  # MJy/sr per 0.6" px -> uJy
    out = {}
    fig, ax = plt.subplots(2, 4, figsize=(15, 6.5), gridspec_kw=dict(width_ratios=[3, 1, 1, 1]))
    yy, xx = np.mgrid[:N, :N]
    for bi, band in enumerate(("I1", "I2")):
        rows = sorted(data[band], key=lambda t: t[0])
        if not rows:
            continue
        cube = np.array([r[1] for r in rows])
        mjd = np.array([r[0] for r in rows])
        ref = np.nanmedian(cube, 0)
        diff = cube - ref
        # remove a local plane per epoch (large-scale background differences between mosaics)
        r = np.hypot(xx - N // 2, yy - N // 2)
        ap = r <= 2.4 / PX
        sky = (r > 6 / PX) & (r < 15 / PX)
        lc = []
        for i in range(len(diff)):
            d = diff[i] - np.nanmedian(diff[i][sky])
            # empirical error: same aperture at 12 positions 10" away
            offs = []
            for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
                cx, cy = N // 2 + 10 / PX * np.cos(a), N // 2 + 10 / PX * np.sin(a)
                rr = np.hypot(xx - cx, yy - cy)
                offs.append(np.nansum(d[rr <= 2.4 / PX]))
            lc.append((float(mjd[i]), float(np.nansum(d[ap]) * conv * (1.213 if band == "I1" else 1.234)),
                       float(np.nanstd(offs) * conv)))
        lc = np.array(lc)
        hi = lc[:, 1] >= np.nanpercentile(lc[:, 1], 80)
        lo = lc[:, 1] <= np.nanpercentile(lc[:, 1], 30)
        dmap = np.nanmean(diff[hi], 0) - np.nanmean(diff[lo], 0)
        dm = dmap - np.nanmedian(dmap[sky])
        win = dm[N // 2 - 8:N // 2 + 9, N // 2 - 8:N // 2 + 9]
        jy, jx = np.unravel_index(np.nanargmax(ndimage.gaussian_filter(np.nan_to_num(win), 1.5)), win.shape)
        sy, sx = slice(jy - 3, jy + 4), slice(jx - 3, jx + 4)
        wgt = np.clip(win[sy, sx], 0, None)
        cyy, cxx = np.mgrid[sy, sx]
        cy = (cyy * wgt).sum() / wgt.sum() + N // 2 - 8
        cx = (cxx * wgt).sum() / wgt.sum() + N // 2 - 8
        pra = RA - (cx - N // 2) * PX / 3600 / np.cos(np.radians(DEC))
        pdec = DEC + (cy - N // 2) * PX / 3600
        out[band] = dict(lc=lc.round(2).tolist(), files=[r[2] for r in rows], var_position=[float(pra), float(pdec)],
                         offset_from_wise_arcsec=float(np.hypot((pra - RA) * np.cos(np.radians(DEC)), pdec - DEC) * 3600),
                         peak_diff_ujy_per_px=float(np.nanmax(win) * conv))
        yrs = 2000 + (lc[:, 0] - 51544.5) / 365.25
        ax[bi, 0].errorbar(yrs, lc[:, 1], lc[:, 2], fmt="o", ms=3, color="C0" if band == "I1" else "C3")
        ax[bi, 0].axhline(0, color="k", lw=0.5)
        ax[bi, 0].set_ylabel(f"IRAC {band} change vs median (uJy, r=2.4\")")
        v0, v1 = np.nanpercentile(ref, [5, 99.7])
        ax[bi, 1].imshow(np.arcsinh((ref - v0) / max(v1 - v0, 1e-6) * 10), origin="lower", cmap="gray")
        ax[bi, 1].set_title(f"{band} median", fontsize=8)
        v = np.nanpercentile(np.abs(dm), 99.5)
        ax[bi, 2].imshow(dm, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
        ax[bi, 2].set_title(f"{band} bright - faint epochs", fontsize=8)
        ax[bi, 3].imshow(diff[int(np.nanargmax(lc[:, 1]))] - np.nanmedian(diff[int(np.nanargmax(lc[:, 1]))][sky]),
                         origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
        ax[bi, 3].set_title(f"{band} peak epoch {yrs[int(np.nanargmax(lc[:, 1]))]:.2f}", fontsize=8)
        for a in ax[bi, 1:]:
            a.plot(N // 2, N // 2, "+", color="lime", ms=10)
            a.plot(cx, cy, "x", color="orange", ms=8)
            a.set_xticks([]); a.set_yticks([])
    ax[1, 0].set_xlabel("year")
    fig.suptitle("NGC 2403 obs#50 in Spitzer/IRAC (36\" boxes; + WISE position, x centroid of the variable)", fontsize=9)
    fig.tight_layout(); fig.savefig(HERE / "spitzer_ngc2403.png", dpi=90)
    (HERE / "spitzer_ngc2403.json").write_text(json.dumps(out, indent=1))
    for b, o in out.items():
        print(b, "n", len(o["lc"]), "pos", o["var_position"], "offset", round(o["offset_from_wise_arcsec"], 2))
        for m, f, e in o["lc"]:
            print(f"  {2000 + (m - 51544.5) / 365.25:.2f} {f:8.1f} {e:6.1f}")


if __name__ == "__main__":
    main()
