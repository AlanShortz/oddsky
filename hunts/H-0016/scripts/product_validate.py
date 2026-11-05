"""H-0016 section 4c: validate the AllWISE profile-fit failure list in the images. For a random sample of tier A and tier B
sources: the absolute W1 magnitude in the unWISE 2010-11 coadd (3-px aperture, Vega nMgy) against the catalogue aperture and
profile magnitudes, and the AllWISE - Gaia DR3 offset (ESA archive). usage: product_validate.py PRODUCT_CSV OUT_CSV [n_per_tier]"""
import io
import sys
import tarfile
import time

import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.wcs import WCS

x = pd.read_csv(sys.argv[1])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
s = pd.concat([x[x.tier == t].sample(n=min(n, int((x.tier == t).sum())), random_state=16) for t in ("A", "B")]).reset_index(drop=True)


def img_mag(ra, dec):
    r = requests.get("https://unwise.me/cutout_fits", params=dict(version="allwise", ra=ra, dec=dec, size=100, bands=1), timeout=120)
    r.raise_for_status()
    best = np.nan
    with tarfile.open(fileobj=io.BytesIO(r.content)) as t:
        for m in t.getmembers():
            if not m.name.endswith("w1-img-m.fits"):
                continue
            h = fits.open(io.BytesIO(t.extractfile(m).read()))
            img, w = h[0].data, WCS(h[0].header)
            x0, y0 = w.all_world2pix(ra, dec, 0)
            if not (10 < x0 < 90 and 10 < y0 < 90):
                continue
            yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
            d = np.hypot(xx - x0, yy - y0)
            f = float(np.nansum((img - np.nanmedian(img[(d >= 6) & (d <= 10)]))[d <= 3]))
            if f > 0:
                best = 22.5 - 2.5 * np.log10(f)
    return best


rows = []
for i, r in enumerate(s.itertuples()):
    rec = dict(cntr=r.cntr, tier=r.tier, w1mpro=r.w1mpro, w1mag=r.w1mag, k=r.k_m_2mass, w1snr=r.w1snr)
    try:
        rec["img"] = img_mag(r.ra, r.dec)
    except Exception:  # noqa: BLE001
        rec["img"] = np.nan
    q = f"SELECT ra, dec, pmra, pmdec, phot_g_mean_mag FROM gaiadr3.gaia_source WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},0.00139))=1"
    try:
        t = requests.post("https://gea.esac.esa.int/tap-server/tap/sync", data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q), timeout=90).text.strip()
        g = pd.read_csv(io.StringIO(t)) if "\n" in t else pd.DataFrame()
        if len(g):
            sep = 3600 * np.hypot((g.ra - r.ra) * np.cos(np.radians(r.dec)), g.dec - r.dec)
            rec["gaia_sep"], rec["n_gaia_5as"] = float(sep.min()), int(len(g))
    except Exception:  # noqa: BLE001
        pass
    rows.append(rec)
    if i % 10 == 0:
        print(i, len(s), flush=True)
    time.sleep(0.3)
d = pd.DataFrame(rows)
d["img_minus_ap"], d["img_minus_pro"] = d.img - d.w1mag, d.img - d.w1mpro
d["img_says"] = np.select([(d.img_minus_ap.abs() < 0.3) & (d.img_minus_pro.abs() > 0.3), (d.img_minus_pro.abs() < 0.3) & (d.img_minus_ap.abs() > 0.3)], ["aperture", "profile"], "neither")
d.to_csv(sys.argv[2], index=False)
print(pd.crosstab(d.tier, d.img_says))
print(d.groupby("tier")[["gaia_sep", "n_gaia_5as", "img_minus_ap", "img_minus_pro"]].median().round(2))
print("isolated (one Gaia source within 5 arcsec):", d.groupby("tier").apply(lambda g: float((g.n_gaia_5as == 1).mean()), include_groups=False).round(2).to_dict())
