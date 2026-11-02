"""HST at NGC 55 fsn#7: list the calibrated drizzled products (WFPC2 2007, prog 11307; WFC3 2024, prog 17520) and
download the drc/drz (or HAP SVM) images covering the position to the scratch directory.

    uv run python hunts/H-0012/reviews/h0012b-referee/hst_ngc55_fetch.py [get]
"""
import sys
from pathlib import Path

from astropy.coordinates import SkyCoord
from astroquery.mast import Observations

OUT = Path("~/oddsky-runs/imaging/scratch/h0012b-referee/hst_ngc55").expanduser()
OUT.mkdir(parents=True, exist_ok=True)
c = SkyCoord(3.80788, -39.2148, unit="deg")
t = Observations.query_region(c, radius="0.0003 deg")
t = t[(t["obs_collection"] == "HST") & (t["dataproduct_type"] == "image") & (t["intentType"] == "science")]
for r in t:
    print(r["obs_id"], r["instrument_name"], r["filters"], round(float(r["t_min"]), 2), r["proposal_id"])
prods = Observations.get_product_list(t)
keep = []
for p in prods:
    fn = str(p["productFilename"]).lower()
    if (fn.endswith("_drc.fits") or fn.endswith("_drz.fits")) and ("hst_" in fn or "_flt" not in fn):
        keep.append(p)
print(len(prods), "products;", len(keep), "drizzled")
for p in keep:
    print(" ", p["productFilename"], p["size"])
sel = [p for p in keep if str(p["productFilename"]).lower().startswith("hst_") and "total" not in str(p["productFilename"]).lower()]
if not sel:
    sel = keep
small = [p for p in sel if int(p["size"]) < 400e6]
if small and "get" in sys.argv:
    from astropy.table import vstack
    tab = vstack([p for p in small]) if len(small) > 1 else small[0:1]
    Observations.download_products(tab, download_dir=str(OUT), cache=True)
