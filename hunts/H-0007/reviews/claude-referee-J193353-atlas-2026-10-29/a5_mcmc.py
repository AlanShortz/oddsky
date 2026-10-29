"""a5: emcee over the parallax point lens with one fs per survey (ATLAS, WISE, ZTF), errors rescaled per survey so that the
best a4 parallax model has chi2/dof = 1 in each survey. Both u0 signs seeded. Also: ATLAS-only static vs parallax chi2.
Outside the Oddsky tools. usage: uv run --with MulensModel --with emcee python a5_mcmc.py [nsteps]"""
import sys, warnings
import numpy as np
import pandas as pd
import MulensModel as mm
import emcee
from scipy.optimize import least_squares

warnings.filterwarnings("ignore")
D = pd.read_csv("/tmp/j1933atl/joint.csv")
COORDS, TP, J = "19:33:53.067 -21:18:13.49", 58925.0, 2400000.5
sv = D.band.map({"Ac": 0, "Ao": 0, "W1": 1, "W2": 1, "Zg": 2, "Zr": 2}).values
tt, ff = D.mjd.values + J, D.f.values


def mag(p, t=tt):
    t0, u0, tE, pn, pe = p
    return mm.Model({"t_0": t0 + J, "u_0": u0, "t_E": tE, "pi_E_N": pn, "pi_E_E": pe, "t_0_par": TP + J}, coords=COORDS).get_magnification(t)


def flux(p):
    fs = np.asarray(p[5:8])
    return fs[sv] * mag(p[:5]) + 1 - fs[sv]


ee = D.e.values.copy()
best = least_squares(lambda p: (flux(p) - ff) / ee, [58929, -0.29, 50, -0.14, 0.47, 0.72, 0.71, 0.70],
                     bounds=([58880, -3, 5, -5, -5, .02, .02, .02], [58960, 3, 600, 5, 5, 1.05, 1.05, 1.05]))
r = (flux(best.x) - ff) / ee
for k, nm in enumerate(["ATLAS", "WISE", "ZTF"]):
    s = sv == k
    sc = np.sqrt(np.sum(r[s] ** 2) / (s.sum() - 8 * s.sum() / len(r)))
    print(f"{nm}: n={s.sum()} chi2={np.sum(r[s] ** 2):.0f} -> error scale {sc:.2f}")
    ee[s] *= sc

# ATLAS-only static vs parallax (fs=1), original errors
a = D.band.str.startswith("A").values
for lab, par in [("static", False), ("parallax", True)]:
    f0 = (lambda p: (mag(list(p[:3]) + ([p[3], p[4]] if par else [0, 0]), tt[a]) - ff[a]) / D.e.values[a])
    rr = min((least_squares(f0, [58928, s * 0.4, 50] + ([-0.1, 0.5] if par else []), bounds=([58880, -3, 5] + ([-5, -5] if par else []),
              [58960, 3, 600] + ([5, 5] if par else []))) for s in (1, -1)), key=lambda x: x.cost)
    print(f"ATLAS-only {lab} fs=1: chi2 {2 * rr.cost:.0f}/{a.sum() - len(rr.x)}  params {np.round(rr.x, 3)}")


def lnp(p):
    t0, u0, tE, pn, pe, *fs = p
    if not (58880 < t0 < 58960 and 0.005 < abs(u0) < 3 and 5 < tE < 600 and abs(pn) < 5 and abs(pe) < 5 and all(0.02 < x < 1.05 for x in fs)):
        return -np.inf
    return -0.5 * np.sum(((flux(p) - ff) / ee) ** 2)


nw, ns = 40, int(sys.argv[1]) if len(sys.argv) > 1 else 2000
rng = np.random.default_rng(1)
p0 = []
for i in range(nw):
    q = best.x.copy() * (1 + 1e-3 * rng.standard_normal(8))
    if i % 2:
        q[1], q[3] = -q[1], -q[3]  # seed the other u0 sign (ecliptic degeneracy)
    p0.append(q)
S = emcee.EnsembleSampler(nw, 8, lnp)
S.run_mcmc(np.array(p0), ns, progress=False)
ch = S.get_chain(discard=ns // 2, flat=True)
lp = S.get_log_prob(discard=ns // 2, flat=True)
np.save("/tmp/j1933atl/chain.npy", ch)
print(f"acceptance {S.acceptance_fraction.mean():.2f}; best chi2 (rescaled) {-2 * lp.max():.0f}/{len(D) - 8}")
names = ["t0", "u0", "tE", "piEN", "piEE", "fs_ATLAS", "fs_WISE", "fs_ZTF"]
for i, nm in enumerate(names):
    q = np.percentile(ch[:, i], [2.5, 16, 50, 84, 97.5])
    print(f"  {nm:9s} 2.5/16/50/84/97.5%: " + " ".join(f"{x:.3f}" for x in q))
print("  u0>0 fraction", (ch[:, 1] > 0).mean().round(3))
piE = np.hypot(ch[:, 3], ch[:, 4]); print("  |piE| " + " ".join(f"{x:.3f}" for x in np.percentile(piE, [2.5, 16, 50, 84, 97.5])))
# derived: observed ATLAS-flux peak and date, source A_max, Gaia transit predictions
sub = ch[rng.choice(len(ch), 400, replace=False)]
g = np.arange(58890, 58970, 0.5) + J
pk, pkd, amax, gaia = [], [], [], []
for p in sub:
    A = mag(p[:5], g); F = p[5] * A + 1 - p[5]
    pk.append(F.max()); pkd.append(g[F.argmax()] - J); amax.append(A.max())
    Ag = mag(p[:5], np.array([58907.5, 58920.5, 58956.5]) + J); gaia.append(-2.5 * np.log10(p[5] * Ag + 1 - p[5]))
for nm, v in [("observed peak flux ratio", pk), ("peak MJD", pkd), ("source A_max", amax)]:
    print(f"  {nm}: " + " ".join(f"{x:.2f}" for x in np.percentile(v, [2.5, 16, 50, 84, 97.5])))
gaia = np.array(gaia)
print("  Gaia dG Feb28/Mar12/Apr17 median (2.5-97.5%):", [f"{np.median(gaia[:, k]):+.2f} ({np.percentile(gaia[:, k], 2.5):+.2f}..{np.percentile(gaia[:, k], 97.5):+.2f})" for k in range(3)])
