"""r2: NEOWISE visit light curves of the ten stars (sky4long lightcurves parquet, allwise_cntr as int64): per visit W1, W2, the
ratio to the quiet-visit baseline, and the per-visit diagnostics (satfrac, hdfrac, nbfrac, ccfrac, rchi). Marks the block."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import KEYS, mjd2date, neowise, targets  # noqa: E402

pd.set_option("display.width", 250)
T = targets()
for k in KEYS:
    t = T[k]
    lc = neowise(k, t, raw=True).copy()
    blk = (lc.t >= t["t_first"] - 1) & (lc.t <= t["t_last"] + 1)
    for b in ("w1", "w2"):
        lc[f"d{b}"] = lc[b] - np.median(lc[b][~blk])
        lc[f"r{b}"] = 10 ** (-0.4 * lc[f"d{b}"])
    lc["date"] = [mjd2date(x) for x in lc.t]
    lc["blk"] = np.where(blk, "*", "")
    print(f"== {k} {t['name']}  AllWISE W1 {t['w1']:.2f} W2 {t['w2']:.2f} W3 {t['w3']:.2f} W4 {t['w4']:.2f} J {t['J']:.2f} K {t['K']:.2f}"
          f"  G {t['G']:.2f} BP-RP {t['bprp']:.2f} (Gaia sep {t['gsep']:.2f}\")  G-W1 {t['G'] - t['w1']:.2f}")
    print(f"   quiet rms W1 {np.std(lc.dw1[~blk]):.3f} W2 {np.std(lc.dw2[~blk]):.3f}; quiet medians: hdfrac {lc.hdfrac[~blk].median():.2f} "
          f"nbfrac {lc.nbfrac[~blk].median():.2f} satfrac {lc.satfrac[~blk].median():.2f} ccfrac {lc.ccfrac[~blk].median():.2f} "
          f"rchi {lc.rchi[~blk].median():.1f}")
    print(lc[["date", "t", "blk", "w1_n", "w2_n", "w1", "w2", "rw1", "rw2", "w1_err", "satfrac", "hdfrac", "nbfrac", "ccfrac", "rchi"]]
          .round(3).to_string(index=False))
