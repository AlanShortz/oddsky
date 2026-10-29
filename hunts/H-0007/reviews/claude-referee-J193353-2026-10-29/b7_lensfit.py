"""b7: point-lens (Paczynski) fits to NEOWISE exposures + ZTF (catflags = 0, field 285) for J193353. Own code (scipy), outside the
Oddsky tools. Variants: all data; NEOWISE only; ZTF only; without the moon-masked Apr 14 exposure; blending free per survey.
Profile in tE. Reads /tmp/j1933ref/target_exp.parquet (b1) and hunts/H-0007/work/ztf_J193353.csv.
Optional argv[1]: csv with per-epoch ZTF comparison-star offsets (columns mjd, filtercode, zoff) to subtract (from b9)."""
import sys

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

t = pd.read_parquet("/tmp/j1933ref/target_exp.parquet")
t = t[(t.nb == 1) & (t.qual_frame > 0)]
base1 = t[t.visit != 11].groupby("visit").w1mpro.median().median()
base2 = t[t.visit != 11].groupby("visit").w2mpro.median().median()
rows = []
for b, base, sig in [("W1", base1, "w1sigmpro"), ("W2", base2, "w2sigmpro")]:
    m = t[f"{b.lower()}mpro"]
    e = np.hypot(t[sig].fillna(0.1), 0.035 if b == "W1" else 0.08)  # per-exposure scatter floor from baseline visits
    rows.append(pd.DataFrame(dict(mjd=t.mjd, band=b, f=10 ** (-0.4 * (m - base)), e=e * 0.921 * 10 ** (-0.4 * (m - base)), moon=t.moon_masked.astype(str) == "11")))
z = pd.read_csv("hunts/H-0007/work/ztf_J193353.csv")
z = z[(z.catflags == 0) & (z.field == 285) & z.filtercode.isin(["zg", "zr"])].copy()
z["d"] = z.mag - z.groupby("filtercode").mag.transform("median")
if len(sys.argv) > 1:
    off = pd.read_csv(sys.argv[1])
    z = z.merge(off, on=["mjd", "filtercode"], how="left")
    z["d"] = z.d - z.zoff.fillna(0)
    print("ZTF offsets applied for", z.zoff.notna().sum(), "epochs")
ze = np.hypot(z.magerr, 0.012)
rows.append(pd.DataFrame(dict(mjd=z.mjd, band=z.filtercode.str[-1], f=10 ** (-0.4 * z.d), e=ze * 0.921 * 10 ** (-0.4 * z.d), moon=False)))
D = pd.concat(rows, ignore_index=True)
D = D[(D.mjd > 58400) & (D.mjd < 59600)].reset_index(drop=True)  # 2018 Oct - 2022 Jan: two seasons either side
print("points:", D.band.value_counts().to_dict())


def A(tt, t0, tE, u0):
    u = np.sqrt(u0 ** 2 + ((tt - t0) / tE) ** 2)
    return (u ** 2 + 2) / (u * np.sqrt(u ** 2 + 4))


def model(p, d, blend):
    t0, ltE, u0 = p[:3]
    a = A(d.mjd.values, t0, 10 ** ltE, abs(u0))
    if not blend:
        return a
    fs = np.ones(len(d))
    fs[d.band.isin(["W1", "W2"]).values] = p[3]
    fs[d.band.isin(["g", "r"]).values] = p[4]
    return fs * a + 1 - fs


def fit(d, blend=False, p0=(58930, np.log10(60), 0.4), fix_tE=None):
    def res(p):
        q = np.r_[p[0], np.log10(fix_tE), p[1:]] if fix_tE else p
        return (d.f.values - model(q, d, blend)) / d.e.values
    best = None
    for t0 in np.arange(58880, 59011, 10):
        for u0 in [0.05, 0.2, 0.4, 0.6]:
            for ltE in ([None] if fix_tE else [1.3, 1.6, 1.9, 2.2]):
                x0 = [t0, u0] if fix_tE else [t0, ltE, u0]
                if blend:
                    x0 += [1.0, 1.0]
                lb = [58700, 0] if fix_tE else [58700, 0.3, 0]
                ub = [59015, 3] if fix_tE else [59015, 3.0, 3]
                if blend:
                    lb += [0.05, 0.05]
                    ub += [1.0, 1.0]
                r = least_squares(res, x0, bounds=(lb, ub))
                if best is None or r.cost < best.cost:
                    best = r
    return best, 2 * best.cost


def report(lab, d, blend=False):
    r, chi = fit(d, blend)
    p = r.x
    print(f"{lab:38s} chi2={chi:7.1f} n={len(d):3d}  t0={p[0]:.1f} tE={10**p[1]:.1f} u0={abs(p[2]):.3f} Amax={A(p[0], p[0], 10**p[1], abs(p[2])):.2f}"
          + (f" fsW={p[3]:.2f} fsZ={p[4]:.2f}" if blend else ""))
    return r


r_all = report("all (NEOWISE + ZTF g,r)", D)
report("all, no moon-masked Apr 14", D[~D.moon])
report("NEOWISE only", D[D.band.isin(["W1", "W2"])])
report("ZTF only", D[D.band.isin(["g", "r"])])
report("all, blending free", D, blend=True)
# residuals of best fit at key epochs
p = r_all.x
D["mod"] = model(p, D, False)
D["pull"] = (D.f - D["mod"]) / D.e
key = D[(D.mjd > 58940) & (D.mjd < 59160)].copy()
key["grp"] = key.band + "_" + np.floor(key.mjd).astype(int).astype(str)
print(key.groupby("grp").agg(mjd=("mjd", "mean"), n=("f", "size"), f=("f", "mean"), mod=("mod", "mean"), pull=("pull", "mean")).sort_values("mjd").round(3).to_string())
print("chi2 contributions: NEOWISE event", (D.pull[(D.band.isin(['W1', 'W2'])) & (D.mjd.between(58940, 58960))] ** 2).sum().round(1),
      " ZTF 2020", (D.pull[(D.band.isin(['g', 'r'])) & (D.mjd.between(59000, 59160))] ** 2).sum().round(1))
print("tE profile (all data):")
for tE in [20, 30, 40, 50, 60, 80, 100, 130, 170, 220]:
    r, chi = fit(D, fix_tE=tE)
    print(f"  tE={tE:4d}  chi2={chi:7.1f}  t0={r.x[0]:.1f} u0={abs(r.x[1]):.3f}")
print("t0 profile (all data, tE and u0 free):")
for T0 in [58900, 58920, 58930, 58940, 58945, 58949.4, 58955, 58960, 58970, 58985, 59000]:
    def res(p, T0=T0):
        return (D.f.values - model(np.r_[T0, p], D, False)) / D.e.values
    best = min((least_squares(res, [lt, u], bounds=([0.3, 0], [3, 3])) for lt in [1.4, 1.7, 2.0] for u in [0.1, 0.4, 0.8]), key=lambda r: r.cost)
    print(f"  t0={T0:8.1f}  chi2={2*best.cost:7.1f}  tE={10**best.x[0]:.1f} u0={abs(best.x[1]):.3f}")
# in-visit slope, W1 and W2 jointly, clean exposures of the Apr 9-10 visit only
v = t[(t.visit == 11) & (t.mjd < 58951)]
for b in ["w1mpro", "w2mpro"]:
    p, cov = np.polyfit(v.mjd - v.mjd.mean(), v[b], 1, cov=True)
    print(f"{b} slope within Apr 9-10 (nb=1, qual_frame>0, n={len(v)}): {p[0]:+.3f} +- {np.sqrt(cov[0, 0]):.3f} mag/d")
