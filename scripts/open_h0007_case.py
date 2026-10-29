"""Hunt H-0007, last step: open the Oddsky case for J040025.77+323527.4 (Gaia DR3 170329679884731008) and fetch its data.

Gaia, NEOWISE (visits and single exposures) and ZTF come from the archives. ATLAS reuses the forced-photometry text the hunt
already downloaded (task 5270459; hunts/H-0007/work/atlas_J040025.txt), so the case does not queue a new ATLAS task, and it is
converted with the chi_n cut disabled: for a star this bright (o ~ 13.8) the PSF-fit chi_n is 5-100 at baseline and up to 10^4
near the peak, so the default cut (chi_n > 10) would flag 78% of all frames and 79 of the 84 event frames.
"""

from __future__ import annotations

from pathlib import Path

from oddsky import skeptic
from oddsky.data import atlas
from oddsky.data.provenance import Provenance
from oddsky.fetch import fetch, open_case

NAME = "Gaia DR3 170329679884731008"
RA, DEC = 60.1073758, 32.5909576
ATLAS_TXT = Path("hunts/H-0007/work/atlas_J040025.txt")


def main() -> None:
    store = open_case(
        NAME,
        title="A red giant toward the Galactic anticentre brightened sevenfold for a few weeks in 2017: a microlensing event",
        hook="Found in Oddsky hunt H-0007 as a one-visit, colour-neutral 2.7x brightening in NEOWISE (2017 Aug 27-28); "
        "ATLAS shows a single smooth event peaking near 2017 Sep 16. Not in VSX, TNS, the Gaia alerts or Gaia DR3.",
        ra=RA,
        dec=DEC,
        hunt="H-0007",
    )
    print(store.path.name, flush=True)
    print(fetch(store, ["gaia", "gaia_epoch", "neowise", "neowise_exp", "ztf"]), flush=True)
    raw = atlas.parse(ATLAS_TXT.read_text())
    df = atlas.to_series(raw, chi_max=1e9)
    store.write_series("atlas", df)
    prov = store.provenance()
    p = Provenance(
        archive="ATLAS forced photometry (fallingstar-data.com), reduced images",
        query={"ra": RA, "dec": DEC, "mjd_min": 57000, "use_reduced": True, "task": "5270459"},
    )
    p.rows_raw = len(raw)
    p.rows_kept = int((df.flag == "").sum())
    p.notes += [
        f"reused the hunt's server response {ATLAS_TXT}",
        "chi_n cut disabled (chi_max=1e9): bright star, PSF-fit chi_n 5-100 at baseline; the default cut flags 78% of frames",
        "frames brighter than m ~ 12.2 are near ATLAS saturation (the 2017 Sep 11-13 peak nights)",
    ]
    prov["atlas"] = p.model_dump()
    store.write_provenance(prov)
    print("atlas", p.rows_kept, "usable of", p.rows_raw, flush=True)
    print(skeptic.run(store)["summary"], flush=True)


if __name__ == "__main__":
    main()
