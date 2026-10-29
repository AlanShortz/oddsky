"""Referee 2, attack 5: is piE ~ 1 plausible for a tE ~ 48 d event on a 3 kpc source at (l, b) = (162.8, -15.3)?
Monte Carlo Galactic model (my own, simple): thin + thick exponential discs, flat rotation curve 233 km/s, Chabrier (2003)
single-star IMF 0.01-1 Msun plus 10% white dwarfs (0.6 Msun) by number; dispersions thin (35, 25, 20), thick (67, 51, 42)
km/s, asymmetric drift 10 / 40 km/s. Source proper motion fixed to Gaia DR3 (-1.22, -1.58) mas/yr; source distance 3.0 +- 0.2 kpc.
Events weighted by theta_E * mu_geo (rate); conditioned on 44 < tE < 56 d. Outside Oddsky tools.
uv run python .../r9_galaxy.py"""
import sys, numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord, Galactocentric, ICRS, CartesianDifferential, get_body_barycentric_posvel
from astropy.time import Time
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L

rng = np.random.default_rng(11)
N = 600_000
l, b = np.radians(162.82), np.radians(-15.27)
gc = Galactocentric()  # astropy defaults: R0 8.122 kpc, z_sun 20.8 pc
R0, zs = gc.galcen_distance.to(u.kpc).value, gc.z_sun.to(u.kpc).value
VC = 233.0


def dens(D):
    x = R0 - D * np.cos(b) * np.cos(l); y = -D * np.cos(b) * np.sin(l); z = D * np.sin(b) + zs
    R = np.hypot(x, y)
    thin = np.exp(-(R - R0) / 2.6 - np.abs(z) / 0.30)
    thick = 0.12 * np.exp(-(R - R0) / 2.0 - np.abs(z) / 0.90) * np.exp(0.02 / 0.90) / np.exp(0.02 / 0.30)
    return thin, thick


DS = np.clip(rng.normal(3.0, 0.2, N), 2.4, 3.8)
grid = np.linspace(0.005, 3.8, 4000)
th, tk = dens(grid)
pdf = (th + tk) * grid**2
DL = np.empty(N)
# sample D_L < D_S by inverse CDF per source distance bin
for lo in np.arange(2.4, 3.8, 0.05):
    m = (DS >= lo) & (DS < lo + 0.05)
    if not m.any():
        continue
    g = grid < lo + 0.025
    c = np.cumsum(pdf[g]); c /= c[-1]
    DL[m] = np.interp(rng.uniform(0, 1, m.sum()), c, grid[g])
thL, tkL = dens(DL)
thick = rng.uniform(0, 1, N) < tkL / (thL + tkL)

# masses: Chabrier 2003 single-star log-normal below 1 Msun (mc 0.079, sigma 0.69), floor 0.01; 10% WDs at 0.6
lm = rng.normal(np.log10(0.079), 0.69, 3 * N)
lm = lm[(lm > -2) & (lm < 0)][:N]
M = 10**lm
wd = rng.uniform(0, 1, N) < 0.10
M[wd] = 0.6


def vel_icrs(D, thick_mask):
    x = R0 - D * np.cos(b) * np.cos(l); y = D * np.cos(b) * np.sin(l); z = D * np.sin(b) + zs
    phi = np.arctan2(y, x)
    sR = np.where(thick_mask, 67, 35); sP = np.where(thick_mask, 51, 25); sZ = np.where(thick_mask, 42, 20)
    ad = np.where(thick_mask, 40, 10)
    vR = rng.normal(0, 1, D.size) * sR; vP = VC - ad + rng.normal(0, 1, D.size) * sP; vZ = rng.normal(0, 1, D.size) * sZ
    # astropy Galactocentric: Sun at x = -R0, rotation towards +y. Our x is measured from GC towards Sun positive -> flip.
    X, Y = -x, y
    ph = np.arctan2(Y, X)
    vx = vR * np.cos(ph) - (-vP) * np.sin(ph)  # disc rotates clockwise seen from NGP in this frame: v_phi = -VC
    vy = vR * np.sin(ph) + (-vP) * np.cos(ph)
    c = SkyCoord(x=X * u.kpc, y=Y * u.kpc, z=z * u.kpc, v_x=vx * u.km / u.s, v_y=vy * u.km / u.s, v_z=vZ * u.km / u.s,
                 frame=gc).transform_to(ICRS())
    return c.pm_ra_cosdec.to(u.mas / u.yr).value, c.pm_dec.to(u.mas / u.yr).value, c


# sanity check of the velocity convention: a disc star at the solar circle near the Sun should have small pm relative to LSR
pa, pd_, cL = vel_icrs(DL, thick)
print(f"sanity: lens direction RA/Dec median {np.median(cL.ra.deg):.2f}, {np.median(cL.dec.deg):.2f} (target 60.11, 32.59)")
ps, pds, _ = vel_icrs(DS, np.zeros(N, bool))
print(f"model source pm median ({np.median(ps):.2f}, {np.median(pds):.2f}) mas/yr vs Gaia (-1.22, -1.58)")
muS = np.array([-1.22, -1.58])
mu_hel = np.c_[pa - muS[0], pd_ - muS[1]]  # (E, N) components
pirel = 1 / DL - 1 / DS
# Earth velocity projected on (E, N) at t0 (AU/yr)
pv = get_body_barycentric_posvel("earth", Time(58012.2, format="mjd"))[1].xyz.to(u.au / u.yr).value
vE = np.array([pv @ L._E, pv @ L._N])
mu_geo = mu_hel - pirel[:, None] * vE[None, :]
mug = np.hypot(*mu_geo.T)
thE = np.sqrt(8.144 * M * pirel)
tE = thE / mug * 365.25
piE = pirel / thE
pa_deg = np.degrees(np.arctan2(mu_geo[:, 0], mu_geo[:, 1])) % 360  # PA of mu_geo (E of N) = PA of piE
w = thE * mug
sel = (tE > 44) & (tE < 56) & (pirel > 0)
W = w[sel] / w[sel].sum()


def wq(x, q):
    o = np.argsort(x); c = np.cumsum(W[o]); return np.interp(q, c, x[o])


print(f"events in tE window: {sel.sum()} of {N}; fraction of rate with tE in 44-56 d: {w[sel].sum() / w[pirel > 0].sum():.3f}")
print(f"tE median (all events) {np.median(tE[pirel > 0]):.1f} d (unweighted), rate-weighted median "
      f"{np.interp(0.5, np.cumsum(w[pirel > 0][np.argsort(tE[pirel > 0])]) / w[pirel > 0].sum(), np.sort(tE[pirel > 0])):.1f} d")
for nm, x in (("piE", piE[sel]), ("D_L kpc", DL[sel]), ("M Msun", M[sel]), ("mu_geo mas/yr", mug[sel])):
    print(f"{nm:14s} 5/16/50/84/95%: " + " ".join(f"{wq(x, q):.3g}" for q in (0.05, 0.16, 0.5, 0.84, 0.95)))
for thr in (0.5, 0.6, 0.75, 0.82, 1.0):
    print(f"P(piE > {thr}) = {W[piE[sel] > thr].sum():.3f}")
hi = piE[sel] > 0.75
print(f"among piE > 0.75: P(M < 0.08) = {W[hi & (M[sel] < 0.08)].sum() / W[hi].sum():.2f}, P(D_L < 1 kpc) = "
      f"{W[hi & (DL[sel] < 1)].sum() / W[hi].sum():.2f}, P(WD) = {W[hi & wd[sel]].sum() / W[hi].sum():.2f}, "
      f"P(M < 0.3) = {W[hi & (M[sel] < 0.3)].sum() / W[hi].sum():.2f}")
# direction: measured PA(piE) ~ 201 deg (u0>0) / 204 (u0<0); 02a-scale solution PA ~ 218
for pa0 in (201, 218):
    dpa = np.abs((pa_deg[sel] - pa0 + 180) % 360 - 180)
    print(f"P(PA within 30 deg of {pa0}) = {W[dpa < 30].sum():.3f}; among piE > 0.6: {W[(dpa < 30) & (piE[sel] > 0.6)].sum() / W[piE[sel] > 0.6].sum():.3f}")
# joint: density ratio of the measured vector relative to the prior median region
m_meas = (np.hypot(piE[sel] * np.cos(np.radians(pa_deg[sel])) + 0.99, piE[sel] * np.sin(np.radians(pa_deg[sel])) + 0.37) < 0.3)
print(f"P(piE vector within 0.3 of (-0.99, -0.37)) = {W[m_meas].sum():.4f}")
m2 = (np.hypot(piE[sel] * np.cos(np.radians(pa_deg[sel])) + 0.60, piE[sel] * np.sin(np.radians(pa_deg[sel])) + 0.46) < 0.3)
print(f"P(piE vector within 0.3 of (-0.60, -0.46)) = {W[m2].sum():.4f}")
