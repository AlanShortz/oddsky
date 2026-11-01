"""r3d: parallax and fs<=1.5 variants (r3 'full' mode) for the other 16 candidates, where r3 --all ran only the static lens.
Coarse start grid (REFEREE_FAST=1, 48 starts per model) to keep the run time reasonable; first star (J174656) was also run with the full grid.
Run: uv run python -I -u hunts/H-0010/reviews/claude-referee-2026-11-01/r3d_parallax_rest.py"""
import os, sys
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["REFEREE_FAST"] = "1"
import r3_fits  # noqa: E402

inv = pd.read_csv(os.path.join(HERE, "..", "..", "work", "gaia_ml_unpub.csv"), dtype={"source_id": str}).set_index("source_id")
out = []
for sid in r3_fits.C.index:
    if sid in list(r3_fits.WIN)[:5]:
        continue
    a, b = float(inv.loc[sid, "ep_first"]), float(inv.loc[sid, "ep_last"])
    win = (a - max(60, b - a) - 30, b + max(60, b - a) + 30)
    out.append(r3_fits.run(sid, win, full=True))
pd.DataFrame(out).to_csv(os.path.join(HERE, "data", "r3d_parallax_rest.csv"), index=False)
