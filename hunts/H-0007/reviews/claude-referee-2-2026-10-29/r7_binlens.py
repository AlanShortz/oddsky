"""Referee 2, attack 3b: static binary lens (point source, no parallax) via MulensModel/VBBL on the same data.
Grid over (s, q), local optimisation of (t0, u0, tE, alpha, log s, log q). Compare with parallax chi2 89.3.
uv run --with MulensModel python .../r7_binlens.py"""
import sys, warnings, numpy as np, pandas as pd
from scipy.optimize import least_squares
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L
import MulensModel as mm
warnings.filterwarnings("ignore")

d = L.nightly(L.load_raw(), sat=None if "--all" in sys.argv else 12.2)
t, f, e = d.mjd.values + 2400000.5, d.f.values, d.e.values


def mag(p):
    t0, u0, tE, alpha, ls, lq = p
    m = mm.Model({"t_0": t0, "u_0": u0, "t_E": tE, "alpha": alpha, "s": 10**ls, "q": 10**lq})
    m.set_magnification_methods([t.min() - 1, "point_source", t.max() + 1])
    m.default_magnification_method = "point_source"
    return m.get_magnification(t)


def res(p):
    try:
        A = mag(p)
    except Exception:
        return np.full_like(f, 1e3)
    r = (A - f) / e
    return np.where(np.isfinite(r), r, 1e3)


rows = []
rng = np.random.default_rng(3)
for s in (0.3, 0.5, 0.7, 1.0, 1.4, 2.0, 3.0, 5.0):
    for q in (1e-3, 1e-2, 0.1, 0.3, 1.0):
        best = None
        for alpha in np.arange(0, 360, 45):
            for u0 in (0.15, -0.15):
                p0 = [2458011.5, u0, 47.0, alpha, np.log10(s), np.log10(q)]
                try:
                    r = least_squares(res, p0, bounds=([2457990, -1.5, 5, -720, -1, -4], [2458030, 1.5, 300, 720, 1, 0.0]),
                                      max_nfev=300, x_scale=[1, 0.05, 2, 10, 0.05, 0.2])
                except Exception:
                    continue
                if best is None or r.cost < best.cost:
                    best = r
        x = best.x
        rows.append(dict(s0=s, q0=q, chi2=round(2 * best.cost, 1), t0=round(x[0] - 2400000.5, 2), u0=round(x[1], 3), tE=round(x[2], 2),
                         alpha=round(x[3] % 360, 1), s=round(10**x[4], 3), q=float(f"{10**x[5]:.3g}")))
        print(rows[-1], flush=True)
B = pd.DataFrame(rows).sort_values("chi2")
B.to_csv(f"hunts/H-0007/reviews/claude-referee-2-2026-10-29/r7_binlens{'_all' if '--all' in sys.argv else ''}.csv", index=False)
print(B.head(10).to_string())
