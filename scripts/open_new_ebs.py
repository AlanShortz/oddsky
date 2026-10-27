"""Open cases for the two eclipsing binaries recognised in hunt H-0001."""
from oddsky import skeptic
from oddsky.fetch import fetch, open_case

for sid, ra, dec, title in (
    (2037357495383317504, 287.10668, 27.83755, "A binary hiding behind the wrong period"),
    (4482344869315388928, 271.37757, 9.46541, "The 2.38-day eclipse nobody catalogued"),
):
    s = open_case(f"Gaia DR3 {sid}", title, ra=ra, dec=dec)
    print(s.path.name, flush=True)
    print(fetch(s, ["gaia", "gaia_epoch", "neowise", "ztf", "tess"]), flush=True)
    print(skeptic.run(s)["summary"], flush=True)
