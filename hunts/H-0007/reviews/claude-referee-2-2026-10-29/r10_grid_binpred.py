"""Referee 2: (a) local minima of the piE chi2 grid (r4_grid.csv) for each u0 sign (jerk-parallax / ecliptic degeneracy);
(b) out-of-sample peak predictions of the best static binary lens (r7) vs parallax.
uv run --with MulensModel python .../r10_grid_binpred.py"""
import sys, warnings, numpy as np, pandas as pd
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L
import MulensModel as mm
from scipy.ndimage import minimum_filter
warnings.filterwarnings("ignore")
G = pd.read_csv("hunts/H-0007/reviews/claude-referee-2-2026-10-29/r4_grid.csv")
gmin = G.chi2.min()
for s in (1, -1):
    g = G[G.sgn == s].pivot(index="piE_N", columns="piE_E", values="chi2")
    Z = g.values
    loc = (Z == minimum_filter(Z, size=5, mode="nearest"))
    print(f"u0 sign {s:+d}: local minima (piE_N, piE_E, dchi2):",
          [(round(g.index[i], 2), round(g.columns[j], 2), round(Z[i, j] - gmin, 1)) for i, j in zip(*np.where(loc))])
    for lev in (1, 4, 9, 25):
        m = Z - gmin < lev
        if m.any():
            iN, iE = np.where(m)
            pis = np.hypot(g.index[iN], g.columns[iE])
            print(f"   dchi2 < {lev:2d}: piE_N {g.index[iN].min():.1f}..{g.index[iN].max():.1f}, piE_E {g.columns[iE].min():.1f}..{g.columns[iE].max():.1f}, |piE| {pis.min():.2f}..{pis.max():.2f}")
print("chi2 at piE = 0:", G[(G.piE_N.abs() < 1e-9) & (G.piE_E.abs() < 1e-9)].chi2.round(1).tolist(), " global min", round(gmin, 1))
# |piE| profile: min chi2 in annuli
G["pi"] = np.hypot(G.piE_N, G.piE_E)
for lo in np.arange(0, 2.6, 0.2):
    a = G[(G.pi >= lo) & (G.pi < lo + 0.2)]
    print(f"|piE| {lo:.1f}-{lo+0.2:.1f}: min dchi2 {a.chi2.min() - gmin:7.1f}")

B = pd.read_csv("hunts/H-0007/reviews/claude-referee-2-2026-10-29/r7_binlens.csv").iloc[0]
m = mm.Model({"t_0": B.t0 + 2400000.5, "u_0": B.u0, "t_E": B.tE, "alpha": B.alpha, "s": B.s, "q": B.q})
m.default_magnification_method = "point_source"
tt = np.array([58007.60, 58009.59])
print(f"binary lens (s {B.s}, q {B.q}, chi2 {B.chi2}) predicts A = {np.round(m.get_magnification(tt + 2400000.5), 2).tolist()} at {tt.tolist()} (observed 5.95, 7.28)")
tf = np.arange(57990, 58035, 0.1)
Af = m.get_magnification(tf + 2400000.5)
print(f"binary lens: max A on 57990-58035 = {Af.max():.1f} at MJD {tf[Af.argmax()]:.1f}; caustic crossings (|dA| > 1 per 0.1 d): {int(np.sum(np.abs(np.diff(Af)) > 1))}")
print("binary-lens light curve every 2 d:", [(round(a, 0), round(b, 2)) for a, b in zip(tf[::20], Af[::20])])
# finite source: rho for R = 8 Rsun at 3 kpc and theta_E 0.3-1.6 mas
th_star = 8 * 6.957e8 / (3 * 3.0857e19) * 206264.8e3
print(f"source angular radius {th_star*1000:.1f} uas; rho = {th_star/1.6:.4f} (thetaE 1.6 mas) .. {th_star/0.3:.4f} (0.3 mas)")
