"""Open case OS-0029 for J180839.93-151910.5 (H-0009): a NEOWISE brightening that Gaia DR3 epoch photometry confirms as achromatic
(hunts/H-0009/reviews/gaia-dr3-sweep-2026-10-31.md), with ATLAS's blurred 2016 images showing the decline. No prediction: the event
is inside Gaia DR3's span, so DR4 cannot test it blind.

    uv run python scripts/open_case_29.py
"""

from pathlib import Path

from oddsky import skeptic
from oddsky.case.store import CaseStore
from oddsky.data import atlas
from oddsky.data.provenance import Provenance
from oddsky.fetch import fetch, open_case
from oddsky.tools import Toolbox

SWEEP = "hunts/H-0009/reviews/gaia-dr3-sweep-2026-10-31.md"
GAIA, RA, DEC = "4145977633638478336", 272.1663777, -15.3195869
store = open_case(f"Gaia DR3 {GAIA}", ra=RA, dec=DEC, hunt="H-0009",
                  title="A star in Serpens brightened by half in March 2016, equally in Gaia's three bands: a microlensing candidate",
                  hook="Found blind in Oddsky hunt H-0009 (NEOWISE x1.6 on 2016 Mar 21). Gaia DR3 epoch photometry shows x1.5 sixteen "
                       "days earlier and x1.4 fifteen days later, equal in G, BP and RP, fading by late April. Gaia's classifier labels "
                       "the star MICROLENSING.")
cid = store.path.name
print(cid, fetch(store, ["gaia", "gaia_epoch", "neowise", "neowise_exp"]), flush=True)
path = "hunts/H-0009/work/atlas/atlas_J180839.txt"
raw = atlas.parse(Path(path).read_text())
df = atlas.to_series(raw, chi_max=1e9)
store.write_series("atlas", df)
prov = store.provenance()
p = Provenance(archive="ATLAS forced photometry (fallingstar-data.com), reduced images",
               query={"ra": RA, "dec": DEC, "use_reduced": True, "task": "5276400"})
p.rows_raw, p.rows_kept = len(raw), int((df.flag == "").sum())
p.notes += [f"reused the hunt's server response {path}", "chi_n cut disabled: chi_n rises with flux",
            "2016 frames have wide PSFs (major axis ~4.6 px), which bias reduced-image fluxes low"]
prov["atlas"] = p.model_dump()
store.write_provenance(prov)
tb = Toolbox(mode="open", author="claude-opus-5.5")
claims = [
    ("NEOWISE on 2016 Mar 21: x1.62 in W1 and x1.67 in W2 against the star's median; every other visit quiet. Found blind by hunt "
     "H-0009.", "observed"),
    ("Gaia DR3 epoch photometry of Gaia DR3 4145977633638478336 (G 16.0): G x1.52 at -16 d; G, BP and RP x1.39, x1.38, x1.39 at +15 d; "
     f"x1.15 at +35 d; no other brightening in 28 transits in 2014-2017 ({SWEEP}).", "observed"),
    ("ATLAS (task 5276400), in blurred 2016 images that bias fluxes low: x1.24 (c) at +12 d, x1.37 and x1.20 (o) at +26 and +30 d, "
     "x0.94-0.96 at +45-52 d, consistent with Gaia's decline.", "observed"),
    ("The Gaia DR3 classifier labels the star MICROLENSING (score 0.21); it is not in the Gaia DR3 microlensing catalogue.", "observed"),
    ("Not in TNS or the Gaia alerts (2026-10-31); MOA and the KMTNet 2016 season unchecked.", "observed")]
ids = [tb.add_claim(cid, t, g, [])["claim"] for t, g in claims]
tb.add_hypothesis(cid, "microlensing", "A lens magnified the star by about half for roughly six weeks around 2016 March; the peak "
                  "fell between Gaia's transits.", supports=ids, would_falsify="A repeat, or BP and RP changing differently.",
                  confidence=0.5)
c = CaseStore(store.path).load()
c.status = "reproduced"
CaseStore(store.path).save(c)
print(skeptic.run(store)["summary"])
