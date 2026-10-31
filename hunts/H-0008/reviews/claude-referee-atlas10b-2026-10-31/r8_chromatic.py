"""r8: chromaticity. For every ATLAS c night in the event, the fractional excess (flux/own baseline - 1) compared with the o
fractional excess interpolated (log-linear in excess) from o nights within 3 d on both sides (any unit; each o night divided
by its own unit's baseline). For a lens with equal blend fractions the ratio is 1 at every phase; a hot added component
(CV/nova/flare/Be disc) raises c far more than o (on a star with c-o = 1.45, a flat-F_nu adder gives a ratio ~ 3.8).
Also the excess colour: delta_c / delta_o in uJy vs the baseline c/o flux ratio."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, mjd2date  # noqa: E402

pd.set_option("display.width", 250)
TP = {"J175634": 59661.3, "J174744": 59654.4}
for k in KEYS:
    nt = pd.read_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"))
    b = nt[np.abs(nt.t - TP[k]) > 400].groupby(["F", "cam"]).ujy.median()
    nt["base"] = [b[(F, c)] for F, c in zip(nt.F, nt.cam)]
    nt["x"] = nt.ujy / nt.base - 1
    nt["xe"] = nt.ujy_err / nt.base
    o = nt[nt.F == "o"].sort_values("t")
    c = nt[(nt.F == "c") & (np.abs(nt.t - TP[k]) < 300)]
    cbase, obase = b["c"].median(), b["o"].median()
    print(f"== {k}: baseline c/o flux ratio {cbase / obase:.3f} (c-o {-2.5 * np.log10(cbase / obase):.2f} AB)")
    rows = []
    for _, r in c.iterrows():
        bef, aft = o[(o.t <= r.t) & (o.t > r.t - 3)], o[(o.t > r.t) & (o.t < r.t + 3)]
        if not (len(bef) and len(aft)):
            continue
        a, d = bef.iloc[-1], aft.iloc[0]
        f = (r.t - a.t) / (d.t - a.t)
        if a.x > 0.02 and d.x > 0.02:
            xo = np.exp(np.log(a.x) + f * (np.log(d.x) - np.log(a.x)))
        else:
            xo = a.x + f * (d.x - a.x)
        xo_lin = a.x + f * (d.x - a.x)
        rows.append((mjd2date(r.t), round(r.t - TP[k], 1), r.cam, round(r.x, 3), round(r.xe, 3), round(xo, 3), round(xo_lin, 3),
                     round(r.x / xo, 2) if abs(xo) > 0.03 else np.nan, round(min(a.x, d.x), 3), round(max(a.x, d.x), 3),
                     f"{a.cam}@{a.t - r.t:+.1f} {d.cam}@{d.t - r.t:+.1f}"))
    df = pd.DataFrame(rows, columns=["date", "dt", "c unit", "c frac.exc", "err", "o interp (log)", "o interp (lin)", "c/o ratio",
                                     "o min", "o max", "o nights"])
    print(df.to_string(index=False))
    ok = df["c/o ratio"].notna() & (df["o interp (log)"] > 0.05)
    if ok.sum():
        print(f"  c/o fractional-excess ratio over {ok.sum()} nights with o excess > 5%: median {df['c/o ratio'][ok].median():.2f}, "
              f"range {df['c/o ratio'][ok].min():.2f}-{df['c/o ratio'][ok].max():.2f}")
    # binned comparison for J174744: c nights vs a smooth o curve (running median of o in 10-d bins)
    if k == "J174744":
        ev = nt[(nt.t > TP[k] - 60) & (nt.t < TP[k] + 250)]
        print("  10-day running comparison (o smoothed by a local quadratic over +-12 d, all units):")
        for _, r in ev[ev.F == "c"].iterrows():
            w = o[np.abs(o.t - r.t) < 12]
            if len(w) < 4:
                continue
            p = np.polyfit(w.t - r.t, w.x, 2, w=1 / np.maximum(w.xe, 0.005))
            print(f"    {mjd2date(r.t)} dt {r.t - TP[k]:+6.1f} c {r.cam} x_c {r.x:.3f}  x_o(fit) {p[-1]:.3f}  ratio {r.x / p[-1]:.2f}  "
                  f"(n_o {len(w)})")
