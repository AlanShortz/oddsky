"""Referee 2: (a) each model fitted WITHOUT the two near-saturated peak nights, then asked to predict them (out-of-sample);
(b) each model fitted WITH them (sat=None). Models: static, parallax (best u0 sign), generic acceleration, acceleration+jerk,
xallarap at P = 180, 365 d. uv run python .../r11_allpoints.py"""
import sys, numpy as np, pandas as pd
from scipy.optimize import least_squares
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L
from r4_fits import fit, par_both

RAW = L.load_raw()
peak = L.nightly(RAW, sat=None)
peak = peak[(peak.mjd > 58005) & (peak.mjd < 58011) & (peak.band == "o")]
tp = peak.mjd.values


def xal_fit(d, P):
    t, f, e = d.mjd.values, d.f.values, d.e.values
    rng = np.random.default_rng(int(P)); best = None
    for k in range(40):
        p0 = [58012, 47.7, rng.choice([0.14, -0.14]), rng.normal(0, 0.5), rng.normal(0, 0.5), rng.uniform(0, 2 * np.pi), rng.uniform(0, np.pi / 2)]
        res = lambda p: (L.pacz(np.hypot(*L.traj_xal(t, *p[:5], P, p[5], p[6]))) - f) / e
        r = least_squares(res, p0, bounds=([57990, 5, -2, -20, -20, -10, 0], [58030, 300, 2, 20, 20, 20, np.pi / 2]))
        if best is None or r.cost < best.cost:
            best = r
    p = best.x
    return 2 * best.cost, L.pacz(np.hypot(*L.traj_xal(tp, *p[:5], P, p[5], p[6])))


rows = []
for tag, sat in (("without peak nights (m > 12.2)", 12.2), ("with peak nights (all)", None)):
    d = L.nightly(RAW, sat=sat)
    g = L.Geo(tp)
    s = fit(d, "static"); A_s = L.pacz(np.hypot(*L.traj_static(tp, *s["p"][:3])))
    p = min(par_both(d).values(), key=lambda q: q["chi2"]); A_p = L.pacz(np.hypot(*L.traj_par(tp, g, *p["p"][:5])))
    a = fit(d, "acc"); A_a = L.pacz(np.hypot(*L.traj_acc(tp, *a["p"][:5])))
    j = fit(d, "accjerk"); A_j = L.pacz(np.hypot(*L.traj_acc(tp, *j["p"][:7])))
    x1, A_x1 = xal_fit(d, 180.0); x2, A_x2 = xal_fit(d, 365.25)
    for nm, c2, k, A in (("static", s["chi2"], 3, A_s), ("parallax", p["chi2"], 5, A_p), ("acceleration", a["chi2"], 5, A_a),
                         ("acc+jerk", j["chi2"], 7, A_j), ("xallarap P=180", x1, 8, A_x1), ("xallarap P=365", x2, 8, A_x2)):
        rows.append(dict(data=tag, model=nm, N=len(d), k=k, chi2=round(c2, 1), BIC=round(c2 + k * np.log(len(d)), 1),
                         pred_58007=round(A[0], 2), pred_58009=round(A[1], 2)))
T = pd.DataFrame(rows)
print(f"observed: 58007.60 {peak.f.values[0]:.2f}, 58009.59 {peak.f.values[1]:.2f}")
print(T.to_string())
T.to_csv("hunts/H-0007/reviews/claude-referee-2-2026-10-29/r11_allpoints.csv", index=False)
