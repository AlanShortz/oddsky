"""H-0016: independent image-level test of a 2010-vs-NEOWISE step. unwise.me serves coadds of the 2010-11 frames only
(version=allwise) and cumulative 2010-2020 coadds (version=neo7). Aperture flux of the star in both (same calibration, Vega
nanomaggies), ratio R = F_allwise / F_neo7. With a = F_2010/F_NEOWISE from the catalogues, a real step predicts R ~ 7a/(a+6) (frames weighted ~1:6); a catalogue artifact predicts R ~ 1. Reference stars in the same cutout are measured the same way.
usage: unwise_check.py IN_CSV OUT_CSV"""
import io
import sys
import tarfile

import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.wcs import WCS


def cutout(version, ra, dec, band, size=100):
    r = requests.get("https://unwise.me/cutout_fits", params=dict(version=version, ra=ra, dec=dec, size=size, bands=band), timeout=120)
    r.raise_for_status()
    with tarfile.open(fileobj=io.BytesIO(r.content)) as t:
        imgs = []
        for m in t.getmembers():
            if m.name.endswith(f"w{band}-img-m.fits"):
                h = fits.open(io.BytesIO(t.extractfile(m).read()))
                imgs.append((h[0].data, WCS(h[0].header)))
        return imgs

def ap_flux(img, wcs, ra, dec, r_ap=3.0, r_in=6, r_out=10):
    x, y = wcs.all_world2pix(ra, dec, 0)
    yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
    d = np.hypot(xx - x, yy - y)
    sky = np.nanmedian(img[(d >= r_in) & (d <= r_out)])
    return float(np.nansum((img - sky)[d <= r_ap])), float(x), float(y)

x = pd.read_csv(sys.argv[1])
rows = []
for s in x.itertuples():
    rec = dict(cntr=s.cntr, designation=s.designation)
    for band in (1, 2):
        f = {}
        for ver in ("allwise", "neo7"):
            try:
                imgs = cutout(ver, s.ra, s.dec, band)
                vals = [ap_flux(im, w, s.ra, s.dec) for im, w in imgs]
                # keep the cutout where the star is best inside the image
                vals = [v for v in vals if 10 < v[1] < 90 and 10 < v[2] < 90] or vals
                f[ver] = max(v[0] for v in vals)
            except Exception as e:  # noqa: BLE001
                f[ver] = np.nan
                rec[f"w{band}_err"] = str(e)[:60]
        rec[f"w{band}_F_allwise"], rec[f"w{band}_F_neo7"] = f["allwise"], f["neo7"]
        rec[f"w{band}_R"] = f["allwise"] / f["neo7"] if f["neo7"] else np.nan
        rec[f"w{band}_dmag_img"] = -2.5 * np.log10(rec[f"w{band}_R"]) if rec[f"w{band}_R"] and rec[f"w{band}_R"] > 0 else np.nan
    a = 10 ** (0.4 * s.d1)  # AllWISE/NEOWISE flux ratio from the catalogues (d1 = w1_base - w1mpro_allwise)
    rec["R_pred_real"] = 7 * a / (a + 6)  # frames weighted ~1 (2010-11) : 6 (2014-2020)
    rows.append(rec)
    print(s.designation, f"d1={s.d1:+.2f}  W1 R={rec['w1_R']:.2f} W2 R={rec['w2_R']:.2f}  pred_if_real={rec['R_pred_real']:.2f}", flush=True)
pd.DataFrame(rows).to_csv(sys.argv[2], index=False)
