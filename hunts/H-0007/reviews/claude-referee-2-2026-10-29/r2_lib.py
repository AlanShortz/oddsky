"""Referee 2: independent microlensing fit library for J040025 (written from scratch; does not import scripts/hunt_h0007_lensfit.py).

Data: ATLAS forced photometry binned per night, per band AND per unit (so unit offsets can be fitted), normalised by each band's
(optionally each unit's) baseline. Geometry: geocentric apparent Sun from astropy get_sun (GCRS), a different route from the
investigators' negative barycentric Earth; checked against MulensModel in r3_geometry.py.
Convention (Gould 2004, as MulensModel): Delta s = Sun position seen from Earth projected on (N, E), minus its value and
velocity at t0par; Delta tau = piE . Delta s; Delta beta = piE x Delta s (sign absorbed by u0 sign).
"""
import numpy as np, pandas as pd
from astropy.coordinates import SkyCoord, get_sun
from astropy.time import Time
import astropy.units as u
from oddsky.data import atlas

RA, DEC = 60.1073758, 32.5909576
T0PAR = 58011.0
ATLAS = "hunts/H-0007/work/atlas_J040025.txt"
NEOWISE = pd.DataFrame({"mjd": [57993.05, 57993.05], "f": [2.731, 2.716], "e": [0.03, 0.035], "band": ["W1", "W2"], "unit": ["NW", "NW"]})


def load_raw(path=ATLAS, clip=True):
    r = atlas.parse(open(path).read())
    r = r[r.F.isin(["c", "o"]) & (r.dujy > 0) & (r.dujy < 1000) & (r.ujy > 0) & (r.err == 0)].copy()
    r["unit"] = r.obs.str[:3]
    if clip:
        # single-frame outliers: > 15% from the median of the same night, band and unit (e.g. 58027.552, f = 1.06 among 2.8s)
        key = [r.F, r.unit, np.floor(r.mjd - 0.3)]
        med = r.groupby(key).ujy.transform("median")
        r = r[np.abs(r.ujy - med) < 0.15 * med]
    return r


def nightly(r, sat=12.2, per_unit_base=False, frac=0.01, window=(57700, 58300), drop_below=0.8, neowise=True,
            chi_max=None, units=None, event=(57900, 58200)):
    """Nightly medians per band/unit; error = hypot(median dujy/sqrt(k), baseline night-to-night scatter, frac*f)."""
    r = r[r.m > sat] if sat is not None else r
    if chi_max is not None:
        r = r[r.chi_n < chi_max]
    if units is not None:
        r = r[r.unit.isin(units)]
    r = r.assign(night=np.floor(r.mjd - 0.3))
    n = r.groupby(["F", "unit", "night"]).agg(mjd=("mjd", "median"), ujy=("ujy", "median"), dujy=("dujy", "median"),
                                              k=("ujy", "size")).reset_index()
    off = (n.mjd < event[0]) | (n.mjd > event[1])
    out = []
    keys = ["F", "unit"] if per_unit_base else ["F"]
    for key, g in n.groupby(keys):
        b = g[off.loc[g.index]]
        if len(b) < 10:
            # too few baseline nights for this unit: fall back to the band baseline
            b = n[off & (n.F == g.F.iloc[0])]
        base = b.ujy.median()
        floor = 1.4826 * np.median(np.abs(b.ujy - base))
        out.append(g.assign(f=g.ujy / base, e=np.hypot(g.dujy / np.sqrt(g.k), floor) / base))
    d = pd.concat(out)
    d = d[(d.mjd > window[0]) & (d.mjd < window[1])]
    d = d[d.f >= drop_below] if drop_below is not None else d
    d = d.assign(e=np.hypot(d.e, frac * d.f), band=d.F)
    d = d[["mjd", "f", "e", "band", "unit", "k"]]
    if neowise:
        d = pd.concat([d, NEOWISE.assign(k=13)], ignore_index=True)
    return d.sort_values("mjd").reset_index(drop=True)


_c = SkyCoord(RA * u.deg, DEC * u.deg)
_E = np.array([-np.sin(_c.ra.rad), np.cos(_c.ra.rad), 0.0])
_N = np.array([-np.sin(_c.dec.rad) * np.cos(_c.ra.rad), -np.sin(_c.dec.rad) * np.sin(_c.ra.rad), np.cos(_c.dec.rad)])


def sun_NE(mjd):
    s = get_sun(Time(np.atleast_1d(mjd), format="mjd"))  # GCRS, geocentric apparent
    xyz = s.cartesian.xyz.to(u.au).value.T
    return xyz @ _N, xyz @ _E


class Geo:
    """Precomputed Delta s (N, E) for given times, t0par."""
    def __init__(self, t, t0par=T0PAR):
        tg = np.linspace(57600, 58400, 1601)
        sn, se = sun_NE(tg)
        n0, e0 = np.interp(t0par, tg, sn), np.interp(t0par, tg, se)
        h = 0.5
        vn = (np.interp(t0par + h, tg, sn) - np.interp(t0par - h, tg, sn)) / (2 * h)
        ve = (np.interp(t0par + h, tg, se) - np.interp(t0par - h, tg, se)) / (2 * h)
        self.dN = np.interp(t, tg, sn) - n0 - vn * (t - t0par)
        self.dE = np.interp(t, tg, se) - e0 - ve * (t - t0par)
        self.t0par = t0par
        # acceleration of the projected Sun at t0par (AU/d^2), for pi_par / pi_perp decomposition
        an = (np.interp(t0par + 5, tg, sn) - 2 * n0 + np.interp(t0par - 5, tg, sn)) / 25
        ae = (np.interp(t0par + 5, tg, se) - 2 * e0 + np.interp(t0par - 5, tg, se)) / 25
        self.acc = np.array([an, ae])


def pacz(uu):
    return (uu**2 + 2) / (uu * np.sqrt(uu**2 + 4))


def traj_static(t, t0, tE, u0):
    return (t - t0) / tE, np.full_like(t, u0, dtype=float)


def traj_par(t, geo, t0, tE, u0, piN, piE):
    tau = (t - t0) / tE + piN * geo.dN + piE * geo.dE
    beta = u0 + (-piN * geo.dE + piE * geo.dN)
    return tau, beta


def traj_acc(t, t0, tE, u0, a_tau, a_beta, j_tau=0.0, j_beta=0.0, t0par=T0PAR):
    """Generic smooth asymmetry: source-lens relative acceleration (and jerk) in Einstein units per tE^2 (tE^3)."""
    x = (t - t0par) / tE
    return (t - t0) / tE + 0.5 * a_tau * x**2 + j_tau * x**3 / 6, u0 + 0.5 * a_beta * x**2 + j_beta * x**3 / 6


def traj_xal(t, t0, tE, u0, xiN, xiE, P, phi0, inc, t0par=T0PAR):
    """Circular-orbit xallarap. Source orbit in sky plane: (cos ph, cos i sin ph), rotated so that (xiN, xiE) sets the
    amplitude (|xi|) and node orientation. Offsets taken relative to value and velocity at t0par, as for parallax."""
    w = 2 * np.pi / P
    def pos(tt):
        ph = w * (tt - t0par) + phi0
        return np.cos(ph), np.cos(inc) * np.sin(ph)
    def vel():
        ph = phi0
        return -w * np.sin(ph), w * np.cos(inc) * np.cos(ph)
    x, y = pos(t); x0, y0 = pos(t0par); vx, vy = vel()
    dx = x - x0 - vx * (t - t0par); dy = y - y0 - vy * (t - t0par)
    xi = np.hypot(xiN, xiE); th = np.arctan2(xiE, xiN)
    dN = xi * (dx * np.cos(th) - dy * np.sin(th)); dE = xi * (dx * np.sin(th) + dy * np.cos(th))
    # unit-amplitude pi-like vector along N: Delta tau = dN, Delta beta = dE (same algebra as parallax with piE=(1,0))
    return (t - t0) / tE + dN, u0 + dE


def flux(A, d, fs=None, scale=None):
    """fs: dict band->source fraction (default 1). scale: dict unit->multiplicative zero-point factor (default 1)."""
    f = A.copy()
    if fs:
        for b, v in fs.items():
            m = d.band.values == b
            f[m] = v * A[m] + 1 - v
    if scale:
        for un, v in scale.items():
            f[d.unit.values == un] *= v
    return f
