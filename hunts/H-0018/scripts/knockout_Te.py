"""Model with e and T fixed, as in Gaia's pseudo-circular solutions, DR3 span and no selection. First: chiral_sim.py --stars 1000 --draws 100 --seed 30 --fix T,e --out ~/oddsky-runs/h0018/sim_ko_Te.parquet"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

d = pd.read_parquet(f"{hd.RUNS}/sim_ko_Te.parquet")
for a, b in [(150, 200), (340, 390), (450, 600), (600, 700), (700, 800), (800, 900), (900, 1100), (1100, 1600)]:
    x = d[d.P.between(a, b)]
    print(a, b, round(np.nanmedian(x.s_plx_plus) / np.nanmedian(x.s_plx_minus), 3))
