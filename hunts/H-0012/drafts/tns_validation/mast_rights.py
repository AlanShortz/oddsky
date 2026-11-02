"""OS-0030 TNS pre-filing check: data rights of the HST and JWST observations used (MAST CAOM), i.e. exposure
dates, release dates (t_obs_release), PIs and dataRights, for every science observation within 30" of the source.

    uv run python hunts/H-0012/drafts/tns_validation/mast_rights.py
Output: ~/oddsky-runs/imaging/scratch/tns-validation-os0030/mast/mast_rights.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.time import Time
from astroquery.mast import Observations

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-validation-os0030/mast"
OUT.mkdir(parents=True, exist_ok=True)
RA, DEC = 156.291224, 17.163778

obs = Observations.query_region(f"{RA} {DEC}", radius="30 arcsec").to_pandas()
obs = obs[obs.obs_collection.isin(["HST", "JWST"]) & (obs.dataproduct_type == "image")]
obs = obs[obs.intentType == "science"] if "intentType" in obs else obs
cols = ["obs_collection", "proposal_id", "proposal_pi", "instrument_name", "filters", "obs_id", "t_min", "t_exptime",
        "t_obs_release", "dataRights", "calib_level", "target_name"]
obs = obs[[c for c in cols if c in obs]].copy()
now = Time.now().mjd
obs["date_obs"] = Time(obs.t_min.values, format="mjd").iso
obs["release_date"] = [Time(t, format="mjd").iso[:10] if np.isfinite(t) else "" for t in obs.t_obs_release]
obs["public_now"] = obs.t_obs_release < now
obs = obs.sort_values(["obs_collection", "t_min"])
obs.to_csv(OUT / "mast_rights.csv", index=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
keep = obs[obs.proposal_id.astype(str).isin(["16179", "15446", "17502", "3707"])]
print(keep[["obs_collection", "proposal_id", "proposal_pi", "instrument_name", "filters", "obs_id", "date_obs",
            "release_date", "dataRights", "public_now"]].to_string())
print("\nall programmes within 30\":")
print(obs.groupby(["obs_collection", "proposal_id", "proposal_pi"]).agg(
    n=("obs_id", "size"), first=("date_obs", "min"), last=("date_obs", "max"),
    release_min=("release_date", "min"), release_max=("release_date", "max"),
    rights=("dataRights", lambda s: ",".join(sorted(set(map(str, s)))))).to_string())
