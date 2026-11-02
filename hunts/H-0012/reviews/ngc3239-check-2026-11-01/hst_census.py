"""Census of HST variables / vanished sources in the 40" x 40" field around the WISE position, to estimate the chance
that an unrelated 2021-only optical source lies as close to the WISE position as the observed one.

    uv run python -I hunts/H-0012/reviews/ngc3239-check-2026-11-01/hst_census.py <scratch work dir>

For every positive and negative peak in F606W(2021 WFC3) - K*F606W(2022 ACS) with |S/N| > 5 (kernel fitted per 10" block):
forced PSF photometry in F814W(2021) - K*F814W(2025) (same camera and filter), and direct forced fluxes in 2021 F606W,
2022 ACS F606W and 2025 F555W/F814W. Classes:
  vanished : 2021 F606W diff > 5 sigma AND F814W diff > 3 sigma (same sign) AND ACS 2022 and F555W 2025 fluxes < 3 sigma
             AND diff/direct(2021) > 0.6 (i.e. a source that is essentially absent in the later epochs) -- like the candidate
  variable : |F606W diff| > 5 sigma AND F814W diff of the same sign > 3 sigma
Writes hst_census.csv and hst_census.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hst_lib as L  # noqa: E402

Z = np.load(Path(sys.argv[1]) / "registered.npz")
wcs = WCS(fits.Header.fromstring(str(Z["ref_wcs"])))
PIX = 0.04
WISE = (156.29118, 17.16387)
SRC = json.load(open(HERE / "hst_diff.json"))["source"]


def img(tag):
    a = Z[tag].astype(float)
    iv = Z[tag + "__ivar"].astype(float)
    return a, np.where(iv > 0, 1 / np.maximum(iv, 1e-30), np.nan)


def combine2(a, va, b, vb, k=5.0):
    m = (a / va + b / vb) / (1 / va + 1 / vb)
    bad = np.abs(a - b) > k * np.sqrt(va + vb)
    return np.where(bad, np.minimum(a, b), m), np.where(bad, np.where(a < b, va, vb), 1 / (1 / va + 1 / vb))


F6, V6 = img("16179_08_wfc3_uvis_f606w_ieb308")
F8, V8 = img("16179_08_wfc3_uvis_f814w_ieb308")
A6, VA6 = img("15446_76_acs_wfc_f606w_jdrz76")
a, va = img("17502_14_wfc3_uvis_f814w_ifab14u8"); b, vb = img("17502_14_wfc3_uvis_f814w_ifab14uk")
G8, VG8 = combine2(a, va, b, vb)
a, va = img("17502_14_wfc3_uvis_f555w_ifab14ui"); b, vb = img("17502_14_wfc3_uvis_f555w_ifab14uu")
G5, VG5 = combine2(a, va, b, vb)
ny, nx = F6.shape
yy, xx = np.mgrid[:ny, :nx]
wx, wy = wcs.all_world2pix([WISE], 0)[0]

# PSFs
xs, ys, _, _ = L.find_peaks(F6, nsig=20)
st = []
for x, y in zip(xs, ys):
    f = L.gauss2d_fit(F6, x, y, box=4)
    if f and 0.7 < f[3] < 1.4 and f[2] > 0:
        st.append(f[:2])
st = np.array(st)
dd = np.hypot(st[:, 0][:, None] - st[:, 0][None], st[:, 1][:, None] - st[:, 1][None]); np.fill_diagonal(dd, 99)
st = st[dd.min(1) > 10]
P6 = L.build_psf(F6, st[:, 0], st[:, 1])[0]
P8 = L.build_psf(F8, st[:, 0], st[:, 1])[0]
PA = L.build_psf(A6, st[:, 0], st[:, 1])[0]
PG8 = L.build_psf(G8, st[:, 0], st[:, 1])[0]
PG5 = L.build_psf(G5, st[:, 0], st[:, 1])[0]


def blockdiff(A, VA, B, VB, blk=250, pad=30):
    """Difference with a kernel fitted per block (blk px) to follow PSF variations; returns D, V (rescaled)."""
    D = np.full_like(A, np.nan); V = np.full_like(A, np.nan)
    for y0 in range(30, ny - 30, blk):
        for x0 in range(30, nx - 30, blk):
            y1, x1 = min(y0 + blk, ny - 30), min(x0 + blk, nx - 30)
            sl = (slice(y0 - pad, y1 + pad), slice(x0 - pad, x1 + pad))
            a_, b_ = A[sl], B[sl]
            m = np.isfinite(a_) & np.isfinite(b_)
            if m.sum() < 1000:
                continue
            conv, K, _ = L.fit_kernel(a_, b_, m, half=5)
            d_ = a_ - conv
            v_ = VA[sl] + ndimage.convolve(np.nan_to_num(VB[sl]), (K ** 2)[::-1, ::-1], mode="constant")
            D[y0:y1, x0:x1] = d_[pad:pad + (y1 - y0), pad:pad + (x1 - x0)]
            V[y0:y1, x0:x1] = v_[pad:pad + (y1 - y0), pad:pad + (x1 - x0)]
    z = (D / np.sqrt(V))[np.isfinite(D) & np.isfinite(V)]
    s = 1.4826 * np.median(np.abs(z - np.median(z)))
    return D, V * s ** 2, s


D6, W6, s6 = blockdiff(F6, V6, A6, VA6)
D8, W8, s8 = blockdiff(F8, V8, G8, VG8)


def mf(D, V, P):
    iv = np.where(np.isfinite(V) & (V > 0), 1 / V, 0)
    num = ndimage.correlate(np.nan_to_num(D) * iv, P, mode="constant")
    den = ndimage.correlate(iv, P ** 2, mode="constant")
    S = np.where(den > 0, num / np.sqrt(np.maximum(den, 1e-30)), np.nan)
    ok = np.isfinite(S)
    sc = 1.4826 * np.median(np.abs(S[ok] - np.median(S[ok])))
    return S / sc, sc


S6, sc6 = mf(D6, W6, P6)
valid = (xx > 45) & (xx < nx - 45) & (yy > 45) & (yy < ny - 45) & np.isfinite(S6)
rng = np.random.default_rng(3)


def local_err(im, V, P, x, y, n=120):
    v = []
    for _ in range(n):
        x0, y0 = x + rng.uniform(-37, 37), y + rng.uniform(-37, 37)
        if np.hypot(x0 - x, y0 - y) < 5:
            continue
        q = L.psf_phot(im, V, P, x0, y0, rad=3.5)
        if q and np.isfinite(q["flux"]):
            v.append(q["flux"])
    v = np.array(v)
    return 1.4826 * np.median(np.abs(v - np.median(v)))


rows = []
for sign in (1, -1):
    Ss = sign * np.nan_to_num(S6)
    pk = (Ss == ndimage.maximum_filter(Ss, 7)) & (Ss > 5) & valid
    for y, x in zip(*np.nonzero(pk)):
        r6 = L.psf_phot(D6, W6, P6, x, y, free=True, rad=3.5)
        if r6 is None or not np.isfinite(r6["flux"]) or np.hypot(r6["x"] - x, r6["y"] - y) > 2:
            continue
        X, Y = r6["x"], r6["y"]
        r8 = L.psf_phot(D8, W8, P8, X, Y, rad=3.5)
        d6 = L.psf_phot(F6, V6, P6, X, Y, rad=3.5)
        dA = L.psf_phot(A6, VA6, PA, X, Y, rad=3.5)
        g5 = L.psf_phot(G5, VG5, PG5, X, Y, rad=3.5)
        g8 = L.psf_phot(G8, VG8, PG8, X, Y, rad=3.5)
        if None in (r8, d6, dA, g5, g8):
            continue
        eA, e5 = max(dA["err"], local_err(A6, VA6, PA, X, Y)), max(g5["err"], local_err(G5, VG5, PG5, X, Y))
        rows.append(dict(x=X, y=Y, sep_wise=float(np.hypot(X - wx, Y - wy) * PIX), snr6_mf=float(S6[y, x]),
                         d6=r6["flux"], e6=r6["err"], snr6=r6["flux"] / r6["err"], d8=r8["flux"], e8=r8["err"], snr8=r8["flux"] / r8["err"],
                         f6_2021=d6["flux"], fA_2022=dA["flux"], eA_2022=eA, f5_2025=g5["flux"], e5_2025=e5, f8_2025=g8["flux"],
                         chi2_d6=r6["chi2nu"]))
C = pd.DataFrame(rows)
C["variable"] = (np.abs(C.snr6) > 5) & (np.sign(C.d8) == np.sign(C.d6)) & (np.abs(C.snr8) > 3)
C["vanished"] = ((C.snr6 > 5) & (C.snr8 > 3) & (C.fA_2022 < 3 * C.eA_2022) & (C.f5_2025 < 3 * C.e5_2025)
                 & (C.d6 / np.maximum(C.f6_2021, 1e-9) > 0.6))
C["brighter_2021"] = C.d6 > 0
area_arcsec2 = valid.sum() * PIX ** 2
C.to_csv(HERE / "hst_census.csv", index=False)
src = C.iloc[np.argmin(np.hypot(C.x - SRC["pix"][0], C.y - SRC["pix"][1]))]
res = dict(area_arcsec2=float(area_arcsec2), noise_scales=dict(D6=float(s6), D8=float(s8), mf6=float(sc6)),
           n_peaks=int(len(C)), n_variable=int(C.variable.sum()), n_variable_brighter2021=int((C.variable & C.brighter_2021).sum()),
           n_variable_fainter2021=int((C.variable & ~C.brighter_2021).sum()), n_vanished=int(C.vanished.sum()),
           candidate_row=src.to_dict())
# densities at the candidate's significance or above
for cls in ("variable", "vanished"):
    sel = C[C[cls] & (C.snr6 >= 0)]
    for thr in (5, 8, min(src.snr6, 15)):
        n = int((sel.snr6 >= thr).sum())
        rho = n / area_arcsec2
        out = {}
        for r in (0.37, 0.6, 1.0):
            out[f"P(<{r}\")"] = float(1 - np.exp(-rho * np.pi * r ** 2))
        res[f"{cls}_snr6>={thr:.1f}"] = dict(n=n, per_arcsec2=rho, **out)
print(json.dumps(res, indent=1, default=float))
print(C[C.vanished].sort_values("snr6", ascending=False).to_string())
json.dump(res, open(HERE / "hst_census.json", "w"), indent=1, default=float)
