"""Referee 2: (a) blending with parallax (fs free for c, o and for NEOWISE); (b) Gaia DR4 predictions per model at the GOST
transits; (c) lens brightness / separation along the mass-distance relation. uv run python .../r12_blend_gaia_lens.py"""
import sys, numpy as np, pandas as pd
from scipy.optimize import least_squares
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L
from r4_fits import fit, par_both

RAW = L.load_raw()
d = L.nightly(RAW)
t, f, e = d.mjd.values, d.f.values, d.e.values
geo = L.Geo(t)
band = d.band.values
isW = np.isin(band, ["W1", "W2"])


def resid(p):
    tau, beta = L.traj_par(t, geo, *p[:5])
    A = L.pacz(np.hypot(tau, beta))
    fs = np.where(band == "o", p[5], np.where(band == "c", p[6], p[7]))
    return (fs * A + 1 - fs - f) / e


for s in (1, -1):
    best = None
    for pi in ([-1, -0.37], [-0.6, -0.46]):
        r = least_squares(resid, [58012.2, 47.7, s * 0.14] + pi + [1, 1, 1],
                          bounds=([57990, 5, -2 if s < 0 else 1e-4, -4, -4, 0.3, 0.3, 0.3], [58030, 300, -1e-4 if s < 0 else 2, 4, 4, 1.5, 1.5, 1.5]))
        if best is None or r.cost < best.cost:
            best = r
    J = best.jac; err = np.sqrt(np.diag(np.linalg.inv(J.T @ J))) * np.sqrt(2 * best.cost / (len(t) - 8))
    print(f"u0 sign {s:+d}: chi2 {2*best.cost:.1f}; piE ({best.x[3]:.2f}, {best.x[4]:.2f}); fs_o {best.x[5]:.3f}+-{err[5]:.3f}, "
          f"fs_c {best.x[6]:.3f}+-{err[6]:.3f}, fs_W {best.x[7]:.3f}+-{err[7]:.3f}")

# (b) Gaia transits (GOST, first referee): 2017-07-27, 2017-08-22 (x2), 2017-09-18 16:35
tg = np.array([57961.70, 57987.20, 57987.27, 58014.69])
g = L.Geo(tg)
s = fit(d, "static")
pb = par_both(d)
p02 = min(par_both(d, scale_units=("02a",)).values(), key=lambda q: q["chi2"])
rows = {"static PSPL (rejected)": L.pacz(np.hypot(*L.traj_static(tg, *s["p"][:3])))}
for k, q in pb.items():
    rows[f"parallax u0{'+' if k > 0 else '-'}"] = L.pacz(np.hypot(*L.traj_par(tg, g, *q["p"][:5])))
rows["parallax, 02a scale free"] = L.pacz(np.hypot(*L.traj_par(tg, g, *p02["p"][:5])))
a = fit(d, "acc"); rows["generic acceleration"] = L.pacz(np.hypot(*L.traj_acc(tg, *a["p"][:5])))
print("\nGaia DR4 predicted dG (mag) at MJD", tg.tolist())
for k, A in rows.items():
    print(f"  {k:28s} " + "  ".join(f"{-2.5*np.log10(x):+.2f}" for x in A))

# (c) lens along M(D_L) for piE = 1.05 and 0.76; MS absolute mags (Pecaut & Mamajek 2013, approx.) interpolated in mass
mass = np.array([0.075, 0.09, 0.10, 0.12, 0.15, 0.20, 0.30, 0.45, 0.60, 0.80])
MG = np.array([17.0, 15.5, 14.6, 13.6, 12.7, 11.8, 10.5, 9.0, 7.9, 6.3])
MK = np.array([10.4, 9.7, 9.3, 8.7, 8.2, 7.6, 6.6, 5.6, 4.9, 4.0])
print("\nlens along the mass-distance relation (A_G ~ 0.27 per kpc, A_K ~ 0.03 per kpc; source G 14.0, Ks 11.22, W1 11.13):")
for piE in (1.05, 0.76):
    for DL in (0.3, 0.4, 0.5, 0.7, 1.0, 1.5):
        pirel = 1 / DL - 0.330; M = pirel / (8.144 * piE**2); thE = pirel / piE
        mu = thE / 48.0 * 365.25
        dm = 5 * np.log10(DL * 100)
        if M < mass[0]:
            gstr = "brown dwarf (G > 25, Ks > 20)"
        else:
            G = np.interp(M, mass, MG) + dm + 0.27 * DL; K = np.interp(M, mass, MK) + dm + 0.03 * DL
            gstr = f"G {G:5.1f}  Ks {K:5.1f}  (dKs {K-11.22:+.1f}; K-band light fraction {10**(-0.4*(K-11.22)):.3f})"
        print(f"  piE {piE:.2f}  D_L {DL:.1f} kpc: M {M:.3f} Msun, theta_E {thE:.2f} mas, mu_rel {mu:4.1f} mas/yr, separation "
              f"2026.8 {mu*9.1/1000:.2f}\", 2030 {mu*12.3/1000:.2f}\"; {gstr}")

# (d) astrometric microlensing at the Gaia transits (dark lens, fs = 1): shift = theta_E * u / (u^2 + 2)
q = pb[1]["p"]
tau, beta = L.traj_par(tg, g, *q[:5]); uu = np.hypot(tau, beta)
print("\nGaia transits u =", np.round(uu, 2).tolist(), "; centroid shift / theta_E =", np.round(uu / (uu**2 + 2), 3).tolist())
for thE in (0.64, 1.05, 1.59, 2.07):
    print(f"  theta_E {thE} mas: shifts (mas) " + ", ".join(f"{x:.2f}" for x in thE * uu / (uu**2 + 2)))
