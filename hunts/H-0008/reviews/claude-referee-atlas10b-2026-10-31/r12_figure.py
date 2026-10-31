"""r12: figure (r12_lightcurves.png) and model predictions at the Gaia (GOST) transits and NEOWISE visits.
J175634: static lens, free blending (best) and Gaia prior (0.8 <= fs <= 1), and the best symmetric Pearson VII.
J174744: annual-parallax lens with fs <= 1, the static lens with fs <= 1, and the asymmetric Pearson VII (ev_dt=250 series)."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import Fitter, build  # noqa: E402
from lib import HERE, mjd2date, targets  # noqa: E402

from oddsky.analysis.lensing import magnification, sun_offsets  # noqa: E402

TT = targets()


def A_at(t, p, T, t0par, parallax):
    t = np.atleast_1d(np.asarray(t, float))
    tau = (t - p[0]) / p[1]
    beta = np.full_like(t, p[2])
    if parallax:
        dn, de = sun_offsets(t, T["ra"], T["dec"], t0par)
        tau = tau + p[3] * dn + p[4] * de
        beta = beta + (-p[3] * de + p[4] * dn)
    return magnification(np.hypot(tau, beta))


fig, ax = plt.subplots(2, 2, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]})
cols = {"01a": "C0", "02a": "C1", "03a": "C2", "04a": "C3"}
for j, (k, tpk, ev, win) in enumerate((("J175634", 59661.3, 150, (59630, 59700)), ("J174744", 59650.0, 250, (59350, 59950)))):
    T = TT[k]
    df, info = build(k, T, tpk, ev_dt=ev)
    caps = {g: (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()}
    mins = {g: 0.8 * c for g, c in caps.items() if g != "ATLAS_c_04a"}
    F0 = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(tpk))
    if k == "J175634":
        Fp = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(tpk), fs_cap={g: c for g, c in caps.items() if g != "ATLAS_c_04a"}, fs_min=mins)
        models = {"static lens, free fs": (F0.fit("static", 59662.0), False), "static lens, 0.8<=fs<=1": (Fp.fit("static", 59662.0), False),
                  "Pearson VII (sym.)": (F0.fit("pv7", 59662.0), None)}
    else:
        Fc = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(tpk), fs_cap=caps)
        models = {"parallax lens, fs<=1": (Fc.fit("parallax", 59650.0), True), "static lens, fs<=1": (Fc.fit("static", 59650.0), False),
                  "Pearson VII (asym.)": (F0.fit("pv7_asym", 59650.0), None)}
    a, r_ = ax[0, j], ax[1, j]
    for g, d in df.groupby("g"):
        if not g.startswith("ATLAS"):
            continue
        base = info[g]["base"]
        m = d.t.between(*win)
        cam = g[-3:]
        a.errorbar(d.t[m], 1 + d.d[m] / base, d.e[m] / base, fmt="o" if "_o_" in g else "s", ms=3, lw=0.5, color=cols[cam],
                   mfc=cols[cam] if "_o_" in g else "none", label=g[6:])
    for b, mk in (("NEOWISE_W1", "k*"), ("NEOWISE_W2", "m^")):
        d = df[(df.g == b) & df.t.between(*win)]
        a.plot(d.t, 1 + d.d, mk, ms=9, label=b[8:])
    tt = np.linspace(*win, 3000)
    print(f"== {k}")
    for (name, (res, par)), ls in zip(models.items(), ("-", "--", ":"), strict=True):
        if par is None:
            sub = Fitter(pd.DataFrame({"t": tt, "d": 0.0, "e": 1.0, "g": "x"}))
            prof = sub.pv7(res["p"]) if len(res["p"]) == 3 else sub.pv7_asym(res["p"])
            amp = res["amp"]["ATLAS_o_04a"] / info["ATLAS_o_04a"]["base"]
            a.plot(tt, 1 + amp * prof, "k" + ls, lw=1, label=f"{name} chi2 {res['chi2']:.0f}")
        else:
            fs = res["amp"]["ATLAS_o_04a"] / info["ATLAS_o_04a"]["base"]
            A = A_at(tt, res["p"], T, round(tpk), par)
            a.plot(tt, 1 + fs * (A - 1), "k" + ls, lw=1, label=f"{name} chi2 {res['chi2']:.0f}")
            p = res["p"]
            print(f"  {name}: chi2 {res['chi2']:.1f} p {np.round(p, 4).tolist()} fs(o_04a) {fs:.2f}")
            if k == "J175634":
                for tg in (59663.007,):
                    Ag = float(A_at(tg, p, T, round(tpk), par)[0])
                    for fsg in (0.8, 0.91, 1.0, 1.2):
                        print(f"     Gaia transit 2022-03-25 00:11 (MJD {tg}): A {Ag:.1f}; fs_G {fsg}: dG {-2.5 * np.log10(1 + fsg * (Ag - 1)):+.2f}")
                    for dt_ in (-0.25, 0.25):
                        Ag2 = float(A_at(tg + dt_, p, T, round(tpk), par)[0])
                        print(f"       (transit time +-6 h: A {Ag2:.1f})")
            else:
                for lab, tg in (("NEOWISE -199 d", 59455.6), ("NEOWISE +1.3", 59655.7), ("NEOWISE +165", 59819.8),
                                ("Gaia 2022-02-28", 59638.28), ("Gaia 2022-03-28", 59666.2), ("Gaia 2022-09-02", 59824.29),
                                ("Gaia 2022-10-03", 59855.02)):
                    Ag = float(A_at(tg, p, T, round(tpk), par)[0])
                    print(f"     {lab} ({mjd2date(tg)}): A {Ag:.3f}; with fs 0.94-0.98 x{1 + 0.94 * (Ag - 1):.3f}-{1 + 0.98 * (Ag - 1):.3f}"
                          f" (dG {-2.5 * np.log10(1 + 0.96 * (Ag - 1)):+.2f})")
    best = list(models.values())[0][0]
    res = (df.d - best["model"]) / df.e
    m = df.t.between(*win) & df.g.str.startswith("ATLAS")
    r_.scatter(df.t[m], res[m], s=6, c=[cols[g[-3:]] for g in df.g[m]])
    r_.axhline(0, color="k", lw=0.5)
    r_.set_ylabel(f"resid ({list(models)[0]}) / sigma")
    a.set_title(f"{T['name']} (G {T['G']:.2f}, l {T['l']:.2f}, b {T['b']:+.2f})")
    a.set_ylabel("flux / own baseline (ATLAS per unit; NEOWISE)")
    a.legend(fontsize=7, ncol=2)
    r_.set_xlabel("MJD")
plt.tight_layout()
plt.savefig(os.path.join(HERE, "r12_lightcurves.png"), dpi=90)
