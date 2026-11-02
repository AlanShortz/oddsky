"""Independent re-derivation of the unWISE (neo11 epochal coadds) difference light curve, colour and position of
the NGC 3239 mid-IR transient at 156.2910 +17.1639.

Fresh code (uses only the repo's cache loader `oddsky.imaging.stack.load_stack` and the PSF builder): per-season
pre-event median references, a least-squares 5x5 PSF-matching kernel per epoch, forced PSF photometry, a free
PSF fit of position at the peak epochs, an injection-recovery estimate of the centroid error, and the absolute
astrometric tie of each epoch to Gaia DR3.

    uv run python hunts/H-0012/reviews/ngc3239-check-2026-11-01/wise_lc.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
import astropy.units as u
from scipy import ndimage, optimize

from oddsky.imaging import F0_JY, flux_to_mjy, psf as P
from oddsky.imaging.stack import load_stack

HERE = Path(__file__).resolve().parent
RA, DEC = 156.2910, 17.1639
TILE = "1556p166"
WIN = (1450, 1920, 0, 440)  # y0, y1, x0, x1 tile px
PRE_MJD = 59000.0  # reference epochs: everything before 2020-05-31
HALF = 2  # kernel half size
PIX = 2.75

gaia = pd.read_csv(HERE / "cat" / "gaia_dr3_12arcmin.csv")


def fit_kernel(img, ref, ivar, mask, half=HALF):
    """img ~ K (x) ref + b, K a (2h+1)^2 kernel, by weighted least squares over unmasked pixels."""
    ny, nx = ref.shape
    cols = []
    for dy in range(-half, half + 1):
        for dx in range(-half, half + 1):
            cols.append(np.roll(np.roll(ref, dy, 0), dx, 1))
    ok = mask & (ivar > 0)
    ok[:half + 1] = ok[-half - 1:] = False
    ok[:, :half + 1] = ok[:, -half - 1:] = False
    A = np.stack([c[ok] for c in cols] + [np.ones(ok.sum())], 1)
    w = np.sqrt(ivar[ok])
    sol, *_ = np.linalg.lstsq(A * w[:, None], img[ok] * w, rcond=None)
    K = sol[:-1].reshape(2 * half + 1, 2 * half + 1)
    conv = sum(sol[i] * cols[i] for i in range(len(cols))) + sol[-1]
    return conv, K, sol[-1]


def psf_fit(D, S, psf, x0, y0, rad=6.0):
    """Free (x, y, flux, bkg) PSF fit; returns params and covariance-based errors."""
    h = psf.shape[0] // 2

    def model(p):
        x, y, f, b = p
        xi, yi = int(round(x0)), int(round(y0))
        st = P.shifted(psf, x - xi, y - yi)
        return st * f + b

    xi, yi = int(round(x0)), int(round(y0))
    d = D[yi - h:yi + h + 1, xi - h:xi + h + 1]
    s = S[yi - h:yi + h + 1, xi - h:xi + h + 1]
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    ok = (np.hypot(xx - (x0 - xi), yy - (y0 - yi)) <= rad) & np.isfinite(d) & (s > 0)

    def res(p):
        return ((model(p) - d) / s)[ok]

    r = optimize.least_squares(res, [x0, y0, max(d[ok].max(), 1) * 10, 0.0], x_scale=[0.3, 0.3, 50, 1])
    J = r.jac
    cov = np.linalg.pinv(J.T @ J) * max(1.0, (r.fun ** 2).sum() / (ok.sum() - 4))
    return r.x, np.sqrt(np.diag(cov)), (r.fun ** 2).sum() / (ok.sum() - 4)


def forced(D, S, psf, x, y, rad=6.0):
    h = psf.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    st = P.shifted(psf, x - xi, y - yi)
    d = D[yi - h:yi + h + 1, xi - h:xi + h + 1]
    s = S[yi - h:yi + h + 1, xi - h:xi + h + 1]
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    ok = (np.hypot(xx - (x - xi), yy - (y - yi)) <= rad) & np.isfinite(d) & (s > 0)
    A = np.c_[st[ok], np.ones(ok.sum())]
    w = 1 / s[ok] ** 2
    cov = np.linalg.inv(A.T @ (A * w[:, None]))
    p = cov @ (A.T @ (d[ok] * w))
    return p[0], np.sqrt(cov[0, 0])


out = {}
lc_rows = []
fig, axes = plt.subplots(3, 1, figsize=(8, 9))
for band in (1, 2):
    st = load_stack(TILE, band, window=WIN)
    w = st.wcs
    x, y = w.all_world2pix([[RA, DEC]], 0)[0]
    n = st.n
    # stars for PSF and the astrometric tie
    gx, gy = w.all_world2pix(np.c_[gaia.ra, gaia.dec], 0).T
    psfs, refs, refv = {}, {}, {}
    for s_ in (0, 1):
        pre = np.where((st.season == s_) & (st.mjd < PRE_MJD))[0]
        refs[s_] = np.median(st.img[pre], 0)
        iv = st.ivar[pre]
        refv[s_] = np.where((iv > 0).all(0), 1.2533 ** 2 / np.maximum(iv, 1e-30).mean(0) / len(pre), np.inf)
        stars = P.find_stars(refs[s_], 1 / refv[s_], snr_min=30, isolation=8, nmax=60)
        psfs[s_] = P.build_psf(refs[s_], stars)
    srcmask = np.hypot(*(np.mgrid[:st.img.shape[1], :st.img.shape[2]] - np.array([y, x])[:, None, None])) > 8
    D = np.zeros_like(st.img)
    S = np.zeros_like(st.img)
    # absolute astrometry per epoch: centroid Gaia stars (G 13.5-18.5, isolated, ruwe<1.4, |pm| known) on the epoch image
    good = ((gaia.phot_g_mean_mag > 13.5) & (gaia.phot_g_mean_mag < 18.0) & (gaia.ruwe < 1.4)
            & (gx > 15) & (gx < st.img.shape[2] - 15) & (gy > 15) & (gy < st.img.shape[1] - 15)).values
    # isolation from any other Gaia source brighter than G+2 within 12"
    cg = SkyCoord(gaia.ra.values * u.deg, gaia.dec.values * u.deg)
    idx, d2, _ = cg.match_to_catalog_sky(cg, nthneighbor=2)
    good &= d2.arcsec > 15
    # exclude the galaxy body (within 2.5' of NGC 3239's centre 156.2703 +17.1637)
    good &= cg.separation(SkyCoord(156.2703 * u.deg, 17.1637 * u.deg)).arcmin > 2.5
    astro = []
    for i in range(n):
        s_ = int(st.season[i])
        ok = st.ivar[i] > 0
        conv, K, b = fit_kernel(st.img[i], refs[s_], st.ivar[i], srcmask & ok)
        D[i] = st.img[i] - conv
        var = np.where(ok, 1 / np.maximum(st.ivar[i], 1e-30), np.inf) + refv[s_] * (K ** 2).sum()
        S[i] = np.sqrt(var)
        # empirical noise rescale: robust std of D/S in a 60 px box excluding the source
        box = (np.abs(np.mgrid[:D.shape[1], :D.shape[2]][0] - y) < 60) & (np.abs(np.mgrid[:D.shape[1], :D.shape[2]][1] - x) < 60) & srcmask & np.isfinite(S[i])
        z = (D[i] / S[i])[box]
        mad = 1.4826 * np.median(np.abs(z - np.median(z)))
        S[i] *= max(mad, 1.0)
        f, e = forced(D[i], S[i], psfs[s_], x, y)
        lc_rows.append(dict(band=band, epoch=int(st.epochs[i]), mjd=float(st.mjd[i]), season=s_, flux_nmgy=f, err_nmgy=e,
                            uJy=flux_to_mjy(f, band) * 1e3, e_uJy=flux_to_mjy(e, band) * 1e3, noise_scale=float(mad),
                            kernel_sum=float(K.sum())))
        # astrometric offsets of Gaia stars on the epoch image (epoch-propagated Gaia positions)
        yr = 2000 + (st.mjd[i] - 51544.5) / 365.25
        dt = yr - 2016.0
        ra_e = gaia.ra + np.nan_to_num(gaia.pmra) * dt / 3.6e6 / np.cos(np.radians(gaia.dec))
        de_e = gaia.dec + np.nan_to_num(gaia.pmdec) * dt / 3.6e6
        ex, ey = w.all_world2pix(np.c_[ra_e[good], de_e[good]], 0).T
        dxs, dys = [], []
        for xx_, yy_ in zip(ex, ey):
            cx, cy = P.centroid(st.img[i], xx_, yy_, box=2, iters=4)
            # PSF-fit centroid (more robust than first moment)
            try:
                pp, ee, _ = psf_fit(st.img[i], np.where(ok, np.sqrt(1 / np.maximum(st.ivar[i], 1e-30)), np.inf), psfs[s_], cx, cy, rad=4)
                if np.hypot(pp[0] - xx_, pp[1] - yy_) < 1.0 and pp[2] > 0:
                    dxs.append(pp[0] - xx_); dys.append(pp[1] - yy_)
            except Exception:
                pass
        dxs, dys = np.array(dxs), np.array(dys)
        astro.append(dict(epoch=int(st.epochs[i]), n=len(dxs), dx_med=float(np.median(dxs)), dy_med=float(np.median(dys)),
                          dx_std=float(1.4826 * np.median(np.abs(dxs - np.median(dxs)))),
                          dy_std=float(1.4826 * np.median(np.abs(dys - np.median(dys))))))
    # peak epochs: free PSF fit
    lc = pd.DataFrame([r for r in lc_rows if r["band"] == band])
    peaks = {}
    for i in range(n):
        if lc.iloc[i].uJy / lc.iloc[i].e_uJy > 8:
            s_ = int(st.season[i])
            p, e, chi2 = psf_fit(D[i], S[i], psfs[s_], x, y)
            a = astro[i]
            # correct the fitted pixel position for the epoch's mean astrometric offset vs Gaia
            xc, yc = p[0] - a["dx_med"], p[1] - a["dy_med"]
            ra_f, de_f = w.all_pix2world([[xc, yc]], 0)[0]
            ra_raw, de_raw = w.all_pix2world([[p[0], p[1]]], 0)[0]
            # injection-recovery: add PSF of the fitted flux at 300 random positions in the D image
            rng = np.random.default_rng(band * 100 + i)
            rec = []
            hh = psfs[s_].shape[0] // 2
            tries = 0
            while len(rec) < 300 and tries < 3000:
                tries += 1
                xi = rng.uniform(hh + 2, D.shape[2] - hh - 3)
                yi = rng.uniform(hh + 2, D.shape[1] - hh - 3)
                if np.hypot(xi - x, yi - y) < 10 or not np.isfinite(S[i][int(yi) - hh:int(yi) + hh + 1, int(xi) - hh:int(xi) + hh + 1]).all():
                    continue
                Dt = D[i].copy()
                ix_, iy_ = int(round(xi)), int(round(yi))
                Dt[iy_ - hh:iy_ + hh + 1, ix_ - hh:ix_ + hh + 1] += P.shifted(psfs[s_], xi - ix_, yi - iy_) * p[2]
                try:
                    q, _, _ = psf_fit(Dt, S[i], psfs[s_], xi + rng.normal(0, 0.3), yi + rng.normal(0, 0.3))
                    rec.append((q[0] - xi, q[1] - yi))
                except Exception:
                    continue
            rec = np.array(rec)
            rec = rec[(np.abs(rec) < 3).all(1)]
            sx = 1.4826 * np.median(np.abs(rec[:, 0] - np.median(rec[:, 0])))
            sy = 1.4826 * np.median(np.abs(rec[:, 1] - np.median(rec[:, 1])))
            sep = SkyCoord(ra_f * u.deg, de_f * u.deg).separation(SkyCoord(RA * u.deg, DEC * u.deg)).arcsec
            peaks[int(st.epochs[i])] = dict(
                mjd=float(st.mjd[i]), season=s_, x=float(p[0]), y=float(p[1]), flux_uJy=float(flux_to_mjy(p[2], band) * 1e3),
                fit_err_px=[float(e[0]), float(e[1])], inj_err_px=[float(sx), float(sy)], inj_err_arcsec=[float(sx * PIX), float(sy * PIX)],
                inj_bias_px=[float(np.median(rec[:, 0])), float(np.median(rec[:, 1]))], n_inj=len(rec),
                gaia_tie_px=[a["dx_med"], a["dy_med"]], gaia_tie_scatter_px=[a["dx_std"], a["dy_std"]], gaia_tie_n=a["n"],
                ra_raw=float(ra_raw), dec_raw=float(de_raw), ra=float(ra_f), dec=float(de_f), sep_from_claim_arcsec=float(sep),
                chi2nu=float(chi2))
    out[f"W{band}"] = dict(peaks=peaks, astro=astro, psf_fwhm_px={s: P.fwhm(psfs[s]) for s in psfs},
                           claim_pix=[float(x), float(y)])
    # panels
    ax = axes[band - 1]
    ax.errorbar(lc.mjd, lc.uJy, lc.e_uJy, fmt="o", ms=4, color="C0" if band == 1 else "C3")
    for s_ in (0, 1):
        m = lc.season == s_
        ax.plot(lc.mjd[m], lc.uJy[m], "-", lw=0.6, alpha=0.5, color="k" if s_ else "gray")
    ax.axhline(0, color="k", lw=0.5)
    ax.axvline(59261.8, color="g", ls=":", label="HST 2021-02-15")
    ax.set_ylabel(f"W{band} difference flux (uJy)")
    ax.legend(fontsize=7)

lc = pd.DataFrame(lc_rows)
lc.to_csv(HERE / "wise_lc.csv", index=False)
# colours and luminosities of the transient light per epoch (W1, W2 matched by epoch)
m = lc.pivot_table(index="epoch", columns="band", values=["uJy", "e_uJy", "mjd"])
rows = []
for ep, r in m.iterrows():
    f1, f2 = r[("uJy", 1)], r[("uJy", 2)]
    e1, e2 = r[("e_uJy", 1)], r[("e_uJy", 2)]
    if f1 / e1 > 5 and f2 / e2 > 5:
        w1 = -2.5 * np.log10(f1 * 1e-6 / F0_JY[1])
        w2 = -2.5 * np.log10(f2 * 1e-6 / F0_JY[2])
        rows.append(dict(epoch=int(ep), mjd=float(r[("mjd", 1)]), W1_uJy=f1, W2_uJy=f2, W1_vega=w1, W2_vega=w2, W1mW2=w1 - w2,
                         W1mW2_err=1.0857 * np.hypot(e1 / f1, e2 / f2)))
out["colour"] = rows
json.dump(out, open(HERE / "wise_result.json", "w"), indent=1, default=float)
axes[2].axis("off")
axes[2].text(0, 0.9, json.dumps(rows, indent=0, default=lambda v: round(float(v), 3))[:900], fontsize=6, va="top", family="monospace")
fig.suptitle("NGC 3239 156.2910 +17.1639: independent unWISE neo11 difference photometry (pre-2020.4 per-season refs)", fontsize=9)
fig.tight_layout()
fig.savefig(HERE / "wise_lc.png", dpi=110)
print(lc[["band", "epoch", "mjd", "season", "uJy", "e_uJy", "noise_scale", "kernel_sum"]].to_string())
print(json.dumps({k: v["peaks"] for k, v in out.items() if k.startswith("W")}, indent=1, default=float))
print(json.dumps(rows, indent=1, default=float))
for b in ("W1", "W2"):
    print(b, "astro tie per epoch (px):", [(a["epoch"], a["n"], round(a["dx_med"], 3), round(a["dy_med"], 3), round(a["dx_std"], 2)) for a in out[b]["astro"]])
