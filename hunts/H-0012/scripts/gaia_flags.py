"""H-0012 triage of the top candidates: Gaia DR3 counterpart (foreground star? quasar?) and mid-IR
colour (AGN?). De et al. 2024 criterion 3, plus the checks the referee showed were missing (two of
the first three M31 "leads" were a catalogued LBV and a catalogued Seyfert).

    uv run python hunts/H-0012/scripts/gaia_flags.py M31 [N]

For the top N by DS1-likeness and the top N by variability (one async TAP job):
  - brightest Gaia DR3 source within 3": G, BP-RP, parallax and proper-motion S/N, VARIABLE flag,
    DSC quasar probability (classprob_dsc_combmod_quasar); source_id kept as a STRING
  - foreground = parallax S/N > 5 or proper-motion S/N > 5; quasar = P(quasar) > 0.5
  - W1-W2 (Vega) from the reference PSF fluxes; agn_colour = W1-W2 >= 0.8 outside D25
Writes work/gaia_<galaxy>.csv (gaia_id as text).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from oddsky.imaging import crossmatch, fetch
from oddsky.imaging.galaxies import GALAXIES

HERE = Path(__file__).resolve().parents[1]


def main(galaxy: str, n: int = 30):
    c = pd.read_csv(fetch.cache_root() / "work" / galaxy / "candidates.csv")
    c["rank_ds1"] = np.arange(1, len(c) + 1)
    c["rank_var"] = c.var_sig.rank(ascending=False, method="first")
    top = c[(c.rank_ds1 <= n) | (c.rank_var <= n)].copy()
    g = crossmatch.gaia_batch(top.ra.to_numpy(), top.dec.to_numpy())
    x = crossmatch.nearest(top, g)
    top["r_ell"] = GALAXIES[galaxy].ellipse_r(top.ra, top.dec)
    top["w1_w2"] = crossmatch.w1_minus_w2(top.w1_ref_flux, top.w2_ref_flux)
    top["agn_colour"] = crossmatch.agn_colour_flag(top.w1_ref_flux, top.w2_ref_flux, top.r_ell)
    out = top[["group", "rank_ds1", "rank_var", "ra", "dec", "r_ell", "cls", "dipole", "w1_w2", "agn_colour"]].merge(x, on="group", how="left")
    p = HERE / "work" / f"gaia_{galaxy}.csv"
    out.to_csv(p, index=False)
    pd.set_option("display.width", 250)
    print(out.round(3).to_string())
    print("wrote", p)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30)
