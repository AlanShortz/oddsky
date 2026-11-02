"""Put every HST drc (visit-level and per-exposure) on the pixel grid of the 2021-02-16 WFC3/UVIS F606W visit drc,
40" x 40" around the WISE position, with a star-based affine correction on top of each image's WCS.

    uv run python -I hunts/H-0012/reviews/ngc3239-check-2026-11-01/hst_register.py <hst dir> <scratch out dir>
Writes <scratch>/registered.npz (all images in uJy/px + inverse variance) and hst_register.json (affine fits).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hst_lib as L  # noqa: E402

D = Path(sys.argv[1])
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
RA, DEC = 156.29118, 17.16387  # independent WISE position (wise_lc.py)
HALF = 500  # 1001 x 1001 px at 0.04" = 40"

ref = L.cutout(D / "hst_16179_08_wfc3_uvis_f606w_ieb308_drc.fits", RA, DEC, HALF)
R = ref["data"]
xs, ys, snr, _ = L.find_peaks(R, nsig=15, fwhm=2.0)
# compact sources only: Gaussian sigma < 1.6 px, not saturated, and isolated (no brighter peak within 8 px)
stars = []
for x, y, s in zip(xs, ys, snr):
    fit = L.gauss2d_fit(R, x, y, box=4)
    if fit is None:
        continue
    fx, fy, fl, sg, b = fit
    if 0.6 < sg < 1.6 and fl > 0:
        stars.append((fx, fy, fl))
stars = np.array(stars)
d = np.hypot(stars[:, 0][:, None] - stars[:, 0][None], stars[:, 1][:, None] - stars[:, 1][None])
np.fill_diagonal(d, 99)
stars = stars[d.min(1) > 8]
print("reference stars", len(stars))
sra, sdec = ref["wcs"].all_pix2world(stars[:, 0], stars[:, 1], 0)

files = sorted(D.glob("hst_*_drc.fits"))
images, meta = {}, {}
for f in files:
    tag = f.name.replace("_drc.fits", "").replace("hst_", "")
    c = L.cutout(f, RA, DEC, int(HALF * 0.04 / 0.04 * 1.3) if "acs" not in f.name else int(HALF * 0.04 / 0.05 * 1.3))
    img = c["data"]
    w = c["wcs"]
    px, py = w.all_world2pix(sra, sdec, 0)
    mx, my = np.full(len(px), np.nan), np.full(len(px), np.nan)
    for i, (x, y) in enumerate(zip(px, py)):
        if not (6 < x < img.shape[1] - 7 and 6 < y < img.shape[0] - 7):
            continue
        cx, cy = L.centroid(img, x, y, box=3)
        if not np.isfinite(cx) or np.hypot(cx - x, cy - y) > 6:
            continue
        fit = L.gauss2d_fit(img, cx, cy, box=4)
        if fit is None or not (0.4 < fit[3] < 2.5) or np.hypot(fit[0] - x, fit[1] - y) > 6:
            continue
        mx[i], my[i] = fit[0], fit[1]
    if np.isfinite(mx).sum() < 10:
        print(tag, "too few matches", np.isfinite(mx).sum())
        continue
    aff, ok, sx, sy = L.fit_affine(px, py, mx, my)
    reg = L.resample(img, w, ref["wcs"], R.shape, affine=aff)
    iv = L.resample(np.where(c["wht"] > 0, c["wht"], np.nan), w, ref["wcs"], R.shape, affine=aff, order=1)
    area = abs(np.linalg.det(ref["wcs"].pixel_scale_matrix)) / abs(np.linalg.det(w.pixel_scale_matrix))
    iv = iv / area ** 2  # inverse variance of area-scaled flux (correlated noise ignored; rescaled empirically later)
    images[tag] = reg.astype(np.float32)
    images[tag + "__ivar"] = np.nan_to_num(iv).astype(np.float32)
    shift_px = (aff[0] + aff[1] * px[ok] + aff[2] * py[ok] - px[ok]).mean(), (aff[3] + aff[4] * px[ok] + aff[5] * py[ok] - py[ok]).mean()
    meta[tag] = dict(n_match=int(np.isfinite(mx).sum()), n_used=int(ok.sum()), rms_px_src=[sx, sy],
                     rms_mas=[sx * c["pixscale"] * 1000, sy * c["pixscale"] * 1000], mean_shift_src_px=[float(shift_px[0]), float(shift_px[1])],
                     mean_shift_mas=[float(shift_px[0] * c["pixscale"] * 1000), float(shift_px[1] * c["pixscale"] * 1000)],
                     affine=[float(a) for a in aff], date=c["date"], expstart=c["expstart"], filt=c["filt"], inst=c["inst"],
                     wcsname=c["wcsname"], exptime=c["exptime"], pixscale=c["pixscale"], factor_uJy_per_eps=c["factor"])
    print(tag, meta[tag]["n_used"], np.round(meta[tag]["rms_mas"], 1), np.round(meta[tag]["mean_shift_mas"], 1), c["filt"], c["date"], flush=True)

ref_w = ref["wcs"].to_header_string()
np.savez_compressed(OUT / "registered.npz", ref_wcs=ref_w, **images)
json.dump(dict(ra=RA, dec=DEC, half=HALF, n_ref_stars=int(len(stars)), images=meta), open(HERE / "hst_register.json", "w"), indent=1)
