"""Data-level tests of the dossier's assumptions. Numbered as in ASSUMPTIONS.md. All exploratory."""
import sys

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy import units as u
from scipy import stats

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import chiral_sim as cs  # noqa: E402
import handedness as hd  # noqa: E402
import wb  # noqa: E402
from nss_rv_test import load  # noqa: E402

rng = np.random.default_rng(90)
path = f"{hd.RUNS}/data/elbadry/cat.parquet"

print("S1 the split: is the dev flag independent of sky, G and period?")
a = pd.concat([load(False), load(True)])
a = a[a.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])]
a["dev"] = hd.is_dev(a.source_id.values)
print(f"   orbits dev fraction {a.dev.mean():.4f}")
for name, col, bins in [("ecl_lat", "ecl_lat", np.linspace(-90, 90, 13)), ("G", "phot_g_mean_mag", [0, 11, 12, 13, 14, 15, 22]), ("period", "period", [0, 200, 400, 600, 800, 1000, 1e5])]:
    tab = pd.crosstab(pd.cut(a[col], bins), a.dev)
    print(f"   {name}: chi2 p = {stats.chi2_contingency(tab)[1]:.3f}")
raw_all = pd.read_parquet(path, columns=["source_id1", "ra1", "dec1", "sep_AU"])
raw_all["dev"] = hd.is_dev(raw_all.source_id1.values)
print(f"   pairs dev fraction {raw_all.dev.mean():.4f}; dec chi2 p = {stats.chi2_contingency(pd.crosstab(pd.cut(raw_all.dec1, np.linspace(-90, 90, 13)), raw_all.dev))[1]:.3f}")

print("\nS2 the field parent of the model: is TOP 400000 with random_index really a sky-wide random sample?")
f = pd.read_csv(f"{hd.RUNS}/data/nss/field_parent.csv")
n = hd.gal_vectors(f.ra.values, f.dec.values)
b = np.degrees(np.arcsin(n[:, 2]))
print(f"   N={len(f)}  ra quantiles {np.round(np.percentile(f.ra, [1, 25, 50, 75, 99]), 1)}  dec {np.round(np.percentile(f.dec, [1, 25, 50, 75, 99]), 1)}  |b|<10 fraction {np.mean(np.abs(b) < 10):.3f}")
beta = SkyCoord(ra=f.ra.values * u.deg, dec=f.dec.values * u.deg).barycentricmeanecliptic.lat.deg
print(f"   mean |sin beta| {np.mean(np.abs(np.sin(np.radians(beta)))):.3f} (uniform sky 0.5);  G median {f.phot_g_mean_mag.median():.2f};  parallax median {f.parallax.median():.3f}")

import io, urllib.parse, urllib.request  # noqa: E402,E401
q2 = "SELECT TOP 60000 ra,dec,parallax,phot_g_mean_mag FROM gaiadr3.gaia_source WHERE random_index>=8000000 AND random_index<16000000 AND phot_g_mean_mag<17 AND parallax>0.1 AND parallax_over_error>5"
try:
    raw = urllib.request.urlopen("https://gea.esac.esa.int/tap-server/tap/sync", urllib.parse.urlencode(dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q2)).encode(), timeout=120).read()
    g2 = pd.read_csv(io.BytesIO(raw))
    b2 = np.degrees(np.arcsin(hd.gal_vectors(g2.ra.values, g2.dec.values)[:, 2]))
    print(f"   second random_index slice, N={len(g2)}: |b|<10 fraction {np.mean(np.abs(b2) < 10):.3f}; G median {g2.phot_g_mean_mag.median():.2f}; KS |b| p = {stats.ks_2samp(np.abs(b[:60000]), np.abs(b2)).pvalue:.3f}, KS G p = {stats.ks_2samp(f.phot_g_mean_mag[:60000], g2.phot_g_mean_mag).pvalue:.3f}")
except Exception as e:
    print("   second slice UNTESTED:", e)

print("\nS3 model transit count and noise against the real sources")
scan = cs.Scan()
x = a.dropna(subset=["astrometric_matched_transits"]).sample(800, random_state=1)
sim_nt = np.array([len(scan.transits(r.ra, r.dec)[0]) for r in x.itertuples()])
print(f"   simulated / matched transits: median {np.median(sim_nt / x.astrometric_matched_transits):.3f}  (5-95%: {np.round(np.percentile(sim_nt / x.astrometric_matched_transits, [5, 95]), 2)}); corr {np.corrcoef(sim_nt, x.astrometric_matched_transits)[0, 1]:.3f}")
# Parallax error against a simple 12-par-free baseline: compare with sim tables at matched G for the opposite sense, P 200-300 d, where sense does not matter
sim = pd.read_parquet(f"{hd.RUNS}/sim_nss.parquet")
for g in [(12, 13), (13, 14), (14, 15), (15, 16)]:
    data = a[(a.nss_solution_type == "Orbital") & a.phot_g_mean_mag.between(*g) & a.period.between(200, 300)].parallax_error.median()
    s_ = sim[sim.G.between(*g) & sim.P.between(200, 300) & sim.acc_minus].s_plx_minus.median()
    print(f"   G {g}: catalogue sigma_plx {data:.4f}, model {s_:.4f}, ratio {data / s_:.2f}")

print("\nW1 wide pairs: is y's dipole robust to the assumptions of the sample?")
base = wb.load(path, True, base_cuts=False)


def row(label, df, n_sig=3):
    z, s, n = wb.rotation(df)
    k = np.abs(z) > n_sig * s
    r = hd.fit_dipole(np.sign(z[k]), n[k])
    print(hd.fmt("   " + label, r))
    return r


cut = (base.R_chance_align < 0.1) & (base.ruwe1 < 1.4) & (base.ruwe2 < 1.4)
sep = base.pairdistance * 3600
row("registered (sep > 3 arcsec)", base[cut & (sep > 3)])
row("sep > 5 arcsec", base[cut & (sep > 5)])
row("sep > 10 arcsec", base[cut & (sep > 10)])
row("R_chance < 0.01", base[(base.R_chance_align < 0.01) & (base.ruwe1 < 1.4) & (base.ruwe2 < 1.4) & (sep > 3)])
row("R_chance < 0.5", base[(base.R_chance_align < 0.5) & (base.ruwe1 < 1.4) & (base.ruwe2 < 1.4) & (sep > 3)])
row("ruwe < 1.2", base[(base.R_chance_align < 0.1) & (base.ruwe1 < 1.2) & (base.ruwe2 < 1.2) & (sep > 3)])
row("no ruwe cut", base[(base.R_chance_align < 0.1) & (sep > 3)])
row("|z|/sigma > 2", base[cut & (sep > 3)], 2)
row("|z|/sigma > 5", base[cut & (sep > 3)], 5)
d0 = base[cut & (sep > 3)].copy()
# PM errors are underestimated, El-Badry+ 2021 inflation of up to 1.3-1.7 for bright stars
inf = d0.copy()
for c in ["pmra_error1", "pmra_error2", "pmdec_error1", "pmdec_error2"]:
    inf[c] = inf[c] * 1.5
row("PM errors x 1.5", inf)
# Same-metric parallax agreement: reject pairs whose parallaxes differ at 3 sigma
agree = np.abs(d0.parallax1 - d0.parallax2) < 3 * np.hypot(d0.parallax_error1, d0.parallax_error2)
row("parallaxes agree at 3 sigma", d0[agree])
row("nearer than 200 pc", d0[d0.parallax1 > 5])

print("\nW2 quadrupole: does a non-dipole y pattern leak into D_Z on this sky?")
d = wb.select(wb.load(path, True))
n = d[["nx", "ny", "nz"]].values
Q = np.column_stack([n[:, 0] * n[:, 1], n[:, 0] * n[:, 2], n[:, 1] * n[:, 2], n[:, 0] ** 2 - n[:, 1] ** 2, 3 * n[:, 2] ** 2 - 1])
X = np.column_stack([np.ones(len(d)), n, Q])
beta_, res = np.linalg.lstsq(X, d.y.values, rcond=None)[:2]
r_ = d.y.values - X @ beta_
XtXi = np.linalg.inv(X.T @ X)
cov = XtXi @ ((X * r_[:, None]).T @ (X * r_[:, None])) @ XtXi
print(f"   with l=2 terms: D_Z = {100 * beta_[3]:+.2f} ± {100 * np.sqrt(cov[3, 3]):.2f}%; l=2 chi2(5) = {beta_[4:] @ np.linalg.solve(cov[4:, 4:], beta_[4:]):.1f}")

print("\nW3 null distribution: permute y over sky positions; negative control with power")
fit = hd.fit_dipole(d.y.values, n)
perm = np.array([hd.fit_dipole(rng.permutation(d.y.values), n)["Dz"] for _ in range(1000)])
print(f"   observed D_Z {100 * fit['Dz']:+.2f}%; permutation sd {100 * perm.std():.2f}%, mean {100 * perm.mean():+.3f}%; two-sided p = {np.mean(np.abs(perm) >= abs(fit['Dz'])):.3f}")
axes = rng.normal(size=(2000, 3))
axes /= np.linalg.norm(axes, axis=1, keepdims=True)
D = np.array([fit["Dx"], fit["Dy"], fit["Dz"]])
print(f"   |D| = {100 * np.linalg.norm(D):.2f}%; D along the Z axis vs random axes: fraction of random axes with a larger component {np.mean(np.abs(axes @ D) >= abs(D[2])):.3f}")

print("\nW4 perspective: comoving pairs with a distance difference, real geometry, no orbit. Should give D = 0")
s = wb.load(path, True).sample(100000, random_state=3)
e1, n1 = wb.basis(s.ra1.values, s.dec1.values)
e2, n2 = wb.basis(s.ra2.values, s.dec2.values)
u1, u2 = wb.unit(s.ra1.values, s.dec1.values), wb.unit(s.ra2.values, s.dec2.values)
d1 = 1000 / s.parallax1.values
ddist = rng.normal(0, 0.5, len(s))  # pc, wider than any bound pair, random sign
V = rng.normal(0, 30, (len(s), 3)) + np.array([-11, -240, -7]) * 0  # km/s, ICRS, isotropic
pm = lambda u_, e_, n_, dist: np.column_stack([(V * e_).sum(1), (V * n_).sum(1)]) / 4.74047 / dist[:, None] * 1000
p1, p2 = pm(u1, e1, n1, d1), pm(u2, e2, n2, d1 + ddist)
m = s.copy()
m["pmra1"], m["pmdec1"], m["pmra2"], m["pmdec2"] = p1[:, 0], p1[:, 1], p2[:, 0], p2[:, 1]
z, sig, nn = wb.rotation(m)
k = np.abs(z) > 3 * sig
print(hd.fmt("   perspective mock", hd.fit_dipole(np.sign(z[k]), nn[k])), f" kept {k.mean():.2f}")

print("\nW5 negative control with power: unrelated stars close together on the sky, same statistic, no comoving cut")
from scipy.spatial import cKDTree  # noqa: E402
c1 = pd.read_parquet(path, columns=[x + "1" for x in ["source_id", "ra", "dec", "pmra", "pmdec", "pmra_error", "pmdec_error", "ruwe", "parallax"]])
c2 = pd.read_parquet(path, columns=[x + "2" for x in ["source_id", "ra", "dec", "pmra", "pmdec", "pmra_error", "pmdec_error", "ruwe", "parallax"]])
c2.columns = c1.columns
stars = pd.concat([c1, c2]).drop_duplicates("source_id1")
stars = stars[stars.ruwe1 < 1.4].reset_index(drop=True)
partner = set(zip(*[pd.read_parquet(path, columns=["source_id1", "source_id2"])[c] for c in ("source_id1", "source_id2")]))
tree = cKDTree(wb.unit(stars.ra1.values, stars.dec1.values))
for lo_am, hi_am, far in [(1, 10, False), (10, 30, False), (1, 10, True)]:
    pairs = tree.query_pairs(2 * np.sin(np.radians(hi_am / 60) / 2), output_type="ndarray")
    if len(pairs) > 800000:
        pairs = pairs[rng.choice(len(pairs), 800000, replace=False)]
    i, j = pairs[:, 0], pairs[:, 1]
    A1, A2 = stars.iloc[i].reset_index(drop=True), stars.iloc[j].reset_index(drop=True)
    sep = np.degrees(np.arccos(np.clip((wb.unit(A1.ra1.values, A1.dec1.values) * wb.unit(A2.ra1.values, A2.dec1.values)).sum(1), -1, 1))) * 60
    keep = (sep > lo_am) & np.array([(a_, b_) not in partner and (b_, a_) not in partner for a_, b_ in zip(A1.source_id1.values, A2.source_id1.values)])
    if far:  # unrelated in distance as well: parallaxes differ by more than 20%
        keep &= np.abs(A1.parallax1 - A2.parallax1).values > 0.2 * A1.parallax1.values
    m = pd.DataFrame(dict(ra1=A1.ra1, dec1=A1.dec1, ra2=A2.ra1, dec2=A2.dec1, pmra1=A1.pmra1, pmdec1=A1.pmdec1, pmra2=A2.pmra1, pmdec2=A2.pmdec1, pmra_error1=A1.pmra_error1, pmra_error2=A2.pmra_error1, pmdec_error1=A1.pmdec_error1, pmdec_error2=A2.pmdec_error1))[keep]
    z, sig, nn = wb.rotation(m)
    k = np.abs(z) > 3 * sig
    print(hd.fmt(f"   unrelated, {lo_am}-{hi_am} arcmin{' far' if far else ''}", hd.fit_dipole(np.sign(z[k]), nn[k])))

print("\nO1 orbit statistic: A by ecliptic longitude and hemisphere")
for lo in range(0, 360, 60):
    x = a[a.ecl_lon.between(lo, lo + 60)]
    print(f"   lon {lo}-{lo + 60}: A={x.sense.mean():+.3f} ± {np.sqrt((1 - x.sense.mean()**2) / len(x)):.3f}")

print("\nO2 is the parallax in these solutions what the catalogue says? nss parallax_error is the orbit-fit error, not 5-par")
print("   Orbital median parallax_over_error x P / 20000 minimum:", round(float((a[a.nss_solution_type == 'Orbital'].parallax / a[a.nss_solution_type == 'Orbital'].parallax_error * a[a.nss_solution_type == 'Orbital'].period / 20000).min()), 4))

print("\nO3 period aliasing: are 340-390 d Orbital periods real? Period agreement with AstroSpectroSB1 not available by construction; report sigma_P")
for lo, hi in [(340, 390), (700, 800), (1100, 1600)]:
    x = a[a.period.between(lo, hi)]
    print(f"   {lo}-{hi}: median period_error/period by sense + {np.median(x[x.sense > 0].period_error / x[x.sense > 0].period):.4f}, - {np.median(x[x.sense < 0].period_error / x[x.sense < 0].period):.4f}")

print("\nO4 is the ratio a G or sky artefact? Ratio at 700-800 d within narrow sky bands (|sin beta| 0.6-0.9, 12<=G<15), Orbital")
o = a[(a.nss_solution_type == "Orbital") & a.period.between(700, 800) & a.phot_g_mean_mag.between(12, 15)]
o = o[np.abs(np.sin(np.radians(o.ecl_lat))).between(0.6, 0.9)]
for lo, hi in [(0, 10), (10, 30), (30, 90)]:
    x = o[np.abs(o.b).between(lo, hi)]
    print(f"   |b| {lo}-{hi}: ratio {x[x.sense > 0].parallax_error.median() / x[x.sense < 0].parallax_error.median():.3f}, N={len(x)}")
print("   same at 200-300 d, control:")
o = a[(a.nss_solution_type == "Orbital") & a.period.between(200, 300) & a.phot_g_mean_mag.between(12, 15)]
o = o[np.abs(np.sin(np.radians(o.ecl_lat))).between(0.6, 0.9)]
print(f"   ratio {o[o.sense > 0].parallax_error.median() / o[o.sense < 0].parallax_error.median():.3f}, N={len(o)}")
