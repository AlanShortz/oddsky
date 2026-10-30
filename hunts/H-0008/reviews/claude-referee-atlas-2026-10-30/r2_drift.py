"""r2: is J180624's 2015-2019 ATLAS rise real? Tests:
 (a) baseline nights (|t - peak| > 400 d) regressed on PSF width (maj) with a zero point per band+unit, then on time;
 (b) same-night pairs of units 01a and 02a (o band) in 2017-2019, when their PSFs differed;
 (c) J183040 (13 deg away, also very red) as a comparison star for any colour-dependent calibration trend;
 (d) NEOWISE W1/W2 and ZTF yearly medians."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import HERE, TARGETS, neowise, ztf  # noqa: E402

pd.set_option("display.width", 250)


def regress(nt, tpk, label):
    b = nt[np.abs(nt.t - tpk) > 400].copy()
    b["key"] = b.F + "_" + b.cam
    ref = b[b.t > 60300].groupby("key").ujy.median()
    b = b[b.key.isin(ref.index)]
    b["y"] = 2.5 * np.log10(b.ujy / b.key.map(ref).values)  # mag-like, brighter = positive
    b["w"] = 1 / np.hypot(1.0857 * b.ujy_err / b.ujy, 0.02) ** 2
    b["yr"] = (b.t - 59000) / 365.25
    keys = sorted(b.key.unique())
    X0 = np.array([[1.0 if kk == k else 0.0 for kk in keys] for k in b.key])
    out = {}
    for name, extra in [("offsets only", []), ("+ maj (per band)", ["maj_c", "maj_o"]), ("+ maj + time (per band)", ["maj_c", "maj_o", "yr_c", "yr_o"]),
                        ("+ time only", ["yr_c", "yr_o"])]:
        cols = [X0]
        for e in extra:
            v, band = e.split("_")
            x = (b.maj - 2.4).values if v == "maj" else b.yr.values
            cols.append((x * (b.F == band).values)[:, None])
        X = np.hstack(cols)
        W = np.sqrt(b.w.values)
        beta, *_ = np.linalg.lstsq(X * W[:, None], b.y.values * W, rcond=None)
        res = b.y.values - X @ beta
        chi2 = float(np.sum(res**2 * b.w.values))
        cov = np.linalg.inv((X * b.w.values[:, None]).T @ X) * chi2 / (len(b) - X.shape[1])
        sl = {e: (round(float(beta[len(keys) + i]), 4), round(float(np.sqrt(cov[len(keys) + i, len(keys) + i])), 4)) for i, e in enumerate(extra)}
        out[name] = (round(chi2, 1), len(b) - X.shape[1], sl)
        print(f"  {label} {name:26s} chi2 {chi2:8.1f} / {len(b) - X.shape[1]}  slopes (mag per px or per yr; +=brighter): {sl}")
        if name == "+ maj (per band)":
            b["res"] = res
            print("    residual yearly medians after the PSF term (mmag), per band:")
            b["season"] = np.floor(2000 + (b.t - 51544.5) / 365.25).astype(int)
            print((b.groupby(["F", "season"]).res.median() * 1000).round(0).unstack(0).to_string())
    return out


for k, T in TARGETS.items():
    print("=" * 30, k)
    nt = pd.read_csv(os.path.join(HERE, f"r1_nightly_{k}.csv"))
    regress(nt, T["tpk"], k)
    # (b) same-night pairs
    o = nt[(nt.F == "o") & (nt.t < 59000)]
    a = o[o.cam == "01a"].set_index("night")
    c = o[o.cam == "02a"].set_index("night")
    j = a.join(c, lsuffix="_1", rsuffix="_2", how="inner")
    ref1 = nt[(nt.F == "o") & (nt.cam == "01a") & (nt.t > 60300)].ujy.median()
    ref2 = nt[(nt.F == "o") & (nt.cam == "02a") & (nt.t > 60300)].ujy.median()
    j["d"] = 2.5 * np.log10((j.ujy_1 / ref1) / (j.ujy_2 / ref2))
    j["dmaj"] = j.maj_1 - j.maj_2
    j["season"] = np.floor(2000 + (j.t_1 - 51544.5) / 365.25).astype(int)
    print(f"  same-night o pairs 01a vs 02a before 2020: n={len(j)}; per season median (01a - 02a, mag, +=01a brighter) and maj difference:")
    print(j.groupby("season").agg(n=("d", "size"), dmag=("d", "median"), dmaj=("dmaj", "median")).round(3).to_string())
    if len(j) > 5:
        p = np.polyfit(j.dmaj, j.d, 1)
        print(f"  pairs: dmag = {p[0]:.3f} * dmaj + {p[1]:.3f}  (corr {np.corrcoef(j.dmaj, j.d)[0, 1]:.2f})")
    # (d) NEOWISE and ZTF yearly
    n = neowise(k)
    n["season"] = np.floor(2000 + (n.t - 51544.5) / 365.25).astype(int)
    n["m"] = -2.5 * np.log10(n.fl)
    print("  NEOWISE per-visit mag minus 2014-2021 median (excluding 2022-23):")
    base = n[(n.t < 59600)]
    for bnd in ("W1", "W2"):
        d = n[n.band == bnd]
        med = base[base.band == bnd].m.median()
        print(f"    {bnd}: " + " ".join(f"{int(s)}:{v:+.3f}" for s, v in zip(d.season, d.m - med, strict=True)))
        early, late = d[(d.t < 57900)].m, d[(d.t > 58300) & (d.t < 59600)].m
        print(f"    {bnd} 2014-2017.3 mean {early.mean() - med:+.3f} vs 2018.5-2021 mean {late.mean() - med:+.3f}; diff {late.mean() - early.mean():+.3f} "
              f"+- {np.hypot(early.std() / np.sqrt(len(early)), late.std() / np.sqrt(len(late))):.3f}")
    z = ztf(k)
    z["season"] = np.floor(2000 + (z.t - 51544.5) / 365.25).astype(int)
    z = z[np.abs(z.t - T["tpk"]) > 300]
    z["m"] = -2.5 * np.log10(z.fl)
    print("  ZTF (catflags 0) season medians away from the event (mag), nights:")
    print(z.groupby(["band", "field", "season"]).agg(n=("m", "size"), m=("m", "median")).round(3).to_string())
