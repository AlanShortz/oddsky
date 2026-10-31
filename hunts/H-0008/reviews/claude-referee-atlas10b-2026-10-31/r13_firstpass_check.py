"""r13: the first-pass J175634 parallax solution (tE 92.5 d, u0 0.02, fs 0.07) in my reduction: parallax fit with tE fixed at
92.5 d (piE free within +-5), and the size of piE it needs; and the static/parallax fits with |piE| <= 1 (physical range for
a disc/bulge lens of a bulge source)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import Fitter, build  # noqa: E402
from lib import targets  # noqa: E402

T = targets()["J175634"]
df, info = build("J175634", T, 59661.3)
F = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=59661)
best = F.fit("static", 59662.0)
for te in (12.0, 30.0, 92.5):
    r = F.fit("parallax", 59662.0, fixed={1: te})
    p = r["p"]
    print(f"parallax, tE fixed {te}: chi2 {r['chi2']:.1f} (static best {best['chi2']:.1f}) u0 {p[2]:+.4f} piE ({p[3]:+.2f},{p[4]:+.2f}) "
          f"|piE| {np.hypot(p[3], p[4]):.2f} fs o_04a {r['amp']['ATLAS_o_04a'] / info['ATLAS_o_04a']['base']:.2f} W1 {r['amp']['NEOWISE_W1']:.2f}")
# parallax with |piE| <= 1 via fixed grid of piE
best_c = None
for pn in np.linspace(-1, 1, 9):
    for pe in np.linspace(-1, 1, 9):
        if np.hypot(pn, pe) > 1:
            continue
        r = F.fit("static", 59662.0) if False else F.fit("parallax", 59662.0, fixed={3: pn, 4: pe})
        if best_c is None or r["chi2"] < best_c["chi2"]:
            best_c = r
p = best_c["p"]
print(f"parallax with |piE|<=1 (grid): chi2 {best_c['chi2']:.1f} vs static {best['chi2']:.1f}: dchi2 {best['chi2'] - best_c['chi2']:+.1f}; "
      f"tE {p[1]:.1f} u0 {p[2]:+.3f} piE ({p[3]:+.2f},{p[4]:+.2f})")
