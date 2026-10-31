"""r6: point-lens (static, annual parallax, separate rise/fall tE) vs fair non-lens shapes (Pearson VII symmetric/asymmetric,
Norris FRED, nova-like exponential rise + power-law decline), in excess flux, every model with the same per-series freedom.
ATLAS per unit/band + NEOWISE W1/W2. Reduction variants one choice at a time. Blend fractions fs = F_source / own baseline
(ATLAS baselines are clearly positive here: o 3300 / 12040 uJy, c 870 / 3120 uJy).
Usage: r6_fits.py <key>   -> r6_fits_<key>.log, data/r6_<key>.json, data/r6_<key>_series.csv"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import Fitter, build, summary  # noqa: E402
from lib import DATA, targets  # noqa: E402

from oddsky.analysis.lensing import magnification  # noqa: E402

k = sys.argv[1]
T = targets()[k]
TPK = {"J175634": 59661.3, "J174744": 59650.0}[k]
T0C = {"J175634": 59662.0, "J174744": 59650.0}[k]
EVDT = {"J175634": 150, "J174744": 250}[k]  # J174744: keep 01a/02a, whose 2021 nights are the only rise data
MODELS = ["static", "parallax", "lens_asym", "pv7", "pv7_asym", "fred", "nova"]
full = (TPK - 2600, TPK + 2600)
VARIANTS = {
    "default": {},
    "chi<10 (fixed)": dict(chi_mode="abs"),
    "no chi cut": dict(chi_mode="none"),
    "no error floor": dict(floor=None),
    "PSF-corrected": dict(psf_corr=True),
    "PSF maj<3.3 px": dict(maj_max=3.3),
    "window +-600 d": dict(window=(TPK - 600, TPK + 600)),
    "baseline >600 d": dict(base_dt=600),
    "o only": dict(bands=("o",)),
    "ATLAS only": dict(use_neowise=False),
    "fs<=1": {},
    "fs>=0.8 (Gaia)": {},
    "free offsets": {},
}
out = {}
log = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"r6_fits_{k}.log"), "w")


def P(*a):
    print(*a, flush=True)
    print(*a, file=log, flush=True)


P(f"== {k} {T['name']}  peak guess {TPK}")
for vname, kw in VARIANTS.items():
    df, info = build(k, T, TPK, ev_dt=EVDT, **kw)
    caps, mins, offs = None, None, False
    if vname == "fs<=1":
        caps = {g: (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()}
    if vname == "fs>=0.8 (Gaia)":
        mins = {g: 0.8 * (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()}
    if vname == "free offsets":
        offs = True
    F = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(TPK), offsets=offs, fs_cap=caps, fs_min=mins)
    P(f"\n-- variant: {vname}   n {len(df)}  series " + ", ".join(f"{g}(base {v['base']:.0f}, nev {v['nev']})" for g, v in info.items()))
    res = {}
    for m in MODELS:
        if vname not in ("default", "PSF-corrected", "ATLAS only", "fs<=1", "fs>=0.8 (Gaia)", "no error floor") and m in ("nova", "lens_asym"):
            continue
        r = F.fit(m, T0C)
        res[m] = {kk: vv for kk, vv in r.items() if kk != "model"}
        if m in ("static", "parallax"):
            res[m]["fs"] = {g: (a / info[g]["base"]) for g, a in r["amp"].items()}
            res[m]["Amax"] = float(magnification(np.array([abs(r["p"][2])]))[0])
        P("   " + summary(r, info))
        if vname == "default":
            df[f"m_{m}"] = r["model"]
    best_lens = min(res[m]["chi2"] for m in ("static", "parallax"))
    best_nl = min(res[m]["chi2"] for m in ("pv7", "pv7_asym", "fred", "nova") if m in res)
    nlname = min((m for m in ("pv7", "pv7_asym", "fred", "nova") if m in res), key=lambda m: res[m]["chi2"])
    P(f"   => static-parallax {res['static']['chi2'] - res['parallax']['chi2']:+.1f}; best non-lens ({nlname}) - best lens "
      f"{best_nl - best_lens:+.1f}; chi2/dof best lens {best_lens / (len(df) - res['parallax']['npar']):.2f}")
    out[vname] = res
    if vname == "default":
        df.to_csv(os.path.join(DATA, f"r6_{k}_series.csv"), index=False)
json.dump(out, open(os.path.join(DATA, f"r6_{k}.json"), "w"), indent=1)
