"""r9: any other brightening 2015-2026 (outside |t - peak| < 300 d)? 20-day bins of the PSF-corrected ATLAS o and c (per-unit
normalised to the 2023-26 median), ZTF, NEOWISE; the largest binned excess. Lomb-Scargle on the ATLAS o baseline (LPV test)."""
import os
import sys

import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import build  # noqa: E402
from lib import TARGETS  # noqa: E402

for k, T in TARGETS.items():
    df = build(k, window=(57000, 61500), psf_corr=True, base_dt=300, min_base=5)
    df["band"] = np.where(df.g.str.startswith("NEOWISE"), df.g, df.g.str.rsplit("_", n=1).str[0])
    off = df[np.abs(df.t - T["tpk"]) > 300].copy()
    off["bin"] = np.floor(off.t / 20)
    print("==", k, f"{len(off)} off-event points 2015-2026")
    for b, d in off.groupby("band"):
        g = d.groupby("bin").agg(t=("t", "mean"), f=("f", "mean"), n=("f", "size"), e=("e", lambda e: np.sqrt(np.sum(e**2)) / len(e)))
        g = g[g.n >= 3] if not b.startswith("NEOWISE") else g
        if g.empty:
            continue
        j = g.f.idxmax()
        print(f"  {b:12s} {len(g):3d} bins: brightest bin {g.f[j]:.3f} at MJD {g.t[j]:.0f} ({(g.f[j] - 1) / g.e[j]:.1f} sigma formal); "
              f"bins > 1.10: {(g.f > 1.10).sum()}; rms of bins {g.f.std():.3f}")
    o = off[off.band == "ATLAS_o"]
    o = o[o.t > 58000]  # after the 02a PSF fix
    ls = LombScargle(o.t, o.f, o.e)
    fr, pw = ls.autopower(minimum_frequency=1 / 1000, maximum_frequency=1 / 5, samples_per_peak=10)
    j = np.argmax(pw)
    amp = np.sqrt(pw[j]) * o.f.std() * np.sqrt(2)
    print(f"  LS ATLAS o 2018-2026 off-event: best period {1 / fr[j]:.1f} d, power {pw[j]:.3f}, FAP {ls.false_alarm_probability(pw[j]):.2g}, "
          f"approx semi-amplitude {amp:.3f} (flux ratio)")
