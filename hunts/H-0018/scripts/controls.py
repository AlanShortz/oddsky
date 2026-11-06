"""Preregistered method controls, development split only: injection, Kepler mock, Oort field pairs, shift catalogue."""
import sys

import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import SkyCoord
from scipy.spatial import cKDTree

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
import wb  # noqa: E402

rng = np.random.default_rng(18)
raw = wb.load(f"{hd.RUNS}/data/elbadry/cat.parquet", heldout=False)
d = wb.select(raw)
base = wb.fit(d)
print(hd.fmt("dev baseline", base))

# 1. Injection: flip -1 to +1 with the probability that adds E[y] = a * (axis.n)
print("\n1. Injection, amplitude 5% (0.5% is below the dev noise; see note in README)")
for name, axis in [("+Z", hd.NGP_GAL), ("+NEP", hd.NEP_GAL)]:
    for amp in [0.005, 0.05]:
        n = d[["nx", "ny", "nz"]].values
        delta = amp * (n @ axis)
        y = d.y.values.copy()
        flip_up = (y < 0) & (rng.random(len(y)) < np.clip(delta, 0, 1))
        flip_dn = (y > 0) & (rng.random(len(y)) < np.clip(-delta, 0, 1))
        y[flip_up] = 1
        y[flip_dn] = -1
        r = hd.fit_dipole(y, n)
        along = np.array([r["Dx"], r["Dy"], r["Dz"]]) @ axis - np.array([base["Dx"], base["Dy"], base["Dz"]]) @ axis
        print(f"  {name} inject {amp:.3f}: recovered change along axis = {along:+.4f} (se {r['Dz_se']:.4f})")

# 2. Kepler mock: known mean L-hat, Gaia-like errors from the real pairs, real positions, phases random
print("\n2. Kepler mock")
sub = raw.sample(min(len(raw), 120000), random_state=1)


def kepler_mock(mean_lhat):
    N = len(sub)
    n = hd.gal_vectors(sub.ra1.values, sub.dec1.values)
    # Dipole distribution of L-hat along Z by rejection
    L = rng.normal(size=(4 * N, 3))
    L /= np.linalg.norm(L, axis=1, keepdims=True)
    keep = rng.random(4 * N) < (1 + 3 * mean_lhat * L[:, 2]) / (1 + 3 * abs(mean_lhat))
    L = L[keep][:N]
    # Thermal eccentricity, random phase; z = L.n at any phase, multiplied by a Gaussian-error-free amplitude
    ampl = rng.lognormal(0, 1, N)
    z = (L * n).sum(axis=1) * ampl
    noise = rng.normal(0, 0.25, N)
    y = np.sign(z + noise)
    keep2 = np.abs(z + noise) > 3 * 0.25
    return hd.fit_dipole(y[keep2], n[keep2])


for a in [0.0, 0.02, 0.05, -0.05]:
    r = kepler_mock(a)
    print(f"  <Lz> = {a:+.3f}  expect Dz = {1.5 * a:+.3f}  got {r['Dz']:+.4f} ± {r['Dz_se']:.4f}")

# 3. Oort test: unrelated field stars
print("\n3. Oort field pairs")
s = raw[(raw.parallax1 > 2) & (raw.parallax1 / raw.parallax_error1 > 20)].drop_duplicates("source_id1")
sc = SkyCoord(ra=s.ra1.values * u.deg, dec=s.dec1.values * u.deg, distance=(1000 / s.parallax1.values) * u.pc, frame="icrs")
xyz = np.asarray(sc.galactic.cartesian.xyz.value).T
v_e, v_n = wb.basis(s.ra1.values, s.dec1.values)
vt = 4.74047e-3 * (v_e * s.pmra1.values[:, None] + v_n * s.pmdec1.values[:, None]) / s.parallax1.values[:, None] * 1000 / 1000
n_icrs = wb.unit(s.ra1.values, s.dec1.values)
r_icrs = n_icrs * (1000 / s.parallax1.values)[:, None]
vt = 4.74047 * (v_e * s.pmra1.values[:, None] + v_n * s.pmdec1.values[:, None]) / s.parallax1.values[:, None]  # km/s
print(f"  stars {len(s)}, median d {np.median(1000 / s.parallax1.values):.0f} pc")
tree = cKDTree(r_icrs)
rows = []
for rmin, rmax in [(30, 60), (60, 100), (100, 150), (150, 220), (220, 320)]:
    idx = rng.integers(0, len(s), 300000)
    dists, nbr = tree.query(r_icrs[idx], k=2, distance_upper_bound=rmax)
    pts = []
    # Draw random partners in the shell directly from a sample to avoid favouring the closest neighbour
    cand = rng.integers(0, len(s), 6000000)
    i = rng.integers(0, len(s), 6000000)
    sep = np.linalg.norm(r_icrs[cand] - r_icrs[i], axis=1)
    ok = (sep > rmin) & (sep < rmax) & (cand != i)
    i, j = i[ok], cand[ok]
    mid = r_icrs[i] + r_icrs[j]
    mid /= np.linalg.norm(mid, axis=1, keepdims=True)
    r = r_icrs[j] - r_icrs[i]
    dv = vt[j] - vt[i]
    # Keep pairs mostly in the plane of the sky, where the projection has meaning
    rperp = r - (r * mid).sum(axis=1, keepdims=True) * mid
    in_sky = np.linalg.norm(rperp, axis=1) > 0.7 * np.linalg.norm(r, axis=1)
    i, r, dv, mid, rperp = i[in_sky], r[in_sky], dv[in_sky], mid[in_sky], rperp[in_sky]
    z = (np.cross(rperp, dv) * mid).sum(axis=1)
    ra = np.degrees(np.arctan2(mid[:, 1], mid[:, 0])) % 360
    dec = np.degrees(np.arcsin(mid[:, 2]))
    ng = hd.gal_vectors(ra, dec)
    fit = hd.fit_dipole(np.sign(z), ng)
    rp = np.linalg.norm(rperp, axis=1)
    t = (np.cross(mid, rperp / rp[:, None]) * dv).sum(axis=1)  # tangential relative speed
    sig = np.std(t[np.abs(t) < 100])
    # E[y] = 0.80 * Omega.n * r / sigma; D_Z = 0.80 * B * <r> / sigma (B in km/s/pc)
    b_est = fit["Dz"] * sig / (0.7979 * rp.mean()) * 1000
    b_err = fit["Dz_se"] * sig / (0.7979 * rp.mean()) * 1000
    print(f"  r {rmin}-{rmax} pc: N={fit['N']:7d} <rperp>={rp.mean():5.0f} sigma_t={sig:5.1f}  m={fit['m']:+.4f}±{fit['m_se']:.4f}"
          f"  Dz={fit['Dz']:+.4f}±{fit['Dz_se']:.4f}  Dx={fit['Dx']:+.4f} Dy={fit['Dy']:+.4f}  -> B={b_est:+.1f}±{b_err:.1f} km/s/kpc")
    rows.append((fit["Dz"], fit["Dz_se"], rp.mean(), sig, b_est, b_err))
b = np.array([x[4] for x in rows])
w = 1 / np.array([x[5] for x in rows]) ** 2
print(f"  Weighted B = {np.sum(b * w) / w.sum():+.1f} ± {1 / np.sqrt(w.sum()):.1f} km/s/kpc (naive error, stars reused across pairs)")

# 5. Shift catalogue
print("\n5. Shift catalogue")
sh = pd.read_parquet(f"{hd.RUNS}/data/elbadry/shift.parquet", columns=wb.COLS)
ang = np.degrees(np.arccos(np.clip((wb.unit(sh.ra1.values, sh.dec1.values) * wb.unit(sh.ra2.values, sh.dec2.values)).sum(axis=1), -1, 1))) * 3600
print("  stored-position separation vs pairdistance (arcsec): median stored", round(float(np.median(ang)), 1),
      " median pairdistance", round(float(np.median(sh.pairdistance) * 3600), 1))
sh = sh[hd.is_dev(sh.source_id1.values)]
print("  dev rows", len(sh))
sh2 = sh[(sh.ruwe1 < 1.4) & (sh.ruwe2 < 1.4) & (sh.pairdistance * 3600 > 3)]
print(hd.fmt("shift, stored positions", wb.fit(wb.select(sh2))))
for lo, hi in wb.BINS:
    x = sh2[(sh2.sep_AU >= lo) & (sh2.sep_AU < hi)]
    if len(x) > 300:
        print(hd.fmt(f"shift [{lo:.0e},{hi:.1e})", wb.fit(wb.select(x))))
