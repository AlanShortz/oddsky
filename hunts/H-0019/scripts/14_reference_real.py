"""The Cloud reference from real OGLE-III light curves (pairs drawn by 13_ogle_real.py), set against the sinusoid
reference. Same boxes and control as the Hubble measurement; each star weighs the same. Writes work/reference_real.csv."""
import pathlib
import numpy as np, pandas as pd

RUN = pathlib.Path.home() / "oddsky-runs/h0019"; HERE = pathlib.Path(__file__).resolve().parents[1]
rng = np.random.default_rng(14); rows = []
sin = pd.read_csv(HERE / "work/reference.csv"); sin = sin[sin.dtip == 0].groupby("cloud").E03.mean()
for cloud, tip in (("lmc", 14.60), ("smc", 15.00)):
    pop = pd.read_csv(HERE / f"work/{cloud}_population.csv", dtype={"star": str})
    pop["star"] = pop.star.fillna("").str.strip().str.zfill(5).where(pop.star.notna() & (pop.star.fillna("").str.strip() != ""), "")
    pr = pd.read_parquet(RUN / f"ogle_pairs_{cloud}.parquet")
    var = pr.merge(pop[pop.star != ""][["star", "VI", "type"]], on="star")
    const = pop[pop.star == ""]
    nolc = pop[(pop.star != "") & ~pop.star.isin(pr.star)]          # OGLE variables with too few I points: sinusoid-free, dropped
    for noise in (0.03, 0.043):
        for lag in (150, 400, 1000, 2500):
            v = var[var.lag == lag]
            w = 1.0 / v.groupby("star").m1.transform("size")
            m1 = v.m1.values + rng.normal(0, noise / np.sqrt(2), len(v)); m2 = v.m2.values + rng.normal(0, noise / np.sqrt(2), len(v))
            c1 = np.repeat(const.I.values, 12) + rng.normal(0, noise / np.sqrt(2), 12 * len(const)); c2 = np.repeat(const.I.values, 12) + rng.normal(0, noise / np.sqrt(2), 12 * len(const))
            mean = np.r_[(m1 + m2) / 2, (c1 + c2) / 2]; d = np.r_[m2 - m1, c2 - c1]
            wt = np.r_[w.values, np.full(12 * len(const), 1 / 12)]; vi = np.r_[v.VI.values, np.repeat(const.VI.values, 12)]
            rel = mean - tip
            for vimin in (1.2, 1.6, 1.8):
                agb = (rel >= -1) & (rel < 0) & (vi > vimin); rgb = (rel >= 0) & (rel < 0.5) & (vi > vimin)
                f = lambda sel, x: float((wt[sel] * (np.abs(d[sel]) > x)).sum() / wt[sel].sum())
                rows.append(dict(cloud=cloud, noise=noise, lag=lag, vi_min=vimin, n_agb=round(float(wt[agb].sum())), n_rgb=round(float(wt[rgb].sum())),
                                 f03_agb=f(agb, 0.3), f03_rgb=f(rgb, 0.3), E03=f(agb, 0.3) - f(rgb, 0.3), E02=f(agb, 0.2) - f(rgb, 0.2), E05=f(agb, 0.5) - f(rgb, 0.5)))
    print(cloud, "variables with light curves:", var.star.nunique(), "constants:", len(const), "dropped (no usable light curve):", len(nolc))
df = pd.DataFrame(rows); df.to_csv(HERE / "work/reference_real.csv", index=False)
pd.set_option("display.width", 200)
print(df[(df.noise == 0.03) & (df.vi_min == 1.2)].round(4).to_string(index=False))
s = df.groupby(["cloud", "noise", "vi_min"])[["f03_agb", "f03_rgb", "E03", "E02", "E05"]].mean().round(4); print(s)
# star-level bootstrap error of E03 is ~0.002 (referee A3); spread over lags:
print(df[(df.vi_min == 1.2)].groupby(["cloud", "noise"]).E03.agg(["mean", "std"]).round(4)); print("sinusoid reference:", sin.round(4).to_dict())
