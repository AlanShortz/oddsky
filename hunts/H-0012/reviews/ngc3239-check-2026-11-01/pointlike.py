"""Is the 2021 HST source (in the differences) and the 2024 JWST F300M/F335M source point-like? Gaussian sigma of the
source vs the median of compact stars measured the same way (native JWST pixels; HST on the 0.04" grid)."""
import json, sys
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hst_lib as L
JD, WD = Path(sys.argv[1]), Path(sys.argv[2])
S = json.load(open(HERE / "hst_diff.json"))["source"]
out = {}
for tag, fn in {"F300M_2024-04": "jw03707-o038_t021_nircam_clear-f300m_i2d.fits", "F335M_2024-04": "jw03707-o038_t021_nircam_clear-f335m_i2d.fits",
                "F300M_2024-05": "jw03707-o138_t021_nircam_clear-f300m_i2d.fits"}.items():
    with fits.open(JD / fn, memmap=True) as h:
        w = WCS(h["SCI"].header); x, y = w.all_world2pix([[S["ra"], S["dec"]]], 0)[0]
        im = np.array(h["SCI"].data[int(y) - 400:int(y) + 400, int(x) - 400:int(x) + 400], float)
    sx, sy = x - (int(x) - 400), y - (int(y) - 400)
    f = L.gauss2d_fit(im, sx, sy, box=4)
    xs, ys, snr, _ = L.find_peaks(im, nsig=30)
    sig = []
    for a, b in zip(xs, ys):
        g = L.gauss2d_fit(im, a, b, box=4)
        if g and 0.5 < g[3] < 3 and g[2] > 0 and np.hypot(a - sx, b - sy) > 5:
            sig.append(g[3])
    out[tag] = dict(src_sigma_px=float(f[3]), stars_sigma_median=float(np.median(sig)), stars_sigma_p16_p84=[float(np.percentile(sig, 16)), float(np.percentile(sig, 84))], n=len(sig))
Z = np.load(WD / "registered.npz")
for tag in ("16179_08_wfc3_uvis_f606w_ieb308", "16179_08_wfc3_uvis_f814w_ieb308"):
    im = Z[tag].astype(float)
    f = L.gauss2d_fit(im, S["pix"][0], S["pix"][1], box=4)
    xs, ys, snr, _ = L.find_peaks(im, nsig=12)
    sig = [g[3] for a, b in zip(xs, ys) if (g := L.gauss2d_fit(im, a, b, box=4)) and 0.5 < g[3] < 3 and g[2] > 0]
    out[tag] = dict(src_sigma_px=float(f[3]), stars_sigma_median=float(np.median(sig)), stars_sigma_p16_p84=[float(np.percentile(sig, 16)), float(np.percentile(sig, 84))], n=len(sig))
print(json.dumps(out, indent=1))
json.dump(out, open(HERE / "pointlike.json", "w"), indent=1)
