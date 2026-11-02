"""List HST image obs_ids (HAP/HLA dataset names) covering a position.  uv run python hst_list.py RA DEC"""
import sys
from astropy.coordinates import SkyCoord
from astroquery.mast import Observations
ra, dec = float(sys.argv[1]), float(sys.argv[2])
t = Observations.query_region(SkyCoord(ra, dec, unit="deg"), radius="0.0003 deg")
t = t[(t["obs_collection"] == "HST") & (t["dataproduct_type"] == "image") & (t["intentType"] == "science")]
for r in sorted(t, key=lambda r: float(r["t_min"])):
    print(r["obs_id"], r["instrument_name"], r["filters"], round(float(r["t_min"]), 2), r["proposal_id"])
