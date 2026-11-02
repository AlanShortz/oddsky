"""HST stamps and aperture photometry at the NGC 55 leads: WFPC2/PC 2007-08 (prog 11307: F606W, F814W) vs WFC3 2024-07
(prog 17520: UVIS F555W, F814W; IR F110W, F160W). HLA fitscut cutouts (300 px) in
~/oddsky-runs/imaging/scratch/h0012b-referee/hst_ngc55/ (fetched with curl; see the report).

    uv run python -I hunts/H-0012/reviews/h0012b-referee/hst_ngc55.py
Writes hst_ngc55.png and hst_ngc55.json next to this script.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

HERE = Path(__file__).resolve().parent
D = Path("~/oddsky-runs/imaging/scratch/h0012b-referee/hst_ngc55").expanduser()
DS = [("WFPC2 F606W 2007", "hst_11307_10_wfpc2_pc_f606w_ua3j10"), ("WFPC2 F814W 2007", "hst_11307_10_wfpc2_pc_f814w_ua3j10"),
      ("WFC3 F555W 2024", "hst_17520_14_wfc3_uvis_f555w_if9s14da"), ("WFC3 F814W 2024", "hst_17520_14_wfc3_uvis_f814w_if9s14de"),
      ("WFC3 F110W 2024", "hst_17520_14_wfc3_ir_f110w_if9s14d6"), ("WFC3 F160W 2024", "hst_17520_14_wfc3_ir_f160w_if9s14d3")]
# WISE pipeline position and the Gaia DR3 sources near each lead (from archives.json)
A = json.loads((HERE / "archives.json").read_text())
LEADS = {"fsn7": ("NGC55_fsn7", 3.80788, -39.2148), "obs184": ("NGC55_obs184", 3.79288, -39.2126),
         "obs299": ("NGC55_obs299", 3.79834, -39.2132)}
HALF = 6.0  # arcsec


def abmag(h, flux_es):
    hd = h[0].header if "PHOTFLAM" in h[0].header else h[1].header if len(h) > 1 else h[0].header
    pf, pl = hd.get("PHOTFLAM"), hd.get("PHOTPLAM")
    if not pf or not pl or flux_es <= 0:
        return None
    return float(-2.5 * np.log10(flux_es * pf) - 5 * np.log10(pl) - 2.408)


def main():
    out = {}
    fig, ax = plt.subplots(len(LEADS), len(DS), figsize=(2.6 * len(DS), 2.7 * len(LEADS)))
    for i, (key, (lab, ra, dec)) in enumerate(LEADS.items()):
        gaia = [(r["ra"], r["dec"], r["phot_g_mean_mag"]) for r in A[lab]["gaia"]["rows"]]
        out[key] = {}
        for j, (title, ds) in enumerate(DS):
            a = ax[i, j]
            a.set_xticks([]); a.set_yticks([])
            p = D / f"{key}_{ds}.fits"
            if not p.exists() or p.stat().st_size < 1000:
                a.set_title(title + " n/a", fontsize=7)
                continue
            h = fits.open(p)
            ext = 0 if h[0].data is not None else 1
            img = h[ext].data.astype(float)
            w = WCS(h[ext].header)
            scale = np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix))) * 3600
            x0, y0 = w.all_world2pix(ra, dec, 0)
            n = int(HALF / scale)
            xi, yi = int(round(float(x0))), int(round(float(y0)))
            sub = img[max(yi - n, 0):yi + n + 1, max(xi - n, 0):xi + n + 1]
            v0, v1 = np.nanpercentile(sub, [5, 99.7])
            a.imshow(np.arcsinh((sub - v0) / max(v1 - v0, 1e-6) * 10), origin="lower", cmap="gray")
            ox, oy = max(xi - n, 0), max(yi - n, 0)
            a.plot(x0 - ox, y0 - oy, "+", color="lime", ms=14, mew=1)
            # 0.5" WISE astrometric floor circle
            a.add_patch(plt.Circle((x0 - ox, y0 - oy), 1.0 / scale, fill=False, color="lime", lw=0.6))
            phot = []
            for gra, gdec, g in gaia:
                gx, gy = w.all_world2pix(gra, gdec, 0)
                a.plot(gx - ox, gy - oy, "o", mfc="none", color="orange", ms=6, mew=0.7)
                yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
                rr = np.hypot(xx - gx, yy - gy)
                rap = 0.2 / scale
                apm = rr <= rap
                sky = (rr > 0.4 / scale) & (rr < 0.8 / scale)
                if apm.sum() and sky.sum() > 10 and np.isfinite(img[apm]).all():
                    f = np.nansum(img[apm] - np.nanmedian(img[sky]))
                    phot.append(dict(gaia_G=g, sep_from_wise=float(np.hypot((gra - ra) * np.cos(np.radians(dec)), gdec - dec) * 3600),
                                     flux_r02=float(f), ab_r02_uncorrected=abmag(h, f)))
            out[key][title] = dict(scale=float(scale), units=h[ext].header.get("BUNIT", ""), gaia_phot=phot)
            a.set_title(f"{key} {title}", fontsize=7)
    fig.suptitle("NGC 55 leads in HST (12\" boxes). Green +: WISE pipeline position; circle r = 1\". "
                 "Orange: Gaia DR3 sources.", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "hst_ngc55.png", dpi=90)
    (HERE / "hst_ngc55.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        for t, d in v.items():
            ph = sorted(d["gaia_phot"], key=lambda x: x["sep_from_wise"])[:3]
            print(k, t, [(round(x["sep_from_wise"], 2), x["gaia_G"], None if x["ab_r02_uncorrected"] is None else round(x["ab_r02_uncorrected"], 2)) for x in ph])


if __name__ == "__main__":
    main()
