"""r9: what is constrained.
J175634: static-lens chi2 profile in tE (tE fixed on a grid, everything else free, blending free per series) and the implied
o/W1 blend fractions; then the same with the Gaia prior fs in [0.8, 1.0] (ATLAS-o, W1). Tests the first-pass 'tE 92 d, u0 0.02,
fs 0.07' solution. Also t0, u0 and Amax ranges within dchi2 < 4 of the best (free fs) and under the prior.
J174744: parallax lens with physical blending (fs <= 1 in every series) across reduction variants, vs the best non-lens shape
of the same variant (non-lens fits never capped); tE profile with fs <= 1.
J174744 series are kept if they have >= 3 nights within 250 d of the peak (ev_dt=250): the Hawaii units 01a/02a hold the only
2021 rise data (to MJD ~59500 = -150 d) and are dropped by the 150-d default."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import Fitter, build  # noqa: E402
from lib import targets  # noqa: E402

from oddsky.analysis.lensing import magnification  # noqa: E402

TT = targets()
log = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "r9_profiles.log"), "w")


def P(*a):
    print(*a, flush=True)
    print(*a, file=log, flush=True)


def fsstr(r, info, keys=("ATLAS_o_04a", "ATLAS_o_03a", "ATLAS_c_03a", "NEOWISE_W1", "NEOWISE_W2")):
    return " ".join(f"{g[6:]}:{r['amp'][g] / info[g]['base']:.2f}" for g in keys if g in r["amp"])


# ---------------------------------------------------------------- J175634
k, tpk = "J175634", 59661.3
T = TT[k]
df, info = build(k, T, tpk)
caps = {g: (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()}
mins = {g: 0.8 * (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()}
# series without event data (c_04a: no night within 30 d) get no prior
for g in ("ATLAS_c_04a",):
    caps.pop(g, None)
    mins.pop(g, None)
P(f"== {k}: static lens, tE profile (free blending | Gaia prior 0.8 <= fs <= 1.0)")
Ff = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(tpk))
Fp = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(tpk), fs_cap=caps, fs_min=mins)
best_f = Ff.fit("static", 59662.0)
best_p = Fp.fit("static", 59662.0)
P(f"  best free: chi2 {best_f['chi2']:.1f} tE {best_f['p'][1]:.2f} u0 {best_f['p'][2]:.4f} t0 {best_f['p'][0]:.2f}  fs {fsstr(best_f, info)}")
P(f"  best prior: chi2 {best_p['chi2']:.1f} tE {best_p['p'][1]:.2f} u0 {best_p['p'][2]:.4f} t0 {best_p['p'][0]:.2f}  fs {fsstr(best_p, info)}")
for te in (5, 7, 8, 9, 10, 11, 12, 13, 14, 16, 18, 22, 30, 45, 60, 92, 150):
    rf = Ff.fit("static", 59662.0, fixed={1: te})
    rp = Fp.fit("static", 59662.0, fixed={1: te})
    P(f"  tE {te:5.1f}: free dchi2 {rf['chi2'] - best_f['chi2']:8.1f} u0 {rf['p'][2]:.4f} Amax "
      f"{float(magnification(np.array([abs(rf['p'][2])]))[0]):6.1f} t0 {rf['p'][0]:.2f} fs {fsstr(rf, info)} | prior dchi2 "
      f"{rp['chi2'] - best_p['chi2']:8.1f} u0 {rp['p'][2]:.4f}")
# u0 / t0 scan under free blending
P("  u0 profile (free blending):")
for u0 in (0.02, 0.05, 0.08, 0.10, 0.12, 0.14, 0.17, 0.20, 0.25):
    r = Ff.fit("static", 59662.0, fixed={2: u0})
    P(f"    u0 {u0:.3f}: dchi2 {r['chi2'] - best_f['chi2']:7.1f} tE {r['p'][1]:6.2f} fs {fsstr(r, info)}")
P("  t0 profile (free blending):")
for t0 in (59661.5, 59662.0, 59662.5, 59663.0, 59663.5, 59664.0, 59664.5):
    r = Ff.fit("static", 59662.0, fixed={0: t0})
    P(f"    t0 {t0:.1f}: dchi2 {r['chi2'] - best_f['chi2']:7.1f} tE {r['p'][1]:6.2f} u0 {r['p'][2]:.3f}")

# ---------------------------------------------------------------- J174744
k, tpk = "J174744", 59650.0
T = TT[k]
P(f"\n== {k}: parallax lens with fs <= 1 vs best non-lens, across variants")
VAR = {"default": {}, "no error floor": dict(floor=None), "PSF-corrected": dict(psf_corr=True), "PSF maj<3.3": dict(maj_max=3.3),
       "window +-600": dict(window=(tpk - 600, tpk + 600)), "baseline >600": dict(base_dt=600), "o only": dict(bands=("o",)),
       "ATLAS only": dict(use_neowise=False), "chi<10": dict(chi_mode="abs")}
for vn, kw in VAR.items():
    df, info = build(k, T, tpk, ev_dt=250, **kw)
    caps = {g: (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()}
    F0 = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(tpk))
    Fc = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(tpk), fs_cap=caps)
    rs = Fc.fit("static", 59650.0)
    rp = Fc.fit("parallax", 59650.0)
    nl = {m: F0.fit(m, 59650.0)["chi2"] for m in ("pv7", "pv7_asym", "fred")}
    bn = min(nl, key=nl.get)
    p = rp["p"]
    P(f"  {vn:15s} n {len(df)}: static(fs<=1) {rs['chi2']:.1f} tE {rs['p'][1]:.0f}; parallax(fs<=1) {rp['chi2']:.1f} t0 {p[0]:.1f} "
      f"tE {p[1]:.1f} u0 {p[2]:+.3f} piE ({p[3]:+.3f},{p[4]:+.3f}) |piE| {np.hypot(p[3], p[4]):.2f} fs {fsstr(rp, info, ('ATLAS_o_03a', 'ATLAS_o_04a', 'ATLAS_c_03a', 'ATLAS_c_04a', 'NEOWISE_W1'))}; "
      f"best non-lens {bn} {nl[bn]:.1f} -> non-lens minus lens {nl[bn] - rp['chi2']:+.1f}")
df, info = build(k, T, tpk, ev_dt=250)
caps = {g: (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()}
Fc = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(tpk), fs_cap=caps)
best = Fc.fit("parallax", 59650.0)
P(f"  tE profile, parallax, fs <= 1 (best chi2 {best['chi2']:.1f}):")
for te in (50, 65, 80, 90, 100, 110, 125, 150, 200, 300):
    r = Fc.fit("parallax", 59650.0, fixed={1: te})
    p = r["p"]
    P(f"    tE {te:4d}: dchi2 {r['chi2'] - best['chi2']:7.1f} t0 {p[0]:.1f} u0 {p[2]:+.3f} piE ({p[3]:+.3f},{p[4]:+.3f}) fs "
      f"{fsstr(r, info, ('ATLAS_o_03a', 'ATLAS_o_04a', 'NEOWISE_W1'))}")
