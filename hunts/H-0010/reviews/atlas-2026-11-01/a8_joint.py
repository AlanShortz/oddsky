"""a8: is the event lens-shaped and achromatic once ATLAS is added? Joint fits of Gaia DR3 G (flux ratios) and ATLAS nightly excess
(same-era kNN PSF-matched baseline as a7, frames with kNN distance < 1 px, nights within 150 d of t0; errors inflated so the quiet
same-era nights have unit robust scatter).
Model: R(t) for the Gaia source; ATLAS band b sees s_b x F_b x (R(t) - 1), with F_b the Gaia star's ATLAS-band flux (a1) and s_b a
free scale (-0.5 to 1.5; negative allowed so a band that does not follow is measured, not pinned) that absorbs the ATLAS flux scale and the Gaia-to-ATLAS conversion. Achromatic: s_c = s_o. Shapes for R(t):
  lens      static point lens, fs (Gaia G) free in 0.02-1;
  lens_fs1  the same with fs = 1;
  pv7a      asymmetric Pearson VII (5 parameters);
  gauss_a   asymmetric Gaussian.
Reported: chi2 (Gaia, ATLAS), BIC, parameters, s_o and s_c (when c has nights), and the chi2 cost of forcing s_c = s_o.
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a8_joint.py   (A8_ONLY_O=1: J184922 with ATLAS o only)"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, atlas_raw, clean, mjd2date, targets  # noqa: E402

from oddsky.analysis.lensing import magnification  # noqa: E402

T = targets()
SH = json.load(open(os.path.join(DATA, "a1_shares.json")))
ERA_END = {"02a": 57754.0, "01a": 58849.0}
KF = 25
KEYS = ("J182124", "J200958", "J184837", "J182811", "J184922", "J180313")


def feats(d):
    e = d.maj - d["min"]
    return np.vstack([d.maj, d["min"], e * np.cos(2 * np.radians(d.phi)), e * np.sin(2 * np.radians(d.phi))]).T


def era_nights(k, win=150):
    t0 = T[k]["t0"]
    r = clean(atlas_raw(k))
    r["dt"] = r.mjd - t0
    rows = []
    for (F, cam), d in r.groupby(["F", "cam"]):
        q = d[(np.abs(d.dt) > 150) & (d.mjd < ERA_END.get(cam, 99999))]
        if len(q) < KF + 5:
            continue
        Xq = feats(q)
        # quiet same-era leave-one-out residuals for the error calibration
        zq = []
        for i in range(len(q)):
            dd = np.sqrt(np.sum((Xq - Xq[i]) ** 2, axis=1))
            dd[i] = np.inf
            o = np.argsort(dd)[:KF]
            v = q.ujy.values[o]
            med = np.median(v)
            zq.append((q.ujy.values[i] - med) / np.hypot(1.4826 * np.median(np.abs(v - med)), q.dujy.values[i]))
        zq = np.array(zq)
        infl = max(1.4826 * np.median(np.abs(zq - np.median(zq))), 1.0)
        e = d[np.abs(d.dt) <= win]
        Xe = feats(e)
        for j, row in enumerate(e.itertuples()):
            dd = np.sqrt(np.sum((Xq - Xe[j]) ** 2, axis=1))
            o = np.argsort(dd)[:KF]
            if dd[o].max() >= 1.0:
                continue
            v = q.ujy.values[o]
            med = np.median(v)
            rows.append(dict(night=row.night, t=row.mjd, F=F, cam=cam, resid=row.ujy - med,
                             err=infl * np.hypot(1.4826 * np.median(np.abs(v - med)), row.dujy)))
    R = pd.DataFrame(rows)
    if len(R) == 0:
        return R
    nb = R.groupby(["night", "F", "cam"]).apply(lambda x: pd.Series(dict(
        t=x.t.mean(), n=len(x), y=np.average(x.resid, weights=1 / x.err**2),
        e=max(1 / np.sqrt(np.sum(1 / x.err**2)), x.resid.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0))), include_groups=False).reset_index()
    return nb


def gaia_G(k):
    t = T[k]
    e = pd.read_csv(os.path.join(DATA, f"epoch_{t['sid']}.csv"))
    d = e[(e.band == "G") & np.isfinite(e.mag) & (e.flag.fillna("") != "rejected_by_photometry")].sort_values("t_mjd")
    out = (d.t_mjd < t["ep_first"] - 30) | (d.t_mjd > t["ep_last"] + 30)
    mb = np.median(d.mag[out])
    f = 10 ** (-0.4 * (d.mag.values - mb))
    fe = f * d.err.values / 1.0857
    sc = 1.4826 * np.median(np.abs(f[out.values] - 1))
    fe = np.hypot(fe, np.sqrt(max(sc**2 - np.median(fe[out.values]) ** 2, 0)))
    return d.t_mjd.values, f, fe


def shapeR(kind, p, t):
    if kind == "lens":
        return p[3] * magnification(np.hypot((t - p[0]) / p[1], p[2])) + 1 - p[3]
    if kind == "lens_fs1":
        return magnification(np.hypot((t - p[0]) / p[1], p[2]))
    if kind == "pv7a":
        w = np.where(t < p[0], p[1], p[2])
        return 1 + p[4] * (1 + ((t - p[0]) / w) ** 2) ** (-p[3])
    if kind == "gauss_a":
        w = np.where(t < p[0], p[1], p[2])
        return 1 + p[3] * np.exp(-0.5 * ((t - p[0]) / w) ** 2)


def starts(kind, tc, amp):
    if kind in ("lens", "lens_fs1"):
        for te in (8, 20, 45, 100, 250):
            for u0 in (0.03, 0.15, 0.4, 0.8):
                for dt in (-15, 0, 15):
                    p = [tc + dt, te, u0] + ([0.7] if kind == "lens" else [])
                    lo = [tc - 150, 1, 1e-4] + ([0.02] if kind == "lens" else [])
                    hi = [tc + 150, 2000, 3] + ([1.0] if kind == "lens" else [])
                    yield p, lo, hi
    elif kind == "pv7a":
        for dt in (-15, 0, 15):
            for w in (5, 15, 40, 100):
                for w2 in (5, 15, 40, 100):
                    for m in (0.7, 2, 6):
                        yield [tc + dt, w, w2, m, amp], [tc - 150, 1, 1, 0.1, 0], [tc + 150, 2000, 2000, 50, 300]
    else:
        for dt in (-15, 0, 15):
            for w in (5, 15, 40, 100):
                for w2 in (5, 15, 40, 100):
                    yield [tc + dt, w, w2, amp], [tc - 150, 1, 1, 0], [tc + 150, 2000, 2000, 300]


def fit(k, kind, tg, fg, eg, A, tied):
    tc = T[k]["tpk"]
    bands = sorted(A.F.unique()) if len(A) else []
    nsc = 1 if (tied or len(bands) <= 1) else len(bands)
    Fb = A.F.map({"c": SH[k]["fc_star"], "o": SH[k]["fo_star"]}).values if len(A) else np.array([])
    bi = np.array([0 if (tied or nsc == 1) else bands.index(b) for b in A.F]) if len(A) else np.array([], int)

    def resid(p, ns):
        R = shapeR(kind, p[:ns], tg)
        out = [(R - fg) / eg]
        if len(A):
            s = p[ns:][bi]
            out.append((s * Fb * (shapeR(kind, p[:ns], A.t.values) - 1) - A.y.values) / A.e.values)
        return np.concatenate(out)

    best = None
    for p0, lo, hi in starts(kind, tc, max(fg.max() - 1, 0.1)):
        ns = len(p0)
        x0 = np.r_[p0, [0.7] * (nsc if len(A) else 0)]
        L = np.r_[lo, [-0.5] * (nsc if len(A) else 0)]
        H = np.r_[hi, [1.5] * (nsc if len(A) else 0)]
        x0 = np.clip(x0, L + 1e-6, H - 1e-6)
        r = least_squares(resid, x0, bounds=(L, H), args=(ns,))
        if best is None or r.cost < best[0].cost:
            best = (r, ns)
    r, ns = best
    res = resid(r.x, ns)
    cg = float(np.sum(res[:len(tg)] ** 2))
    ca = float(np.sum(res[len(tg):] ** 2))
    n = len(res)
    kpar = len(r.x)
    return dict(kind=kind, chi2=cg + ca, chi2_gaia=cg, chi2_atlas=ca, n=n, k=kpar, bic=cg + ca + kpar * np.log(n),
                p=[float(x) for x in r.x[:ns]], s=dict(zip(bands if nsc > 1 else (["oc"] if len(bands) > 1 else bands), [float(x) for x in r.x[ns:]])))


OUT = {}
ONLY_O = os.environ.get("A8_ONLY_O") == "1"  # J184922: its c nights carry unphysical dips (a6/a7), so also fit o alone
for k in (("J184922",) if ONLY_O else KEYS):
    A = era_nights(k)
    if ONLY_O:
        A = A[A.F == "o"].reset_index(drop=True)
    tg, fg, eg = gaia_G(k)
    t0 = T[k]["t0"]
    print("=" * 30, k, T[k]["name"], f"ATLAS nights within 150 d: {len(A)} (o {int((A.F == 'o').sum()) if len(A) else 0}, c {int((A.F == 'c').sum()) if len(A) else 0})")
    if len(A):
        A.to_csv(os.path.join(DATA, f"a8_atlas_nights_{k}.csv"), index=False)
    res = {}
    for kind in ("lens", "lens_fs1", "pv7a", "gauss_a"):
        f1 = fit(k, kind, tg, fg, eg, A, tied=True)
        res[kind] = f1
        line = (f"  {kind:8s} tied s: chi2 {f1['chi2']:7.1f} (Gaia {f1['chi2_gaia']:.1f}, ATLAS {f1['chi2_atlas']:.1f}; n {f1['n']}, k {f1['k']}) "
                f"BIC {f1['bic']:.1f}; s {', '.join(f'{a} {b:.2f}' for a, b in f1['s'].items())}; p "
                + ", ".join(f"{x:.3g}" for x in f1["p"]) + f" (t0 {mjd2date(f1['p'][0])})")
        if len(A) and A.F.nunique() > 1:
            f2 = fit(k, kind, tg, fg, eg, A, tied=False)
            res[kind + "_free_s"] = f2
            line += f"\n           free s_c, s_o: chi2 {f2['chi2']:.1f} (tied minus free {f1['chi2'] - f2['chi2']:+.1f}); s " + ", ".join(
                f"{a} {b:.2f}" for a, b in f2["s"].items())
        print(line)
    # Gaia-only reference for the same shapes
    g = {kind: fit(k, kind, tg, fg, eg, A.iloc[:0] if len(A) else A, tied=True) for kind in ("lens", "pv7a")}
    print(f"  Gaia only: lens chi2 {g['lens']['chi2']:.1f}, pv7a chi2 {g['pv7a']['chi2']:.1f}; with ATLAS: "
          f"dBIC(best shape - best lens) = {min(res['pv7a']['bic'], res['gauss_a']['bic']) - min(res['lens']['bic'], res['lens_fs1']['bic']):+.1f}")
    res["gaia_only"] = g
    OUT[k] = res
json.dump(OUT, open(os.path.join(DATA, "a8_summary_o_only.json" if ONLY_O else "a8_summary.json"), "w"), indent=1, default=float)
