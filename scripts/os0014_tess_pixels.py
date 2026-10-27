"""OS-0014: is the ~1.8-day TESS signal on the star? Per-pixel Lomb-Scargle power (1.70-1.95 d) in TESScut
full-frame cutouts, after a 5-day running-median detrend (keeps a 1.8-d signal, removes scattered light)."""
import warnings

import astropy.units as u
import lightkurve as lk
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.timeseries import LombScargle
from scipy.ndimage import median_filter

warnings.simplefilter("ignore")
RA, DEC = 278.27585, -36.12034
res = lk.search_tesscut(f"{RA} {DEC}")
for i in range(len(res)):
    tpf = res[i].download(cutout_size=11, download_dir="/tmp/oddsky_tesscut")
    ok = np.isfinite(tpf.flux.value).all(axis=(1, 2)) & (tpf.quality == 0)
    flux, t = tpf.flux.value[ok], tpf.time.value[ok]
    w = int(max(3, 5.0 / np.median(np.diff(t)))) | 1
    detr = flux - median_filter(flux, size=(w, 1, 1), mode="nearest")
    freq = np.linspace(1 / 5, 1 / 0.5, 3000)
    band = (1 / freq > 1.70) & (1 / freq < 1.95)
    pmap = np.array([[LombScargle(t, detr[:, y, x]).power(freq)[band].max() for x in range(flux.shape[2])]
                     for y in range(flux.shape[1])])
    amap = detr.std(axis=0)
    col, row = tpf.wcs.world_to_pixel(SkyCoord(RA * u.deg, DEC * u.deg))
    yb, xb = np.unravel_index(np.argmax(pmap * amap), pmap.shape)
    on = pmap[int(round(float(row))), int(round(float(col)))]
    print(f"sector {tpf.sector}: strongest signal at ({xb},{yb}), target at ({float(col):.1f},{float(row):.1f}), "
          f"offset {np.hypot(xb - float(col), yb - float(row)):.1f} px; power on target {on:.2f}, max {pmap.max():.2f}")
