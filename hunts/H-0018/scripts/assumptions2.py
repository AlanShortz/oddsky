"""Perspective on real geometry, at higher power: comoving pairs with a distance difference and no orbit."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
import wb  # noqa: E402

rng = np.random.default_rng(91)
s = wb.load(f"{hd.RUNS}/data/elbadry/cat.parquet", True)
e1, n1 = wb.basis(s.ra1.values, s.dec1.values)
e2, n2 = wb.basis(s.ra2.values, s.dec2.values)
d1 = 1000 / s.parallax1.values
gal_to_icrs = hd.gal_vectors  # n only; the solar reflex below is given in ICRS (apex near RA 270, Dec 30)
apex = wb.unit(np.array([270.0]), np.array([30.0]))[0]
for label, sd_pc, ordered in [("isotropic V, dd 0.5 pc", 0.5, 0.0), ("isotropic V, dd 5 pc", 5.0, 0.0), ("solar reflex + isotropic, dd 5 pc", 5.0, 18.0)]:
    ys, ns = [], []
    for it in range(6):
        V = rng.normal(0, 25, (len(s), 3)) - ordered * apex
        dd = rng.normal(0, sd_pc, len(s))
        pm = lambda e_, n_, dist: np.column_stack([(V * e_).sum(1), (V * n_).sum(1)]) / 4.74047 / dist[:, None] * 1000
        p1, p2 = pm(e1, n1, d1), pm(e2, n2, d1 + dd)
        m = s.copy()
        m["pmra1"], m["pmdec1"], m["pmra2"], m["pmdec2"] = p1[:, 0], p1[:, 1], p2[:, 0], p2[:, 1]
        z, sig, nn = wb.rotation(m)
        k = np.abs(z) > 3 * sig
        ys.append(np.sign(z[k]))
        ns.append(nn[k])
    print(hd.fmt("   " + label, hd.fit_dipole(np.concatenate(ys), np.concatenate(ns))))
