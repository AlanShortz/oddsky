"""Pre-event Spitzer (LVL, cryogenic, 2008-01-02, the only IRAC epoch) at the HST source: is there a dusty progenitor?

    uv run python -I hunts/H-0012/reviews/ngc3239-check-2026-11-01/spitzer_check.py <spitzer dir>

PSF fit (Gaussian, IRAC FWHM 1.66/1.72/1.88/1.98") + local plane at the HST position; error from the scatter of
fits at random positions within 15" (confusion-dominated). Expected fluxes of the 2024 JWST source if it had been
present in 2008, from a blackbody fitted to F300M and F335M, are printed for comparison.
"""
import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hst_lib as L  # noqa: E402

D = Path(sys.argv[1])
SRC = json.load(open(HERE / "hst_diff.json"))["source"]
J = json.load(open(HERE / "jwst_check.json"))
ra, dec = SRC["ra"], SRC["dec"]
FWHM = {"irac1": 1.66, "irac2": 1.72, "irac3": 1.88, "irac4": 1.98, "mips24": 5.9}
LAM = {"irac1": 3.55, "irac2": 4.49, "irac3": 5.73, "irac4": 7.87, "mips24": 23.7}
rng = np.random.default_rng(7)

# blackbody through the two NIRCam points (F300M 3.0 um avg of two epochs, F335M 3.35 um)
h_, c_, k_ = 6.626e-34, 2.998e8, 1.381e-23
f300 = 0.5 * (J["F300M_2024-04"]["flux_uJy"] + J["F300M_2024-05"]["flux_uJy"])
f335 = J["F335M_2024-04"]["flux_uJy"]


def bnu(lam_um, T):
    nu = c_ / (lam_um * 1e-6)
    return nu ** 3 / np.expm1(h_ * nu / (k_ * T))


Ts = np.linspace(250, 2000, 3501)
ratio = bnu(3.35, Ts) / bnu(2.99, Ts)
T = float(Ts[np.argmin(np.abs(ratio - f335 / f300))])
norm = f335 / bnu(3.35, T)
pred = {b: float(norm * bnu(l, T)) for b, l in LAM.items()}
# luminosity of that blackbody at 7.9 Mpc
d = 7.9 * 3.0857e22
F335 = f335 * 1e-32  # W/m2/Hz
nu335 = c_ / 3.35e-6
x = h_ * nu335 / (k_ * T)
frac = 15 / np.pi ** 4 * x ** 4 / np.expm1(x)  # nu F_nu / F_bol for a blackbody
Lbol = nu335 * F335 / frac * 4 * np.pi * d ** 2 / 3.828e26
R_au = np.sqrt(Lbol * 3.828e26 / (4 * np.pi * 5.670e-8 * T ** 4)) / 1.496e11
out = dict(jwst_bb=dict(T_K=T, Lbol_Lsun_7p9Mpc=float(Lbol), R_bb_au=float(R_au), F300M=f300, F335M=f335,
                        note="F335M contains the 3.3um PAH band; if part of F335M is PAH, T is lower than this"), predicted_2008_uJy=pred, measured={})
for b in ("irac1", "irac2", "irac3", "irac4", "mips24"):
    p = D / f"NGC3239_{b}.fits"
    if not p.exists():
        continue
    with fits.open(p) as hdul:
        hdu = hdul[0] if hdul[0].data is not None else hdul[1]
        img = hdu.data.astype(float)
        w = WCS(hdu.header).celestial
        if img.ndim > 2:
            img = img.reshape(img.shape[-2:])
    scale = float(np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix))) * 3600)
    pix_sr = (scale / 206264.806) ** 2
    img = img * pix_sr * 1e12  # MJy/sr -> uJy/px
    x0, y0 = w.all_world2pix([[ra, dec]], 0)[0]
    sig = FWHM[b] / 2.355 / scale
    hsz = int(np.ceil(4 * sig)) | 1
    yy, xx = np.mgrid[-hsz:hsz + 1, -hsz:hsz + 1]
    P = np.exp(-(xx ** 2 + yy ** 2) / (2 * sig ** 2)); P /= P.sum()
    var = np.ones_like(img)
    rad = 1.5 * FWHM[b] / scale
    r = L.psf_phot(img, var, P, x0, y0, rad=rad)
    rf = L.psf_phot(img, var, P, x0, y0, free=True, rad=rad)
    loc = []
    for _ in range(400):
        xr, yr = x0 + rng.uniform(-15, 15) / scale, y0 + rng.uniform(-15, 15) / scale
        if np.hypot(xr - x0, yr - y0) * scale < 2.5:
            continue
        q = L.psf_phot(img, var, P, xr, yr, rad=rad)
        if q and np.isfinite(q["flux"]):
            loc.append(q["flux"])
    loc = np.array(loc)
    el = float(1.4826 * np.median(np.abs(loc - np.median(loc))))
    out["measured"][b] = dict(pixscale=scale, flux_uJy=r["flux"], err_conf_uJy=el, snr=r["flux"] / el, frac_random_brighter=float((loc > r["flux"]).mean()),
                              free_fit_flux=rf["flux"], free_fit_shift_arcsec=float(np.hypot(rf["x"] - x0, rf["y"] - y0) * scale),
                              predicted_if_present=pred[b], predicted_over_err=pred[b] / el)
    print(b, {k: round(v, 3) for k, v in out["measured"][b].items()})
print(json.dumps(out["jwst_bb"], indent=1), json.dumps(pred, indent=1))
json.dump(out, open(HERE / "spitzer_check.json", "w"), indent=1)
