"""HST at NGC 2403 obs#50 (114.228 +65.598): stamps (8" boxes) from HLA fitscut cutouts in
~/oddsky-runs/imaging/scratch/h0012b-referee/hst_ngc2403/, and r = 0.12" aperture photometry of the near-IR-brightest
sources within 1.5" of the WISE position in every F814W epoch (2004, 2005, 2018, 2019), to look for a variable red star.

    uv run python -I hunts/H-0012/reviews/h0012b-referee/hst_ngc2403.py
Writes hst_ngc2403.png and hst_ngc2403.json next to this script.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy import ndimage

HERE = Path(__file__).resolve().parent
D = Path("~/oddsky-runs/imaging/scratch/h0012b-referee/hst_ngc2403").expanduser()
RA, DEC = 114.228, 65.598
DS = [("ACS F606W 2004.6", "hst_10182_x1_acs_wfc_f606w_j90zx1"), ("ACS F814W 2004.6", "hst_10182_x1_acs_wfc_f814w_j90zx1"),
      ("ACS F814W 2005.2", "hst_10402_25_acs_wfc_f814w_j96r25"), ("WFC3/IR F160W 2010.3", "hst_11719_34_wfc3_ir_f160w_ib2x34"),
      ("WFC3 F555W 2018.4", "hst_15166_51_wfc3_uvis_f555w_idi151"), ("WFC3 F814W 2018.4", "hst_15166_51_wfc3_uvis_f814w_idi151"),
      ("ACS F814W 2019.3", "hst_15645_27_acs_wfc_f814w_jdxk27")]
HALF = 4.0


def load(ds):
    h = fits.open(D / f"{ds}.fits")
    ext = 0 if h[0].data is not None else 1
    img = h[ext].data.astype(float)
    w = WCS(h[ext].header)
    hd = h[ext].header if "PHOTFLAM" in h[ext].header else h[0].header
    return img, w, hd


def ab(hd, f):
    pf, pl = hd.get("PHOTFLAM"), hd.get("PHOTPLAM")
    return float(-2.5 * np.log10(f * pf) - 5 * np.log10(pl) - 2.408) if (pf and pl and f > 0) else None


def aperture(img, w, ra, dec, r_as):
    x, y = w.all_world2pix(ra, dec, 0)
    sc = np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix))) * 3600
    yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
    rr = np.hypot(xx - x, yy - y)
    ap = rr <= r_as / sc
    sk = (rr > 0.25 / sc) & (rr < 0.5 / sc)
    return float(np.nansum(img[ap] - np.nanmedian(img[sk])))


def main():
    # near-IR-bright sources within 1.5" (F160W 2010)
    img, w, hd = load("hst_11719_34_wfc3_ir_f160w_ib2x34")
    sc = np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix))) * 3600
    x0, y0 = w.all_world2pix(RA, DEC, 0)
    sm = ndimage.gaussian_filter(np.nan_to_num(img), 1)
    pk = np.argwhere((sm == ndimage.maximum_filter(sm, 5)) & (sm > np.nanpercentile(sm, 90)))
    cand = []
    for (py, px) in pk:
        if np.hypot(px - x0, py - y0) * sc < 1.5:
            ra, dec = w.all_pix2world(px, py, 0)
            cand.append((float(ra), float(dec), float(sm[py, px])))
    cand = sorted(cand, key=lambda c: -c[2])[:6]
    out = dict(sources=[])
    for ra, dec, _ in cand:
        row = dict(ra=ra, dec=dec, sep=float(np.hypot((ra - RA) * np.cos(np.radians(DEC)), dec - DEC) * 3600))
        for title, ds in DS:
            im, ww, h2 = load(ds)
            row[title] = ab(h2, aperture(im, ww, ra, dec, 0.12))
        out["sources"].append(row)
    fig, ax = plt.subplots(1, len(DS), figsize=(2.5 * len(DS), 2.8))
    for a, (title, ds) in zip(ax, DS):
        im, ww, _ = load(ds)
        s = np.sqrt(abs(np.linalg.det(ww.pixel_scale_matrix))) * 3600
        x, y = ww.all_world2pix(RA, DEC, 0)
        n = int(HALF / s); xi, yi = int(round(float(x))), int(round(float(y)))
        sub = im[yi - n:yi + n + 1, xi - n:xi + n + 1]
        v0, v1 = np.nanpercentile(sub, [5, 99.7])
        a.imshow(np.arcsinh((sub - v0) / max(v1 - v0, 1e-6) * 10), origin="lower", cmap="gray")
        a.add_patch(plt.Circle((x - xi + n, y - yi + n), 1.0 / s, fill=False, color="lime", lw=0.7))
        for k, c in enumerate(out["sources"]):
            cx, cy = ww.all_world2pix(c["ra"], c["dec"], 0)
            a.text(cx - xi + n, cy - yi + n, str(k), color="orange", fontsize=7)
        a.set_title(title, fontsize=7); a.set_xticks([]); a.set_yticks([])
    fig.suptitle("NGC 2403 obs#50 in HST (8\" boxes). Green circle: r = 1\" around the WISE position; numbers: near-IR-bright "
                 "sources (F160W 2010)", fontsize=8)
    fig.tight_layout(); fig.savefig(HERE / "hst_ngc2403.png", dpi=90)
    (HERE / "hst_ngc2403.json").write_text(json.dumps(out, indent=1))
    for k, r in enumerate(out["sources"]):
        print(k, round(r["sep"], 2), {t: (None if r[t] is None else round(r[t], 2)) for t, _ in DS})


if __name__ == "__main__":
    main()
