"""Hunt H-0008, last step: open an Oddsky case for a candidate that ATLAS has reproduced, and fetch its data.

    uv run python scripts/open_h0008_case.py J180624

Gaia, NEOWISE (visits and single exposures) and ZTF come from the archives. ATLAS reuses the forced-photometry text the hunt
already downloaded (work/atlas/), so opening a case does not queue a new ATLAS task. No chi_n cut (it removes the peak).
"""

from __future__ import annotations

import sys
from pathlib import Path

from oddsky import skeptic
from oddsky.data import atlas
from oddsky.data.provenance import Provenance
from oddsky.fetch import fetch, open_case

TARGETS = {
    "J180624": dict(
        name="Gaia DR3 4158424169627436800", ra=271.603281, dec=-9.069857, task="5272650", chi_max=1e9,
        title="A star in Serpens brightened fivefold over four months in 2022: an apparently unreported microlensing event",
        hook="Found blind in Oddsky hunt H-0008 as a colour-neutral 3.5x brightening in NEOWISE (2022 Aug 31). ATLAS shows one "
        "smooth, symmetric event peaking near 2022 Sep 19 at about 5x, lasting months. Not in TNS, the Gaia alerts, the KMTNet or "
        "OGLE lists, the ZTF microlensing catalogues, SIMBAD, VSX or ADS full text.",
        notes=["chi_n cut disabled (chi_max=1e9): chi_n rises with flux, so a cut removes the peak (ATLAS referee)", "ATLAS baseline before 2019 is 30-50% low, tracking each unit's PSF width: instrumental (ATLAS referee)"]),
    "J183040": dict(
        name="Gaia DR3 4090003970570642816", ra=277.670788, dec=-22.163984, task="5272651", chi_max=1e9,
        title="A bulge giant in Sagittarius brightened by half for four months in 2022: a blended microlensing candidate",
        hook="Found blind in Oddsky hunt H-0008 as a colour-neutral 1.5x brightening in NEOWISE (2022 Sep 8). ATLAS and ZTF show "
        "one smooth event peaking in late August 2022, equal from g to 4.6 microns. ALeRCE classifies the ZTF object as LPV/YSO.",
        notes=["chi_n cut disabled (chi_max=1e9): chi_n rises with flux, so a cut removes the peak (ATLAS referee)"]),
}


def main(key: str) -> None:
    t = TARGETS[key]
    store = open_case(t["name"], title=t["title"], hook=t["hook"], ra=t["ra"], dec=t["dec"], hunt="H-0008")
    print(store.path.name, flush=True)
    print(fetch(store, ["gaia", "gaia_epoch", "neowise", "neowise_exp", "ztf"]), flush=True)
    txt = Path(f"hunts/H-0008/work/atlas/atlas_{key}.txt")
    raw = atlas.parse(txt.read_text())
    df = atlas.to_series(raw, chi_max=t["chi_max"])
    store.write_series("atlas", df)
    prov = store.provenance()
    p = Provenance(archive="ATLAS forced photometry (fallingstar-data.com), reduced images",
                   query={"ra": t["ra"], "dec": t["dec"], "mjd_min": 57000, "use_reduced": True, "task": t["task"]})
    p.rows_raw = len(raw)
    p.rows_kept = int((df.flag == "").sum())
    p.notes += [f"reused the hunt's server response {txt}", *t["notes"]]
    prov["atlas"] = p.model_dump()
    store.write_provenance(prov)
    print("atlas", p.rows_kept, "usable of", p.rows_raw, flush=True)
    print(skeptic.run(store)["summary"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
