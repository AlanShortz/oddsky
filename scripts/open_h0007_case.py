"""Hunt H-0007, last step: open an Oddsky case for a reproduced microlensing event and fetch its data.

    uv run python scripts/open_h0007_case.py J040025   # -> OS-0016
    uv run python scripts/open_h0007_case.py J193353   # -> OS-0017

Gaia, NEOWISE (visits and single exposures) and ZTF come from the archives. ATLAS reuses the forced-photometry text the hunt
already downloaded, so opening a case does not queue a new ATLAS task. For J040025 (o ~ 13.8) the chi_n cut is disabled: the
PSF-fit chi_n is 5-100 at baseline and up to 10^4 near the peak, so the default cut (chi_n > 10) would flag 78% of all frames.
J193353 (o ~ 15.4) keeps the default cut (83% of frames pass).
"""

from __future__ import annotations

import sys
from pathlib import Path

from oddsky import skeptic
from oddsky.data import atlas
from oddsky.data.provenance import Provenance
from oddsky.fetch import fetch, open_case

TARGETS = {
    "J040025": dict(
        name="Gaia DR3 170329679884731008", ra=60.1073758, dec=32.5909576, task="5270459", chi_max=1e9,
        title="A red giant toward the Galactic anticentre brightened sevenfold for a few weeks in 2017: a microlensing event",
        hook="Found in Oddsky hunt H-0007 as a one-visit, colour-neutral 2.7x brightening in NEOWISE (2017 Aug 27-28); "
        "ATLAS shows a single smooth event peaking near 2017 Sep 16. Not in VSX, TNS, the Gaia alerts or Gaia DR3.",
        notes=["chi_n cut disabled (chi_max=1e9): bright star, PSF-fit chi_n 5-100 at baseline; the default cut flags 78% of frames",
               "frames brighter than m ~ 12.2 are near ATLAS saturation (the 2017 Sep 11-13 peak nights)"]),
    "J193353": dict(
        name="Gaia DR3 6772245406602788608", ra=293.471115, dec=-21.3037472, task="5271652", chi_max=10.0,
        title="A halo giant doubled in brightness in spring 2020 and faded over six months: a microlensing event",
        hook="Found in Oddsky hunt H-0007 among faint stars: a one-visit, colour-neutral 2x brightening in NEOWISE (2020 Apr 9-10). "
        "ATLAS shows one smooth event, x2.4 on Mar 11 and gone by October; ZTF catches the tail. Not in VSX, TNS, SIMBAD or the Gaia alerts.",
        notes=["default chi_n cut (chi_max=10): 83% of frames pass"]),
}


def main(key: str) -> None:
    t = TARGETS[key]
    store = open_case(t["name"], title=t["title"], hook=t["hook"], ra=t["ra"], dec=t["dec"], hunt="H-0007")
    print(store.path.name, flush=True)
    print(fetch(store, ["gaia", "gaia_epoch", "neowise", "neowise_exp", "ztf"]), flush=True)
    txt = Path(f"hunts/H-0007/work/atlas_{key}.txt")
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
    main(sys.argv[1] if len(sys.argv) > 1 else "J040025")
