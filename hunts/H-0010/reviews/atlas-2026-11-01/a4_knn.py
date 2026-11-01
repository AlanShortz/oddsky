"""a4: PSF-shape-matched excess for every ATLAS night, the error model calibrated on quiet nights, the event test and the repeat
search (2015-2026).

For each night, the baseline is the median of the K=15 nearest nights of the same unit and band in PSF-shape space
(maj, min, e*cos 2phi, e*sin 2phi; e = maj - min; px), drawn only from nights more than 150 d from that night and more than 150 d
from the Gaia t0 (Gaia is flat there: a3). The orientation terms matter because the dominant neighbours sit at fixed position angles.
Night error = hypot(formal, kNN robust scatter) + scatter / sqrt(K). The error model is then calibrated per series: the robust std of
(excess / error) over quiet nights (|dt| > 150 d) multiplies every error of that series (listed as 'infl').

Event test: nights within 30 / 90 d of t0. The Gaia prediction for the ATLAS excess on the Gaia star is F_band x (R_G(t) - 1), where
R_G comes from a point lens fitted to Gaia G with fs = 1 (unblended; the physical limit) and with fs free (0.02-1), and from linear
interpolation between Gaia transits (only where the night falls between two transits less than 40 d apart). F_band is the Gaia star's
ATLAS-band flux (a1). The ATLAS flux scale against this Gaia conversion is 0.6-1.0 (a1/a2: ATLAS o baselines of the two detected
fields are 0.72 and 0.87 of the Gaia-predicted PSF-weighted flux; c 0.63 and 0.96), so alpha = observed / predicted of 0.6-1.0 is
what an achromatic event on the Gaia star gives.

Repeat test (bins with median kNN PSF distance < 1 px only): 20-d bins (weighted over units, per band) of the calibrated excess over the whole history; the largest bin away from the
event (|dt| > 200 d), its significance and its size in units of the Gaia star's band flux.
Writes data/a4_nights_<k>.csv, data/a4_summary.json.
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a4_knn.py"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, mjd2date, targets  # noqa: E402

from oddsky.analysis.lensing import magnification  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 500)
T = targets()
SH = json.load(open(os.path.join(DATA, "a1_shares.json")))
K = 15
OUT = {}


def feats(d):
    e = d.maj - d.mnr
    return np.vstack([d.maj, d.mnr, e * np.cos(2 * np.radians(d.phi)), e * np.sin(2 * np.radians(d.phi))]).T


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
    return pd.DataFrame(dict(t=d.t_mjd.values, f=f, e=fe))


def lens_fit(g, t0c, fs_fixed=None):
    t, f, e = g.t.values, g.f.values, g.e.values

    def m(p, tt):
        fs = fs_fixed if fs_fixed is not None else p[3]
        return fs * magnification(np.hypot((tt - p[0]) / p[1], p[2])) + 1 - fs

    best = None
    for te in (5, 10, 25, 60, 150, 300):
        for u0 in (0.02, 0.1, 0.3, 0.7):
            for dt in (-15, 0, 15):
                p0 = [t0c + dt, te, u0] + ([] if fs_fixed is not None else [0.7])
                lo = [t0c - 150, 1, 1e-4] + ([] if fs_fixed is not None else [0.02])
                hi = [t0c + 150, 2000, 3] + ([] if fs_fixed is not None else [1.0])
                r = least_squares(lambda p: (m(p, t) - f) / e, p0, bounds=(lo, hi))
                if best is None or r.cost < best.cost:
                    best = r
    return (lambda tt, p=best.x: m(p, tt)), best.x, 2 * best.cost


def interp_R(g, tt):
    t, f = g.t.values, g.f.values
    out = np.full(len(tt), np.nan)
    for i, x in enumerate(tt):
        j = np.searchsorted(t, x)
        if 0 < j < len(t) and t[j] - t[j - 1] < 40:
            out[i] = f[j - 1] + (f[j] - f[j - 1]) * (x - t[j - 1]) / (t[j] - t[j - 1])
    return out


def alpha(y, ye, x):
    ok = np.isfinite(y) & np.isfinite(ye) & np.isfinite(x) & (ye > 0)
    if ok.sum() == 0 or np.sum(x[ok] ** 2) == 0:
        return dict(n=0)
    w = 1 / ye[ok] ** 2
    a = float(np.sum(w * x[ok] * y[ok]) / np.sum(w * x[ok] ** 2))
    ae = float(1 / np.sqrt(np.sum(w * x[ok] ** 2)))
    chi = float(np.sum(w * (y[ok] - a * x[ok]) ** 2))
    nu = max(int(ok.sum()) - 1, 1)
    return dict(n=int(ok.sum()), alpha=a, err=ae * np.sqrt(max(chi / nu, 1)), chi2_fit=chi, chi2_zero=float(np.sum(w * y[ok] ** 2)),
                snr_pred=float(np.sqrt(np.sum(w * x[ok] ** 2))))


raw_cache = {}
for k in KEYS:
    t = T[k]
    t0 = t["t0"]
    nt = pd.read_csv(os.path.join(DATA, f"a2_nightly_{k}.csv"))
    # phi per night (a2 did not keep it): recompute from the frames
    from lib import atlas_raw, clean  # noqa: E402
    rc = clean(atlas_raw(k))
    ph = rc.groupby(["F", "cam", "night"]).phi.median().rename("phi").reset_index()
    nt = nt.merge(ph, on=["F", "cam", "night"], how="left")
    nt["kb"] = np.nan
    nt["ks"] = np.nan
    nt["kd"] = np.nan
    for (F, cam), d in nt.groupby(["F", "cam"]):
        X = feats(d)
        tt = d.t.values
        for i, idx in enumerate(d.index):
            ok = (np.abs(tt - tt[i]) > 150) & (np.abs(tt - t0) > 150)
            if ok.sum() < K:
                continue
            dist = np.sqrt(np.sum((X[ok] - X[i]) ** 2, axis=1))
            o = np.argsort(dist)[:K]
            v = d.ujy.values[ok][o]
            med = np.median(v)
            nt.loc[idx, ["kb", "ks", "kd"]] = med, 1.4826 * np.median(np.abs(v - med)) * 1.07, dist[o].max()
    nt["kexc"] = nt.ujy - nt.kb
    nt["kerr0"] = np.hypot(nt.ujy_err, nt.ks) + nt.ks / np.sqrt(K)
    # calibrate per series on quiet nights
    nt["infl"] = np.nan
    infl = {}
    for (F, cam), d in nt.groupby(["F", "cam"]):
        q = d[(np.abs(d.t - t0) > 150) & d.kexc.notna()]
        if len(q) < 10:
            continue
        z = q.kexc / q.kerr0
        s = float(1.4826 * np.median(np.abs(z - np.median(z))))
        infl[f"{F}_{cam}"] = (round(s, 2), len(q), round(float(np.median(q.ks)), 1))
        nt.loc[d.index, "infl"] = max(s, 1.0)
    nt["kerr"] = nt.kerr0 * nt.infl
    nt["ksig"] = nt.kexc / nt.kerr
    g = gaia_G(k)
    L1, p1, c1 = lens_fit(g, t["tpk"], fs_fixed=1.0)
    LF, pf, cf = lens_fit(g, t["tpk"])
    fband = {"c": SH[k]["fc_star"], "o": SH[k]["fo_star"]}
    nt["Fb"] = nt.F.map(fband)
    nt["R_fs1"] = L1(nt.t.values)
    nt["R_fsfree"] = LF(nt.t.values)
    nt["R_interp"] = interp_R(g, nt.t.values)
    for c in ("fs1", "fsfree", "interp"):
        nt[f"pred_{c}"] = nt.Fb * (nt[f"R_{c}"] - 1)
    nt["dt"] = nt.t - t0
    nt.to_csv(os.path.join(DATA, f"a4_nights_{k}.csv"), index=False)

    print("=" * 40, k, t["name"], f"Gaia t0 {mjd2date(t0)}; Gaia star c {fband['c']:.0f} uJy, o {fband['o']:.0f} uJy")
    print("error-model inflation per series (robust std of excess/error on quiet nights; n; median kNN scatter uJy):",
          "  ".join(f"{a}:{b[0]}(n{b[1]},{b[2]})" for a, b in sorted(infl.items())))
    print(f"Gaia G lens, fs=1: t0 {mjd2date(p1[0])} tE {p1[1]:.1f} u0 {p1[2]:.3f} chi2 {c1:.1f}; fs free: t0 {mjd2date(pf[0])} tE {pf[1]:.1f} "
          f"u0 {pf[2]:.3f} fs {pf[3]:.2f} chi2 {cf:.1f} (n {len(g)})")
    ev = nt[np.abs(nt.dt) <= 120].sort_values("t").copy()
    ev["date"] = [mjd2date(x) for x in ev.t]
    if len(ev):
        print(ev[["date", "dt", "F", "cam", "n", "maj", "mnr", "ujy", "kb", "kd", "kexc", "kerr", "ksig", "R_fs1", "R_fsfree", "R_interp",
                  "pred_fs1", "pred_fsfree", "pred_interp"]].round(2).to_string(index=False))
    summ = {"infl": infl, "lens_fs1": [float(x) for x in p1], "lens_fsfree": [float(x) for x in pf]}
    for win in (30, 90):
        for F in ("o", "c", "oc"):
            d = nt[(np.abs(nt.dt) <= win) & nt.F.isin(list(F)) & nt.kexc.notna()]
            if len(d) == 0:
                if F != "oc":
                    print(f"  {F} +-{win} d: no night with a kNN baseline")
                continue
            res = {c: alpha(d.kexc.values, d.kerr.values, d[f"pred_{c}"].values) for c in ("fs1", "fsfree", "interp")}
            w = 1 / d.kerr**2
            pe = float(np.sum(w * d.kexc) / np.sum(w))
            pee = float(1 / np.sqrt(np.sum(w)))
            res["pooled"] = dict(n=len(d), exc=pe, err=pee)
            summ[f"{F}_{win}"] = res
            txt = "; ".join(f"{c}: alpha {v['alpha']:+.2f} +- {v['err']:.2f} (pred S/N {v['snr_pred']:.1f})" for c, v in res.items()
                            if c != "pooled" and v.get("n"))
            print(f"  {F:2s} +-{win} d: {len(d)} nights; pooled excess {pe:+.1f} +- {pee:.1f} uJy ({pe / pee:+.1f} sigma); {txt}")
    # repeats
    rows = []
    for F in ("o", "c"):
        d = nt[(nt.F == F) & nt.kexc.notna()].copy()
        d["bin"] = np.floor((d.t - 57200) / 20).astype(int)
        for b, x in d.groupby("bin"):
            w = 1 / x.kerr**2
            m = float(np.sum(w * x.kexc) / np.sum(w))
            me = float(1 / np.sqrt(np.sum(w)))
            chi = float(np.sum(w * (x.kexc - m) ** 2) / max(len(x) - 1, 1))
            rows.append(dict(F=F, t=float(x.t.mean()), n=len(x), exc=m, err=me * np.sqrt(max(chi, 1)), units=",".join(sorted(x.cam.unique())),
                             kd=float(x.kd.median())))
    B = pd.DataFrame(rows)
    B["sig"] = B.exc / B.err
    B["dt"] = B.t - t0
    B["in_star"] = B.exc / B.F.map(fband)
    # only bins whose nights found PSF-matched comparison nights (median kNN distance < 1 px); in the wide-PSF seasons (02a 2015-16,
    # 01a 2017-19) the matching nights sit within 150 d of the night itself and are excluded, so those bins are not testable
    far = B[(np.abs(B.dt) > 200) & (B.kd < 1.0)]
    print(f"  repeat bins dropped for poor PSF match (median kNN distance >= 1 px): {int(((np.abs(B.dt) > 200) & (B.kd >= 1.0)).sum())}")
    summ["repeat"] = {}
    for F in ("o", "c"):
        f = far[far.F == F]
        if len(f) == 0:
            continue
        j = f.sig.idxmax()
        n5 = int((f.sig > 5).sum())
        n4 = int((f.sig > 4).sum())
        nneg5 = int((f.sig < -5).sum())
        summ["repeat"][F] = dict(nbins=len(f), max_sig=float(f.sig[j]), max_date=mjd2date(f.t[j]), max_exc=float(f.exc[j]),
                                 max_in_star=float(f.in_star[j]), n_gt5=n5, n_gt4=n4, n_lt_minus5=nneg5,
                                 years=f"{2000 + (f.t.min() - 51544.5) / 365.25:.1f}-{2000 + (f.t.max() - 51544.5) / 365.25:.1f}")
        top = f.sort_values("sig", ascending=False).head(3)
        print(f"  repeats {F}: {len(f)} 20-d bins with |dt| > 200 d ({summ['repeat'][F]['years']}); bins > 4 sigma {n4}, > 5 sigma {n5} "
              f"(< -5 sigma: {nneg5}); top: " + "; ".join(f"{mjd2date(r.t)} {r.exc:+.0f} +- {r.err:.0f} uJy ({r.sig:+.1f} sig, "
                                                              f"x{1 + r.in_star:.2f} of the star, n {r.n}, {r.units})" for r in top.itertuples()))
    B.to_csv(os.path.join(DATA, f"a4_bins_{k}.csv"), index=False)
    OUT[k] = summ
json.dump(OUT, open(os.path.join(DATA, "a4_summary.json"), "w"), indent=1, default=float)
