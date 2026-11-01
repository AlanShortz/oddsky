"""r3c: where the chi-square of the r3 fits comes from (per band, event window vs baseline, worst points), for the five best,
using the best physical static lens (fs<=1). Large baseline chi2 means the error floor is too small or the baseline is variable;
then BIC differences between models are inflated and should be rescaled by chi2/dof.
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r3c_chi2_budget.py"""
import os, sys, warnings
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fitlib import Lens, load_gaia  # noqa: E402
from r3_fits import WIN, C  # noqa: E402
warnings.filterwarnings("ignore")
for sid, win in WIN.items():
    c = C.loc[sid]
    df, base, _ = load_gaia(os.path.join(HERE, "data", "epoch_raw", f"{sid}.csv"), win)
    tpk = float(df[df.g == "G"].t.values[np.argmax(df[df.g == "G"].f.values)])
    L = Lens(df, c.ra, c.dec, parallax=False, fs_max=1.0, t0par=tpk)
    p, chi2 = L.fit(tpk)
    r = (L.model(p) - L.f) / L.e
    df = df.assign(r=r, inside=(df.t > win[0]) & (df.t < win[1]))
    print(f"\n{c['name']}: total chi2 {chi2:.1f} n {len(df)}")
    for (g, ins), x in df.groupby(["g", "inside"]):
        print(f"   {g:2s} {'event' if ins else 'base '} n {len(x):3d} chi2 {np.sum(x.r**2):7.1f}  (|r|>4: {int((np.abs(x.r) > 4).sum())})")
    w = df.reindex(df.r.abs().sort_values(ascending=False).index).head(5)
    print("   worst:", "; ".join(f"{x.g} {x.t:.1f} F {x.f:.3f} r {x.r:+.1f}" for x in w.itertuples()))
