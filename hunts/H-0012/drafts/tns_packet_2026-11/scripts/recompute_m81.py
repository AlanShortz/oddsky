"""TNS packet 2026-11 (M81 = OS-0035): tns_validation/recompute_numbers.py re-run on the cached unWISE neo11
epochal coadds of tile 1507p696 (the only candidate tile fully cached), as a cross-check of lc_screen.py.

1. Per-epoch timing AT THE SOURCE: the unWISE header MJDMIN/MJDMAX are tile-wide (1.56 deg tile), so the epoch MJD
   used so far (their midpoint) is not necessarily the mean time of the exposures covering the source. Query IRSA's
   NEOWISE-R single-exposure (L1b) frame index for every frame containing the position, and compare with the
   unWISE n-m (exposure count) map at the source pixel.
2. Photometry: per-season pre-event median reference, LEAVE-ONE-OUT (an epoch never enters its own reference),
   5x5 least-squares PSF-matching kernel + constant, forced PSF photometry at the HST 2021 position, noise rescaled
   by the robust scatter of D/sigma in a 120-px box. Fluxes in uJy via the unWISE Vega zero points used by the repo
   (F0 = 309.540 / 171.787 Jy); AB magnitudes = -2.5 log10(f / 3631 Jy).

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/recompute_m81.py
Outputs: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/numbers_m81/ (pre-event = 2014.0-2023.5; forced at the
WISE centroid instead of an HST position)
"""
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS

from oddsky.imaging import F0_JY, fetch, psf as P
from oddsky.imaging.stack import load_stack

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/numbers_m81"
OUT.mkdir(parents=True, exist_ok=True)
RA, DEC = 148.739293, 69.146800  # WISE centroid of the 2023-24 eruption (lc_screen.py)
TILE = "1507p696"
WIN = (125, 595, 1700, 2048)  # around tile pixel (1938, 360)
PRE_LO, PRE_HI = 56900.0, 60126.0  # 2014.6-2023.5: 2010 still holds the tail of the 2009.9 event; epoch 2
# (2014-04, one frame at the source, mostly ivar = 0 here) is left out
HALF = 2

# ---------------------------------------------------------------- 1. exposure timing at the source
ibe = "https://irsa.ipac.caltech.edu/ibe/search/wise/neowiser/p1bm_frm"
url = f"{ibe}?POS={RA},{DEC}&ct=csv"
cached = OUT / "neowiser_l1b_frames_at_source.csv"
if cached.exists():  # IRSA resets connections intermittently: reuse the frame list fetched by an earlier run
    text = cached.read_text()
    print("using cached IRSA frame list", cached)
else:
  try:
    r = requests.get(url, headers={"User-Agent": "curl/8.7.1"}, timeout=300)
    r.raise_for_status()
    text = r.text
  except requests.RequestException:  # python TLS to IRSA was reset once; curl works
    import subprocess
    text = subprocess.run(["curl", "-s", "-m", "300", url], capture_output=True, text=True, check=True).stdout
frames = pd.read_csv(io.StringIO(text))
frames.to_csv(OUT / "neowiser_l1b_frames_at_source.csv", index=False)
print("IRSA NEOWISE-R L1b frames containing the source:", len(frames), "| URL:", url)

timing = []
for e in range(18, 23):
    for band in (1, 2):
        p = fetch.local_path(TILE, band, e, "img-m")
        hdr = fits.getheader(p)
        w = WCS(hdr)
        x, y = w.all_world2pix([[RA, DEC]], 0)[0]
        nmap = fits.getdata(fetch.local_path(TILE, band, e, "n-m"))
        n_at = int(nmap[int(round(y)), int(round(x))])
        lo, hi = float(hdr["MJDMIN"]), float(hdr["MJDMAX"])
        f = frames[(frames.band == band) & (frames.mjd_obs > lo - 0.5) & (frames.mjd_obs < hi + 0.5)]
        fq = f[f.qual_frame > 0]
        timing.append(dict(
            epoch=e, band=band, tile_mjdmin=lo, tile_mjdmax=hi, tile_mid=0.5 * (lo + hi), n_m_at_source=n_at,
            n_frames_irsa=len(f), n_frames_qual_gt0=len(fq),
            src_mjd_first=float(f.mjd_obs.min()) if len(f) else None,
            src_mjd_last=float(f.mjd_obs.max()) if len(f) else None,
            src_mjd_mean_all=float(f.mjd_obs.mean()) if len(f) else None,
            src_mjd_mean_qual=float(fq.mjd_obs.mean()) if len(fq) else None,
            src_utc_mean_qual=Time(fq.mjd_obs.mean(), format="mjd").iso if len(fq) else None,
            src_utc_first=Time(f.mjd_obs.min(), format="mjd").iso if len(f) else None,
            src_utc_last=Time(f.mjd_obs.max(), format="mjd").iso if len(f) else None,
        ))
tim = pd.DataFrame(timing)
tim.to_csv(OUT / "epoch_timing_at_source.csv", index=False)
print(tim.to_string())


# ---------------------------------------------------------------- 2. leave-one-out difference photometry
def fit_kernel(img, ref, ivar, mask, half=HALF):
    cols = [np.roll(np.roll(ref, dy, 0), dx, 1) for dy in range(-half, half + 1) for dx in range(-half, half + 1)]
    ok = mask & (ivar > 0)
    ok[:half + 1] = ok[-half - 1:] = False
    ok[:, :half + 1] = ok[:, -half - 1:] = False
    A = np.stack([c[ok] for c in cols] + [np.ones(ok.sum())], 1)
    wt = np.sqrt(ivar[ok])
    sol, *_ = np.linalg.lstsq(A * wt[:, None], img[ok] * wt, rcond=None)
    K = sol[:-1].reshape(2 * half + 1, 2 * half + 1)
    return sum(sol[i] * cols[i] for i in range(len(cols))) + sol[-1], K


def forced(D, S, psf, x, y, rad=6.0):
    h = psf.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    stp = P.shifted(psf, x - xi, y - yi)
    d = D[yi - h:yi + h + 1, xi - h:xi + h + 1]
    s = S[yi - h:yi + h + 1, xi - h:xi + h + 1]
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    ok = (np.hypot(xx - (x - xi), yy - (y - yi)) <= rad) & np.isfinite(d) & (s > 0) & np.isfinite(s)
    A = np.c_[stp[ok], np.ones(ok.sum())]
    wt = 1 / s[ok] ** 2
    cov = np.linalg.inv(A.T @ (A * wt[:, None]))
    p = cov @ (A.T @ (d[ok] * wt))
    return p[0], np.sqrt(cov[0, 0])


rows = []
for band in (1, 2):
    st = load_stack(TILE, band, window=WIN)
    x, y = st.wcs.all_world2pix([[RA, DEC]], 0)[0]
    yy, xx = np.mgrid[:st.img.shape[1], :st.img.shape[2]]
    srcmask = np.hypot(xx - x, yy - y) > 8
    box = (np.abs(yy - y) < 60) & (np.abs(xx - x) < 60) & srcmask
    psfs = {}
    for s_ in (0, 1):
        pre = np.where((st.season == s_) & (st.mjd > PRE_LO) & (st.mjd < PRE_HI))[0]
        ref = np.median(st.img[pre], 0)
        iv = np.where((st.ivar[pre] > 0).all(0), np.maximum(st.ivar[pre], 1e-30).mean(0), 0)
        psfs[s_] = P.build_psf(ref, P.find_stars(ref, iv * len(pre) / 1.2533 ** 2, snr_min=30, isolation=8, nmax=60))
    for i in range(st.n):
        s_ = int(st.season[i])
        pre = [j for j in np.where((st.season == s_) & (st.mjd > PRE_LO) & (st.mjd < PRE_HI))[0] if j != i]  # leave-one-out
        ref = np.median(st.img[pre], 0)
        refv = np.where((st.ivar[pre] > 0).all(0), 1.2533 ** 2 / np.maximum(st.ivar[pre], 1e-30).mean(0) / len(pre), np.inf)
        ok = st.ivar[i] > 0
        conv, K = fit_kernel(st.img[i], ref, st.ivar[i], srcmask & ok & np.isfinite(refv))
        D = st.img[i] - conv
        S = np.sqrt(np.where(ok, 1 / np.maximum(st.ivar[i], 1e-30), np.inf) + refv * (K ** 2).sum())
        z = (D / S)[box & np.isfinite(S)]
        mad = 1.4826 * np.median(np.abs(z - np.median(z)))
        S = S * max(mad, 1.0)
        try:
            f, e = forced(D, S, psfs[s_], x, y)
        except np.linalg.LinAlgError:  # epoch 2: one frame at the source, ivar = 0 (min_nexp = 2)
            f, e = np.nan, np.nan
        ujy, eujy = f * F0_JY[band] * 1e-3, e * F0_JY[band] * 1e-3
        rows.append(dict(band=band, epoch=int(st.epochs[i]), tile_mid_mjd=float(st.mjd[i]), season=s_, n_ref=len(pre),
                         uJy=ujy, e_uJy=eujy, snr=ujy / eujy, noise_scale=float(mad), kernel_sum=float(K.sum())))
lc = pd.DataFrame(rows)


def ab(f_ujy):
    return -2.5 * np.log10(np.asarray(f_ujy, float) * 1e-6 / 3631.0)


lc["AB"] = np.where(lc.uJy > 0, ab(lc.uJy.clip(lower=1e-9)), np.nan)
lc["e_mag"] = 1.0857 * lc.e_uJy / lc.uJy.abs()
lc["Vega"] = np.where(lc.uJy > 0, -2.5 * np.log10(lc.uJy.clip(lower=1e-9) * 1e-6 / lc.band.map(F0_JY)), np.nan)
lc["AB_lim3"] = ab(3 * lc.e_uJy)
lc["AB_lim5"] = ab(5 * lc.e_uJy)
lc["Vega_lim5"] = -2.5 * np.log10(5 * lc.e_uJy * 1e-6 / lc.band.map(F0_JY))
lc.to_csv(OUT / "loo_lightcurve.csv", index=False)
pd.set_option("display.width", 200)
print(lc.round(3).to_string())

first = {b: int(lc[(lc.band == b) & (lc.snr >= 5) & (lc.tile_mid_mjd > PRE_HI)].epoch.min()) for b in (1, 2)}
summary = {"first_epoch_ge5sigma": first, "timing": timing,
           "rows_e18_e22": lc[lc.epoch.between(18, 22)].round(4).to_dict("records")}
(OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
print("first >=5 sigma epoch per band:", first)
