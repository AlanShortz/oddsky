"""A small Galactic model for microlensing priors: given a line of sight, a source and a lens mass, what Einstein radius,
relative proper motion and microlensing parallax should the lens have?

For a fixed tE the deflection theta_E = mu_rel tE does not depend on the mass; the mass sets the lens distance through
pi_rel = theta_E^2 / (kappa M). So "if this lens were a 10 Msun black hole" is a statement about where it must sit and how
fast it must move, and the Galaxy decides how likely that is. This module samples it:

  * lens distance D_L from the mass density along the line of sight (thin + thick disc, double exponential; a Dwek G2 bar
    for the bulge), times the event-rate weight D_L^2 theta_E mu_rel (Batista et al. 2011; Han & Gould 1995/2003);
  * lens velocity from its population (disc: flat rotation minus asymmetric drift, dispersions (35, 25, 20) km/s; bulge:
    no net streaming, isotropic 100 km/s); the Sun at R0 = 8.2 kpc moving (11.1, 12.24 + 233, 7.25) km/s (Schoenrich et al.
    2010);
  * the source proper motion from Gaia DR3 if measured (it usually is), so mu_rel = mu_L - mu_S needs only the lens;
  * observed constraints as weights: tE in [lo, hi] and |piE| in [lo, hi] if known.

Simplifications, stated: a fixed lens mass (no mass function here; `mass_function_samples` gives one for population
forecasts), no extinction or lens light, no spiral arms, a smooth bar. Good to a factor ~2 in rates and ~30% in typical
theta_E, which is what a detectability ranking needs.
"""

from __future__ import annotations

import numpy as np

KAPPA = 8.144
R0, Z_SUN = 8.2, 0.02                      # kpc
V_SUN = np.array([11.1, 12.24 + 233.0, 7.25])   # km/s, Galactocentric Cartesian (+x toward the GC, +y rotation)
K_MASYR = 4.74047                          # km/s per (mas/yr * kpc)

# disc: thin + thick, local densities (Msun/pc^3) in stars and remnants
THIN = dict(rho0=0.040, hr=2.6, hz=0.30)
THICK = dict(rho0=0.0040, hr=3.6, hz=0.90)
# bulge: Dwek et al. 1995 G2 bar, scale lengths (kpc), angle of the near end to the Sun-GC line
BAR = dict(x0=1.58, y0=0.62, z0=0.43, angle_deg=27.0, mass=1.6e10, rcut=2.4)


def _bar_density_unnorm(x, y, z):
    a = np.radians(BAR["angle_deg"])
    xb = x * np.cos(a) + y * np.sin(a)
    yb = -x * np.sin(a) + y * np.cos(a)
    rs4 = ((xb / BAR["x0"]) ** 2 + (yb / BAR["y0"]) ** 2) ** 2 + (z / BAR["z0"]) ** 4
    r = np.sqrt(x**2 + y**2)
    cut = np.where(r > BAR["rcut"], np.exp(-0.5 * (r - BAR["rcut"]) ** 2 / 0.5**2), 1.0)
    return np.exp(-0.5 * np.sqrt(rs4)) * cut


def _bar_norm():
    g = np.linspace(-6, 6, 121)
    zz = np.linspace(-3, 3, 61)
    X, Y, Z = np.meshgrid(g, g, zz, indexing="ij")
    vol = (g[1] - g[0]) ** 2 * (zz[1] - zz[0]) * 1e9   # pc^3
    return BAR["mass"] / (_bar_density_unnorm(X, Y, Z).sum() * vol)


_BAR_NORM = None


def _gc(d, l_deg, b_deg):
    """Galactocentric Cartesian (kpc), the Sun at (-R0, 0, Z_SUN), +x toward the GC, +y toward l = 90 deg."""
    lr, b = np.radians(l_deg), np.radians(b_deg)
    x = -R0 + d * np.cos(b) * np.cos(lr)
    y = d * np.cos(b) * np.sin(lr)
    z = Z_SUN + d * np.sin(b)
    return x, y, z


def densities(d, l_deg, b_deg):
    """(disc, bulge) mass densities (Msun/pc^3) at distance d (kpc) along (l, b)."""
    global _BAR_NORM
    if _BAR_NORM is None:
        _BAR_NORM = _bar_norm()
    x, y, z = _gc(d, l_deg, b_deg)
    r = np.sqrt(x**2 + y**2)
    disc = sum(c["rho0"] * np.exp(-(r - R0) / c["hr"] - (np.abs(z) - Z_SUN) / c["hz"]) for c in (THIN, THICK))
    # the disc has a hole inside ~1 kpc where the bar dominates
    disc = disc * np.where(r < 1.0, r, 1.0)
    return disc, _BAR_NORM * _bar_density_unnorm(x, y, z)


def _unit_lb(l_deg, b_deg):
    lr, b = np.radians(l_deg), np.radians(b_deg)
    el = np.array([-np.sin(lr), np.cos(lr), 0.0])
    eb = np.array([-np.sin(b) * np.cos(lr), -np.sin(b) * np.sin(lr), np.cos(b)])
    return el, eb


def velocities(pop, x, y, rng):
    """Velocity samples (km/s, Galactocentric Cartesian; Sun at -x, rotation toward +y) for 'disc' or 'bulge'."""
    n = len(x)
    if pop == "bulge":
        return rng.normal(0, 100.0, (n, 3))
    phi = np.arctan2(y, x)
    vrot = 233.0 - 10.0
    # rotation: at the Sun (x<0, y=0) the disc moves toward +y
    e_phi = np.column_stack([np.sin(phi), -np.cos(phi), np.zeros(n)])
    # clockwise seen from +z: at the Sun (phi = pi) e_phi = (0, 1, 0), the direction of Galactic rotation
    v = vrot * e_phi
    e_r = np.column_stack([np.cos(phi), np.sin(phi), np.zeros(n)])
    v = v + rng.normal(0, 35.0, n)[:, None] * e_r + rng.normal(0, 25.0, n)[:, None] * e_phi
    v[:, 2] += rng.normal(0, 20.0, n)
    return v


def proper_motion_lb(v, d, l_deg, b_deg):
    """Heliocentric proper motion (mu_l*, mu_b) in mas/yr of velocity v (km/s, Galactocentric) at distance d (kpc)."""
    el, eb = _unit_lb(l_deg, b_deg)
    dv = v - V_SUN
    return (dv @ el) / (K_MASYR * d), (dv @ eb) / (K_MASYR * d)


def lb_to_radec_rotation(ra, dec):
    """2x2 matrix turning (mu_l*, mu_b) into (mu_alpha*, mu_delta) at (ra, dec)."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    c = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
    gal = c.galactic
    m = np.empty((2, 2))
    for j, (pl, pb) in enumerate(((1.0, 0.0), (0.0, 1.0))):
        g = SkyCoord(l=gal.l, b=gal.b, pm_l_cosb=pl * u.mas / u.yr, pm_b=pb * u.mas / u.yr, frame="galactic")
        e = g.icrs
        m[0, j] = e.pm_ra_cosdec.to_value(u.mas / u.yr)
        m[1, j] = e.pm_dec.to_value(u.mas / u.yr)
    return m


def sample_lenses(l_deg, b_deg, ra, dec, mass, n=4000, *, ds=8.0, ds_sig=0.8, mu_s=None, mu_s_sig=(0.3, 0.3),
                  te_range=None, pie_range=None, rng=None, oversample=20):
    """Weighted lens samples for one target and one lens mass (Msun; scalar or array of length n*oversample).

    ds, ds_sig: source distance (kpc) and its spread (a normal, truncated at 0.3 kpc). mu_s: source proper motion
    (mu_alpha*, mu_delta) in mas/yr (Gaia), or None to draw it from the source's population. te_range, pie_range: observed
    constraints (hard limits). Returns dict of arrays: weight, D_L, D_S, theta_E (mas), mu_rel (mas/yr), tE (d),
    piE_N, piE_E, pop ('disc'/'bulge'), and 'n_eff' (effective sample size after weighting)."""
    rng = np.random.default_rng(0) if rng is None else rng
    N = n * oversample
    dsamp = np.clip(rng.normal(ds, ds_sig, N), 0.3, 20.0)
    # D_L uniform in (0, D_S) with the rate weight D_L^2 rho applied as a weight
    dl = dsamp * rng.uniform(0.0, 1.0, N) ** 0.5     # proposal ~ D_L (partial importance sampling)
    prop = 2 * dl / dsamp**2
    rho_d, rho_b = densities(dl, l_deg, b_deg)
    rho = rho_d + rho_b
    p_b = np.divide(rho_b, rho, out=np.zeros_like(rho), where=rho > 0)
    is_b = rng.uniform(size=N) < p_b
    x, y, _ = _gc(dl, l_deg, b_deg)
    v = np.where(is_b[:, None], velocities("bulge", x, y, rng), velocities("disc", x, y, rng))
    mul, mub = proper_motion_lb(v, dl, l_deg, b_deg)
    rot = lb_to_radec_rotation(ra, dec)
    mua = rot[0, 0] * mul + rot[0, 1] * mub
    mud = rot[1, 0] * mul + rot[1, 1] * mub
    if mu_s is None:
        xs, ys, _ = _gc(dsamp, l_deg, b_deg)
        rd_s, rb_s = densities(dsamp, l_deg, b_deg)
        sb = rng.uniform(size=N) < rb_s / np.maximum(rd_s + rb_s, 1e-30)
        vs = np.where(sb[:, None], velocities("bulge", xs, ys, rng), velocities("disc", xs, ys, rng))
        sl, sbm = proper_motion_lb(vs, dsamp, l_deg, b_deg)
        msa, msd = rot[0, 0] * sl + rot[0, 1] * sbm, rot[1, 0] * sl + rot[1, 1] * sbm
    else:
        msa = mu_s[0] + rng.normal(0, mu_s_sig[0], N)
        msd = mu_s[1] + rng.normal(0, mu_s_sig[1], N)
    # relative proper motion, lens minus source, geocentric ~ heliocentric (the Earth's velocity matters only for piE)
    mra, mde = mua - msa, mud - msd
    mu = np.hypot(mra, mde)
    prel = np.maximum(1.0 / dl - 1.0 / dsamp, 1e-6)
    m = np.broadcast_to(np.asarray(mass, float), (N,))
    th = np.sqrt(KAPPA * m * prel)
    te = th / np.maximum(mu, 1e-6) * 365.25
    pie = prel / th
    w = rho * dl**2 * th * mu / prop
    w = np.where(dl < dsamp, w, 0.0)
    if te_range is not None:
        w = w * ((te >= te_range[0]) & (te <= te_range[1]))
    if pie_range is not None:
        w = w * ((pie >= pie_range[0]) & (pie <= pie_range[1]))
    sw = w.sum()
    out = dict(weight=w / sw if sw > 0 else w, D_L=dl, D_S=dsamp, theta_E=th, mu_rel=mu, tE=te,
               piE_N=pie * mde / np.maximum(mu, 1e-9), piE_E=pie * mra / np.maximum(mu, 1e-9), pop=np.where(is_b, "bulge", "disc"),
               mass=m)
    out["n_eff"] = float(sw**2 / np.sum(w**2)) if sw > 0 else 0.0
    out["rate"] = float(sw / N)
    return out


def resample(s: dict, n: int, rng=None) -> dict:
    """Equal-weight resample of `sample_lenses` output."""
    rng = np.random.default_rng(1) if rng is None else rng
    if s["weight"].sum() <= 0:
        return {k: np.array([]) for k in s if isinstance(s[k], np.ndarray)}
    i = rng.choice(len(s["weight"]), size=n, p=s["weight"])
    return {k: v[i] for k, v in s.items() if isinstance(v, np.ndarray)}


def mass_function_samples(n, rng=None, f_wd=0.06, f_ns=0.010, f_bh=0.0013):
    """Lens masses (Msun) and kinds by number: main-sequence stars and brown dwarfs (Kroupa 2001, 0.01-1 Msun, a present-day
    bulge/disc population with no stars above ~1 Msun), white dwarfs (0.6 +- 0.1), neutron stars (1.35 +- 0.1) and black holes
    (7.8 +- 1.5, the Galactic X-ray-binary mass distribution; Oezel et al. 2010). The number fractions are set so that, with
    this module's event-rate weighting toward (l, b) = (1, -3), black holes cause 0.9% of all events, white dwarfs ~11% and
    neutron stars ~3% (Gould 2000, ApJ 535, 928; PopSyCLE gives ~0.5-1% for black holes, Lam et al. 2020, ApJ 889, 31),
    and ~21% of events with tE > 120 d. The model makes too few long events overall (median tE 14 d against ~20 d
    observed), which if anything inflates the black-hole share of long events; treat P(BH) from it as an upper estimate."""
    rng = np.random.default_rng(2) if rng is None else rng
    kind = rng.choice(4, size=n, p=[1 - f_wd - f_ns - f_bh, f_wd, f_ns, f_bh])
    m = np.empty(n)
    k0 = kind == 0
    # Kroupa: dN/dm ~ m^-0.3 (0.01-0.08), m^-1.3 (0.08-0.5), m^-2.3 (0.5-1.0), sampled piecewise by inverse CDF
    edges = np.array([0.01, 0.08, 0.5, 1.0])
    alph = np.array([0.3, 1.3, 2.3])
    norm = np.array([1.0, 0.08**1.0, 0.08**1.0 * 0.5**1.0])   # continuity factors for m^-alpha
    seg = []
    for i in range(3):
        a, lo, hi = alph[i], edges[i], edges[i + 1]
        seg.append(norm[i] * (hi ** (1 - a) - lo ** (1 - a)) / (1 - a))
    seg = np.array(seg) / np.sum(seg)
    si = rng.choice(3, size=k0.sum(), p=seg)
    u = rng.uniform(size=k0.sum())
    lo, hi, a = edges[si], edges[si + 1], alph[si]
    m[k0] = (lo ** (1 - a) + u * (hi ** (1 - a) - lo ** (1 - a))) ** (1 / (1 - a))
    m[kind == 1] = np.clip(rng.normal(0.6, 0.1, (kind == 1).sum()), 0.45, 1.2)
    m[kind == 2] = np.clip(rng.normal(1.35, 0.1, (kind == 2).sum()), 1.1, 2.0)
    m[kind == 3] = np.clip(rng.normal(7.8, 1.5, (kind == 3).sum()), 4.0, 15.0)
    return m, np.array(["star", "WD", "NS", "BH"])[kind]
