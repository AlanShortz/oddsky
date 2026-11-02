"""List and download HST single-visit (SVM) drizzled products (drc) plus per-exposure flc files of every HST visit
covering the position, and JWST i2d level-3 mosaics. Downloads go to argv[1] (outside the repo)."""
import sys
from pathlib import Path
from astroquery.mast import Observations
import astropy.units as u
from astropy.coordinates import SkyCoord

HERE = Path(__file__).resolve().parent
dest = Path(sys.argv[1]); dest.mkdir(parents=True, exist_ok=True)
do_dl = len(sys.argv) > 2 and sys.argv[2] == "dl"
c = SkyCoord(156.2910, 17.1639, unit="deg")
obs = Observations.query_region(c, radius=0.001 * u.deg)
hst = obs[(obs["obs_collection"] == "HST") & ([str(o).startswith("hst_1") for o in obs["obs_id"]])
          & ([f != "detection" for f in obs["filters"]])]
jw = obs[(obs["obs_collection"] == "JWST")]
prods = Observations.get_product_list(hst)
sel = [(str(p["productFilename"]).endswith(("_drc.fits", "_flc.fits"))) for p in prods]
prods = prods[sel]
# SVM drc are named hst_<prop>_<visit>_<inst>_<det>_<filt>_<ipppss>_drc.fits; per-exposure SVM flc: hst_..._<exp>_flc.fits
prods.sort("productFilename")
for p in prods:
    print(p["productFilename"], p["size"])
jp = Observations.get_product_list(jw)
jp = jp[[str(f).endswith("_i2d.fits") for f in jp["productFilename"]]]
for p in jp:
    print(p["productFilename"], p["size"])
if do_dl:
    Observations.download_products(prods, download_dir=str(dest), flat=True)
    Observations.download_products(jp, download_dir=str(dest), flat=True)
