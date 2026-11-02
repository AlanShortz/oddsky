"""Locate and inspect the positive F606W(2021-02-15) - F606W(2022-12-11) residual within 1.2" of the NGC 3239
mid-IR transient; also measure it in the 2025-01 F555W and the (2021+2025) F814W skycell images.

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/hst_ngc3239_peak.py /tmp/h0012_ref_hst
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
    h = fits.open(D / f"hst_combined_skycells-ra156d291-decn17d1639_{tag}.fits")
    ext = 1 if len(h) > 1 and h[1].data is not None else 0
    return np.nan_to_num(h[ext].data.astype(float)), WCS(h[ext].header), h[ext].header


A, w, ha = load("wfc3_uvis_f606w")
B, _, _ = load("acs_wfc_f606w")
x, y = w.all_world2pix([[RA, DEC]], 0)[0]
yy, xx = np.mgrid[: A.shape[0], : A.shape[1]]
rr = np.hypot(xx - x, yy - y) * 0.04
ring = (rr > 1) & (rr < 3)
k = np.median(A[ring]) / np.median(B[ring])
raw = A - k * B
ker = (np.hypot(*np.mgrid[-3:4, -3:4]) <= 3).astype(float)
aps = ndimage.convolve(raw, ker, mode="nearest")
inner = rr <= 1.2
iy, ix = np.unravel_index(np.argmax(np.where(inner, aps, -np.inf)), aps.shape)
pra, pdec = w.all_pix2world([[ix, iy]], 0)[0]
sep = float(np.hypot((pra - RA) * np.cos(np.radians(DEC)), pdec - DEC) * 3600)
fa = ha["PHOTFLAM"]; pl = ha.get("PHOTPLAM", 5887)
zp = -2.5 * np.log10(fa) - 21.10 - 5 * np.log10(pl) + 18.6921


def apmag(img, f, plam, x0, y0, r=3, rin=8, rout=14):
    yy_, xx_ = np.mgrid[: img.shape[0], : img.shape[1]]
    d = np.hypot(xx_ - x0, yy_ - y0)
    net = img[d <= r].sum() - np.median(img[(d > rin) & (d < rout)]) * (d <= r).sum()
    z = -2.5 * np.log10(f) - 21.10 - 5 * np.log10(plam) + 18.6921
    return float(-2.5 * np.log10(net / 0.75) + z) if net > 0 else None, float(net)


res = dict(peak_pix=[int(ix), int(iy)], peak_radec=[float(pra), float(pdec)], sep_from_wise_arcsec=sep,
           diff_mag_AB=apmag(raw, fa, pl, ix, iy)[0], f606w_2021_mag_AB=apmag(A, fa, pl, ix, iy)[0])
for tag in ("acs_wfc_f606w", "wfc3_uvis_f555w", "wfc3_uvis_f814w"):
    im, ww, hh = load(tag)
    f = hh.get("PHOTFLAM")
    res[f"{tag}_mag_AB"] = apmag(im, f, hh.get("PHOTPLAM", 5887), ix, iy)[0] if f else apmag(im * k * fa, fa, pl, ix, iy)[0]
print(res)
fig, ax = plt.subplots(1, 5, figsize=(16, 3.4))
s = 30
for a_, (im, t) in zip(ax, [(A, "WFC3 F606W 2021-02-15"), (k * B, "ACS F606W 2022-12-11 (scaled)"), (raw, "difference"),
                            (load("wfc3_uvis_f555w")[0], "WFC3 F555W 2025-01-07"), (load("wfc3_uvis_f814w")[0], "F814W 2021+2025")]):
    cut = im[iy - s:iy + s, ix - s:ix + s]
    if t == "difference":
        v = np.percentile(np.abs(cut), 99.5); a_.imshow(cut, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
    else:
        v0, v1 = np.percentile(cut, [2, 99.7]); a_.imshow(cut, origin="lower", cmap="gray", vmin=v0, vmax=v1)
    a_.plot(x - ix + s, y - iy + s, "+", color="lime", ms=14)
    a_.plot(s, s, "o", mfc="none", mec="orange", ms=14)
    a_.set_title(t, fontsize=7); a_.set_xticks([]); a_.set_yticks([])
fig.suptitle(f"2.4\" boxes centred on the residual peak (orange); WISE position (green +), sep {sep:.2f}\"", fontsize=8)
fig.tight_layout(); fig.savefig(HERE / "hst_ngc3239_peak.png", dpi=90)
(HERE / "hst_ngc3239_peak.json").write_text(json.dumps(res, indent=1))
