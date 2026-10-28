"""Hunt H-0005: Gaia20cdd in TESS full-frame cutouts. Daily-binned flux in three pixels: the target's, the one on the far
side of it from the G 13.58 neighbour (Gaia DR3 1624712052777229824, 16" away; most target light, least neighbour
light), and the neighbour's. A dip on the target shows in the first two and not the third."""
import io
import warnings

import astropy.units as u
import lightkurve as lk
import numpy as np
import pandas as pd
import requests
from astropy.coordinates import SkyCoord

warnings.simplefilter("ignore")
TARGET = SkyCoord(245.22399 * u.deg, 59.43955 * u.deg)
q = "SELECT ra, dec FROM gaiadr3.gaia_source WHERE source_id=1624712052777229824"
n = pd.read_csv(io.StringIO(requests.post("https://gea.esac.esa.int/tap-server/tap/sync", timeout=120,
                                          data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": q}).text))
NEIGHBOUR = SkyCoord(n.ra[0] * u.deg, n.dec[0] * u.deg)

for sector in (16, 23, 24, 25, 51, 52, 55):
    tpf = lk.search_tesscut(f"{TARGET.ra.deg} {TARGET.dec.deg}", sector=sector)[0].download(
        cutout_size=15, download_dir="/tmp/oddsky_tesscut")
    ok = np.isfinite(tpf.flux.value).all(axis=(1, 2)) & (tpf.quality == 0)
    f, t = tpf.flux.value[ok], tpf.time.value[ok]
    sky = np.percentile(f.reshape(len(f), -1), 20, axis=1)
    tx, ty = (int(round(float(v))) for v in tpf.wcs.world_to_pixel(TARGET))
    nx, ny = (int(round(float(v))) for v in tpf.wcs.world_to_pixel(NEIGHBOUR))
    fx, fy = tx + int(np.sign(tx - nx)), ty + int(np.sign(ty - ny))
    pixels = {"target": (ty, tx), "far": (fy, fx), "nbr": (ny, nx)}
    lc = {k: f[:, row, col] - sky for k, (row, col) in pixels.items()}
    day = np.floor(t)
    out = []
    for d in np.unique(day):
        m = day == d
        if m.sum() >= 10:
            out.append((d, *(np.median(lc[k][m]) for k in pixels)))
    o = np.array(out)
    o[:, 1:] /= np.median(o[:, 1:], axis=0)
    print(f"S{sector}: target px ({tx},{ty}); neighbour px ({nx},{ny}); far px ({fx},{fy})  [BTJD day: target/far/nbr]")
    print(" ".join(f"{int(r[0])}:{r[1]:.3f}/{r[2]:.3f}/{r[3]:.3f}" for r in o))
