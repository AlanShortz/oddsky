"""The frozen tests of H-0018. Run on dev to debug; run once with --heldout. Everything printed here goes in the dossier."""
import argparse
import json
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
import wb  # noqa: E402
from nss_rv_test import load  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--heldout", action="store_true")
args = ap.parse_args()
tag = "heldout" if args.heldout else "dev"
out = {"split": tag}

# ---------- Wide pairs: the preregistered decision ----------
print("=" * 30, "WB", tag)
raw = wb.load(f"{hd.RUNS}/data/elbadry/cat.parquet", args.heldout)
d = wb.select(raw)
r = wb.fit(d)
print("base-cut pairs", len(raw), "selected", len(d))
print(hd.fmt("WB all", r))
boot = hd.bootstrap(d.y.values, d[["nx", "ny", "nz"]].values, draws=1000)
print("  bootstrap se: m %.4f Dx %.4f Dy %.4f Dz %.4f (sandwich Dz %.4f)" % (*boot, r["Dz_se"]))
out["wb_all"] = r
print("  free direction: angle to NGP %.1f deg, to NEP %.1f deg; chi2(3) for D=0: %.2f, p=%.3g" % (r["ang_to_ngp"], r["ang_to_nep"], r["chi2_D"], stats.chi2.sf(r["chi2_D"], 3)))
limit = (abs(r["Dz"]) + 1.96 * r["Dz_se"]) * 2 / 3
print(f"  95% limit |<L_z>| < {limit:.4f} (gain 3/2: conservative, see mock)")
out["wb_bins"] = []
for lo, hi in wb.BINS:
    s = d[(d.sep_AU >= lo) & (d.sep_AU < hi)]
    if len(s) < 100:
        print(f"  [{lo:.0e},{hi:.1e}) only {len(s)} pairs: no fit")
        continue
    b = wb.fit(s)
    lim = (abs(b["Dz"]) + 1.96 * b["Dz_se"]) * 2 / 3
    print(hd.fmt(f"[{lo:.0e},{hi:.1e}) au", b), f" p(Dz)={2 * stats.norm.sf(abs(b['Dz_sig'])):.3f}  lim {lim:.3f}")
    out["wb_bins"].append(dict(lo=lo, hi=hi, **b, limit=lim))
print(hd.fmt("b>0", wb.fit(d[d.nz > 0])))
print(hd.fmt("b<0", wb.fit(d[d.nz < 0])))
near = d.parallax1 > d.parallax1.median()
print(hd.fmt("near", wb.fit(d[near])))
print(hd.fmt("far", wb.fit(d[~near])))
gmax = d[["phot_g_mean_mag1", "phot_g_mean_mag2"]].max(axis=1)
print(hd.fmt("bright", wb.fit(d[gmax < gmax.median()])))
print(hd.fmt("faint", wb.fit(d[gmax >= gmax.median()])))
gmin = d[["phot_g_mean_mag1", "phot_g_mean_mag2"]].min(axis=1)
clean = (gmin > 13) & ((d.phot_g_mean_mag1 - d.phot_g_mean_mag2).abs() < 1)
print(hd.fmt("both G>13, |dG|<1", wb.fit(d[clean])))
print(hd.fmt("the rest", wb.fit(d[~clean])))

# Shift catalogue: undo the 0.5 deg on-sky RA shift so that the separation vector is the one the pair was selected with
sh = pd.read_parquet(f"{hd.RUNS}/data/elbadry/shift.parquet", columns=wb.COLS)
dev = hd.is_dev(sh.source_id1.values)
sh = sh[~dev if args.heldout else dev]
sh = sh[(sh.ruwe1 < 1.4) & (sh.ruwe2 < 1.4) & (sh.pairdistance * 3600 > 3)].copy()
xa = ((sh.ra2 - sh.ra1 + 180) % 360 - 180) * np.cos(np.radians(sh.dec1))
candidates = [np.abs(np.hypot(xa + off, sh.dec2 - sh.dec1) - sh.pairdistance).values for off in (0.5, -0.5)]
offs = np.where(candidates[0] < candidates[1], 0.5, -0.5)
match = np.minimum(*candidates) * 3600
print(f"\nshift: {len(sh)} pairs, median separation mismatch after undoing shift {np.median(match):.3f} arcsec, within 1 arcsec {np.mean(match < 1):.3f}")
sh, offs, xa = sh[match < 1], offs[match < 1], xa[match < 1]
dalpha = np.radians(xa + offs)
ddelta = np.radians(sh.dec2 - sh.dec1)
dma, dmd = sh.pmra2 - sh.pmra1, sh.pmdec2 - sh.pmdec1
z = dalpha * dmd - ddelta * dma
s = np.sqrt(dalpha**2 * (sh.pmdec_error1**2 + sh.pmdec_error2**2) + ddelta**2 * (sh.pmra_error1**2 + sh.pmra_error2**2))
k = np.abs(z) > 3 * s
n = hd.gal_vectors(sh.ra1[k].values, sh.dec1[k].values)
print(hd.fmt("shift, all", hd.fit_dipole(np.sign(z[k]).values, n)))
out["shift"] = hd.fit_dipole(np.sign(z[k]).values, n)
sep = sh.sep_AU[k].values
for lo, hi in wb.BINS:
    m = (sep >= lo) & (sep < hi)
    if m.sum() > 200:
        print(hd.fmt(f"shift [{lo:.0e},{hi:.1e})", hd.fit_dipole(np.sign(z[k]).values[m], n[m])))

# ---------- Astrometric orbits ----------
print("\n" + "=" * 30, "NSS", tag)
a = load(args.heldout)
a = a[a.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])].copy()
a[["nx", "ny", "nz"]] = hd.gal_vectors(a.ra.values, a.dec.values)
Nall = hd.fit_dipole(a.y.values, a[["nx", "ny", "nz"]].values)
print(hd.fmt("NSS Orbital+AstroSpectroSB1", Nall))
print("  free direction: angle to NGP %.1f, to NEP %.1f; sense asymmetry A = %+.4f ± %.4f" % (Nall["ang_to_ngp"], Nall["ang_to_nep"], a.sense.mean(), np.sqrt((1 - a.sense.mean() ** 2) / len(a))))
out["nss_all"] = Nall
out["nss_A"] = [a.sense.mean(), float(np.sqrt((1 - a.sense.mean() ** 2) / len(a)))]

# A and parallax-error ratio by period, against the forward model frozen in work/sim_prediction.csv
pred = pd.read_csv(sys.argv[0].rsplit("/", 2)[0] + "/work/sim_prediction.csv")
o = a[a.nss_solution_type == "Orbital"]
rows = []
for x in pred.itertuples():
    s = a[(a.period >= x.lo) & (a.period < x.hi)]
    so = o[(o.period >= x.lo) & (o.period < x.hi) & (o.phot_g_mean_mag >= 12) & (o.phot_g_mean_mag < 16)]
    p_, m_ = so[so.sense > 0], so[so.sense < 0]
    rng = np.random.default_rng(1)
    # Median ratio within G bins, averaged, so that a G difference between senses cannot enter
    ratios = []
    for g in np.arange(12, 16):
        pg, mg = p_[(p_.phot_g_mean_mag >= g) & (p_.phot_g_mean_mag < g + 1)], m_[(m_.phot_g_mean_mag >= g) & (m_.phot_g_mean_mag < g + 1)]
        if min(len(pg), len(mg)) >= 10:
            ratios.append((np.median(pg.parallax_error) / np.median(mg.parallax_error), len(pg) + len(mg)))
    ratio = np.average([q[0] for q in ratios], weights=[q[1] for q in ratios]) if ratios else np.nan
    boots = [np.median(rng.choice(p_.parallax_error.values, len(p_))) / np.median(rng.choice(m_.parallax_error.values, len(m_))) for _ in range(200)] if min(len(p_), len(m_)) > 3 else [np.nan]
    Aobs = s.sense.mean()
    rows.append(dict(lo=x.lo, hi=x.hi, N=len(s), A=Aobs, A_se=np.sqrt((1 - Aobs**2) / max(len(s), 1)), A_model=x.A_model, ratio=ratio, ratio_se=np.nanstd(boots), ratio_model=x.ratio_model))
t = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(t.round(3).to_string(index=False))
ok = t.ratio.notna()
T1_r = np.corrcoef(t.ratio[ok], t.ratio_model[ok])[0, 1]
T1_med = np.median(np.abs(t.ratio[ok] - t.ratio_model[ok]))
T2_rho = stats.spearmanr(t.A, t.A_model).statistic
print(f"\nT1 parallax-error ratio vs model: Pearson r = {T1_r:.3f} (needs >= 0.8), median |diff| = {T1_med:.3f} (needs <= 0.05)")
print(f"T2 A(P) vs model: Spearman rho = {T2_rho:.3f} (needs >= 0.7)")
res = t[t.lo >= 450]
print(f"   residual A - A_model for P>=450 d, N-weighted: {np.average(res.A - res.A_model, weights=res.N):+.3f}")
hy = a[(a.period >= 150) & (a.period < 200)]
hm = hy.sense.mean()
print(f"   half-year zone 150-200 d: A = {hm:+.3f} ± {np.sqrt((1 - hm**2) / len(hy)):.3f} (needs > 0 at 2 sigma)")
yr = a[(a.period >= 340) & (a.period < 390)]
print(f"   one-year zone 340-390 d: A = {yr.sense.mean():+.3f} ± {np.sqrt((1 - yr.sense.mean()**2) / len(yr)):.3f}")
out["T1_r"], out["T1_med"], out["T2_rho"] = T1_r, T1_med, T2_rho
t.to_csv(sys.argv[0].rsplit("/", 2)[0] + f"/work/nss_by_period_{tag}.csv", index=False)

# T3: are the excess-sense orbits fake? RV variability independent of astrometry
has = o[o.rv_chisq_pvalue.notna() & (o.rv_nb_transits >= 8) & (o.kpred > 5)]
s = has[(has.period >= 600) & (has.period < 900)]
pl, mi = s[s.sense > 0], s[s.sense < 0]
fp, fm = (pl.rv_chisq_pvalue < 0.001).mean(), (mi.rv_chisq_pvalue < 0.001).mean()
ep, em = np.sqrt(fp * (1 - fp) / len(pl)), np.sqrt(fm * (1 - fm) / len(mi))
excess = 1 - len(pl) / len(mi)
fake_pred = fp * (1 - excess)
print(f"\nT3 RV variable, P 600-900 d, K_pred > 5 km/s: +NEP {fp:.3f}±{ep:.3f} (N={len(pl)}), -NEP {fm:.3f}±{em:.3f} (N={len(mi)})")
print(f"   if the whole -NEP excess ({excess:.3f}) were fake, -NEP would be {fake_pred:.3f}; observed is {(fm - fake_pred) / np.hypot(ep, em):+.1f} sigma above that")
for lo, hi in [(100, 300), (300, 450), (450, 600), (900, 3000)]:
    s2 = has[(has.period >= lo) & (has.period < hi)]
    p2, m2 = s2[s2.sense > 0], s2[s2.sense < 0]
    print(f"   P {lo}-{hi}: +NEP {(p2.rv_chisq_pvalue < 0.001).mean():.3f} (N={len(p2)}), -NEP {(m2.rv_chisq_pvalue < 0.001).mean():.3f} (N={len(m2)})")
amp_p, amp_m = pl.rv_amplitude_robust / (2 * pl.kpred), mi.rv_amplitude_robust / (2 * mi.kpred)
print(f"   median RV amplitude / 2K_pred: +NEP {amp_p.median():.3f}, -NEP {amp_m.median():.3f}")

# T5: does the handedness fade with distance from the parallax cut, measured with an error that does not know the sense?
z6 = a[(a.period >= 600) & (a.period < 900)].copy()
ref = z6[z6.sense < 0].groupby(pd.cut(z6[z6.sense < 0].phot_g_mean_mag, np.arange(5, 19)), observed=True).parallax_error.median()
gb = pd.cut(z6.phot_g_mean_mag, np.arange(5, 19))
z6["m_ref"] = z6.parallax / gb.map(ref).astype(float) * z6.period / 20000
print("\nT5 A against the margin over the parallax cut, sense-blind error, P 600-900 d")
t5 = []
for lo, hi in [(0, 1.5), (1.5, 2.5), (2.5, 5), (5, 10), (10, 1e9)]:
    x = z6[(z6.m_ref >= lo) & (z6.m_ref < hi)]
    m = x.sense.mean()
    print(f"   [{lo},{hi:.3g}) N={len(x)} A={m:+.3f} ± {np.sqrt((1 - m**2) / len(x)):.3f}")
    t5.append(m)
print(f"   pass if |A| at margin >= 5 is under half of |A| at margin < 1.5: {abs(z6[z6.m_ref >= 5].sense.mean()):.3f} vs {abs(t5[0]):.3f}")

# T4: Galactic handedness in orbits after the ecliptic pattern is taken out
pbins = np.digitize(a.period.values, [150, 200, 300, 340, 390, 450, 600, 900])
sgn = np.sign(a.ecl_lat.values)
nuis = [((pbins == pb) * sgn) for pb in np.unique(pbins)]
X = np.column_stack([np.ones(len(a)), a.nz.values, a.nx.values, a.ny.values, *nuis])
y = a.y.values
beta = np.linalg.lstsq(X, y, rcond=None)[0]
res_ = y - X @ beta
XtXi = np.linalg.pinv(X.T @ X)
cov = XtXi @ ((X * res_[:, None]).T @ (X * res_[:, None])) @ XtXi
print(f"\nT4 NSS, ecliptic pattern removed ({len(nuis)} nuisance terms): Dz = {beta[1]:+.4f} ± {np.sqrt(cov[1, 1]):.4f}; m = {beta[0]:+.4f} ± {np.sqrt(cov[0, 0]):.4f}")
out["nss_dz_clean"] = [float(beta[1]), float(np.sqrt(cov[1, 1]))]
for label, m in [("parallax > 3 mas", a.parallax > 3), ("P < 300 d", a.period < 300), ("AstroSpectroSB1", a.nss_solution_type == "AstroSpectroSB1")]:
    print(hd.fmt(label, hd.fit_dipole(a.y[m].values, a[["nx", "ny", "nz"]][m].values)))

# 3D mean of L-hat
s3 = a[a.nss_solution_type == "AstroSpectroSB1"].dropna(subset=["c_thiele_innes", "h_thiele_innes"])
P = np.column_stack([s3.b_thiele_innes, s3.a_thiele_innes, s3.c_thiele_innes])
Q = np.column_stack([s3.g_thiele_innes, s3.f_thiele_innes, s3.h_thiele_innes])
L = np.cross(P, Q)
L /= np.linalg.norm(L, axis=1, keepdims=True)
ra_, dec_ = np.radians(s3.ra.values), np.radians(s3.dec.values)
ee = np.column_stack([-np.sin(ra_), np.cos(ra_), np.zeros_like(ra_)])
en = np.column_stack([-np.sin(dec_) * np.cos(ra_), -np.sin(dec_) * np.sin(ra_), np.cos(dec_)])
er = np.column_stack([np.cos(dec_) * np.cos(ra_), np.cos(dec_) * np.sin(ra_), np.sin(dec_)])
L3 = ee * L[:, [0]] + en * L[:, [1]] + er * L[:, [2]]
from astropy import units as u  # noqa: E402
from astropy.coordinates import SkyCoord  # noqa: E402
gal = SkyCoord(x=L3[:, 0], y=L3[:, 1], z=L3[:, 2], representation_type="cartesian", frame="icrs").galactic.cartesian.xyz.value.T
mean_, se_ = gal.mean(axis=0), gal.std(axis=0) / np.sqrt(len(gal))
print(f"\nAstroSpectroSB1 3D <L-hat> (Galactic): X {mean_[0]:+.4f}±{se_[0]:.4f}  Y {mean_[1]:+.4f}±{se_[1]:.4f}  Z {mean_[2]:+.4f}±{se_[2]:.4f}  N={len(gal)}")
out["sb1_3d"] = dict(mean=mean_.tolist(), se=se_.tolist(), N=len(gal))

with open(sys.argv[0].rsplit("/", 2)[0] + f"/work/final_{tag}.json", "w") as f:
    json.dump(out, f, indent=1, default=float)
