"""Which free element puts the orbit's sense into the parallax error? Median sigma_plx(+)/sigma_plx(-) by period."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

edges = [100, 150, 170, 200, 250, 300, 340, 390, 450, 500, 600, 700, 720, 745, 800, 900, 1000, 1300, 1600, 3000]
labels = {"all free": "sim_ko_none", "e fixed": "sim_ko_e", "P fixed": "sim_ko_P", "T fixed": "sim_ko_T", "P,T fixed": "sim_ko_PT", "P,T,e fixed": "sim_ko_all"}
fr = {k: pd.read_parquet(f"{hd.RUNS}/{v}.parquet") for k, v in labels.items()}
print("P range     " + "  ".join(f"{k:>11}" for k in labels))
for lo, hi in zip(edges[:-1], edges[1:]):
    vals = []
    for k in labels:
        x = fr[k][(fr[k].P >= lo) & (fr[k].P < hi)]
        vals.append(np.nanmedian(x.s_plx_plus) / np.nanmedian(x.s_plx_minus))
    print(f"{lo:>5}-{hi:<5} " + "  ".join(f"{v:11.3f}" for v in vals))
# Eccentricity dependence in the model, 700-800 d
x = fr["all free"]
x = x[(x.P >= 700) & (x.P < 800)]
print("\nmodel, 700-800 d, ratio by e:", [(a, round(float(np.nanmedian(s.s_plx_plus) / np.nanmedian(s.s_plx_minus)), 3)) for a, s in ((a, x[(x.ecc >= a) & (x.ecc < a + 0.2)]) for a in np.arange(0, 0.9, 0.2).round(1))])
