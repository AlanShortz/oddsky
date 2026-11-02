"""Recover the exact Gaia DR3 ids of H-0004's R CrB candidates (hunts/H-0004/candidates.csv stores them as floats).

Run from the repo root: uv run python -I hunts/H-0014/scripts/recover_h0004_ids.py
Writes hunts/H-0014/data/h0004_ids.csv (id, float_id, ra, dec, gaia_g, pool, source_id, sep_arcsec, dG, n_window, reason).
Run before 2026-11-25, when the archive closes for a week ahead of DR4; most DR3 ids carry over to DR4."""
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path.cwd() / "src"))
from oddsky.dr4day import config, idfix  # noqa: E402
from oddsky.dr4day.archive import Archive  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
c = pd.read_csv("hunts/H-0004/candidates.csv", dtype=str)
rows = pd.DataFrame(dict(id=c["id"], float_id=c.source_id, ra=c.ra.astype(float), dec=c.dec.astype(float),
                         gaia_g=pd.to_numeric(c.gaia_g, errors="coerce"), pool=c.pool))
arc = Archive(config.release("dr3"))
out = idfix.recover(arc, rows)
Path("hunts/H-0014/data").mkdir(parents=True, exist_ok=True)
out.to_csv("hunts/H-0014/data/h0004_ids.csv", index=False)
print(f"{len(out)} candidates; recovered {int((out.source_id != '').sum())}; "
      f"no id listed {int((out.reason == 'no Gaia id listed').sum())}; other failures "
      f"{int(((out.source_id == '') & (out.reason != 'no Gaia id listed')).sum())}; "
      f"ambiguous {int(out.reason.str.contains('matched').sum())}")
print(out.reason.value_counts().to_string())
if arc.errors:
    print("archive errors:", arc.errors)
    sys.exit(1)
