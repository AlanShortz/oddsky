"""All HST/JWST/Spitzer/Swift/GALEX observations in MAST whose footprint covers NGC 3239 156.2910 +17.1639,
and the science products (flc/flt/drc/drz/c1m etc.) of the HST ones. Writes mast_obs.csv, mast_products.csv."""
import sys
from pathlib import Path
from astroquery.mast import Observations
import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np

HERE = Path(__file__).resolve().parent
c = SkyCoord(156.2910, 17.1639, unit="deg")
obs = Observations.query_region(c, radius=0.001 * u.deg)
print(len(obs), "observations within 3.6\" (footprint test)")
keep = obs[[o in ("HST", "JWST", "SPITZER_SHA", "SWIFT", "GALEX", "HLA", "PS1") for o in obs["obs_collection"]]]
cols = ["obs_collection", "instrument_name", "filters", "obs_id", "proposal_id", "t_min", "t_exptime", "dataproduct_type", "calib_level", "target_name", "s_ra", "s_dec"]
keep = keep[cols]
keep.sort("t_min")
keep.write(HERE / "mast_obs.csv", overwrite=True)
for r in keep:
    print(r["obs_collection"], r["instrument_name"], r["filters"], r["obs_id"], r["proposal_id"], f"{r['t_min']:.2f}", r["t_exptime"], r["dataproduct_type"], r["calib_level"], r["target_name"])
