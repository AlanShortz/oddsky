"""After the referee (finding D1): is the SMC's low reference value a colour-mix effect? Raw fraction of stars 0-1 mag
above the tip changing by more than 0.3 mag at two random times, for red cuts of increasing V-I, and the reference's
sensitivity to amplitude scale. Writes work/cloud_colour.csv."""
import pathlib
import numpy as np, pandas as pd
from oddsky.analysis import twopoint

HERE = pathlib.Path(__file__).resolve().parents[1]; rows = []
for cloud, tip in (("lmc", 14.60), ("smc", 15.00)):
    pop = pd.read_csv(HERE / f"work/{cloud}_population.csv")
    for scale in (1.0, 1.2, 1.4):
        mean, d = twopoint.simulate_two_visits(pop.I.values, pop[["P1", "P2", "P3"]].values, pop[["A1", "A2", "A3"]].values * scale, 1000.0, seed=12)
        rel = mean - tip; agb = (rel >= -1) & (rel < 0); rgb = (rel >= 0) & (rel < 0.5)
        box = (pop.I.values - tip >= -1) & (pop.I.values - tip < 0)
        for vi in (1.2, 1.6, 1.8, 2.0):
            c = (pop.VI.values > vi)[None, :]
            rows.append(dict(cloud=cloud, amp_scale=scale, vi_min=vi, share_of_box=round(float((box & (pop.VI.values > vi)).sum() / box.sum()), 3),
                             f03_agb=round(float((np.abs(d)[agb & c] > 0.3).mean()), 4), E03=round(float((np.abs(d)[agb & c] > 0.3).mean() - (np.abs(d)[rgb & c] > 0.3).mean()), 4)))
df = pd.DataFrame(rows); df.to_csv(HERE / "work/cloud_colour.csv", index=False)
print(df[df.amp_scale == 1].to_string(index=False)); print(df[df.vi_min == 1.2].to_string(index=False))
