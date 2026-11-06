"""After the referee, exploratory. Recomputes what the report found and two further tests of the mechanism."""
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
import wb  # noqa: E402
import chiral_sim as cs  # noqa: E402
from nss_rv_test import load  # noqa: E402

warnings.filterwarnings("ignore")
a = pd.concat([load(False), load(True)])
a = a[a.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])].copy()
o = a[a.nss_solution_type == "Orbital"]


def ratio(df):
    """N-weighted mean over unit G bins, 12 <= G < 16, of median parallax_error +NEP / -NEP, with a bootstrap error."""
    rng = np.random.default_rng(3)
    df = df[(df.phot_g_mean_mag >= 12) & (df.phot_g_mean_mag < 16)]

    def one(x):
        vals, w = [], []
        for g in range(12, 16):
            s = x[(x.phot_g_mean_mag >= g) & (x.phot_g_mean_mag < g + 1)]
            p, m = s[s.sense > 0].parallax_error, s[s.sense < 0].parallax_error
            if min(len(p), len(m)) >= 5:
                vals.append(np.median(p) / np.median(m))
                w.append(len(p) + len(m))
        return np.average(vals, weights=w) if vals else np.nan

    boots = [one(df.iloc[rng.integers(0, len(df), len(df))]) for _ in range(200)]
    return one(df), np.nanstd(boots), len(df)


print("1. Gaia's own knockout: pseudo-circular solutions (e and T fixed, Halbwachs+ 2023 sec 5.2) vs low-e free solutions")
for lo, hi in [(450, 600), (600, 700), (700, 800), (800, 900), (900, 1100)]:
    z = o[(o.period >= lo) & (o.period < hi)]
    pc, fr = z[z.eccentricity < 5e-4], z[(z.eccentricity >= 6e-3) & (z.eccentricity < 0.05)]
    r1, r2 = ratio(pc), ratio(fr)
    print(f"   {lo}-{hi} d: e<5e-4 {r1[0]:.3f} ± {r1[1]:.3f} (N={r1[2]}, A={pc.sense.mean():+.3f}); 0.006<=e<0.05 {r2[0]:.3f} ± {r2[1]:.3f} (N={r2[2]}, A={fr.sense.mean():+.3f})")
z = o[(o.period >= 600) & (o.period < 900)]
pc, fr = z[z.eccentricity < 5e-4], z[(z.eccentricity >= 6e-3) & (z.eccentricity < 0.05)]
print(f"   600-900 d: A = {pc.sense.mean():+.3f} ± {np.sqrt((1 - pc.sense.mean()**2) / len(pc)):.3f} (N={len(pc)}) vs {fr.sense.mean():+.3f} ± {np.sqrt((1 - fr.sense.mean()**2) / len(fr)):.3f} (N={len(fr)})")

print("\n2. Ratio at 700-800 d by eccentricity (registered definition)")
z = o[(o.period >= 700) & (o.period < 800)]
for lo, hi in [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 1)]:
    r = ratio(z[(z.eccentricity >= lo) & (z.eccentricity < hi)])
    print(f"   e {lo}-{hi}: {r[0]:.3f} ± {r[1]:.3f} (N={r[2]})")

print("\n3. AstroSpectroSB1 3D mean L-hat, with C and H (au) converted to mas")
s3 = a[a.nss_solution_type == "AstroSpectroSB1"].dropna(subset=["c_thiele_innes", "h_thiele_innes"])
P = np.column_stack([s3.b_thiele_innes, s3.a_thiele_innes, s3.c_thiele_innes * s3.parallax])
Q = np.column_stack([s3.g_thiele_innes, s3.f_thiele_innes, s3.h_thiele_innes * s3.parallax])
print(f"   median |cos(P,Q)| {np.median(np.abs((P * Q).sum(1) / np.linalg.norm(P, axis=1) / np.linalg.norm(Q, axis=1))):.3f}")
L = np.cross(P, Q)
L /= np.linalg.norm(L, axis=1, keepdims=True)
ra_, dec_ = s3.ra.values, s3.dec.values
ee, en = wb.basis(ra_, dec_)
er = wb.unit(ra_, dec_)
L3 = ee * L[:, [0]] + en * L[:, [1]] + er * L[:, [2]]
from astropy.coordinates import SkyCoord  # noqa: E402
gal = SkyCoord(x=L3[:, 0], y=L3[:, 1], z=L3[:, 2], representation_type="cartesian", frame="icrs").galactic.cartesian.xyz.value.T
print("   all AstroSpectroSB1:", np.round(100 * gal.mean(axis=0), 2), "±", np.round(100 * gal.std(axis=0) / np.sqrt(len(gal)), 2), "N", len(gal))
pred = gal.mean(axis=0)[1] * hd.NEP_GAL[2] / hd.NEP_GAL[1]
print(f"   Z expected from an ecliptic-pole mean with this Y: {100 * pred:+.2f}%")
h = ~hd.is_dev(s3.source_id.values)
print("   held-out:", np.round(100 * gal[h].mean(axis=0), 2), "±", np.round(100 * gal[h].std(axis=0) / np.sqrt(h.sum()), 2), "N", h.sum())

print("\n4. Independent parallaxes: orbit star against its wide companion")
w = pd.read_parquet(f"{hd.RUNS}/data/elbadry/cat.parquet", columns=["source_id1", "source_id2", "parallax1", "parallax2", "parallax_error1", "parallax_error2", "ruwe1", "ruwe2", "R_chance_align", "sep_AU"])
w = w[w.R_chance_align < 0.1]
parts = []
for i, j in [("1", "2"), ("2", "1")]:
    m = o.merge(w, left_on="source_id", right_on=f"source_id{i}")
    m["plx_c"], m["err_c"], m["ruwe_c"] = m[f"parallax{j}"], m[f"parallax_error{j}"], m[f"ruwe{j}"]
    parts.append(m)
m = pd.concat(parts)
m = m[(m.ruwe_c < 1.4) & (m.sep_AU > 1000)]
m["dp"] = m.parallax - m.plx_c
print(f"   pairs with a clean companion: {len(m)}")


def mad(x):
    return 1.4826 * np.median(np.abs(x - np.median(x)))


rng = np.random.default_rng(4)
for lo, hi in [(100, 300), (300, 450), (450, 600), (600, 900), (900, 3000)]:
    s = m[(m.period >= lo) & (m.period < hi)]
    pl, mi = s[s.sense > 0], s[s.sense < 0]
    if min(len(pl), len(mi)) < 15:
        print(f"   {lo}-{hi} d: too few ({len(pl)}, {len(mi)})")
        continue
    # Excess scatter beyond the companion's error, in mas
    sc = lambda x: mad(x.dp.values / np.hypot(x.parallax_error.values, x.err_c.values))
    boot = [sc(pl.iloc[rng.integers(0, len(pl), len(pl))]) / sc(mi.iloc[rng.integers(0, len(mi), len(mi))]) for _ in range(300)]
    ms = lambda x: mad(x.dp.values)
    bm = [ms(pl.iloc[rng.integers(0, len(pl), len(pl))]) / ms(mi.iloc[rng.integers(0, len(mi), len(mi))]) for _ in range(300)]
    print(f"   {lo}-{hi} d: N {len(pl)}, {len(mi)}; scatter of parallax difference (mas) {ms(pl):.4f} vs {ms(mi):.4f}, ratio {ms(pl) / ms(mi):.3f} ± {np.std(bm):.3f};"
          f" normalised {sc(pl):.3f} vs {sc(mi):.3f}, ratio {sc(pl) / sc(mi):.3f} ± {np.std(boot):.3f}; median orbit-star err {pl.parallax_error.median():.4f} vs {mi.parallax_error.median():.4f}")

print("\n5. A real non-linear fit: 12 parameters with least squares on simulated epochs, both senses, same noise")
scan = cs.Scan()
from astropy.coordinates import get_body_barycentric  # noqa: E402
from astropy.time import Time  # noqa: E402


def model(par, t, tc, sp, cp, fpl, tau):
    _, _, _, _, _, A, B, F, G, phi, nu, ecc = par
    M = 2 * np.pi * nu * (t - tc) / 365.25 + phi
    E = cs.kepler(M, ecc)
    X, Y = np.cos(E) - ecc, np.sqrt(1 - ecc**2) * np.sin(E)
    return par[0] * sp + par[1] * cp + par[2] * fpl + par[3] * tau * sp + par[4] * tau * cp + cp * (A * X + F * Y) + sp * (B * X + G * Y)


rng = np.random.default_rng(5)
coords = a.sample(250, random_state=7)
coords = coords[np.abs(np.sin(np.radians(coords.ecl_lat))) > 0.6]
tab = []
for P_d in (250.0, 365.25, 550.0, 730.5, 1500.0):
    ests = {1: [], -1: []}
    forms = {1: [], -1: []}
    for s in coords.itertuples():
        t, psi = scan.transits(s.ra, s.dec)
        if len(t) < 20:
            continue
        tc = 0.5 * (scan.t.min() + scan.t.max())
        sp, cp = np.sin(np.radians(psi)), np.cos(np.radians(psi))
        ep = get_body_barycentric("earth", Time(t + cs.T0_JD, format="jd", scale="tdb")).xyz.to_value("au")
        ra, de = np.radians(s.ra), np.radians(s.dec)
        fpl = (ep[0] * np.sin(ra) - ep[1] * np.cos(ra)) * sp + (ep[0] * np.cos(ra) * np.sin(de) + ep[1] * np.sin(ra) * np.sin(de) - ep[2] * np.cos(de)) * cp
        tau = (t - tc) / 365.25
        sig = 0.15 / np.sqrt(8)  # G about 14
        a0, ecc = 0.8, 0.15
        cosi, om, Om, phi = rng.uniform(0.4, 0.95), *rng.uniform(0, 2 * np.pi, 3)
        A = a0 * (np.cos(om) * np.cos(Om) - np.sin(om) * np.sin(Om) * cosi)
        B = a0 * (np.cos(om) * np.sin(Om) + np.sin(om) * np.cos(Om) * cosi)
        F = a0 * (-np.sin(om) * np.cos(Om) - np.cos(om) * np.sin(Om) * cosi)
        G = a0 * (-np.sin(om) * np.sin(Om) + np.cos(om) * np.cos(Om) * cosi)
        base_sign = np.sign(B * F - A * G) * np.sign(s.ecl_lat)
        for flip in (1, -1):
            F2, G2 = flip * F, flip * G
            sense = int(base_sign * flip)
            truth = np.array([0, 0, 1.0, 0, 0, A, B, F2, G2, phi, 365.25 / P_d, ecc])
            noise = rng.normal(0, sig, len(t))
            obs = model(truth, t, tc, sp, cp, fpl, tau) + noise
            lo_b = np.full(12, -np.inf)
            hi_b = np.full(12, np.inf)
            lo_b[11], hi_b[11] = 0, 0.95
            r = least_squares(lambda p: (model(p, t, tc, sp, cp, fpl, tau) - obs) / sig, truth, bounds=(lo_b, hi_b), max_nfev=40)
            ests[sense].append(r.x[2] - 1.0)
            try:
                forms[sense].append(np.sqrt(np.linalg.inv(r.jac.T @ r.jac)[2, 2]))
            except np.linalg.LinAlgError:
                pass
    sp_, sm_ = mad(np.array(ests[1])), mad(np.array(ests[-1]))
    n1, n2 = len(ests[1]), len(ests[-1])
    print(f"   P={P_d:7.1f} d: scatter of fitted parallax, +NEP {sp_:.4f} (N={n1}), -NEP {sm_:.4f} (N={n2}), ratio {sp_ / sm_:.3f} ± {sp_ / sm_ * np.sqrt(0.5 * (1 / n1 + 1 / n2)) * 1.2:.3f}; formal-error ratio {np.median(forms[1]) / np.median(forms[-1]):.3f}")
