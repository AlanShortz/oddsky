"""H-0016 section 4b: the AllWISE profile-fit failure rate over the whole catalogue.
Input: the IRSA pull of every AllWISE source with |b| > 10, 8 <= W1 <= 14.5, cc_flags 0000, nb 1, ext_flg 0, |w1mag - w1mpro| > 0.4
and w1snr < 15 (IRSA async job 27125305). Steps: (1) column census of all of them (direction, magnitude, sky, epoch, 2MASS
agreement); (2) a random stratified sample through the unWISE image test (2010-only vs 2010-2020 coadds: a real 2010 change
gives R != 1, a catalogue error R = 1) and a Gaia DR3 cross-match for the AllWISE - Gaia offset.
usage: catalog_rate.py LIST_CSV OUT_PREFIX [n_sample]"""
import io
import sys
import tarfile
import time

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
out = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 300
x["ap_pro"] = x.w1mag - x.w1mpro
x["kw1_pro"] = x.k_m_2mass - x.w1mpro
x["kw1_ap"] = x.k_m_2mass - x.w1mag
print(len(x), "sources; profile brighter than aperture:", int((x.ap_pro > 0).sum()), "fainter:", int((x.ap_pro < 0).sum()))
print("W1 bins:", pd.cut(x.w1mpro, [8, 10, 11, 12, 13, 14, 14.5]).value_counts().sort_index().to_dict())
print("|ap-pro| quantiles:", x.ap_pro.abs().quantile([.1, .5, .9]).round(2).to_dict())
print("2MASS K present:", int(x.k_m_2mass.notna().sum()), "; of those, |K - w1mag| < 0.5:", int((x.kw1_ap.abs() < 0.5).sum()),
      "; |K - w1mpro| < 0.5:", int((x.kw1_pro.abs() < 0.5).sum()))
print("sigra quantiles:", x.sigra.quantile([.1, .5, .9]).round(2).to_dict(), "; |pm| median:", float(np.hypot(x.pmra, x.pmdec).median()))
print("w1nm/w1m median:", float((x.w1nm / x.w1m).median()), "; w1rchi2 median:", float(x.w1rchi2.median()))
print("glat bins:", pd.cut(x.glat.abs(), [10, 20, 30, 45, 60, 90]).value_counts().sort_index().to_dict())
rng = np.random.default_rng(16)
s = x.sample(n=min(n, len(x)), random_state=16).reset_index(drop=True)
rows = []
for i, r in s.iterrows():
    rec = dict(cntr=r.cntr, designation=r.designation, ra=r.ra, dec=r.dec, w1mpro=r.w1mpro, w1mag=r.w1mag, w1snr=r.w1snr, ap_pro=r.ap_pro, k=r.k_m_2mass, glat=r.glat, pm_aw=float(np.hypot(r.pmra, r.pmdec)))
    for band in (1, 2):
        f = {}
        for ver in ("allwise", "neo7"):
            try:
                imgs = cutout(ver, r.ra, r.dec, band)
                vals = [ap_flux(im, w, r.ra, r.dec) for im, w in imgs]
                vals = [v for v in vals if 10 < v[1] < 90 and 10 < v[2] < 90] or vals
                f[ver] = max(v[0] for v in vals)
            except Exception:  # noqa: BLE001
                f[ver] = np.nan
        rec[f"w{band}_R"] = f["allwise"] / f["neo7"] if f.get("neo7") else np.nan
        rec[f"w{band}_mag_2010img"] = 22.5 - 2.5 * np.log10(f["allwise"]) if f.get("allwise") and f["allwise"] > 0 else np.nan  # unWISE Vega nMgy
    a = 10 ** (0.4 * (r.w1mag - r.w1mpro))  # if the PROFILE value were right, the 2010 image would differ from later by this
    rec["R_if_profile_right"] = 7 * (1 / a) / (1 / a + 6)
    try:
        g = pd.read_csv(io.StringIO(requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY":
            f"SELECT ra,dec,pmra,pmdec,phot_g_mean_mag,parallax_over_error FROM gaia_dr3_source WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},0.0017))=1",
            "FORMAT": "csv"}, timeout=120).text))
        if len(g):
            sep = 3600 * np.hypot((g.ra - r.ra) * np.cos(np.radians(r.dec)), g.dec - r.dec)
            j = int(np.argmin(sep))
            rec["gaia_sep"] = float(sep[j])
            rec["gaia_G"] = float(g.phot_g_mean_mag[j])
            rec["n_gaia_6as"] = int(len(g))
            rec["gaia_pm"] = float(np.hypot(g.pmra[j], g.pmdec[j]))
    except Exception:  # noqa: BLE001
        pass
    rows.append(rec)
    if i % 20 == 0:
        print(i, n, flush=True)
    time.sleep(0.3)
d = pd.DataFrame(rows)
d.to_csv(f"{out}_sample.csv", index=False)
d["R"] = d[["w1_R", "w2_R"]].mean(axis=1)
d["verdict"] = np.select([(d.R - 1).abs() < 0.08, ((d.R - d.R_if_profile_right).abs() < 0.3 * (d.R_if_profile_right - 1).abs())],
                         ["catalogue artifact (image = aperture)", "real 2010 change (image = profile)"], "other")
print(d.verdict.value_counts().to_dict())
print(d.groupby("verdict")[["gaia_sep", "w1snr", "ap_pro"]].median())
