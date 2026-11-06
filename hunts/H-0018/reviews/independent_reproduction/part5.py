"""(e): does a parallax-orbit degeneracy (a formal-error difference between mirrored orbits)
combined with the catalogue cut parallax_over_error>20000/P reproduce A(P) and the ratio in (b)?
Controls on the simulation, data-side discriminator, and a forward mock."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

rng = np.random.default_rng(2018)
T = 1038.0
XI = np.radians(45.0)
DAY = np.arange(-T / 2, T / 2, 0.05)
LAM = 2 * np.pi * DAY / 365.25 + 1.3
NU0 = 2 * np.pi * DAY * 5.8 / 365.25


def scan(lon, lat, sign_nu=1, mode="nsl", earth_sign=1):
    uv = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    e = np.array([-np.sin(lon), np.cos(lon), 0.0])
    n = np.array([-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)])
    s = np.stack([np.cos(LAM), np.sin(LAM), 0 * LAM], 1)
    nu = sign_nu * NU0 + 0.7
    y_ = np.stack([-np.sin(LAM), np.cos(LAM), 0 * LAM], 1)
    z = np.cos(XI) * s + np.sin(XI) * (np.cos(nu)[:, None] * y_ + np.sin(nu)[:, None] * np.array([0, 0, 1.0]))
    dp = z @ uv
    idx = np.where(np.sign(dp[:-1]) != np.sign(dp[1:]))[0]
    if mode == "random":   # same number of epochs, random times and scan angles
        t = np.sort(rng.uniform(-T / 2, T / 2, max(len(idx), 25)))
        psi = rng.uniform(0, 2 * np.pi, len(t))
        we, wn = np.sin(psi), np.cos(psi)
        lam_t = 2 * np.pi * t / 365.25 + 1.3
    else:
        t = DAY[idx]
        w = np.cross(z[idx], uv)
        w /= np.linalg.norm(w, axis=1, keepdims=True)
        we, wn = w @ e, w @ n
        lam_t = LAM[idx]
    lam_t = earth_sign * lam_t
    st = np.stack([np.cos(lam_t), np.sin(lam_t), 0 * lam_t], 1)
    pf = we * (st @ e) + wn * (st @ n)
    return t, we, wn, pf


def kep(t, P, ecc, tau):
    M = np.mod(2 * np.pi * (t - tau) / P + np.pi, 2 * np.pi) - np.pi
    E = M + ecc * np.sin(M)
    for _ in range(12):
        E = E - (E - ecc * np.sin(E) - M) / (1 - ecc * np.cos(E))
    return np.cos(E) - ecc, np.sqrt(1 - ecc**2) * np.sin(E)


def ti(inc, om, Om):
    return (np.cos(om) * np.cos(Om) - np.sin(om) * np.sin(Om) * np.cos(inc),
            np.cos(om) * np.sin(Om) + np.sin(om) * np.cos(Om) * np.cos(inc),
            -np.sin(om) * np.cos(Om) - np.cos(om) * np.sin(Om) * np.cos(inc),
            -np.sin(om) * np.sin(Om) + np.cos(om) * np.cos(Om) * np.cos(inc))


def sigma_plx(t, we, wn, pf, P, ecc, tau, abfg, nonlinear=True, with_plx=True, probe=None):
    X, Y = kep(t, P, ecc, tau)
    tA, tB, tF, tG = abfg
    cols = [we, wn, we * t, wn * t]
    if with_plx:
        cols.append(pf)
    cols += [wn * X, we * X, wn * Y, we * Y]
    if nonlinear:
        def m(P_, e_, tau_):
            x, y = kep(t, P_, e_, tau_)
            return we * (tB * x + tG * y) + wn * (tA * x + tF * y)
        dP, de, dt = P * 1e-4, 1e-4, P * 1e-4
        cols += [(m(P + dP, ecc, tau) - m(P - dP, ecc, tau)) / (2 * dP),
                 (m(P, ecc + de, tau) - m(P, ecc - de, tau)) / (2 * de),
                 (m(P, ecc, tau + dt) - m(P, ecc, tau - dt)) / (2 * dt)]
    M = np.column_stack(cols)
    sc = np.linalg.norm(M, axis=0)
    C = np.linalg.pinv((M / sc).T @ (M / sc), rcond=1e-10, hermitian=True) / np.outer(sc, sc)
    return np.sqrt(C[4, 4]) if with_plx else np.sqrt(C[0, 0])


def pair_lr(P, lat=None, ecc=None, cosi=None, **kw):
    """0.5 ln[sigma_plx(sense=+1)/sigma_plx(sense=-1)] for a mirrored pair."""
    scan_kw = {k: kw.pop(k) for k in list(kw) if k in ("sign_nu", "mode", "earth_sign")}
    lon = rng.uniform(0, 2 * np.pi)
    lat = np.arcsin(rng.uniform(-1, 1)) if lat is None else lat
    t, we, wn, pf = scan(lon, lat, **scan_kw)
    if len(t) < 14:
        return np.nan
    ecc = rng.uniform(0.05, 0.6) if ecc is None else ecc
    tau = rng.uniform(-P / 2, P / 2)
    ci = rng.uniform(0.02, 1) if cosi is None else cosi
    inc = np.arccos(ci)
    om, Om = rng.uniform(0, 2 * np.pi, 2)
    res = {}
    for cs in (+1, -1):
        abfg = ti(inc if cs > 0 else np.pi - inc, om, Om)
        res[-cs * np.sign(lat)] = sigma_plx(t, we, wn, pf, P, ecc, tau, abfg, **kw)
    return 0.5 * np.log(res[1] / res[-1])


def summary(xs):
    xs = np.array(xs); xs = xs[np.isfinite(xs)]
    return f"{np.exp(2*np.median(xs)):.3f} (mean {np.exp(2*xs.mean()):.3f}+-{2*xs.std()/np.sqrt(len(xs)):.3f}, N={len(xs)})"


N = 400
print("Simulation controls: sigma_plx(sense+)/sigma_plx(sense-) for mirrored isotropic pairs")
for P in (365.25, 730.0):
    print(f" P={P}")
    print("   nominal scan law, full fit     ", summary([pair_lr(P) for _ in range(N)]))
    print("   opposite precession            ", summary([pair_lr(P, sign_nu=-1) for _ in range(N)]))
    print("   random times and scan angles   ", summary([pair_lr(P, mode="random") for _ in range(N)]))
    print("   Earth orbit reversed           ", summary([pair_lr(P, earth_sign=-1) for _ in range(N)]))
    print("   no P,e,T columns (linear)      ", summary([pair_lr(P, nonlinear=False) for _ in range(N)]))
    print("   no parallax column (sig pos)   ", summary([pair_lr(P, with_plx=False) for _ in range(N)]))
print(" P=730 by |beta| band (sim ratio)")
for lo, hi in [(0, 15), (15, 30), (30, 45), (45, 60), (60, 90)]:
    print(f"   [{lo},{hi})", summary([pair_lr(730.0, lat=np.radians(rng.uniform(lo, hi)) * rng.choice([-1, 1])) for _ in range(N)]))
print(" P=730 by |cos i| band (sim ratio)")
for lo, hi in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1)]:
    print(f"   [{lo},{hi})", summary([pair_lr(730.0, cosi=rng.uniform(max(lo, .01), hi)) for _ in range(N)]))

# ---------------- data
d = pd.read_pickle("/tmp/repro_h18/d.pkl")
BINS = [50, 100, 150, 200, 250, 300, 340, 390, 450, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1600, 3000]
o = d[d.nss_solution_type == "Orbital"].copy()
o["gb"] = np.floor(o.phot_g_mean_mag * 2) / 2
o["bb"] = pd.cut(o.ecl_lat.abs(), [0, 15, 30, 45, 60, 90.01], right=False)
o["sref"] = o.groupby(["pbin", "gb", "bb"], observed=True).parallax_error.transform("median")
o["mref"] = o.parallax * o.period / 20000 / o.sref   # margin with a sense-blind reference error
print("\nData: A vs sense-blind margin (parallax*P/20000/median sigma in cell of P,G,|beta|); Orbital")
for label, lo_p, hi_p in [("P[300,1100)", 300, 1100), ("P[600,800)", 600, 800), ("P[340,450)", 340, 450), ("P[1100,3000)", 1100, 3000)]:
    g = o[(o.period >= lo_p) & (o.period < hi_p)]
    print(" ", label)
    for lo, hi in [(0, 1), (1, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 10), (10, 20), (20, 1e9)]:
        k = g[(g.mref >= lo) & (g.mref < hi)]
        if len(k) > 20:
            m = k.sense.mean()
            print(f"    [{lo},{hi}) A={m:+.4f}+-{np.sqrt((1-m*m)/len(k)):.4f} N={len(k)} err_ratio={np.median(k.parallax_error[k.sense>0])/np.median(k.parallax_error[k.sense<0]):.3f}")

# Binned simulation + forward mock
print("\nBin: sim ratio | observed ratio from (b) | A_obs Orbital | A_mock")
obs_ratio = {}; a_obs = []; a_mock = []; sim_ratio = []; obs_r = []
o12 = o[(o.phot_g_mean_mag >= 12) & (o.phot_g_mean_mag < 16)]
for lo, hi in zip(BINS[:-1], BINS[1:]):
    g = o[(o.period >= lo) & (o.period < hi)]
    mid = np.sqrt(lo * hi)
    eccs = g.eccentricity.clip(0.02, 0.9).values
    bands = [(0, 15), (15, 30), (30, 45), (45, 60), (60, 90.01)]
    lrs = {}
    for b in bands:
        vals = [pair_lr(rng.uniform(lo, hi), lat=np.radians(rng.uniform(b[0], b[1])) * rng.choice([-1, 1]),
                        ecc=rng.choice(eccs), sign_nu=rng.choice([-1, 1])) for _ in range(160)]
        vals = np.array(vals); lrs[b] = vals[np.isfinite(vals)]
    all_lr = np.concatenate(list(lrs.values()))
    # forward mock: mirror each observed source using a simulated lr of its period and |beta| band
    lr = np.empty(len(g)); ab = g.ecl_lat.abs().values
    for b in bands:
        k = (ab >= b[0]) & (ab < b[1])
        lr[k] = rng.choice(lrs[b], k.sum())
    s0 = g.parallax_error.values * np.exp(-g.sense.values * lr)
    cut = 20000 / g.period.values
    plus = g.parallax.values / (s0 * np.exp(lr)) > cut
    minus = g.parallax.values / (s0 * np.exp(-lr)) > cut
    am = (plus.sum() - minus.sum()) / (plus.sum() + minus.sum())
    ao = g.sense.mean()
    h = o12[(o12.period >= lo) & (o12.period < hi)]
    r_o = np.median(h.parallax_error[h.sense > 0]) / np.median(h.parallax_error[h.sense < 0])
    r_s = np.exp(2 * np.median(all_lr))
    a_obs.append(ao); a_mock.append(am); sim_ratio.append(r_s); obs_r.append(r_o)
    print(f"[{lo},{hi}) sim={r_s:.3f} obs={r_o:.3f} A_obs={ao:+.3f} A_mock={am:+.3f}")
print("Spearman sim ratio vs obs ratio", spearmanr(sim_ratio, obs_r))
print("Spearman A_obs vs ln(sim ratio)", spearmanr(a_obs, np.log(sim_ratio)))
print("Spearman A_obs vs A_mock", spearmanr(a_obs, a_mock))
print("Pearson A_obs vs A_mock", np.corrcoef(a_obs, a_mock)[0, 1], "mean A_mock", np.mean(a_mock), "mean A_obs", np.mean(a_obs))

# Population-level check of the same discriminator on AstroSpectroSB1
a = d[d.nss_solution_type == "AstroSpectroSB1"]
print("\nAstroSpectroSB1 frac with poe*P/20000<1:", ((a.parallax / a.parallax_error * a.period / 20000) < 1).mean(),
      " median margin", np.median(a.parallax / a.parallax_error * a.period / 20000))
