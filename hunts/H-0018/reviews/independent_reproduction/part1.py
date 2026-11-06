"""Independent reproduction: parts (a), (b), (c), ecl_lat check, sign tests."""
import os
import numpy as np
import pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord, BarycentricMeanEcliptic

P = os.path.expanduser("~/oddsky-runs/h0018/data/nss/nss_astrometric.csv")
df = pd.read_csv(P)
print("all rows", len(df))
print(df.nss_solution_type.value_counts().to_string())
d = df[df.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])].copy()
print("kept", len(d), "unique source_id", d.source_id.nunique())
print("types per duplicated id:", d[d.source_id.duplicated(keep=False)].groupby("source_id").nss_solution_type.apply(tuple).value_counts().to_dict())
print("exact dup rows", d.duplicated().sum())
print("NaN", d[["a_thiele_innes", "b_thiele_innes", "f_thiele_innes", "g_thiele_innes", "period", "ecl_lat", "parallax_error", "ra", "dec"]].isna().sum().to_dict())
print("period range", d.period.min(), d.period.max())

# ---- 1. ecl_lat / b verification
c = SkyCoord(d.ra.values * u.deg, d.dec.values * u.deg, frame="icrs")
ecl = c.transform_to(BarycentricMeanEcliptic())
dbeta = ecl.lat.deg - d.ecl_lat.values
print("ecl_lat diff (astropy BarycentricMeanEcliptic - file), all rows: max abs [arcsec]", np.abs(dbeta).max() * 3600, "median", np.median(dbeta) * 3600)
print("sign(ecl_lat) mismatches", (np.sign(ecl.lat.deg) != np.sign(d.ecl_lat.values)).sum())
gal = c.galactic
print("b diff max abs [arcsec]", np.abs(gal.b.deg - d.b.values).max() * 3600)

# ---- 2. Sign formula and synthetic verification
def s_of(A, B, F, G):
    return np.sign(B * F - A * G)

# Check: east x north = +n_hat at random positions (finite differences of unit vector)
rng = np.random.default_rng(18)
def unit(ra, dec):
    return np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], -1)
def en(ra, dec):
    e = np.stack([-np.sin(ra), np.cos(ra), 0 * ra], -1)
    n = np.stack([-np.sin(dec) * np.cos(ra), -np.sin(dec) * np.sin(ra), np.cos(dec)], -1)
    return e, n
ra = rng.uniform(0, 2 * np.pi, 1000); dec = np.arcsin(rng.uniform(-1, 1, 1000))
e, n = en(ra, dec)
eps = 1e-6
fd_e = (unit(ra + eps, dec) - unit(ra - eps, dec)) / (2 * eps)
fd_e /= np.linalg.norm(fd_e, axis=1, keepdims=True)
print("e_hat vs d(unit)/d(ra) max diff", np.abs(fd_e - e).max())
print("min (e x n).n_hat", np.min(np.sum(np.cross(e, n) * unit(ra, dec), 1)), "max", np.max(np.sum(np.cross(e, n) * unit(ra, dec), 1)))

# Time-domain check: kepler orbit, random TI numbers, direct r x v along n_hat
def kepler_xy(M, ecc):
    E = M.copy()
    for _ in range(60):
        E = E - (E - ecc * np.sin(E) - M) / (1 - ecc * np.cos(E))
    return np.cos(E) - ecc, np.sqrt(1 - ecc**2) * np.sin(E)
N = 2000
cA, cB, cF, cG = rng.normal(size=(4, N))
ecc = rng.uniform(0, 0.9, N)
ra = rng.uniform(0, 2 * np.pi, N); dec = np.arcsin(rng.uniform(-1, 1, N))
e, n = en(ra, dec); nh = unit(ra, dec)
agree = 0
for i in range(N):
    M = np.linspace(0, 2 * np.pi, 400)
    X, Y = kepler_xy(M, ecc[i])
    # confirm X->Y counter-clockwise with M
    assert np.all(np.diff(np.unwrap(np.arctan2(Y, X))) > 0)
    r = np.outer(cB[i] * X + cG[i] * Y, e[i]) + np.outer(cA[i] * X + cF[i] * Y, n[i])
    v = np.gradient(r, M, axis=0)
    L = np.cross(r, v) @ nh[i]
    agree += np.sign(np.median(L)) == s_of(cA[i], cB[i], cF[i], cG[i])
print(f"time-domain r x v . n_hat vs sign(BF-AG): {agree}/{N}")

# Campbell -> TI: isotropic orbits; sign vs cos i; mean sense on isotropic population
N = 2_000_000
inc = np.arccos(rng.uniform(-1, 1, N)); om = rng.uniform(0, 2 * np.pi, N); Om = rng.uniform(0, 2 * np.pi, N)
tA = np.cos(om) * np.cos(Om) - np.sin(om) * np.sin(Om) * np.cos(inc)
tB = np.cos(om) * np.sin(Om) + np.sin(om) * np.cos(Om) * np.cos(inc)
tF = -np.sin(om) * np.cos(Om) - np.cos(om) * np.sin(Om) * np.cos(inc)
tG = -np.sin(om) * np.sin(Om) + np.cos(om) * np.cos(Om) * np.cos(inc)
print("BF-AG == -cos i max err", np.abs(tB * tF - tA * tG + np.cos(inc)).max())
print("isotropic mean s", s_of(tA, tB, tF, tG).mean(), "+-", 1 / np.sqrt(N))

# Parallax ellipse mimicry: sign of parallax motion vs ecliptic pole
obl = np.deg2rad(23.4392911)
ra = rng.uniform(0, 2 * np.pi, 5000); dec = np.arcsin(rng.uniform(-1, 1, 5000))
e, n = en(ra, dec); nh = unit(ra, dec)
lam = np.linspace(0, 2 * np.pi, 400)
Re = np.stack([np.cos(lam), np.sin(lam) * np.cos(obl), np.sin(lam) * np.sin(obl)], 1)  # Earth (ecliptic prograde)
NEP = np.array([0, -np.sin(obl), np.cos(obl)])
beta = np.arcsin(nh @ NEP)
sg = np.empty(5000)
for i in range(5000):
    disp = -(Re - np.outer(Re @ nh[i], nh[i]))  # apparent displacement of star
    vel = np.gradient(disp, lam, axis=0)
    sg[i] = np.sign(np.median(np.cross(disp, vel) @ nh[i]))
print("parallax-ellipse pseudo-orbit: mean(s*sign(beta)) =", np.mean(sg * np.sign(beta)))

# ---- external anchors
d["s"] = s_of(d.a_thiele_innes, d.b_thiele_innes, d.f_thiele_innes, d.g_thiele_innes)
print("s==0:", (d.s == 0).sum())
d["sense"] = d.s * np.sign(d.ecl_lat)
d["cosi_like"] = (d.a_thiele_innes * d.g_thiele_innes - d.b_thiele_innes * d.f_thiele_innes)
for name, sid in [("Gaia BH1", 4373465352415301632), ("Gaia BH2", 5870569352746779008)]:
    r = d[d.source_id == sid]
    if len(r):
        r = r.iloc[0]
        A, B, F, G = r.a_thiele_innes, r.b_thiele_innes, r.f_thiele_innes, r.g_thiele_innes
        u_ = 0.5 * (A * A + B * B + F * F + G * G)
        v_ = A * G - B * F
        a2 = u_ + np.sqrt(u_**2 - v_**2)
        print(name, r.nss_solution_type, "P", r.period, "s", r.s, "i_from_TI [deg]", np.degrees(np.arccos(v_ / a2)))
    else:
        print(name, "not in sample")

BINS = [50, 100, 150, 200, 250, 300, 340, 390, 450, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1600, 3000]
d["pbin"] = pd.cut(d.period, BINS, right=False)
print("outside bins:", d.pbin.isna().sum(), "period<50:", (d.period < 50).sum(), ">=3000:", (d.period >= 3000).sum())
def mean_err(x):
    x = np.asarray(x)
    m = x.mean(); return m, np.sqrt((1 - m**2) / len(x)), len(x)

print("\n(a) A overall (all, in-bin)")
print("all %.5f +- %.5f N=%d" % mean_err(d.sense))
print("in bins %.5f +- %.5f N=%d" % mean_err(d.sense[d.pbin.notna()]))
for t in ["Orbital", "AstroSpectroSB1"]:
    print(t, "%.5f +- %.5f N=%d" % mean_err(d.sense[d.nss_solution_type == t]))
print("bin            N      A       err     z  | Orbital A err N | ASB1 A err N")
for b, g in d.groupby("pbin", observed=False):
    m, se, nn = mean_err(g.sense)
    o = g[g.nss_solution_type == "Orbital"].sense
    a = g[g.nss_solution_type == "AstroSpectroSB1"].sense
    so = "%.3f %.3f %d" % mean_err(o) if len(o) else "-"
    sa = "%.3f %.3f %d" % mean_err(a) if len(a) else "-"
    print(f"{str(b):16s} {nn:6d} {m:+.4f} {se:.4f} {m/se:+.1f} | {so} | {sa}")

print("\n(b) Orbital 12<=G<16 parallax_error ratio sense>0 / sense<0")
o = d[(d.nss_solution_type == "Orbital") & (d.phot_g_mean_mag >= 12) & (d.phot_g_mean_mag < 16)].copy()
o["gbin"] = np.floor(o.phot_g_mean_mag).astype(int)
def ratio(g):
    tot = 0.0; w = 0
    per = {}
    for gb, h in g.groupby("gbin"):
        p = h.parallax_error[h.sense > 0]; q = h.parallax_error[h.sense < 0]
        if len(p) == 0 or len(q) == 0:
            continue
        r = np.median(p) / np.median(q)
        tot += len(h) * r; w += len(h); per[gb] = r
    return (tot / w if w else np.nan), w, per
print("all-P ratio", ratio(o)[:2])
rngb = np.random.default_rng(1)
for b, g in o.groupby("pbin", observed=False):
    r, w, per = ratio(g)
    vals = g[["gbin", "parallax_error", "sense"]].to_numpy()
    boots = []
    for _ in range(300):
        idx = rngb.integers(0, len(g), len(g))
        h = pd.DataFrame(vals[idx], columns=["gbin", "parallax_error", "sense"])
        boots.append(ratio(h)[0])
    print(f"{str(b):16s} N={w:6d} ratio={r:.4f} +-{np.std(boots):.4f}  " + " ".join(f"G{k}:{v:.3f}" for k, v in per.items()))

print("\n(c) dipole, s on (1,nX,nY,nZ), Galactic Cartesian")
def ols_robust(y, X):
    XtX = X.T @ X
    XtXi = np.linalg.inv(XtX)
    beta = XtXi @ (X.T @ y)
    res = y - X @ beta
    lev = np.einsum("ij,jk,ik->i", X, XtXi, X)
    meat0 = (X * (res**2)[:, None]).T @ X
    meat3 = (X * (res**2 / (1 - lev) ** 2)[:, None]).T @ X
    return beta, np.sqrt(np.diag(XtXi @ meat0 @ XtXi)), np.sqrt(np.diag(XtXi @ meat3 @ XtXi)), XtXi @ meat3 @ XtXi

gn = gal.cartesian.xyz.value.T
nep_gal = SkyCoord(0 * u.deg, 90 * u.deg, frame=BarycentricMeanEcliptic()).galactic
nep = nep_gal.cartesian.xyz.value
print("NEP galactic l,b", nep_gal.l.deg, nep_gal.b.deg, "xyz", nep)
def dipole(y, n_, label):
    X = np.column_stack([np.ones(len(y)), n_])
    b, hc0, hc3, cov = ols_robust(np.asarray(y, float), X)
    v = b[1:]
    ang_gp = np.degrees(np.arccos(v[2] / np.linalg.norm(v)))
    ang_ep = np.degrees(np.arccos(v @ nep / np.linalg.norm(v)))
    # bootstrap-free angular uncertainty by Gaussian draws
    r = np.random.default_rng(3).multivariate_normal(v, cov[1:, 1:], 20000)
    rn = r / np.linalg.norm(r, axis=1, keepdims=True)
    a_gp = np.degrees(np.arccos(rn[:, 2])); a_ep = np.degrees(np.arccos(rn @ nep))
    print(f"{label}: N={len(y)} c0={b[0]:+.4f}+-{hc3[0]:.4f} X={b[1]:+.4f}+-{hc3[1]:.4f} Y={b[2]:+.4f}+-{hc3[2]:.4f} Z={b[3]:+.4f}+-{hc3[3]:.4f} |v|={np.linalg.norm(v):.4f}"
          f" ang(NGP)={ang_gp:.1f} [{a_gp.std():.1f}] ang(NEP)={ang_ep:.1f} [{a_ep.std():.1f}]")
    return b
dipole(d.s, gn, "all")
for t in ["Orbital", "AstroSpectroSB1"]:
    m = (d.nss_solution_type == t).values
    dipole(d.s[m], gn[m], t)
for lo, hi in [(50, 340), (340, 390), (390, 3000), (50, 200), (200, 340), (390, 700), (700, 1100), (1100, 3000)]:
    m = ((d.period >= lo) & (d.period < hi)).values
    dipole(d.s[m], gn[m], f"P[{lo},{hi})")

print("\n(e) hemisphere split")
N_ = d.ecl_lat > 0
print("fN", N_.mean(), "N north", N_.sum(), "south", (~N_).sum())
print("overall mean(s) all %.5f +- %.5f" % mean_err(d.s)[:2])
print("overall mean(s|N) %.5f +- %.5f N=%d" % mean_err(d.s[N_]))
print("overall mean(s|S) %.5f +- %.5f N=%d" % mean_err(d.s[~N_]))
print("identity check A vs fN*mN - fS*mS:", d.sense.mean(), N_.mean() * d.s[N_].mean() - (~N_).mean() * d.s[~N_].mean())
print("bin  mean(s|N) err  mean(s|S) err   sense_N  sense_S  (sense_S=-mean(s|S))  diff/sigma")
for b, g in d.groupby("pbin", observed=False):
    n1 = g[g.ecl_lat > 0].s; n2 = g[g.ecl_lat < 0].s
    m1, e1, k1 = mean_err(n1); m2, e2, k2 = mean_err(n2)
    print(f"{str(b):16s} {m1:+.4f} {e1:.4f} ({k1}) {m2:+.4f} {e2:.4f} ({k2})  A_N={m1:+.3f} A_S={-m2:+.3f}  diff_z={(m1+m2)/np.hypot(e1,e2):+.1f}")

d.to_pickle("/tmp/repro_h18/d.pkl")
