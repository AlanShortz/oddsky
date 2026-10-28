"""Hunt H-0005: Gaia20fgk on the Palomar plates (DSS cutouts in hunts/H-0005/dss/). Aperture photometry of every Gaia
DR3 star within 75", a quadratic fit of plate instrumental magnitude against Gaia BP (blue plates) or RP (red and IR
plates), and the target's residual: positive means fainter than its Gaia magnitude predicts."""
import glob
import io
import warnings

import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.wcs import WCS

warnings.simplefilter("ignore")
RA, DEC, SID = 17.13953, 64.14006, 523457286761045120
q = ("SELECT source_id, ra, dec, pmra, pmdec, phot_g_mean_mag AS g, phot_bp_mean_mag AS bp, phot_rp_mean_mag AS rp "
     f"FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT(ra,dec),CIRCLE({RA},{DEC},{75 / 3600})) AND phot_g_mean_mag < 19.5")
s = pd.read_csv(io.StringIO(requests.post("https://gea.esac.esa.int/tap-server/tap/sync", timeout=120,
                                          data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": q}).text))
target = s.source_id == SID

for path in sorted(glob.glob("hunts/H-0005/dss/*.fits")):
    h = fits.getheader(path)
    im = fits.getdata(path).astype(float)
    dt = float(h["DATE-OBS"][:4]) + 0.7 - 2016.0  # years from Gaia's epoch
    ra = s.ra + s.pmra * dt / 3.6e6 / np.cos(np.radians(s.dec))
    de = s.dec + s.pmdec * dt / 3.6e6
    x, y = WCS(h).world_to_pixel_values(ra, de)
    pix = abs(h.get("PLTSCALE", 67.2) * h.get("XPIXELSZ", 25) / 1000.0)  # arcsec per pixel
    rap = 3.5 / pix
    yy, xx = np.mgrid[:im.shape[0], :im.shape[1]]
    flux = []
    for xi, yi in zip(x, y, strict=True):
        rr = np.hypot(xx - xi, yy - yi)
        ap, sky = rr <= rap, (rr > rap + 2) & (rr <= rap + 6)
        flux.append(im[ap].sum() - np.median(im[sky]) * ap.sum() if ap.any() else np.nan)
    s["inst"] = -2.5 * np.log10(np.clip(flux, 1e-3, None))
    ref = "bp" if "blue" in path else "rp"
    inside = (x > 8) & (y > 8) & (x < im.shape[1] - 8) & (y < im.shape[0] - 8)
    ok = ~target & np.isfinite(s.inst) & np.isfinite(s[ref]) & inside
    res = s.inst - np.polyval(np.polyfit(s.loc[ok, ref], s.loc[ok, "inst"], 2), s[ref])
    scatter = 1.4826 * np.median(np.abs(res[ok] - np.median(res[ok])))
    print(f"{path.split('/')[-1][:-5]:16s} {h['DATE-OBS'][:10]} pix {pix:.2f}\" n_ref {ok.sum():2d} scatter {scatter:.2f}  "
          f"target {ref.upper()}={float(s.loc[target, ref].iloc[0]):.2f} residual {float(res[target].iloc[0]):+.2f} mag")
