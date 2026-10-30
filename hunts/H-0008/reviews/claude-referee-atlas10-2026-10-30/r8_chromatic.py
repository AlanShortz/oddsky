"""r8: achromaticity / shape test. Take the default parallax-lens profile (r3) as a template; for each series refit only its
amplitude separately in phases (rise: t < t0 - teff_window, peak, decline). A lens gives the same amplitude in every phase
for every series; a colour change (nova, CV, YSO, Be) shows as a phase-dependent amplitude ratio between bands.
Also: the c/o excess ratio night by night (o interpolated to the c nights) where both exist."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA  # noqa: E402

TPK = {"J163539": 57980.0, "J075219": 58208.0, "J174440": 60010.0, "J191120": 59294.0, "J173150": 58311.0}
for k, tpk in TPK.items():
    p = os.path.join(DATA, f"r3_{k}_series.csv")
    if not os.path.exists(p):
        print(k, "no r3 series yet")
        continue
    s = pd.read_csv(p)
    js = json.load(open(os.path.join(DATA, f"r3_{k}.json")))["default"]["res"]["parallax"]
    t0, te, u0 = js["p"][:3]
    amp = js["amp"]
    hw = max(abs(u0) * te * 3, 5.0)
    print(f"== {k}: parallax t0 {t0:.1f} tE {te:.1f} u0 {u0:+.4f}; phases: rise t<t0-{hw:.0f} d, peak |dt|<{hw:.0f} d, decline")
    for g, d in s.groupby("g"):
        if abs(amp[g]) < 1e-12:
            continue
        P = d.m_parallax.values / amp[g]  # template (A-1) incl. parallax
        out = []
        for name, m in (("rise", d.t < t0 - hw), ("peak", np.abs(d.t - t0) <= hw), ("decline", (d.t > t0 + hw) & (d.t < t0 + 3 * te))):
            m = m.values & (P > 0.05)
            if m.sum() < 1:
                out.append(f"{name}: -")
                continue
            w = 1 / d.e.values[m] ** 2
            a = np.sum(w * P[m] * d.d.values[m]) / np.sum(w * P[m] ** 2)
            ae = 1 / np.sqrt(np.sum(w * P[m] ** 2))
            out.append(f"{name}: {a / amp[g]:.2f}+-{ae / abs(amp[g]):.2f} (n {m.sum()})")
        print(f"   {g:14s} amplitude / global amplitude  " + "  ".join(out))
    c = s[s.g.str.startswith("ATLAS_c")]
    o = s[s.g.str.startswith("ATLAS_o")].sort_values("t")
    ev = c[np.abs(c.t - t0) < 2 * te]
    rows = []
    for _, r in ev.iterrows():
        near = o[np.abs(o.t - r.t) < 4]
        if len(near) == 0:
            continue
        oi = np.interp(r.t, near.t, near.d) if len(near) > 1 else near.d.iloc[0]
        oe = near.e.mean()
        if oi > 3 * oe:
            rows.append((r.t - t0, r.d / oi, np.hypot(r.e / oi, r.d * oe / oi**2)))
    if rows:
        print("   c/o excess ratio by night (dt, ratio): " + "  ".join(f"{a:+.0f}:{b:.2f}+-{e:.2f}" for a, b, e in rows))
