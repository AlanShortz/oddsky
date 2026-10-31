"""r1: re-reduction of the ATLAS forced photometry (reduced images) for J175634 and J174744.

 - cuts and what a fixed chi/N<10 cut would remove near the peak vs in the baseline;
 - per unit/band yearly baseline medians (|dt| > 400 d), PSF major axis, mag5sig, chi/N;
 - PSF-width regression of the baseline (fractional flux per px of major axis, zero point per unit);
 - nightly per-unit series around the event, ratio to that unit's own baseline;
 - writes data/r1_nightly_<k>.csv (all nights, both bands) for later scripts.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, atlas_raw, clean, mjd2date, nightly, ujy2ab  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)

for k in KEYS:
    print("=" * 40, k)
    raw = atlas_raw(k)
    r0 = raw[(raw.err == 0) & (raw.dujy > 0)]
    print(f"raw c/o rows {len(raw)}; err==0 & dujy>0: {len(r0)}; mag5sig<=17.5 removes {(r0.mag5sig <= 17.5).sum()}")
    # peak (nightly o max from the rel-chi reduction)
    nt = nightly(clean(raw))
    o = nt[nt.F == "o"]
    seas = o[(o.t > 59500) & (o.t < 59800)]
    tpk = float(seas.t.iloc[np.argmax(seas.ujy.values)])
    print(f"brightest o night 2021-22: MJD {tpk:.2f} ({mjd2date(tpk)})  {seas.ujy.max():.0f} uJy = {ujy2ab(seas.ujy.max()):.2f} AB")
    near = np.abs(r0.mjd - tpk) < 100
    far = np.abs(r0.mjd - tpk) > 400
    a = r0[r0.mag5sig > 17.5]
    for lab, m in (("|dt|<100", np.abs(a.mjd - tpk) < 100), ("|dt|<20", np.abs(a.mjd - tpk) < 20), ("|dt|>400", np.abs(a.mjd - tpk) > 400)):
        print(f"  fixed chi/N<10 removes {np.mean(a.chi_n[m] >= 10) * 100:5.1f}% of {m.sum()} rows at {lab}; "
              f"my flux-scaled cut removes {100 * (1 - len(clean(a[m].copy())) / max(m.sum(), 1)):5.1f}% "
              f"(computed on that subset only; global cut below)")
    rc = clean(raw)
    m = np.abs(rc.mjd - tpk) < 20
    print(f"  global flux-scaled cut keeps {len(rc)} of {len(a)} rows; within 20 d of peak keeps {m.sum()} of "
          f"{(np.abs(a.mjd - tpk) < 20).sum()}")

    # yearly baseline per unit/band
    nt["yr"] = np.floor(2000 + (nt.t - 51544.5) / 365.25).astype(int)
    b = nt[np.abs(nt.t - tpk) > 400]
    g = b.groupby(["F", "cam", "yr"]).agg(n=("ujy", "size"), med=("ujy", "median"), rob=("ujy", lambda x: 1.4826 * np.median(np.abs(x - np.median(x)))),
                                          maj=("maj", "median"), m5=("m5", "median"), chi=("chi", "median"))
    ref = b[b.t > 60300].groupby(["F", "cam"]).ujy.median()  # 2024-26 reference
    g["rel_2024_26"] = [row.med / ref.get((F, cam), np.nan) for (F, cam, yr), row in g.iterrows()]
    print("\nYearly baseline (nights > 400 d from peak):")
    print(g.round(3).to_string())
    print("\nPer unit/band baseline medians (all |dt|>400):")
    print(b.groupby(["F", "cam"]).agg(n=("ujy", "size"), med=("ujy", "median"), maj=("maj", "median"), chi=("chi", "median")).round(2).to_string())

    # PSF-width regression per band, zero point per unit (fractional)
    print("\nBaseline flux vs PSF major axis (zero point per unit; slope as fraction of unit median per px):")
    for F, d in b.groupby("F"):
        cams = sorted(d.cam.unique())
        X = np.zeros((len(d), len(cams) + 1))
        for i, c in enumerate(d.cam.values):
            X[i, cams.index(c)] = 1
        X[:, -1] = d.maj.values - 2.4
        y = d.ujy.values
        keep = np.ones(len(y), bool)
        for _ in range(4):
            p, *_ = np.linalg.lstsq(X[keep], y[keep], rcond=None)
            res = y - X @ p
            s = 1.4826 * np.median(np.abs(res[keep]))
            keep = np.abs(res) < 4 * s
        J = X[keep]
        cov = np.linalg.inv(J.T @ J) * s**2
        zp = np.median(p[:-1])
        print(f"  {F}: slope {p[-1]:+.1f} +- {np.sqrt(cov[-1, -1]):.1f} uJy/px = {p[-1] / zp * 100:+.2f}%/px of {zp:.0f} uJy "
              f"(n {keep.sum()}, maj range {d.maj.min():.1f}-{d.maj.max():.1f}); unit zps {dict(zip(cams, np.round(p[:-1])))}")

    # event nights
    ev = nt[np.abs(nt.t - tpk) < 150].copy()
    bm = b.groupby(["F", "cam"]).ujy.median()
    ev["base"] = [bm.get((F, c), np.nan) for F, c in zip(ev.F, ev.cam)]
    ev["ratio"] = ev.ujy / ev.base
    ev["dt"] = ev.t - tpk
    ev["date"] = [mjd2date(t) for t in ev.t]
    ev["mag"] = ujy2ab(np.clip(ev.ujy, 1, None))
    print("\nNights within 150 d of the peak:")
    print(ev[["date", "dt", "F", "cam", "n", "nraw", "ujy", "ujy_err", "base", "ratio", "mag", "maj", "m5", "chi", "sky"]]
          .sort_values("dt").round(2).to_string(index=False))
    nt.drop(columns="yr").to_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"), index=False)
    print(f"\npeak MJD {tpk:.2f}")
