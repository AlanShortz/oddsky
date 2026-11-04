"""H-0016 section 5.4: a sweep for more B stars whose 2010-11 excess vanished. Input: every sky2 source that is fainter now by > 0.4 mag
in both bands with NEOWISE ptp < 1.5 (BigQuery pull be_sweep_raw.csv) joined to its AllWISE row. Steps: flags (steps_triage logic),
Gaia DR3 via IRSA (one cone each) for the unflagged, keep Teff_gspphot > 9,000 K or BP-RP < 0.3, then the unWISE image test.
usage: be_sweep.py RAW_CSV ALLWISE_CSV OUT_PREFIX"""
import io
import sys
import tarfile
import time

import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.wcs import WCS

raw, aw, out = pd.read_csv(sys.argv[1]), pd.read_csv(sys.argv[2]), sys.argv[3]
x = raw.merge(aw, left_on="allwise_cntr", right_on="cntr", how="inner")
cc = x.cc_flags.fillna("0000").astype(str).str.zfill(4)
x["nflags"] = ((cc.str[0] != "0") | (cc.str[1] != "0")).astype(int) + (x.nb.fillna(1) > 1).astype(int) + (x.ext_flg.fillna(0) > 0).astype(int) + ((x.w1sat.fillna(0) > 0) | (x.w2sat.fillna(0) > 0)).astype(int) + (x.w1rchi2.fillna(1) > 3).astype(int) + ((x.w1nm / x.w1m.replace(0, np.nan)).fillna(1) < 0.7).astype(int)
x["ap_pro"] = x.w1mag - x.w1mpro
c = x[(x.nflags == 0) & (x.ap_pro.abs() < 0.3)].copy()   # the aperture/profile test removes the catalogue failures up front
print(len(x), "candidates;", len(c), "unflagged with aperture = profile")
GC = "source_id, ra, dec, phot_g_mean_mag, bp_rp, parallax, parallax_over_error, teff_gspphot, pmra, pmdec"
rows = []
for i, r in enumerate(c.itertuples()):
    rec = dict(cntr=r.cntr)
    for k in range(4):
        try:
            t = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": f"SELECT {GC} FROM gaia_dr3_source WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},0.000833))=1", "FORMAT": "csv"}, timeout=120).text.strip()
            g = pd.read_csv(io.StringIO(t)) if "\n" in t else pd.DataFrame()
            if len(g):
                g = g.sort_values("phot_g_mean_mag").iloc[0]
                rec.update(g_id=str(int(g.source_id)), G=float(g.phot_g_mean_mag), bp_rp=float(g.bp_rp), plx=float(g.parallax), poe=float(g.parallax_over_error), teff=float(g.teff_gspphot) if pd.notna(g.teff_gspphot) else np.nan)
            break
        except Exception:  # noqa: BLE001
            time.sleep(10 * (k + 1))
    rows.append(rec)
    if i % 50 == 0:
        print("gaia", i, len(c), flush=True)
    time.sleep(0.4)
c = c.merge(pd.DataFrame(rows), on="cntr", how="left")
c.to_csv(f"{out}_gaia.csv", index=False)
hot = c[(c.teff > 9000) | (c.bp_rp < 0.3)].copy()
print("hot (Teff > 9000 K or BP-RP < 0.3):", len(hot))

def cutout(version, ra, dec, band, size=100):
    r = requests.get("https://unwise.me/cutout_fits", params=dict(version=version, ra=ra, dec=dec, size=size, bands=band), timeout=120)
    r.raise_for_status()
    with tarfile.open(fileobj=io.BytesIO(r.content)) as t:
        return [(fits.open(io.BytesIO(t.extractfile(m).read()))[0].data, WCS(fits.open(io.BytesIO(t.extractfile(m).read()))[0].header)) for m in t.getmembers() if m.name.endswith(f"w{band}-img-m.fits")]

def ap_flux(img, wcs, ra, dec, r_ap=3.0, r_in=6, r_out=10):
    xx0, yy0 = wcs.all_world2pix(ra, dec, 0)
    yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
    d = np.hypot(xx - xx0, yy - yy0)
    sky = np.nanmedian(img[(d >= r_in) & (d <= r_out)])
    return float(np.nansum((img - sky)[d <= r_ap])), float(xx0), float(yy0)

res = []
for r in hot.itertuples():
    rec = dict(cntr=r.cntr)
    for band in (1, 2):
        f = {}
        for ver in ("allwise", "neo7"):
            try:
                vals = [ap_flux(im, w, r.ra, r.dec) for im, w in cutout(ver, r.ra, r.dec, band)]
                vals = [v for v in vals if 10 < v[1] < 90 and 10 < v[2] < 90] or vals
                f[ver] = max(v[0] for v in vals)
            except Exception:  # noqa: BLE001
                f[ver] = np.nan
        rec[f"w{band}_R"] = f["allwise"] / f["neo7"] if f.get("neo7") else np.nan
    a = 10 ** (0.4 * r.d1)
    rec["R_pred"] = 7 * a / (a + 6)
    res.append(rec)
    print(r.designation, rec, flush=True)
hot = hot.merge(pd.DataFrame(res), on="cntr", how="left")
hot["img_frac"] = np.log(hot[["w1_R", "w2_R"]].mean(axis=1)) / np.log(hot.R_pred)
hot["verdict"] = np.select([hot.img_frac > 0.6, hot.img_frac < 0.3], ["REAL", "artifact"], "partial")
hot.to_csv(f"{out}_hot.csv", index=False)
print(hot.verdict.value_counts().to_dict())
