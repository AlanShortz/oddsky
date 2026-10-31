"""r5: point lens (static, annual parallax, separate rise/fall tE) against fair non-lens shapes (Pearson VII symmetric and
asymmetric, Norris FRED, nova-like rise + power-law decline), in excess flux, every model with the same per-series freedom
(fitlib.py, copied from the H-0008 atlas10b referee pass). Reduction variants one choice at a time.
  J174401: ATLAS c/o per unit + NEOWISE W1/W2. The ATLAS 01a baseline before 2020 was taken with a wide PSF (3.2-3.4 px) and reads
           ~100 uJy against 366 uJy in 2020 (PSF 2.5 px) and 367-385 uJy in 02a: the default therefore starts in 2020.
  J180402: ATLAS o 02a (2015 PSF 3.7-4.1 px) + Gaia DR3 G and RP epoch photometry + NEOWISE.
  J172057: Gaia DR3 G/RP of the source 0.59" from the AllWISE position + NEOWISE (no ATLAS before 2016).
Usage: r5_fits.py <key>  -> r5_fits_<key>.log, data/r5_<key>.json, data/r5_<key>_series.csv"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import Fitter, build, summary  # noqa: E402
from lib import DATA, targets  # noqa: E402

from oddsky.analysis.lensing import magnification  # noqa: E402

k = sys.argv[1]
T = targets()[k]
MODELS = ["static", "parallax", "lens_asym", "pv7", "pv7_asym", "fred", "nova"]


def gaia_extra(sid, bands=("G", "RP")):
    g = pd.read_csv(os.path.join(DATA, f"r4_gaia_{sid}.csv"))
    g = g[(g.flag != "rejected_by_photometry") & np.isfinite(g.mag)]
    out = []
    for b in bands:
        x = g[g.band == b]
        fl = 10 ** (-0.4 * x.mag.values)
        rob = 1.4826 * np.median(np.abs(x.mag - x.mag.median()))
        err = np.hypot(x.err.values, max(rob, 0.01))
        out.append(pd.DataFrame({"t": x.t_mjd.values, "fl": fl, "fl_err": fl * err / 1.0857, "g": f"GAIA_{b}"}))
    return pd.concat(out, ignore_index=True)


if k == "J174401":
    # The southern units (03a, 04a) start in 2022 Feb, +160 d after the peak, and their 2022 nights carry PSF-width offsets of
    # 10-25% (narrow-PSF nights read high): ev_dt=150 keeps only series with nights within 150 d of the peak (c 02a, o 01a, o 02a);
    # the 2022 tail is constrained by NEOWISE (+200 d) instead. A variant keeps 03a/04a with the PSF correction.
    TPK, T0C, EVDT = 59450.0, 59450.0, 150
    W20 = (58850, 61500)
    VARIANTS = {
        "default (2020+)": dict(window=W20),
        "2020+ PSF-corrected": dict(window=W20, psf_corr=True),
        "2020+ chi<10": dict(window=W20, chi_mode="abs"),
        "2020+ PSF maj<3.0": dict(window=W20, maj_max=3.0),
        "2020+ no error floor": dict(window=W20, floor=None),
        "2020+ o only": dict(window=W20, bands=("o",)),
        "2020+ ATLAS only": dict(window=W20, use_neowise=False),
        "all years PSF-corrected": dict(psf_corr=True),
        "2020+ PSF-corrected with 03a/04a": dict(window=W20, psf_corr=True, ev_dt=400),
        "2020+ fs<=1": dict(window=W20),
        "2020+ fs<=0.8 (Gaia share 0.75)": dict(window=W20),
    }
    EXTRA = None
elif k == "J180402":
    TPK, T0C, EVDT = 57285.0, 57285.0, 120
    EXTRA = [gaia_extra(4143495279954502016)]
    VARIANTS = {
        "default (ATLAS o+c, Gaia G/RP, NEOWISE)": dict(),
        "PSF-corrected": dict(psf_corr=True),
        "no ATLAS (Gaia + NEOWISE)": dict(units=("zzz",)),
        "o only": dict(bands=("o",)),
        "fs<=1": dict(),
    }
else:  # J172057
    TPK, T0C, EVDT = 57272.0, 57272.0, 120
    EXTRA = [gaia_extra(5959812622743175552)]
    VARIANTS = {"Gaia G/RP + NEOWISE": dict(units=("zzz",)), "fs<=1": dict(units=("zzz",))}

out = {}
log = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"r5_fits_{k}.log"), "w")


def P(*a):
    print(*a, flush=True)
    print(*a, file=log, flush=True)


P(f"== {k} {T['name']}  peak guess {TPK}")
for vname, kw in VARIANTS.items():
    try:
        kw = dict(kw)
        evdt = kw.pop("ev_dt", EVDT)
        df, info = build(k, T, TPK, ev_dt=evdt, extra=EXTRA, **kw)
    except ValueError as e:
        P(f"-- {vname}: {e}")
        continue
    caps, mins, offs = None, None, False
    if "fs<=1" in vname:
        caps = {g: (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()}
    if "fs<=0.8" in vname:
        caps = {g: 0.8 * (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items() if not g.startswith("NEOWISE")}
        caps.update({g: 1.0 for g in info if g.startswith("NEOWISE")})
    if "free offsets" in vname:
        offs = True
    F = Fitter(df, ra=T["ra"], dec=T["dec"], t0par=round(TPK), offsets=offs, fs_cap=caps, fs_min=mins)
    P(f"\n-- variant: {vname}   n {len(df)}  series " + ", ".join(f"{g}(base {v['base']:.0f}, nev {v['nev']})" for g, v in info.items()))
    res = {}
    for m in MODELS:
        r = F.fit(m, T0C)
        res[m] = {kk: vv for kk, vv in r.items() if kk != "model"}
        if m in ("static", "parallax"):
            res[m]["fs"] = {g: (a / info[g]["base"]) for g, a in r["amp"].items()}
            res[m]["Amax"] = float(magnification(np.array([abs(r["p"][2])]))[0])
        P("   " + summary(r, info))
        if vname.startswith("default") or vname.startswith("Gaia G/RP"):
            df[f"m_{m}"] = r["model"]
    best_lens = min(res[m]["chi2"] for m in ("static", "parallax"))
    nl = [m for m in ("pv7", "pv7_asym", "fred", "nova")]
    nlname = min(nl, key=lambda m: res[m]["chi2"])
    P(f"   => static-parallax {res['static']['chi2'] - res['parallax']['chi2']:+.1f}; best non-lens ({nlname}) - best lens "
      f"{res[nlname]['chi2'] - best_lens:+.1f}; chi2/dof best lens {best_lens / (len(df) - res['parallax']['npar']):.2f}")
    out[vname] = res
    if vname.startswith("default") or vname.startswith("Gaia G/RP"):
        df.to_csv(os.path.join(DATA, f"r5_{k}_series.csv"), index=False)
json.dump(out, open(os.path.join(DATA, f"r5_{k}.json"), "w"), indent=1)
