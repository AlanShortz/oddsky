"""Per-exposure SVM drc files of the 2025-01-09 visit (17502_14) in F814W, F555W, F438W: the visit-level drc
combine misaligned exposures (stars broadened, ~1 px local misregistration). argv[1] = destination."""
import re
import sys
from pathlib import Path
from astroquery.mast import Observations

dest = Path(sys.argv[1])
obs = Observations.query_criteria(obs_collection="HST", proposal_id="17502", obs_id=["hst_17502_14_wfc3_uvis_f814w_ifab14",
                                  "hst_17502_14_wfc3_uvis_f555w_ifab14", "hst_17502_14_wfc3_uvis_f438w_ifab14"])
P = Observations.get_product_list(obs)
pat = re.compile(r"^hst_17502_14_wfc3_uvis_f(814|555|438)w_ifab14\w\w_drc\.fits$")
P = P[[bool(pat.match(str(f))) for f in P["productFilename"]]]
seen = set()
for i in range(len(P)):
    f = P["productFilename"][i]
    if f in seen or (dest / f).exists():
        continue
    seen.add(f)
    Observations.download_products(P[i:i + 1], download_dir=str(dest), flat=True)
print("done")
