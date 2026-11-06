"""Independent reproduction: part (d), wide binaries."""
import os
import numpy as np
import pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord, BarycentricMeanEcliptic

cols = ["source_id1", "source_id2", "ra1", "ra2", "dec1", "dec2", "pmra1", "pmra2", "pmdec1", "pmdec2",
        "pmra_error1", "pmra_error2", "pmdec_error1", "pmdec_error2", "pmra_pmdec_corr1", "pmra_pmdec_corr2",
        "ruwe1", "ruwe2", "phot_g_mean_mag1", "phot_g_mean_mag2", "parallax1", "parallax2", "pairdistance", "sep_AU", "R_chance_align"]
w0 = pd.read_parquet(os.path.expanduser("~/oddsky-runs/h0018/data/elbadry/cat.parquet"), columns=cols)
print("rows", len(w0))
print("NaN", w0[["R_chance_align", "ruwe1", "ruwe2", "pmra1", "pmra2", "pmdec1", "pmdec2", "pmra_error1", "pmra_error2", "sep_AU", "pmra_pmdec_corr1", "pmra_pmdec_corr2"]].isna().sum().to_dict())
m = (w0.R_chance_align < 0.1) & (w0.ruwe1 < 1.4) & (w0.ruwe2 < 1.4) & (w0.pairdistance * 3600 > 3)
w = w0[m].copy().reset_index(drop=True)
print("after cuts", len(w))
print("dup pair rows", w.duplicated(["source_id1", "source_id2"]).sum(),
      "reversed-order dups", len(set(zip(w.source_id1, w.source_id2)) & set(zip(w.source_id2, w.source_id1))))
ids = pd.concat([w.source_id1, w.source_id2])
print("stars in >1 pair:", (ids.value_counts() > 1).sum())


def unit(ra, dec):
    return np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], -1)
def en(ra, dec):
    e = np.stack([-np.sin(ra), np.cos(ra), 0 * ra], -1)
    n = np.stack([-np.sin(dec) * np.cos(ra), -np.sin(dec) * np.sin(ra), np.cos(dec)], -1)
    return e, n


def compute(w, flip=False, use_corr=True):
    a, b = ("1", "2") if not flip else ("2", "1")
    ra1, dec1 = np.radians(w["ra" + a].values), np.radians(w["dec" + a].values)
    ra2, dec2 = np.radians(w["ra" + b].values), np.radians(w["dec" + b].values)
    u1, u2 = unit(ra1, dec1), unit(ra2, dec2)
    e1, n1 = en(ra1, dec1); e2, n2 = en(ra2, dec2)
    v1 = e1 * w["pmra" + a].values[:, None] + n1 * w["pmdec" + a].values[:, None]
    v2 = e2 * w["pmra" + b].values[:, None] + n2 * w["pmdec" + b].values[:, None]
    sep = u2 - u1
    dv = v2 - v1
    nh = u1 + u2; nh /= np.linalg.norm(nh, axis=1, keepdims=True)
    z = np.sum(np.cross(sep, dv) * nh, 1)
    wv = np.cross(nh, sep)            # z = dv . (nh x sep)
    ca2, cd2 = np.sum(wv * e2, 1), np.sum(wv * n2, 1)
    ca1, cd1 = -np.sum(wv * e1, 1), -np.sum(wv * n1, 1)
    sa1, sd1 = w["pmra_error" + a].values, w["pmdec_error" + a].values
    sa2, sd2 = w["pmra_error" + b].values, w["pmdec_error" + b].values
    var = (ca1 * sa1) ** 2 + (cd1 * sd1) ** 2 + (ca2 * sa2) ** 2 + (cd2 * sd2) ** 2
    if use_corr:
        r1 = np.nan_to_num(w["pmra_pmdec_corr" + a].values); r2 = np.nan_to_num(w["pmra_pmdec_corr" + b].values)
        var = var + 2 * ca1 * cd1 * sa1 * sd1 * r1 + 2 * ca2 * cd2 * sa2 * sd2 * r2
    return z, np.sqrt(var), nh, np.linalg.norm(sep, axis=1), np.sum(wv * dv, 1)


z, sz, nh, sepn, z_chk = compute(w)
print("identity z vs dv.(nh x sep) max rel", np.nanmax(np.abs(z - z_chk) / np.abs(z).clip(1e-30)))
z_f, sz_f, *_ = compute(w, flip=True)
print("1<->2 swap: sign disagreements", (np.sign(z) != np.sign(z_f)).sum(), "of", len(z), "max sigma diff", np.nanmax(np.abs(sz - sz_f)))
print("pairdistance vs 3D chord [arcsec] max abs diff", np.nanmax(np.abs(np.degrees(sepn) - w.pairdistance.values) * 3600))
z_nc, sz_nc, *_ = compute(w, use_corr=False)
print("NaN z", np.isnan(z).sum(), "NaN sigma", np.isnan(sz).sum())
w["z"] = z; w["sz"] = sz; w["snr"] = np.abs(z) / sz; w["sgn"] = np.sign(z)
print("|z|>3s with corr", (w.snr > 3).sum(), "without corr", ((np.abs(z_nc) / sz_nc) > 3).sum())

# Galactic Cartesian of the pair midpoint
c = SkyCoord(x=nh[:, 0], y=nh[:, 1], z=nh[:, 2], representation_type="cartesian", frame="icrs")
gn = c.galactic.cartesian.xyz.value.T
gn = gn / np.linalg.norm(gn, axis=1, keepdims=True)
ecl_lat = np.degrees(np.arcsin(c.transform_to(BarycentricMeanEcliptic()).cartesian.xyz.value[2] / np.linalg.norm(c.cartesian.xyz.value, axis=0)))
nep = SkyCoord(0 * u.deg, 90 * u.deg, frame=BarycentricMeanEcliptic()).galactic.cartesian.xyz.value

def fit(y, n_, label, weights=None):
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y)), n_])
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ y
    res = y - X @ b
    lev = np.einsum("ij,jk,ik->i", X, XtXi, X)
    cov = XtXi @ ((X * (res**2 / (1 - lev) ** 2)[:, None]).T @ X) @ XtXi
    se = np.sqrt(np.diag(cov))
    v = b[1:]
    print(f"{label:34s} N={len(y):7d} c0={b[0]:+.4f}+-{se[0]:.4f} X={b[1]:+.4f}+-{se[1]:.4f} Y={b[2]:+.4f}+-{se[2]:.4f} Z={b[3]:+.4f}+-{se[3]:.4f}"
          f" |  ang(NGP)={np.degrees(np.arccos(v[2]/np.linalg.norm(v))):.0f} ang(NEP)={np.degrees(np.arccos(v@nep/np.linalg.norm(v))):.0f}")

sel = (w.snr > 3).values
print("\n(d)")
fit(w.sgn[sel], gn[sel], "|z|>3s")
BINS = [(1e2, 1e3), (1e3, 1e4), (1e4, 3e4), (3e4, 1e5)]
for lo, hi in BINS:
    k = sel & (w.sep_AU >= lo).values & (w.sep_AU < hi).values
    fit(w.sgn[k], gn[k], f"sep_AU [{lo:.0e},{hi:.0e})")
print("outside sep bins:", (sel & ~((w.sep_AU >= 1e2) & (w.sep_AU < 1e5)).values).sum())

print("\nsensitivity")
fit(w.sgn[np.abs(z_nc) / sz_nc > 3], gn[np.abs(z_nc) / sz_nc > 3], "|z|>3s no PM corr")
fit(w.sgn, gn, "no snr cut")
fit(w.sgn[w.snr > 5], gn[w.snr > 5], "|z|>5s")
uniq = sel & ~(w.source_id1.isin(ids[ids.duplicated()]) | w.source_id2.isin(ids[ids.duplicated()])).values
fit(w.sgn[uniq], gn[uniq], "|z|>3s, stars in one pair only")
print("ecliptic analogue (sign z)*sign(beta) mean:", np.mean(w.sgn[sel] * np.sign(ecl_lat[sel])), "+-", np.sqrt((1 - np.mean(w.sgn[sel] * np.sign(ecl_lat[sel])) ** 2) / sel.sum()))
print("mean sign z, N/S ecl hemispheres:", np.mean(w.sgn[sel & (ecl_lat > 0)]), np.mean(w.sgn[sel & (ecl_lat < 0)]))
g = np.minimum(w.phot_g_mean_mag1, w.phot_g_mean_mag2)
for lab, k in [("bright pair G1,2<16", (w.phot_g_mean_mag1 < 16) & (w.phot_g_mean_mag2 < 16)), ("sep>10as", w.pairdistance * 3600 > 10), ("sep>30as", w.pairdistance * 3600 > 30), ("|b|>30", np.abs(gn[:, 2]) > 0.5), ("|b|<30", np.abs(gn[:, 2]) <= 0.5)]:
    k = sel & np.asarray(k)
    fit(w.sgn[k], gn[k], "|z|>3s " + lab)

# shuffle null: pair each sep with another pair's dv is meaningless on the sky, so use random-sign of sep on the same data as a check
rng = np.random.default_rng(5)
fit(w.sgn[sel] * rng.choice([-1, 1], sel.sum()), gn[sel], "null: random sign flips")

# Oort-rotation magnitude check: a rigid rotation of frame yields dv = omega x sep along n̂ scale; expected <sign z> not computed, only amplitude
w_rad = sepn
print("median |sep| [arcsec]", np.median(np.degrees(w_rad[sel]) * 3600), "median |z|/|sep| [mas/yr]", np.median(np.abs(z[sel]) / w_rad[sel]), "median sigma_z/|sep| [mas/yr]", np.median(sz[sel] / w_rad[sel]))
