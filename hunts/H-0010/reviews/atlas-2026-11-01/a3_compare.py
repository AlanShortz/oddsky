"""a3: ATLAS against Gaia at the event, in excess flux (immune to the additive offsets of crowded reduced-image photometry).

Per night within 150 d of the Gaia t0 (a2 nightly bins), a PSF-matched baseline from the same unit and band:
  strict : nights with |dt| > 400 d and |maj - maj_night| < 0.25 px (0.4 px if fewer than 5);
  relaxed: nights with |dt| > 150 d (outside every Gaia event transit by > 100 d; Gaia is flat there, checked below), same PSF match.
excess = night - matched median; error^2 = max(night error, matched robust scatter)^2 + scatter^2 / n_matched.

Gaia template R_G(t) (G flux / G baseline): static point lens with fs <= 1 and an asymmetric Pearson VII, fitted to Gaia DR3 G alone.
Predicted ATLAS excess on the star = F_band(Gaia star) x (R_G(t) - 1), F_band from Gaia G/BP/RP (lib.gaia_to_atlas_ujy; ~0.2 mag).
alpha_band = weighted LSQ scale of observed on predicted excess (alpha = 1: ATLAS sees Gaia's event on the Gaia star, achromatic;
alpha = 0: ATLAS sees nothing). Where the series baseline is clearly detected (a2 'usable') the ratio 1 + excess / matched baseline is
also given with the ratio a lens on the star predicts, 1 + predicted excess / matched baseline.
Writes data/a3_nights_<k>.csv and data/a3_summary.json.
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a3_compare.py"""
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
pd.set_option("display.max_rows", 400)
T = targets()
SH = json.load(open(os.path.join(DATA, "a1_shares.json")))
A2 = json.load(open(os.path.join(DATA, "a2_summary.json")))
OUT = {}


def gaia_ratios(k):
    t = T[k]
    e = pd.read_csv(os.path.join(DATA, f"epoch_{t['sid']}.csv"))
    e = e[e.flag.fillna("") != "rejected_by_photometry"]
    res = {}
    for b in ("G", "BP", "RP"):
        d = e[(e.band == b) & np.isfinite(e.mag)].sort_values("t_mjd")
        out = (d.t_mjd < t["ep_first"] - 30) | (d.t_mjd > t["ep_last"] + 30)
        mb = np.median(d.mag[out])
        f = 10 ** (-0.4 * (d.mag.values - mb))
        fe = f * d.err.values / 1.0857
        sc = 1.4826 * np.median(np.abs(f[out.values] - 1))
        fe = np.hypot(fe, np.sqrt(max(sc**2 - np.median(fe[out.values]) ** 2, 0)))
        res[b] = pd.DataFrame(dict(t=d.t_mjd.values, f=f, e=fe))
    return res


def fit_templates(g, t0c):
    t, f, e = g.t.values, g.f.values, g.e.values

    def lens(p, tt):
        u = np.hypot((tt - p[0]) / p[1], p[2])
        return p[3] * magnification(u) + 1 - p[3]

    best = None
    for te in (10, 25, 60, 150, 300):
        for u0 in (0.05, 0.2, 0.5, 1.0):
            for dt in (-20, 0, 20):
                r = least_squares(lambda p: (lens(p, t) - f) / e, [t0c + dt, te, u0, 0.8],
                                  bounds=([t0c - 200, 1, 1e-4, 0.02], [t0c + 200, 3000, 3, 1.0]))
                if best is None or r.cost < best.cost:
                    best = r
    pl = best.x

    def pv7(p, tt):
        w = np.where(tt < p[0], p[1], p[2])
        return 1 + p[4] * (1 + ((tt - p[0]) / w) ** 2) ** (-p[3])

    bs = None
    for dt in (-20, 0, 20):
        for w in (5, 15, 40, 100, 250):
            for m in (0.5, 1, 3):
                r = least_squares(lambda p: (pv7(p, t) - f) / e, [t0c + dt, w, w, m, max(f.max() - 1, 0.1)],
                                  bounds=([t0c - 200, 1, 1, 0.1, 0], [t0c + 200, 3000, 3000, 50, 200]))
                if bs is None or r.cost < bs.cost:
                    bs = r
    return (lambda tt: lens(pl, tt)), pl, 2 * best.cost, (lambda tt: pv7(bs.x, tt)), bs.x, 2 * bs.cost


def matched(d, row, D, tol=0.25):
    c = d[(d.F == row.F) & (d.cam == row.cam) & (np.abs(d.dt) > D)]
    for tl in (tol, 0.4):
        m = c[np.abs(c.maj - row.maj) < tl]
        if len(m) >= 5:
            med = float(np.median(m.ujy))
            rob = float(1.4826 * np.median(np.abs(m.ujy - med)))
            return med, rob, len(m), tl, float(np.median(m.t))
    return np.nan, np.nan, len(c[np.abs(c.maj - row.maj) < 0.4]), np.nan, np.nan


def alpha(y, ye, x):
    ok = np.isfinite(y) & np.isfinite(ye) & np.isfinite(x) & (ye > 0)
    if ok.sum() == 0 or np.sum(x[ok] ** 2 / ye[ok] ** 2) == 0:
        return dict(n=0)
    w = 1 / ye[ok] ** 2
    a = float(np.sum(w * x[ok] * y[ok]) / np.sum(w * x[ok] ** 2))
    ae = float(1 / np.sqrt(np.sum(w * x[ok] ** 2)))
    chi = float(np.sum(w * (y[ok] - a * x[ok]) ** 2))
    chi0 = float(np.sum(w * y[ok] ** 2))
    nu = max(int(ok.sum()) - 1, 1)
    return dict(n=int(ok.sum()), alpha=a, err=ae * np.sqrt(max(chi / nu, 1)), chi2=chi, chi2_zero=chi0,
                chi2_one=float(np.sum(w * (y[ok] - x[ok]) ** 2)), snr_pred=float(np.sqrt(np.sum(w * x[ok] ** 2))))


for k in KEYS:
    t = T[k]
    t0 = t["t0"]
    nt = pd.read_csv(os.path.join(DATA, f"a2_nightly_{k}.csv"))
    g = gaia_ratios(k)
    lensf, pl, chil, shapef, ps, chis = fit_templates(g["G"], t["tpk"])
    print("=" * 40, k, t["name"])
    print(f"Gaia G template: lens t0 {pl[0]:.1f} ({mjd2date(pl[0])}) tE {pl[1]:.1f} u0 {pl[2]:.3f} fs {pl[3]:.2f} chi2 {chil:.1f}; "
          f"asym PV7 t0 {ps[0]:.1f} w {ps[1]:.1f}/{ps[2]:.1f} m {ps[3]:.2f} amp {ps[4]:.2f} chi2 {chis:.1f} (n {len(g['G'])})")
    ge = g["G"][(g["G"].t > t0 - 150) & (g["G"].t < t0 + 150)]
    print("Gaia G transits within 150 d of t0: " + "  ".join(f"{mjd2date(a)}({a - t0:+.0f}):x{b:.2f}" for a, b in zip(ge.t, ge.f)))
    # Gaia flatness on the relaxed-baseline nights' span (2015-2017 part)
    gg = g["G"]
    far = gg[(np.abs(gg.t - t0) > 150)]
    print(f"Gaia G away from the event (|dt| > 150 d): n {len(far)}, max x{far.f.max():.3f}, min x{far.f.min():.3f}, robust scatter "
          f"{1.4826 * np.median(np.abs(far.f - 1)):.3f}")
    fc, fo = SH[k]["fc_star"], SH[k]["fo_star"]
    ev = nt[np.abs(nt.dt) <= 150].copy().sort_values("t")
    rows = []
    for r in ev.itertuples():
        ms, rs, ns, tls, tms = matched(nt, r, 400)
        mr, rr, nr, tlr, tmr = matched(nt, r, 150)
        Fb = fc if r.F == "c" else fo
        RL, RS = float(lensf(np.array([r.t]))[0]), float(shapef(np.array([r.t]))[0])
        j = np.argmin(np.abs(gg.t.values - r.t))
        ser = A2[k]["series"].get(f"{r.F}_{r.cam}", {})
        rows.append(dict(date=mjd2date(r.t), t=r.t, dt=r.dt, F=r.F, cam=r.cam, n=r.n, maj=r.maj, m5=r.m5, chi=r.chi, ujy=r.ujy,
                         ujy_err=r.ujy_err, b400=ms, s400=rs, n400=ns, b150=mr, s150=rr, n150=nr,
                         exc400=r.ujy - ms, err400=np.sqrt(max(r.ujy_err, rs) ** 2 + rs**2 / max(ns, 1)) if np.isfinite(rs) else np.nan,
                         exc150=r.ujy - mr, err150=np.sqrt(max(r.ujy_err, rr) ** 2 + rr**2 / max(nr, 1)) if np.isfinite(rr) else np.nan,
                         RG_lens=RL, RG_shape=RS, pred_lens=Fb * (RL - 1), pred_shape=Fb * (RS - 1),
                         gaia_near_dt=float(gg.t.values[j] - r.t), gaia_near_R=float(gg.f.values[j]), usable=bool(ser.get("usable", False))))
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(DATA, f"a3_nights_{k}.csv"), index=False)
    summ = {}
    if len(R) == 0:
        print("no ATLAS night within 150 d")
        OUT[k] = summ
        continue
    R["sig150"] = R.exc150 / R.err150
    R["sig400"] = R.exc400 / R.err400
    show = R[np.abs(R.dt) <= 120]
    print(f"Gaia star in ATLAS bands: c {fc:.0f} uJy, o {fo:.0f} uJy. Nights within 120 d (excess in uJy; pred = lens-on-star from Gaia G):")
    print(show[["date", "dt", "F", "cam", "n", "maj", "ujy", "ujy_err", "n400", "exc400", "err400", "n150", "exc150", "err150",
                "RG_lens", "pred_lens", "pred_shape", "gaia_near_dt", "gaia_near_R"]].round(2).to_string(index=False))
    for win in (30, 90):
        for F in ("o", "c", "oc"):
            d = R[(np.abs(R.dt) <= win) & (R.F.isin(list(F)))]
            for bl in ("400", "150"):
                for tmpl in ("lens", "shape"):
                    a = alpha(d[f"exc{bl}"].values, d[f"err{bl}"].values, d[f"pred_{tmpl}"].values)
                    summ[f"{F}_{win}_{bl}_{tmpl}"] = a
                    if a.get("n", 0) and tmpl == "lens":
                        aS = alpha(d[f"exc{bl}"].values, d[f"err{bl}"].values, d["pred_shape"].values)
                        print(f"  {F:2s} +-{win} d, baseline |dt|>{bl}: {a['n']:2d} nights; alpha {a['alpha']:+.2f} +- {a['err']:.2f} "
                              f"(shape template {aS['alpha']:+.2f} +- {aS['err']:.2f}); chi2 alpha=0 {a['chi2_zero']:.1f}, alpha=1 "
                              f"{a['chi2_one']:.1f}; predicted-signal S/N {a['snr_pred']:.1f}")
    # pooled excess and ratio per band in the +-30 d window, against prediction
    for F in ("o", "c"):
        for win in (30, 90):
            d = R[(np.abs(R.dt) <= win) & (R.F == F) & np.isfinite(R.err150)]
            if len(d) == 0:
                continue
            w = 1 / d.err150**2
            m = float(np.sum(w * d.exc150) / np.sum(w))
            me = float(1 / np.sqrt(np.sum(w)))
            p = float(np.sum(w * d.pred_lens) / np.sum(w))
            ratio = ""
            if d.usable.all():
                bm = float(np.sum(w * d.b150) / np.sum(w))
                ratio = f"; ATLAS ratio {1 + m / bm:.3f} +- {me / bm:.3f} against a lens on the star {1 + p / bm:.3f}"
            summ[f"pooled_{F}_{win}"] = dict(n=len(d), exc=m, err=me, pred=p)
            print(f"  pooled {F} +-{win} d (relaxed baseline): {len(d)} nights, excess {m:+.1f} +- {me:.1f} uJy, predicted {p:+.1f}; "
                  f"in Gaia-star units {m / (fc if F == 'c' else fo):+.2f} +- {me / (fc if F == 'c' else fo):.2f} "
                  f"(Gaia G-1 there {p / (fc if F == 'c' else fo):+.2f}){ratio}")
    OUT[k] = dict(summary=summ, lens=[float(x) for x in pl], shape=[float(x) for x in ps])
json.dump(OUT, open(os.path.join(DATA, "a3_summary.json"), "w"), indent=1, default=float)
