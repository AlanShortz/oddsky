"""Hunt H-0004, step 5: open an Oddsky case for each surviving pick and run the Skeptic.

  .venv/bin/python scripts/open_h0004_cases.py T20-1234 T20-77 ...
  .venv/bin/python scripts/open_h0004_cases.py --from-vetted      # every rcb_pick in vetted.csv not yet a case

The case name is the WISE designation (or Gaia DR3 id for pool B); the title is a plain description, the
hook says how it was found. ATLAS and ZTF are re-fetched into the case so the ledger replays from the
archives, not from the hunt cache.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from oddsky import skeptic
from oddsky.case.store import CaseStore
from oddsky.fetch import fetch, open_case

here = Path("hunts/H-0004")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--from-vetted", action="store_true")
    ap.add_argument("--surveys", default="gaia,gaia_epoch,neowise,ztf,atlas,aavso")
    a = ap.parse_args()
    sc = pd.read_csv(here / "scored.csv").set_index("id")
    ids = list(a.ids)
    if a.from_vetted:
        v = pd.read_csv(here / "vetted.csv")
        ids += [i for i in v[v.verdict.eq("rcb_like")].id if i not in ids]
    for cid in ids:
        s = sc.loc[cid]
        name = f"WISE {s.wise_id}" if isinstance(s.get("wise_id"), str) else f"Gaia DR3 {int(s.source_id)}"
        try:
            CaseStore.find(name)
            print(cid, "already a case", flush=True)
            continue
        except FileNotFoundError:
            pass
        depth = f"{s.depth:.1f}" if pd.notna(s.depth) else "?"
        title = f"{name}: a {depth}-mag fade from a flat maximum"
        hook = (f"Found in Oddsky hunt H-0004 (stars that go dark). A WISE-selected R CrB candidate from Tisserand+2020 "
                f"({s.get('k24_lc_pri', '')}/{s.get('k24_col_pri', '')}) with its first recorded decline in {s.band} data.")
        store = open_case(name, title, hook=hook, ra=float(s.ra), dec=float(s.dec), hunt="H-0004")
        print(store.path.name, name, flush=True)
        print(fetch(store, a.surveys.split(",")), flush=True)
        print(skeptic.run(store)["summary"], flush=True)


if __name__ == "__main__":
    main()
