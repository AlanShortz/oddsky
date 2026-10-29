"""H-0007: joint microlensing fit for J040025.77+323527.4 (ATLAS c/o nightly bins + NEOWISE W1/W2 visit).

Error model: ATLAS points are binned per night and band (median), and each band gets an error floor equal to the robust
night-to-night scatter of its own baseline (2015-2017 Jun and 2018-2026), so chi2/dof ~ 1 off-event. Nights more than 20% below
baseline are dropped, a 1% flux-proportional floor is added, and points with m < 12.2 are
excluded (near ATLAS saturation). Models: (a) standard point lens, no blending (fs = 1); (b) fs free per band; (c) annual
parallax (piE_N, piE_E; geocentric frame, t0par = 58011). Uncertainties from an MCMC (emcee) on model (c).
usage: hunt_h0007_lensfit.py ATLAS_TXT OUT_PREFIX

CAUTION (second referee, hunts/H-0007/reviews/claude-referee-2-2026-10-29.md): the MCMC explores one u0 mode and treats nightly
residuals as independent (lag-1 autocorrelation ~0.4), so its intervals are 4-10x too narrow. pi_E,perp moves with a 1% zero point
for ATLAS unit 02a. Quote the referee's ranges (tE 47-56 d, |piE| 0.6-1.6), not this script's.
"""
import sys, json
import numpy as np, pandas as pd
from scipy.optimize import least_squares
from astropy.coordinates import SkyCoord, get_body_barycentric
from astropy.time import Time
import astropy.units as u
from oddsky.data import atlas

RA, DEC = 60.1073758, 32.5909576
raw = atlas.parse(open(sys.argv[1]).read())
r = raw[(raw.dujy > 0) & (raw.dujy < 1000) & raw.F.isin(["c", "o"]) & (raw.m > 12.2)].copy()
r["night"] = np.floor(r.mjd - 0.3)
n = r.groupby(["F", "night"]).agg(mjd=("mjd", "median"), ujy=("ujy", "median"), dujy=("dujy", "median"), k=("ujy", "size")).reset_index()
off = (n.mjd < 57900) | (n.mjd > 58200)
rows = []
for F, g in n.groupby("F"):
    b = g[off.loc[g.index]]
    base = b.ujy.median(); floor = 1.4826 * np.median(np.abs(b.ujy - base))
    g = g.assign(f=g.ujy / base, e=np.hypot(g.dujy / np.sqrt(g.k), floor) / base, band=F)
    rows.append(g); print(f"ATLAS {F}: baseline {base:.0f} uJy, nightly floor {floor/base*100:.2f}%")
d = pd.concat(rows)
d = d[(d.mjd > 57700) & (d.mjd < 58300)].copy()
# dropouts: nights > 20% below baseline (clouds, bad subtraction); none of them are physical for a brightening event
drop = d[d.f < 0.8]; print(f"dropped {len(drop)} dropout night(s): {drop.mjd.round(2).tolist()} f={drop.f.round(2).tolist()}")
d = d[d.f >= 0.8]
d["e"] = np.hypot(d.e, 0.01 * d.f)  # 1% flux-proportional calibration floor
# NEOWISE visit (exposure medians; error = rms/sqrt(n) plus 1% calibration)
nw = pd.DataFrame({"mjd": [57993.08, 57993.08], "f": [2.731, 2.716], "e": [0.03, 0.035], "band": ["W1", "W2"]})
d = pd.concat([d[["mjd", "f", "e", "band"]], nw], ignore_index=True)
t, f, e, band = d.mjd.values, d.f.values, d.e.values, d.band.values
print(f"{len(d)} points: " + ", ".join(f"{b} {int((band == b).sum())}" for b in np.unique(band)))

# annual parallax offsets (Gould 2004): Sun position projected on the sky, minus its value and derivative at t0par
c = SkyCoord(RA * u.deg, DEC * u.deg)
east = np.array([-np.sin(c.ra.rad), np.cos(c.ra.rad), 0.0])
north = np.array([-np.sin(c.dec.rad) * np.cos(c.ra.rad), -np.sin(c.dec.rad) * np.sin(c.ra.rad), np.cos(c.dec.rad)])
def sun_proj(mjd):
    xyz = -get_body_barycentric("earth", Time(mjd, format="mjd")).xyz.to(u.au).value.T  # Sun as seen from Earth (barycentre ~ Sun)
    return xyz @ north, xyz @ east
T0PAR = 58011.0
tg = np.unique(np.r_[t, np.linspace(57700, 58300, 601)])
sn, se = sun_proj(tg)
dt = 1.0; sn1, se1 = sun_proj(np.array([T0PAR - dt, T0PAR, T0PAR + dt]))
vn, ve = (sn1[2] - sn1[0]) / (2 * dt), (se1[2] - se1[0]) / (2 * dt)
dN = np.interp(t, tg, sn) - sn1[1] - vn * (t - T0PAR)
dE = np.interp(t, tg, se) - se1[1] - ve * (t - T0PAR)

def mag(p, par):
    t0, tE, u0 = p[:3]
    tau = (t - t0) / tE; beta = np.full_like(t, u0)
    if par:
        piN, piE = p[3], p[4]
        tau = tau + piN * dN + piE * dE
        beta = beta + (-piN * dE + piE * dN)
    uu = np.sqrt(tau**2 + beta**2)
    return (uu**2 + 2) / (uu * np.sqrt(uu**2 + 4))

def model(p, kind):
    if kind == "a":
        return mag(p, False)
    if kind == "b":
        A = mag(p[:3], False); fc, fo = p[3], p[4]
        fs = np.where(band == "c", fc, np.where(band == "o", fo, 1.0))
        return fs * A + 1 - fs
    return mag(p, True)

fits = {}
for kind, p0, lo, hi in [("a", [58011, 45, 0.1], [57990, 5, 1e-4], [58030, 300, 2]),
                         ("b", [58011, 45, 0.1, 1, 1], [57990, 5, 1e-4, .05, .05], [58030, 300, 2, 1.5, 1.5]),
                         ("c", [58011, 45, 0.1, 0, 0], [57990, 5, -2, -3, -3], [58030, 300, 2, 3, 3])]:
    best = None
    for u0s in (0.02, 0.1, 0.2, -0.1) if kind == "c" else (0.05, 0.1, 0.2):
        q = list(p0); q[2] = u0s
        if kind != "c" and u0s < 0:
            continue
        rr = least_squares(lambda p: (model(p, kind) - f) / e, q, bounds=(lo, hi))
        if best is None or rr.cost < best.cost:
            best = rr
    chi2 = 2 * best.cost
    fits[kind] = {"p": best.x.tolist(), "chi2": chi2, "dof": len(t) - len(best.x)}
    print(f"model {kind}: chi2 {chi2:.1f} / dof {len(t) - len(best.x)}; params {np.round(best.x, 4).tolist()}")
print(f"parallax improves chi2 by {fits['a']['chi2'] - fits['c']['chi2']:.1f} for 2 extra parameters")

import emcee
lo, hi = np.array([57990, 5, -2, -3, -3]), np.array([58030, 300, 2, 3, 3])
def lnp(p):
    if np.any(p < lo) or np.any(p > hi):
        return -np.inf
    return -0.5 * np.sum(((model(p, "c") - f) / e) ** 2)
nw_, nd = 32, 5
start = np.array(fits["c"]["p"]) + 1e-3 * np.random.default_rng(1).standard_normal((nw_, nd))
s = emcee.EnsembleSampler(nw_, nd, lnp); s.run_mcmc(start, 4000, progress=False)
ch = s.get_chain(discard=1500, thin=10, flat=True)
q = np.percentile(ch, [2.5, 16, 50, 84, 97.5], axis=0)
names = ["t0", "tE", "u0", "piE_N", "piE_E"]
summ = {nm: {"median": q[2, i], "lo68": q[1, i], "hi68": q[3, i], "lo95": q[0, i], "hi95": q[4, i]} for i, nm in enumerate(names)}
piE = np.hypot(ch[:, 3], ch[:, 4]); summ["piE"] = dict(zip(["lo95", "lo68", "median", "hi68", "hi95"], np.percentile(piE, [2.5, 16, 50, 84, 97.5])))
Amax = (ch[:, 2]**2 + 2) / (np.abs(ch[:, 2]) * np.sqrt(ch[:, 2]**2 + 4)); summ["Amax"] = dict(zip(["lo95", "lo68", "median", "hi68", "hi95"], np.percentile(Amax, [2.5, 16, 50, 84, 97.5])))
for k, v in summ.items():
    print(f"{k:6s} median {v['median']:.4g}  68% [{v['lo68']:.4g}, {v['hi68']:.4g}]  95% [{v['lo95']:.4g}, {v['hi95']:.4g}]")
json.dump({"fits": fits, "mcmc": summ, "n_points": int(len(t))}, open(f"{sys.argv[2]}.json", "w"), indent=1, default=float)
d.assign(model_a=model(fits["a"]["p"], "a"), model_c=model(fits["c"]["p"], "c")).to_csv(f"{sys.argv[2]}.csv", index=False)
