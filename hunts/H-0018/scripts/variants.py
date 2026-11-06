"""How much do the model's predictions depend on what was assumed? Own-sense ratio (the grader's statistic) and A, per variant."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
from forecast_table_lib import ratio  # noqa: E402

bins = [(150, 200), (340, 390), (450, 600), (600, 700), (700, 800), (800, 900), (1100, 1600)]
print("variant                  " + " ".join(f"{a}-{b:<5}" for a, b in bins) + "  A:340-390 A:600-900 N_acc")
for name in sys.argv[1:]:
    d = pd.read_parquet(f"{hd.RUNS}/{name}.parquet")
    x = d[d.P.between(340, 390)]
    z = d[d.P.between(600, 900)]
    A1 = (x.acc_plus.sum() - x.acc_minus.sum()) / max(x.acc_plus.sum() + x.acc_minus.sum(), 1)
    A2 = (z.acc_plus.sum() - z.acc_minus.sum()) / max(z.acc_plus.sum() + z.acc_minus.sum(), 1)
    print(f"{name:<25}" + " ".join(f"{ratio(d, a, b):9.3f}" for a, b in bins) + f"  {A1:+.3f}    {A2:+.3f}   {int(d.acc_plus.sum() + d.acc_minus.sum())}")
