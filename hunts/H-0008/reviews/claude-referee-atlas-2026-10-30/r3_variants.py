"""r3: do the fitted parameters depend on reduction choices? Point lens + blending (static and parallax; Oddsky lensing.Problem)
for a grid of choices, plus non-lens shapes (Gaussian, Pearson VII, FRED, and a lens with separate rise/decline tE) for the
main variants. Output r3_variants_<k>.json and the log."""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import build, shape_fits  # noqa: E402
from lib import HERE, TARGETS  # noqa: E402

from oddsky.analysis.lensing import Problem, magnification  # noqa: E402

VARIANTS = {
    "inv_emul": dict(window=(58480, 60680), chi="abs", base_dt=250, floor="mad_inv", clip=99),
    "main": dict(),
    "chi_abs10": dict(chi="abs"),
    "chi_none": dict(chi="none"),
    "base250": dict(base_dt=250),
    "win2019_2024": dict(window=(58480, 60680)),
    "win2017_psfcorr": dict(window=(57750, 61500), psf_corr=True),
    "win2015_all_psfcorr": dict(window=(57000, 61500), psf_corr=True),
    "floor_scale": dict(floor="scale"),
    "floor_none": dict(floor="none"),
    "merged_per_band": dict(per_unit=False),
    "ztf_flag32768": dict(ztf_flags=(0, 32768)),
    "no_neowise": dict(use_neowise=False),
    "no_ztf": dict(use_ztf=False),
    "atlas_only": dict(use_ztf=False, use_neowise=False),
    "o_only_atlas": dict(use_ztf=False, use_neowise=False, bands=("o",)),
    "southern_units_only": dict(units=("03a", "04a"), use_ztf=False, use_neowise=False),
    "hawaii_units_only": dict(units=("01a", "02a"), use_ztf=False, use_neowise=False),
}


def summarise(prob, p, chi2, df):
    fs = dict(zip(prob.names, np.round(p[prob.nlens:], 3), strict=True))
    ag = {}
    for key in ("ATLAS_c", "ATLAS_o", "ZTF_g", "ZTF_r", "ZTF_i", "NEOWISE_W1", "NEOWISE_W2"):
        v = [fs[n] for n in fs if n.startswith(key)]
        if v:
            ag[key] = round(float(np.median(v)), 3)
    out = dict(chi2=round(chi2, 1), dof=int(len(df) - len(p)), t0=round(float(p[0]), 1), tE=round(float(p[1]), 1),
               u0=round(float(p[2]), 3), Amax=round(float(magnification(np.array([abs(p[2])]))[0]), 2), fs_median=ag, fs=fs)
    if prob.parallax:
        out["piE"] = [round(float(p[3]), 3), round(float(p[4]), 3)]
    return out


if __name__ == "__main__":
    keys = sys.argv[1:] or list(TARGETS)
    for k in keys:
        T = TARGETS[k]
        res = {}
        for vname, opts in VARIANTS.items():
            if k == "J183040" and vname == "win2015_all_psfcorr":
                pass
            t1 = time.time()
            df = build(k, **opts)
            r = {"n": len(df), "series": df.g.value_counts().sort_index().to_dict()}
            for par in (False, True):
                prob = Problem(df.t.values, df.f.values, df.e.values, df.g.values, ra=T["ra"], dec=T["dec"], parallax=par, blend=True,
                               t0par=T["tpk"])
                p, chi2 = prob.fit(t0c=T["tpk"])
                r["parallax" if par else "static"] = summarise(prob, p, chi2, df)
            if vname in ("inv_emul", "main", "chi_abs10", "win2017_psfcorr", "merged_per_band", "atlas_only", "o_only_atlas"):
                r["shapes"] = shape_fits(df, T["tpk"])
            res[vname] = r
            s, q = r["static"], r["parallax"]
            print(f"{k} {vname:20s} n={r['n']:4d} static chi2 {s['chi2']:7.1f}/{s['dof']} t0 {s['t0']:.1f} tE {s['tE']:6.1f} u0 {s['u0']:.3f} | "
                  f"parallax chi2 {q['chi2']:7.1f} t0 {q['t0']:.1f} tE {q['tE']:6.1f} u0 {q['u0']:+.3f} piE {q['piE']} | fs {q['fs_median']} "
                  f"[{time.time() - t1:.0f}s]", flush=True)
            if "shapes" in r:
                print("      shapes:", {kk: v[0] for kk, v in r["shapes"].items()}, "lens_asym (t0, tE_rise, tE_fall, u0):", r["shapes"]["lens_asym"][1][:4],
                      "fred:", r["shapes"]["fred"][1][:3], flush=True)
        json.dump(res, open(os.path.join(HERE, f"r3_variants_{k}.json"), "w"), indent=1, default=str)
