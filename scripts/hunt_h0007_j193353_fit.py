"""H-0007: point-lens fit to the ATLAS light curve of J193353.06-211813.4 (task 5271652), checked against NEOWISE and ZTF.

ATLAS frames are binned per night and band (median of flux / band baseline; baseline = 2015-2019 Oct and 2020 Nov onward). Nights
below 0.8x (dropouts) are removed; errors are the baseline night-to-night scatter plus 1% of flux. No blending, no parallax.
The NEOWISE visit (2020 Apr 9-10, x1.98) and the comparison-corrected ZTF tail (referee: -0.17 mag Jun 18, -0.09 Jul 14-21) are
not fitted; they are predicted.
usage: hunt_h0007_j193353_fit.py ATLAS_TXT OUT_CSV

CAUTION (second referee, hunts/H-0007/reviews/claude-referee-J193353-atlas-2026-10-29.md): without parallax this model leaves a
rise/decline asymmetry, so its t0, tE and u0 are biased and its covariance errors are too small (the peak is unsampled). Quote
the referee's parallax ranges (t0 2020 Mar 17-22, tE 40-55 d), not this script's.
"""

import sys

import numpy as np
from astropy.time import Time
from scipy.optimize import least_squares

from oddsky.data import atlas

r = atlas.parse(open(sys.argv[1]).read())
r = r[(r.dujy > 0) & (r.dujy < 2000) & r.F.isin(["c", "o"])].copy()
off = (r.mjd < 58800) | (r.mjd > 59200)
base = {F: g[off.loc[g.index]].ujy.median() for F, g in r.groupby("F")}
r["A"] = r.ujy / r.F.map(base)
r["night"] = np.floor(r.mjd - 0.3)
n = r.groupby(["F", "night"]).agg(mjd=("mjd", "median"), A=("A", "median"), k=("A", "size")).reset_index()
n = n[(n.A > 0.8) & (n.mjd > 58600) & (n.mjd < 59400)].copy()
floor = {F: 1.4826 * np.median(np.abs(g[(g.mjd < 58800) | (g.mjd > 59200)].A - 1)) for F, g in n.groupby("F")}
n["e"] = np.hypot(n.F.map(floor), 0.01 * n.A)
t, f, e = n.mjd.values, n.A.values, n.e.values


def mag(p, tt):
    t0, tE, u0 = p
    u = np.sqrt(u0**2 + ((tt - t0) / tE) ** 2)
    return (u**2 + 2) / (u * np.sqrt(u**2 + 4))


best = None
for t0 in (58880, 58900, 58920, 58940):
    for tE in (40, 70, 100):
        for u0 in (0.2, 0.4, 0.6):
            res = least_squares(lambda p: (mag(p, t) - f) / e, [t0, tE, u0], bounds=([58700, 5, 0.01], [58960, 400, 2]))
            if best is None or res.cost < best.cost:
                best = res
p = best.x
chi2, dof = 2 * best.cost, len(t) - 3
cov = np.linalg.inv(best.jac.T @ best.jac) * max(1, chi2 / dof)
err = np.sqrt(np.diag(cov))
print(f"floors: {({k: round(v, 4) for k, v in floor.items()})}")
print(f"t0 = MJD {p[0]:.1f} ± {err[0]:.1f} ({Time(p[0], format='mjd').iso[:10]}), tE = {p[1]:.1f} ± {err[1]:.1f} d, "
      f"u0 = {p[2]:.3f} ± {err[2]:.3f}, A_max = {mag(p, np.array([p[0]]))[0]:.2f}; chi2/dof = {chi2:.0f}/{dof}")
for lab, tt, obs in [("NEOWISE 2020 Apr 9-10", 58949.4, 1.98), ("ZTF Jun 18 (corrected)", 59018.4, 10 ** (0.4 * 0.17)),
                     ("ZTF Jul 14-21 (corrected)", 59048.0, 10 ** (0.4 * 0.09))]:
    print(f"{lab}: model x{mag(p, np.array([tt]))[0]:.3f}, observed x{obs:.3f}")
ev = n[(n.mjd > 58900) & (n.mjd < 59130)]
res_ev = (ev.A - mag(p, ev.mjd.values)) / ev.A
print(f"event residual rms {res_ev.std():.3f}; mean residual by band:",
      {F: round(float(((g.A - mag(p, g.mjd.values)) / g.A).mean()), 3) for F, g in ev.groupby("F")})
n.assign(model=mag(p, n.mjd.values)).to_csv(sys.argv[2], index=False)
