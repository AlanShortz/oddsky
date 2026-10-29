"""a3: point-lens fits to ATLAS nightly (a2 output) alone and jointly with NEOWISE exposures + comparison-corrected ZTF
(the first referee's /tmp/j1933ref/target_exp.parquet and ztf_zoff.csv). Own scipy code, outside the Oddsky tools.
Variants: fs = 1; fs free per survey/band; profiles in t0; wing residuals (2019 Oct-Nov rise vs 2020 Jul-Sep decline).
Window 2018 Oct - 2022 Jan. ATLAS errors: per-unit/band baseline nightly scatter (+) 1% of flux.
usage: a3_fits.py  (run a2 first; run from the repo root)"""
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

W0, W1 = 58400, 59600
n = pd.read_csv("/tmp/j1933atl/nightly_ref.csv")
bl = n[(n.mjd < 58400) | (n.mjd > 59300)]
floor = bl.groupby(["F", "unit"]).A.agg(lambda x: 1.4826 * np.median(np.abs(x - 1)))
n = n[(n.mjd > W0) & (n.mjd < W1) & (n.A > 0.5)].copy()
n["e"] = np.hypot([floor[(f, u)] for f, u in zip(n.F, n.unit)], 0.01 * n.A)
rows = [pd.DataFrame(dict(mjd=n.mjd, band="A" + n.F, f=n.A, e=n.e))]
t = pd.read_parquet("/tmp/j1933ref/target_exp.parquet")
t = t[(t.nb == 1) & (t.qual_frame > 0)]
for b, fl in [("W1", 0.035), ("W2", 0.08)]:
    m = t[f"{b.lower()}mpro"]; base = t[t.visit != 11].groupby("visit")[f"{b.lower()}mpro"].median().median()
    f = 10 ** (-0.4 * (m - base))
    rows.append(pd.DataFrame(dict(mjd=t.mjd, band=b, f=f, e=np.hypot(t[f"{b.lower()}sigmpro"].fillna(0.1), fl) * 0.921 * f)))
z = pd.read_csv("hunts/H-0007/work/ztf_J193353.csv")
z = z[(z.catflags == 0) & (z.field == 285) & z.filtercode.isin(["zg", "zr"])].copy()
z["d"] = z.mag - z.groupby("filtercode").mag.transform("median")
z = z.merge(pd.read_csv("/tmp/j1933ref/ztf_zoff.csv"), on=["mjd", "filtercode"], how="left")
z["d"] = z.d - z.zoff.fillna(0)
f = 10 ** (-0.4 * z.d)
rows.append(pd.DataFrame(dict(mjd=z.mjd, band="Z" + z.filtercode.str[-1], f=f, e=np.hypot(z.magerr, 0.012) * 0.921 * f)))
D = pd.concat(rows, ignore_index=True)
D = D[(D.mjd > W0) & (D.mjd < W1)].reset_index(drop=True)
print("points:", D.band.value_counts().to_dict())


def A(tt, t0, tE, u0):
    u = np.sqrt(u0 ** 2 + ((tt - t0) / tE) ** 2)
    return (u ** 2 + 2) / (u * np.sqrt(u ** 2 + 4))


def fit(d, groups, t0fix=None, fsfree=True, start=(58925, 63, 0.43)):
    """groups: list of band-sets sharing one fs. Returns (chi2, params, fs dict)."""
    gi = np.zeros(len(d), int)
    for k, g in enumerate(groups):
        gi[d.band.isin(g).values] = k
    tt, ff, ee = d.mjd.values, d.f.values, d.e.values
    ng = len(groups) if fsfree else 0

    def res(p):
        if t0fix is None:
            t0, tE, u0 = p[:3]; q = p[3:]
        else:
            t0 = t0fix; tE, u0 = p[:2]; q = p[2:]
        fs = np.ones(len(groups)) if not fsfree else q
        a = A(tt, t0, tE, u0)
        return (fs[gi] * a + 1 - fs[gi] - ff) / ee
    best = None
    for tE0 in (40, 63, 90, 140):
        for u00 in (0.1, 0.25, 0.43, 0.7):
            p0 = ([start[0]] if t0fix is None else []) + [tE0, u00] + [1.0] * ng
            lo = ([58850] if t0fix is None else []) + [5, 0.001] + [0.02] * ng
            hi = ([58960] if t0fix is None else []) + [600, 3] + [1.5] * ng
            r = least_squares(res, p0, bounds=(lo, hi))
            if best is None or r.cost < best.cost:
                best = r
    p = best.x
    t0 = p[0] if t0fix is None else t0fix
    tE, u0 = (p[1], p[2]) if t0fix is None else (p[0], p[1])
    fs = p[3:] if t0fix is None else p[2:]
    return 2 * best.cost, (t0, tE, u0), dict(zip(["/".join(g) for g in groups], np.round(fs, 3))) if fsfree else {}


def summary(lab, d, groups, fsfree):
    c2, (t0, tE, u0), fs = fit(d, groups, fsfree=fsfree)
    am = A(np.array([t0]), t0, tE, u0)[0]
    print(f"\n[{lab}] chi2 {c2:.0f}/{len(d) - 3 - (len(groups) if fsfree else 0)}  t0 {t0:.1f} ({pd.Timestamp(t0 - 40587, unit='D').date()})"
          f"  tE {tE:.1f}  u0 {u0:.3f}  A_max {am:.2f}  fs {fs}")
    gi = {b: k for k, g in enumerate(groups) for b in g}
    fsv = np.array(list(fs.values())) if fsfree else np.ones(len(groups))
    mod = np.array([fsv[gi[b]] * a + 1 - fsv[gi[b]] for b, a in zip(d.band, A(d.mjd.values, t0, tE, u0))])
    r = (d.f - mod)
    for wl, w0, w1 in [("2019 Sep 15-Nov 15 (rise wing)", 58741, 58803), ("2020 Mar 11", 58919, 58920), ("2020 Apr 8-12", 58946, 58952),
                       ("2020 Jun 10-30", 59010, 59031), ("2020 Jul 1-31", 59031, 59062), ("2020 Aug-Sep", 59062, 59123), ("2020 Oct", 59123, 59154)]:
        s = (D.loc[d.index].mjd > w0) & (D.loc[d.index].mjd < w1) if False else ((d.mjd > w0) & (d.mjd < w1))
        if s.sum():
            parts = {b: f"{r[s & (d.band == b)].mean():+.3f}({(s & (d.band == b)).sum()})" for b in sorted(d[s].band.unique())}
            print(f"   resid {wl}: {parts}")
    return c2, (t0, tE, u0)


at = D[D.band.str.startswith("A")]
summary("ATLAS, fs=1", at, [["Ac", "Ao"]], False)
summary("ATLAS, fs free (c,o)", at, [["Ac"], ["Ao"]], True)
summary("joint, fs=1", D, [["Ac", "Ao", "W1", "W2", "Zg", "Zr"]], False)
summary("joint, fs free per survey", D, [["Ac", "Ao"], ["W1", "W2"], ["Zg", "Zr"]], True)
summary("joint, one fs", D, [["Ac", "Ao", "W1", "W2", "Zg", "Zr"]], True)
print("\nprofile in t0 (ATLAS only; fs=1 | fs free):")
for t0 in range(58905, 58946, 4):
    a1 = fit(at, [["Ac", "Ao"]], t0fix=t0, fsfree=False)
    a2 = fit(at, [["Ac", "Ao"]], t0fix=t0, fsfree=True)
    print(f"  t0 {t0} ({pd.Timestamp(t0 - 40587, unit='D').strftime('%b %d')}): fs=1 chi2 {a1[0]:6.0f} tE {a1[1][1]:5.1f} u0 {a1[1][2]:.3f} "
          f"Amax {A(np.array([t0]), t0, *a1[1][1:])[0]:.2f} | fs free chi2 {a2[0]:6.0f} tE {a2[1][1]:5.1f} u0 {a2[1][2]:.3f} fs {list(a2[2].values())[0]} "
          f"Amax {A(np.array([t0]), t0, *a2[1][1:])[0]:.2f}")
D.to_csv("/tmp/j1933atl/joint.csv", index=False)
