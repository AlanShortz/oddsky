"""Open Oddsky cases for the H-0002 afterglow candidates that survived vetting."""
from oddsky import skeptic
from oddsky.fetch import fetch, open_case

for name, ra, dec, title in (
    ("Gaia DR3 5792808347020475136", 220.96627, -76.19612, "The K dwarf that lit up in 2018"),
    ("AllWISE 2779036401351050434", 278.27585, -36.12034, "A Sun-like star with a new warm glow"),
):
    s = open_case(name, title, ra=ra, dec=dec)
    print(s.path.name, flush=True)
    print(fetch(s, ["gaia", "gaia_epoch", "neowise", "neowise_exp", "tess"]), flush=True)
    print(skeptic.run(s)["summary"], flush=True)
