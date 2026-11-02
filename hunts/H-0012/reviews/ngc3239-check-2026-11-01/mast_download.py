"""Download the HST visit-level and per-exposure SVM drc files and the JWST level-3 mosaics that matter
(serial, one connection). argv[1] = destination directory (outside the repo)."""
import re
import sys
from pathlib import Path
from astroquery.mast import Observations
import astropy.units as u
from astropy.coordinates import SkyCoord

dest = Path(sys.argv[1]); dest.mkdir(parents=True, exist_ok=True)
c = SkyCoord(156.2910, 17.1639, unit="deg")
obs = Observations.query_region(c, radius=0.001 * u.deg)
hst = obs[(obs["obs_collection"] == "HST") & ([str(o).startswith("hst_1") for o in obs["obs_id"]])
          & ([f != "detection" for f in obs["filters"]])]
jw = obs[obs["obs_collection"] == "JWST"]
P = Observations.get_product_list(hst)
visit = re.compile(r"^hst_\d+_\d+_\w+?_(f\d+\w)_(\w{6})_drc\.fits$")
exp_ = re.compile(r"^hst_(16179|15446)_\d+_\w+?_(f\d+\w)_(\w{8})_drc\.fits$")
want = [bool(visit.match(str(f)) or exp_.match(str(f))) for f in P["productFilename"]]
P = P[want]
J = Observations.get_product_list(jw)
jw_ok = ("o038_t021_nircam_clear-f150w_i2d", "o138_t021_nircam_clear-f150w_i2d", "o038_t021_nircam_clear-f300m_i2d",
         "o138_t021_nircam_clear-f300m_i2d", "o038_t021_nircam_clear-f335m_i2d", "o137_t021_miri_f770w_i2d",
         "o137_t021_miri_f2100w_i2d")
J = J[[any(k in str(f) for k in jw_ok) for f in J["productFilename"]]]
# unique by filename
seen = set(); keepP = []
for i, f in enumerate(P["productFilename"]):
    if f not in seen:
        seen.add(f); keepP.append(i)
P = P[keepP]
seen = set(); keepJ = []
for i, f in enumerate(J["productFilename"]):
    if f not in seen:
        seen.add(f); keepJ.append(i)
J = J[keepJ]
for f in list(P["productFilename"]) + list(J["productFilename"]):
    print("want", f, flush=True)
for tab in (P, J):
    for i in range(len(tab)):
        if (dest / tab["productFilename"][i]).exists():
            continue
        Observations.download_products(tab[i:i + 1], download_dir=str(dest), flat=True)
print("done", flush=True)
