"""Write the forward model's predictions, by period, before the held-out split is opened."""
import numpy as np
import pandas as pd
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

edges = [50, 100, 150, 200, 250, 300, 340, 390, 450, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1600, 3000]
f = pd.read_parquet(f"{hd.RUNS}/sim_field.parquet")
n = pd.read_parquet(f"{hd.RUNS}/sim_nss.parquet")
rows = []
for lo, hi in zip(edges[:-1], edges[1:]):
    a, b = f[(f.P >= lo) & (f.P < hi)], n[(n.P >= lo) & (n.P < hi)]
    acc = b[(b.acc_plus | b.acc_minus) & (b.G >= 12) & (b.G < 16)]
    A = (a.acc_plus.sum() - a.acc_minus.sum()) / max(a.acc_plus.sum() + a.acc_minus.sum(), 1)
    rows.append(dict(lo=lo, hi=hi, A_model=A, N_model=int(a.acc_plus.sum() + a.acc_minus.sum()), ratio_model=np.nanmedian(acc.s_plx_plus) / np.nanmedian(acc.s_plx_minus)))
out = pd.DataFrame(rows)
out.to_csv(__file__.rsplit("/", 2)[0] + "/work/sim_prediction.csv", index=False)
print(out.round(3).to_string(index=False))
