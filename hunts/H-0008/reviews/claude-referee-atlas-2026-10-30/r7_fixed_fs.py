"""r7: blending as a prior, not a free nuisance. Gaia DR3 resolves the neighbours (r5): the Gaia target should give ~93% (J180624)
and ~97% (J183040) of the ATLAS forced flux, and the ZTF difference-image centroids sit on the Gaia target (0.12" and 0.09").
Fit the point lens (static and parallax) with ONE common fs fixed at a grid of values in every band, and compare chi2 with the
free-fs fit and with a free symmetric Pearson VII bump (r3). Main reduction (fitlib.build defaults)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import build, shape_fits  # noqa: E402
from lib import TARGETS  # noqa: E402

from oddsky.analysis.lensing import Problem, magnification  # noqa: E402

for k, T in TARGETS.items():
    for label, opts in (("main", {}), ("atlas_only", dict(use_ztf=False, use_neowise=False))):
        df = build(k, **opts)
        # series without data within 150 d of the peak cannot constrain fs; drop them so 'free' is honest
        keep = df.groupby("g").t.transform(lambda t: (np.abs(t - T["tpk"]) < 150).sum() >= 3).astype(bool)
        df = df[keep]
        shp = shape_fits(df, T["tpk"])
        print(f"== {k} {label}: n {len(df)}, series {sorted(df.g.unique())}")
        print(f"   Pearson VII symmetric chi2 {shp['pv7_sym'][0]} (t0, w, m = {shp['pv7_sym'][1][:3]}); Gaussian {shp['gaussian'][0]}")
        for par in (False, True):
            prob = Problem(df.t.values, df.f.values, df.e.values, df.g.values, ra=T["ra"], dec=T["dec"], parallax=par, blend=True, t0par=T["tpk"])
            nl = prob.nlens
            p, c_free = prob.fit(t0c=T["tpk"])
            print(f"   {'parallax' if par else 'static  '} fs free: chi2 {c_free:.1f}  tE {p[1]:.1f} u0 {p[2]:+.3f} fs {np.round(p[nl:], 2).tolist()}"
                  + (f" piE {np.round(p[3:5], 3).tolist()}" if par else ""))
            for fs in (1.0, 0.93, 0.8, 0.6, 0.4):
                fixed = {nl + i: fs for i in range(len(prob.names))}
                q, c = prob.fit(fixed=fixed, t0c=T["tpk"])
                print(f"      fs = {fs:.2f} everywhere: chi2 {c:8.1f} (d = {c - c_free:+7.1f})  t0 {q[0]:.1f} tE {q[1]:6.1f} u0 {q[2]:+.3f} "
                      f"A_max {magnification(np.array([abs(q[2])]))[0]:.2f}" + (f" piE {np.round(q[3:5], 3).tolist()}" if par else ""))
