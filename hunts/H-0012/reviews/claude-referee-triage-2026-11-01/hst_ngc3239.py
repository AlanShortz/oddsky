"""HST at the NGC 3239 mid-IR transient (156.2910 +17.1639; WISE peak 2020-11-21): WFC3/UVIS F606W on 2021-02-15
(85 d after the WISE peak, W1 excess ~170 uJy) vs ACS/WFC F606W on 2022-12-11 (WISE back near baseline), on the
same HAP skycell grid (0.04"/px). Input: HAP MVM cutouts downloaded with astroquery.mast.Hapcut into a directory
given as argv[1]. Output: hst_ngc3239.png and hst_ngc3239.json (aperture photometry of the difference).

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/hst_ngc3239.py /tmp/h0012_ref_hst
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
from scipy import ndimage

HERE = Path(__file__).resolve().parent
D = Path(sys.argv[1])
RA, DEC = 156.2910, 17.1639


def load(tag):
    f = D / f"hst_combined_skycells-ra156d291-decn17d1639_{tag}.fits"
    h = fits.open(f)
    ext = 1 if len(h) > 1 and h[1].data is not None else 0
    img, hdr = h[ext].data.astype(float), h[ext].header
    return img, WCS(hdr), hdr


panels = {}
for tag in ("wfc3_uvis_f606w", "acs_wfc_f606w", "wfc3_uvis_f814w", "wfc3_uvis_f555w", "wfc3_uvis_f657n", "wfc3_uvis_f336w"):
    try:
        panels[tag] = load(tag)
    except Exception as e:  # noqa: BLE001
        print(tag, "ERR", e)
a, wa, ha = panels["wfc3_uvis_f606w"]
b, wb, hb = panels["acs_wfc_f606w"]
x, y = wa.all_world2pix([[RA, DEC]], 0)[0]
xb, yb = wb.all_world2pix([[RA, DEC]], 0)[0]
print("pix", x, y, xb, yb, a.shape, b.shape, "PHOTFLAM", ha.get("PHOTFLAM"), hb.get("PHOTFLAM"))
# both are in electrons/s on the skycell grid; put on the same flux scale with PHOTFLAM, match PSFs roughly
fa, fb = ha.get("PHOTFLAM", 1.0), hb.get("PHOTFLAM", 1.0)
A = np.nan_to_num(a) * fa
B = np.nan_to_num(b) * fb
if A.shape == B.shape:
    # scale B to A on the galaxy background within 3" (absorbs throughput differences between the two F606W filters)
    yy, xx = np.mgrid[: A.shape[0], : A.shape[1]]
    r = np.hypot(xx - x, yy - y) * 0.04
    ring = (r > 1.0) & (r < 3.0)
    k = np.median(A[ring]) / np.median(B[ring]) if np.median(B[ring]) != 0 else 1.0
    Dm = ndimage.gaussian_filter(A, 1.0) - k * ndimage.gaussian_filter(B, 1.0)
    ap = r < 0.15
    bg = (r > 0.4) & (r < 0.8)
    net = float(np.sum(Dm[ap] - np.median(Dm[bg])))
    noise = float(np.std(Dm[bg]) * np.sqrt(ap.sum()))
    zp = -2.5 * np.log10(fa) - 21.10 - 5 * np.log10(ha.get("PHOTPLAM", 5900)) + 18.692  # AB from PHOTFLAM/PHOTPLAM
    res = dict(scale_B_to_A=float(k), net_flux_flam=net / fa, net_snr=net / noise if noise else None,
               note="aperture r=0.15\", difference WFC3 F606W (2021-02-15) minus scaled ACS F606W (2022-12-11)")
    if net > 0:
        res["mag_AB_approx"] = float(-2.5 * np.log10(net / fa) + zp)
    lim = 5 * noise / fa
    res["mag_AB_5sigma_limit"] = float(-2.5 * np.log10(lim) + zp) if lim > 0 else None
else:
    Dm, res = None, dict(error=f"shape mismatch {A.shape} {B.shape}")
print(res)
fig, ax = plt.subplots(1, len(panels) + 1, figsize=(3.2 * (len(panels) + 1), 3.4))
for i, (tag, (im, w, h)) in enumerate(panels.items()):
    xi, yi = w.all_world2pix([[RA, DEC]], 0)[0]
    s = 60
    cut = im[int(yi) - s:int(yi) + s, int(xi) - s:int(xi) + s]
    v0, v1 = np.nanpercentile(cut, [2, 99.5])
    ax[i].imshow(np.arcsinh((cut - v0) / max(v1 - v0, 1e-9) * 10), origin="lower", cmap="gray")
    ax[i].plot(s, s, "o", mfc="none", mec="lime", ms=18)
    ax[i].set_title(f"{tag} MJD {h.get('EXPSTART', float('nan')):.0f}", fontsize=7)
if Dm is not None:
    s = 60
    cut = Dm[int(y) - s:int(y) + s, int(x) - s:int(x) + s]
    v = np.nanpercentile(np.abs(cut), 99)
    ax[-1].imshow(cut, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
    ax[-1].plot(s, s, "o", mfc="none", mec="k", ms=18)
    ax[-1].set_title("F606W 2021 - k x F606W 2022", fontsize=7)
for a_ in ax:
    a_.set_xticks([]); a_.set_yticks([])
fig.suptitle("NGC 3239 mid-IR transient, HST, 4.8\" boxes (circle r=0.36\")", fontsize=8)
fig.tight_layout()
fig.savefig(HERE / "hst_ngc3239.png", dpi=90)
(HERE / "hst_ngc3239.json").write_text(json.dumps(res, indent=1))

# Search the whole 1.2" radius (WISE astrometric uncertainty) for any positive residual, against the
# distribution of the same aperture sums over the rest of the cutout (unsmoothed difference, r = 0.12" apertures).
if Dm is not None:
    raw = A - k * B
    ker = np.zeros((7, 7)); yy7, xx7 = np.mgrid[-3:4, -3:4]; ker[np.hypot(xx7, yy7) <= 3] = 1
    apsum = ndimage.convolve(raw, ker, mode="nearest")
    yy, xx = np.mgrid[: raw.shape[0], : raw.shape[1]]
    rr = np.hypot(xx - x, yy - y) * 0.04
    ctrl = apsum[(rr > 2.0) & (rr < 3.8)]
    sig = 1.4826 * np.median(np.abs(ctrl - np.median(ctrl)))
    inner = apsum[rr <= 1.2]
    zp = -2.5 * np.log10(fa) - 21.10 - 5 * np.log10(ha.get("PHOTPLAM", 5887)) + 18.6921
    res2 = dict(max_snr_within_1p2=float((inner.max() - np.median(ctrl)) / sig),
                frac_control_apertures_above_that=float(np.mean(ctrl - np.median(ctrl) > inner.max() - np.median(ctrl))),
                five_sigma_mag_AB_r012=float(-2.5 * np.log10(5 * sig / fa / 0.75) + zp))  # ~75% of a point source in r=0.12"
    print(res2)
    res.update(res2)
    (HERE / "hst_ngc3239.json").write_text(json.dumps(res, indent=1))
