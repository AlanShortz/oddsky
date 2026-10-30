"""r3: point lens (static, parallax) vs non-lens shapes in excess-flux space, with reduction variants.
usage: r3_fits.py <key> [quick]
Default series: ATLAS per (band, unit) nightly, chi/N cut scaled with flux, baseline |dt|>400 d, error floor from the
baseline's excess scatter; NEOWISE W1/W2; plus Gaia alert photometry and ZTF where they exist (J191120, J174440).
Writes data/r3_<key>.json and data/r3_<key>_series.csv (default build + static/parallax models).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import Fitter, build, gaia_alert_series, summary, ztf_series  # noqa: E402
from lib import DATA, mjd2date, targets  # noqa: E402

T = targets()
TPK = {"J163539": 57980.0, "J075219": 58208.0, "J174440": 60010.0, "J191120": 59294.0, "J173150": 58311.0,
       "J185846": 57485.0, "J182120": 57472.0}
GSA = {"J191120": "Gaia21atr", "J174440": "Gaia23boj"}
ZTFF = {"J191120": "ztf_J191120.csv"}

k = sys.argv[1]
quick = len(sys.argv) > 2
t = T[k]
tpk = TPK[k]


def extras(gaia=True, ztf=True):
    ex = []
    if gaia and k in GSA:
        ex.append(gaia_alert_series(GSA[k]))
    if ztf and k in ZTFF:
        ex.append(ztf_series(os.path.join(DATA, ZTFF[k])))
    return ex


VARIANTS = {
    "default": {},
    "chi_abs10": dict(chi_mode="abs"),
    "chi_none": dict(chi_mode="none"),
    "base300": dict(base_dt=300),
    "base600": dict(base_dt=600),
    "no_floor": dict(floor="none"),
    "psf_corr": dict(psf_corr=True),
    "maj<3.3": dict(maj_max=3.3),
    "window+-800d": dict(window=(tpk - 800, tpk + 800), min_base=5),
    "o_only+WISE": dict(bands=("o",)),
    "ATLAS_only": dict(use_neowise=False, _noextra=True),
    "no_extra_surveys": dict(_noextra=True),
    "offsets_free": dict(_offsets=True),
    "fs<=1": dict(_cap=True),
}
if quick:
    VARIANTS = {kk: VARIANTS[kk] for kk in ("default",)}

out = {}
for vname, opt in VARIANTS.items():
    opt = dict(opt)
    noextra = opt.pop("_noextra", False)
    offsets = opt.pop("_offsets", False)
    cap = opt.pop("_cap", False)
    df, info = build(k, t, tpk, extra=[] if noextra else extras(), **opt)
    fs_cap = None
    if cap:
        fs_cap = {g: (v["base"] if v["unit"] == "uJy" else 1.0) for g, v in info.items()
                  if v["unit"] != "uJy" or v["base"] > 3 * v["rob"]}
    F = Fitter(df, ra=t["ra"], dec=t["dec"], t0par=round(tpk), offsets=offsets, fs_cap=fs_cap)
    kinds = ["static", "parallax", "lens_asym", "pv7", "pv7_asym", "fred", "nova"]
    if vname not in ("default",):
        kinds = ["static", "parallax", "lens_asym", "pv7_asym", "nova"]
    print(f"===== {k} variant {vname}: {len(df)} points, series " +
          ", ".join(f"{g}(base {v['base']:.0f}{'' if v['unit'] == 'uJy' else 'rel'}, rob {v['rob']:.3g}, nev {v['nev']})"
                    for g, v in info.items()), flush=True)
    res = {}
    for kind in kinds:
        r = F.fit(kind, tpk)
        print("  " + summary(r, info), flush=True)
        res[kind] = {kk: vv for kk, vv in r.items() if kk != "model"}
        if vname == "default" and kind in ("static", "parallax"):
            df[f"m_{kind}"] = r["model"]
    best_lens = min(res["static"]["chi2"], res["parallax"]["chi2"])
    others = {kk: v["chi2"] for kk, v in res.items() if kk not in ("static", "parallax", "lens_asym")}
    bo = min(others, key=others.get)
    print(f"  -> best lens {best_lens:.1f} vs best non-lens {bo} {others[bo]:.1f}: dchi2 {others[bo] - best_lens:+.1f}; "
          f"static t0 {mjd2date(res['static']['p'][0])}", flush=True)
    out[vname] = dict(res=res, info=info)
    if vname == "default":
        df.to_csv(os.path.join(DATA, f"r3_{k}_series.csv"), index=False)
json.dump(out, open(os.path.join(DATA, f"r3_{k}{'_quick' if quick else ''}.json"), "w"), indent=1, default=float)

if not quick:
    print("\n===== robustness summary", k)
    rows = []
    for vname, o in out.items():
        s, p = o["res"]["static"], o["res"]["parallax"]
        la = o["res"]["lens_asym"]
        nl = min(v["chi2"] for kk, v in o["res"].items() if kk not in ("static", "parallax", "lens_asym"))
        print(f"  {vname:18s} static t0 {s['p'][0]:.1f} tE {s['p'][1]:6.1f} u0 {s['p'][2]:.4f} chi2 {s['chi2']:8.1f} | parallax t0 "
              f"{p['p'][0]:.1f} tE {p['p'][1]:6.1f} u0 {p['p'][2]:+.4f} piE ({p['p'][3]:+.2f},{p['p'][4]:+.2f}) chi2 {p['chi2']:8.1f} | "
              f"asym tEr/tEf {la['p'][1] / la['p'][2]:.2f} | best non-lens {nl:8.1f} (d {nl - min(s['chi2'], p['chi2']):+.1f})")
