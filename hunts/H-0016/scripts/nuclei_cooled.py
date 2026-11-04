"""H-0016 section 5.5 pre-pilot: galaxy nuclei that lost a hot-dust component across the gap. Input: BigQuery pull of sky2 sources
with AllWISE W1-W2 >= 0.4 in 2010-11, both bands fainter by > 0.3/0.5 mag in 2014-15, colour bluer by >= 0.25, quiet after
(nuclei_cooled_raw.csv) joined to AllWISE rows (positions). Steps: Gaia DR3 via ESA (galaxy/quasar probabilities, parallax),
the unWISE image test, and a table ranked by colour change. usage: nuclei_cooled.py RAW_CSV ALLWISE_CSV OUT_CSV"""
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
x["ap_pro"] = x.w1mag - x.w1mpro
x = x[(x.ap_pro.abs() < 0.3) & (x.nb.fillna(1) == 1)].copy()
print(len(x), "candidates with aperture = profile and nb = 1")
rows = []
for i, r in enumerate(x.itertuples()):
    rec = dict(cntr=r.cntr)
    q = (f"SELECT source_id, phot_g_mean_mag, bp_rp, parallax_over_error, classprob_dsc_combmod_galaxy, classprob_dsc_combmod_quasar, in_galaxy_candidates, in_qso_candidates "
         f"FROM gaiadr3.gaia_source WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},0.000833))=1")
    for k in range(3):
        try:
            t = requests.post("https://gea.esac.esa.int/tap-server/tap/sync", data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q), timeout=90).text.strip()
            g = pd.read_csv(io.StringIO(t)) if "\n" in t else pd.DataFrame()
            if len(g):
                g = g.sort_values("phot_g_mean_mag").iloc[0]
                rec.update(g_id=str(int(g.source_id)), G=float(g.phot_g_mean_mag), bp_rp=float(g.bp_rp) if pd.notna(g.bp_rp) else np.nan, poe=float(g.parallax_over_error) if pd.notna(g.parallax_over_error) else np.nan,
                           p_gal=float(g.classprob_dsc_combmod_galaxy) if pd.notna(g.classprob_dsc_combmod_galaxy) else np.nan, p_qso=float(g.classprob_dsc_combmod_quasar) if pd.notna(g.classprob_dsc_combmod_quasar) else np.nan,
                           gal_cand=bool(g.in_galaxy_candidates), qso_cand=bool(g.in_qso_candidates))
            break
        except Exception:  # noqa: BLE001
            time.sleep(10 * (k + 1))
    rows.append(rec)
    time.sleep(0.3)
    if i % 25 == 0:
        print("gaia", i, len(x), flush=True)
x = x.merge(pd.DataFrame(rows), on="cntr", how="left")

def cutout(version, ra, dec, band, size=100):
    r = requests.get("https://unwise.me/cutout_fits", params=dict(version=version, ra=ra, dec=dec, size=size, bands=band), timeout=120)
    r.raise_for_status()
    with tarfile.open(fileobj=io.BytesIO(r.content)) as t:
        return [(fits.open(io.BytesIO(t.extractfile(m).read()))[0].data, WCS(fits.open(io.BytesIO(t.extractfile(m).read()))[0].header)) for m in t.getmembers() if m.name.endswith(f"w{band}-img-m.fits")]

def ap_flux(img, wcs, ra, dec, r_ap=3.0, r_in=6, r_out=10):
    x0, y0 = wcs.all_world2pix(ra, dec, 0)
    yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
    d = np.hypot(xx - x0, yy - y0)
    sky = np.nanmedian(img[(d >= r_in) & (d <= r_out)])
    return float(np.nansum((img - sky)[d <= r_ap])), float(x0), float(y0)

res = []
for r in x.itertuples():
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
        a = 10 ** (0.4 * (r.d1 if band == 1 else r.d2))
        rec[f"w{band}_R_pred"] = 7 * a / (a + 6)
    res.append(rec)
    print(r.designation, rec, flush=True)
x = x.merge(pd.DataFrame(res), on="cntr", how="left")
x["img_frac"] = (np.log(x.w1_R) / np.log(x.w1_R_pred) + np.log(x.w2_R) / np.log(x.w2_R_pred)) / 2
x["verdict"] = np.select([x.img_frac > 0.6, x.img_frac < 0.3], ["REAL", "artifact"], "partial")
x.sort_values("dcolor", ascending=False).to_csv(out, index=False)
print(x.verdict.value_counts().to_dict())
print(x[x.verdict == "REAL"][["designation", "d1", "d2", "dcolor", "w1mpro_allwise", "G", "p_gal", "p_qso", "poe"]].head(30).to_string())
