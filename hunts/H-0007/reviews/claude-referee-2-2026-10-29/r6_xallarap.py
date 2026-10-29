"""Referee 2, attack 3a: circular-orbit xallarap (binary source) at fixed periods; compare with parallax (chi2 89.3 on the
same data). Also: what companion would the best xallarap need? uv run python .../r6_xallarap.py"""
import sys, numpy as np, pandas as pd
from scipy.optimize import least_squares
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L

d = L.nightly(L.load_raw())
t, f, e = d.mjd.values, d.f.values, d.e.values


def chi2_xal(P, starts=None):
    best = None
    rng = np.random.default_rng(int(P))
    for k in range(40):
        u0 = rng.choice([0.14, -0.14, 0.08, -0.08])
        p0 = [58012, 47.7, u0, rng.normal(0, 0.5), rng.normal(0, 0.5), rng.uniform(0, 2 * np.pi), rng.uniform(0, np.pi / 2)]
        def res(p):
            tau, beta = L.traj_xal(t, p[0], p[1], p[2], p[3], p[4], P, p[5], p[6])
            return (L.pacz(np.hypot(tau, beta)) - f) / e
        try:
            r = least_squares(res, p0, bounds=([57990, 5, -2, -20, -20, -10, 0], [58030, 300, 2, 20, 20, 20, np.pi / 2]))
        except ValueError:
            continue
        if best is None or r.cost < best.cost:
            best = r
    return 2 * best.cost, best.x


rows = []
for P in (15, 25, 40, 60, 90, 120, 180, 250, 365.25, 500, 750, 1000, 2000, 5000):
    c2, p = chi2_xal(P)
    xi = np.hypot(p[3], p[4])
    rows.append(dict(P=P, chi2=round(c2, 1), xiE=round(xi, 3), u0=round(p[2], 3), tE=round(p[1], 2), inc_deg=round(np.degrees(p[6]), 1)))
    print(rows[-1], flush=True)
X = pd.DataFrame(rows)
X.to_csv("hunts/H-0007/reviews/claude-referee-2-2026-10-29/r6_xallarap.csv", index=False)
# physical requirement: source semi-major axis a_s = xi_E * D_S * theta_E (AU, kpc, mas)
# For each P, minimum companion mass if theta_E = 0.3, 0.6, 1.0 mas (D_S = 3.0 kpc, M_giant = 1.5 Msun).
print("\ncompanion mass needed (Msun) for M_giant = 1.5, D_S = 3.0 kpc:")
for _, r in X.iterrows():
    out = []
    for thE in (0.3, 0.6, 1.0):
        a_s = r.xiE * 3.0 * thE
        # a_s = a * Mc / (Ms + Mc), a^3 = (Ms + Mc) P_yr^2  -> solve for Mc
        Py = r.P / 365.25
        Mc = np.nan
        for m in np.logspace(-2, 2, 4000):
            a = ((1.5 + m) * Py**2) ** (1 / 3)
            if a * m / (1.5 + m) >= a_s:
                Mc = m; break
        out.append(f"thetaE {thE}: Mc {Mc:.2f}")
    print(f"P {r.P:7.1f} d  xi_E {r.xiE:6.3f}  chi2 {r.chi2:6.1f}   " + ";  ".join(out))
