"""Two unremarkable stars for the trials: one stays honest (normal), one gets planted artifacts."""

from oddsky import skeptic
from oddsky.fetch import fetch, open_case

CONTROLS = [
    ("Gaia DR3 1633269723578294016", 268.42233, 66.02871, "Control A",
     "A quiet G star in TESS's continuous viewing zone. Used in trials as a canvas for planted artifacts."),
    ("Gaia DR3 1441063855405214080", 269.92753, 65.85794, "Control B",
     "A quiet G star in TESS's continuous viewing zone. Nothing to see here, and that is the test."),
]

for name, ra, dec, title, hook in CONTROLS:
    s = open_case(name, title, hook, ra=ra, dec=dec)
    print("==", s.path.name, name, flush=True)
    print(fetch(s, ["gaia", "neowise", "ztf", "tess"]), flush=True)
    print(skeptic.run(s)["summary"], flush=True)
