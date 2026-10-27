"""Open the seed cases and fetch their data. the advisor will veto and replace these (docs/OPEN_QUESTIONS.md).

Run: python scripts/seed_cases.py [name ...]
"""

import sys

from oddsky import skeptic
from oddsky.fetch import fetch, open_case

SEEDS = [
    ("ASASSN-21qj", "The star that glowed before it dimmed",
     "In 2018 this Sun-like star started glowing in the infrared. Three years later it began to fade. Something hot came first."),
    ("KIC 8462852", "The most mysterious star in the galaxy (allegedly)",
     "Boyajian's Star: irregular dips of up to 22% that no planet could make. Aliens were proposed. Dust was found."),
    ("EE Cep", "The eclipse that comes back every 5.6 years",
     "Every 2,050 days something dark and enormous passes in front of this star, and every time the shadow looks different."),
    ("R CrB", "The star that smokes",
     "For months it shines steadily; then it vanishes by eight magnitudes, as if someone blew out a candle. It makes its own soot."),
    ("R Cyg", "Breathing in, breathing out",
     "A giant star swelling and shrinking every 14 months, brightening a thousandfold. Strange to the eye, ordinary to astrophysics."),
    ("SS Cyg", "The star that won't stay quiet",
     "Every few weeks, for a century of amateur records, it leaps fiftyfold in brightness in a day. Something is feeding on its neighbour."),
    ("AA Tau", "The young star that went dark in 2011",
     "A famous, well-behaved young star that suddenly dimmed by two magnitudes and stayed dim for a decade."),
]


def main(names):
    for name, title, hook in SEEDS:
        if names and name not in names:
            continue
        s = open_case(name, title, hook)
        print(f"== {s.path.name} {name}", flush=True)
        try:
            if not s.surveys() or "--refetch" in sys.argv:
                print(fetch(s), flush=True)
            print(skeptic.run(s)["summary"], flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"!! {name}: {type(e).__name__}: {e}", flush=True)


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")])
