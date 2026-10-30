"""r8: chromaticity without leaning on blending. Each band fitted ALONE (point lens with free fs per series, and a free symmetric
Pearson VII bump): if the event is achromatic in the source, t0 and the shape (t_eff = |u0| tE; PV7 width) agree between bands,
whatever the per-band blend. Intrinsic outbursts (YSO, Be, nova, symbiotic, CV) peak earlier/narrower in the blue.
Also: the source's own colour from fs x baseline flux per band, against the Gaia target's colour."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import build, shape_fits  # noqa: E402
from lib import TARGETS  # noqa: E402

from oddsky.analysis.lensing import Problem, profile_range  # noqa: E402

for k, T in TARGETS.items():
    df = build(k)
    df["band"] = np.where(df.g.str.startswith("NEOWISE"), "NEOWISE", df.g.str.rsplit("_", n=1).str[0])
    print("==", k)
    for b, d in df.groupby("band"):
        if (np.abs(d.t - T["tpk"]) < 60).sum() < 4 or b == "NEOWISE":
            continue
        d = d[d.groupby("g").t.transform(lambda t: (np.abs(t - T["tpk"]) < 150).sum() >= 3).astype(bool)]
        prob = Problem(d.t.values, d.f.values, d.e.values, d.g.values, blend=True)
        p, c = prob.fit(t0c=T["tpk"])
        lo, hi, _ = profile_range(prob, p, c, 0, 15.0)
        sh = shape_fits(d, T["tpk"])
        teff = abs(p[2]) * p[1]
        print(f"  {b:8s} n {len(d):4d}  lens: t0 {p[0]:.1f} [{lo:.1f}, {hi:.1f}] tE {p[1]:6.1f} u0 {p[2]:.3f} t_eff {teff:5.1f} d "
              f"fs {np.round(p[3:], 2).tolist()} | PV7: t0 {sh['pv7_sym'][1][0]:.1f} w {sh['pv7_sym'][1][1]:.1f} m {sh['pv7_sym'][1][2]:.2f} | "
              f"rise/fall tE {sh['lens_asym'][1][1]:.0f}/{sh['lens_asym'][1][2]:.0f}", flush=True)
