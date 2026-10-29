"""Referee 2, attack 1a: parallax geometry. Compare (i) my get_sun (GCRS) Delta s, (ii) the investigators' -barycentric-Earth
Delta s, (iii) MulensModel 3.x (independent implementation of Gould 2004) magnifications for the investigators' best fit.
run: uv run --with MulensModel python hunts/H-0007/reviews/claude-referee-2-2026-10-29/r3_geometry.py"""
import sys, json, numpy as np
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L
from astropy.coordinates import get_body_barycentric
from astropy.time import Time
import astropy.units as u
import MulensModel as mm

t = np.linspace(57950, 58090, 141)
g = L.Geo(t)
# investigators' route
def inv(mjd):
    xyz = -get_body_barycentric("earth", Time(mjd, format="mjd")).xyz.to(u.au).value.T
    return xyz @ L._N, xyz @ L._E
sn, se = inv(t); s1n, s1e = inv(np.array([57010.0 + 1000, 58011.0, 58012.0]))
s1n, s1e = inv(np.array([58010.0, 58011.0, 58012.0]))
dN = sn - s1n[1] - (s1n[2] - s1n[0]) / 2 * (t - 58011); dE = se - s1e[1] - (s1e[2] - s1e[0]) / 2 * (t - 58011)
print(f"max |dN mine - investigators| = {np.max(np.abs(g.dN - dN)):.2e} AU, |dE| = {np.max(np.abs(g.dE - dE)):.2e} AU "
      f"(range of dN {g.dN.min():.3f}..{g.dN.max():.3f}, dE {g.dE.min():.3f}..{g.dE.max():.3f})")

p = json.load(open("hunts/H-0007/work/lensfit_J040025.json"))["fits"]["c"]["p"]
t0, tE, u0, piN, piE = p
tau, beta = L.traj_par(t, g, t0, tE, u0, piN, piE)
A_me = L.pacz(np.hypot(tau, beta))
coords = f"{L.RA} {L.DEC}"
for sgn in (+1, -1):
    m = mm.Model({"t_0": t0 + 2400000.5, "u_0": sgn * u0, "t_E": tE, "pi_E_N": piN, "pi_E_E": piE, "t_0_par": 58011.0 + 2400000.5},
                 coords="04:00:25.770 +32:35:27.45")
    A_mm = m.get_magnification(t + 2400000.5)
    print(f"MulensModel u0 = {sgn * u0:+.4f}: max |A_mine/A_MM - 1| = {np.max(np.abs(A_me / A_mm - 1)):.2e}")
# pi_parallel / pi_perp: direction of the projected Sun acceleration at t0par
a = g.acc / np.linalg.norm(g.acc)
print(f"projected Sun acceleration at t0par: |a| = {np.linalg.norm(g.acc):.2e} AU/d^2, unit (N, E) = ({a[0]:.3f}, {a[1]:.3f}); "
      f"PA = {np.degrees(np.arctan2(a[1], a[0])) % 360:.1f} deg")
par = piN * a[0] + piE * a[1]; perp = -piN * a[1] + piE * a[0]
print(f"investigators' piE = ({piN:.3f}, {piE:.3f}) -> pi_parallel {par:+.3f}, pi_perp {perp:+.3f}")
from astropy.coordinates import SkyCoord
c = SkyCoord(L.RA * u.deg, L.DEC * u.deg).barycentrictrueecliptic
print(f"ecliptic latitude {c.lat.deg:.2f} deg, longitude {c.lon.deg:.2f}; Sun ecliptic longitude at t0 ~ "
      f"{L.get_sun(Time(58011, format='mjd')).geocentrictrueecliptic.lon.deg:.1f}")
