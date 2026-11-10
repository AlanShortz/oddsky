"""The Magellanic Cloud reference for the preregistered statistic, built the way the Hubble measurement is built:
two visits at random phases, boxes placed on the two-visit mean magnitude, Gaussian noise added, RGB control subtracted.

Writes work/reference.csv. Usage: 05_compare.py [noise_mag=0.03]
"""
import sys, pathlib
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parents[1]
NOISE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.03
rng = np.random.default_rng(1905)
REP = 60


def simulate(pop, lag):
    n = len(pop)
    m1 = np.tile(pop.I.values, (REP, 1)); m2 = m1.copy()
    for k in "123":
        P, A = pop["P" + k].values, pop["A" + k].fillna(0).values
        P = np.where(np.isfinite(P) & (P > 0), P, 1.0)
        ph = rng.uniform(0, 2 * np.pi, (REP, n))
        m1 += A / 2 * np.sin(ph); m2 += A / 2 * np.sin(ph + 2 * np.pi * lag / P)
    m1 += rng.normal(0, NOISE / np.sqrt(2), m1.shape); m2 += rng.normal(0, NOISE / np.sqrt(2), m2.shape)
    return (m1 + m2) / 2, m2 - m1


rows = []
for cloud, tip in (("lmc", 14.60), ("smc", 15.00)):
    pop = pd.read_csv(HERE / f"work/{cloud}_population.csv")
    for dtip in (-0.1, 0.0, 0.1):
        for lag in (150, 400, 1000, 3000):
            mean, d = simulate(pop, lag)
            rel = mean - (tip + dtip)
            a = np.abs(d)
            r = dict(cloud=cloud, dtip=dtip, lag=lag)
            for box, (lo, hi) in {"agb": (-1, 0), "agb_bright": (-2, -1), "rgb": (0, 0.5)}.items():
                sel = (rel >= lo) & (rel < hi)
                r["n_" + box] = int(sel.sum() / REP)
                for x in (0.2, 0.3, 0.5):
                    r[f"f{int(x*10):02d}_{box}"] = float(a[sel].mean() if False else (a[sel] > x).mean())
            for x in ("02", "03", "05"):
                r["E" + x] = r[f"f{x}_agb"] - r[f"f{x}_rgb"]; r["Eb" + x] = r[f"f{x}_agb_bright"] - r[f"f{x}_rgb"]
            rows.append(r)
df = pd.DataFrame(rows); df.to_csv(HERE / "work/reference.csv", index=False)
pd.set_option("display.width", 220)
print(df[df.dtip == 0][["cloud", "lag", "n_agb", "n_rgb", "f03_agb", "f03_rgb", "E02", "E03", "E05", "Eb03"]].round(4).to_string(index=False))
print(df.groupby(["cloud", "dtip"])[["E02", "E03", "E05", "Eb03"]].mean().round(4))
