"""H-0008: the ATLAS light curves of the two candidates, and joint point-lens fits (ATLAS + ZTF + NEOWISE).

ATLAS forced photometry on reduced images (tasks 5272650, 5272651; `work/atlas/`), binned per night, band and unit (weighted
mean), as flux / that series' baseline median (nights more than 400 d from the peak, outside the lens wings). No chi/N cut:
chi/N rises with flux, so a cut removes the peak (the ATLAS referee's correction 1). Errors: the per-night error, plus whatever
part of the baseline's robust night-to-night scatter it does not already explain. A series is fitted only if it has a baseline
(8 ATLAS nights or 3 ZTF nights) and data within 200 d of the peak. ZTF (catflags 0) and NEOWISE visits are the H-0008 referee's
(`reviews/claude-referee-2026-10-30/data/`). Fitted: 2019-2026. Before 2019, J180624's ATLAS flux is 30-50% low, tracking each
unit's PSF width (instrumental; NEOWISE is flat).

Models: point lens with a blend fraction per series, static and with annual parallax (oddsky.analysis.lensing, the lens_fit tool),
95% chi-square profile ranges for t0, tE and u0. Alternatives with the same per-series amplitudes, which a lens must beat for the
shape to count as evidence: a Pearson VII profile (symmetric and two-sided, free power, so its wings can be as wide as a lens's)
and a fast-rise exponential-decay pulse (Norris).
usage: uv run python scripts/hunt_h0008_atlas_fit.py [J180624 J183040]
"""

import json
import os
import sys

import numpy as np
import pandas as pd
from astropy.time import Time
from scipy.optimize import least_squares

from oddsky.analysis.lensing import Problem, coverage, magnification, profile_range
from oddsky.data import atlas

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hunts", "H-0008")
REF = os.path.join(ROOT, "reviews", "claude-referee-2026-10-30", "data")
OUT = os.path.join(ROOT, "work")
TARGETS = {  # AllWISE position, NEOWISE event visit
    "J180624": ("J180624.78-090411.4", 271.603281, -9.069857, 59823.3),
    "J183040": ("J183040.98-220950.3", 277.670788, -22.163984, 59831.3),
}
WINDOW = (58480, 61500)  # 2019-2026
BASE_DT = 400


def ratio_series(t, flux, ferr, label, tpk):
    """Flux / baseline median; the error gains the part of the baseline scatter that the quoted errors do not explain.
    Returns None when the baseline is not clearly detected (median below 5 times its typical error, or negative): a ratio to
    it is meaningless, and a negative baseline turns a brightening into a dip (the ATLAS follow-up referee's correction 2)."""
    base = np.abs(t - tpk) > BASE_DT
    med = np.median(flux[base])
    if not med > 5 * np.median(ferr[base]):
        return None
    scatter = 1.4826 * np.median(np.abs(flux[base] / med - 1))
    quoted = np.median(ferr[base] / med)
    extra = np.sqrt(max(scatter**2 - quoted**2, 0.0))
    return pd.DataFrame({"t": t, "f": flux / med, "e": np.hypot(ferr / med, extra), "g": label})


def usable(t, tpk, min_base):
    return (np.abs(t - tpk) > BASE_DT).sum() >= min_base and (np.abs(t - tpk) < 200).sum() >= 1


def series(k):
    name, ra, dec, tpk = TARGETS[k]
    rows = []
    raw = atlas.parse(open(os.path.join(OUT, "atlas", f"atlas_{k}.txt")).read())
    raw = raw[(raw.err == 0) & (raw.dujy > 0) & (raw.mag5sig > 17.5) & (raw.mjd > WINDOW[0]) & (raw.mjd < WINDOW[1])].copy()
    raw["night"] = np.floor(raw.mjd)
    for (F, cam), d in raw.groupby(["F", raw.obs.str[:3]]):
        w = 1 / d.dujy**2
        g = d.assign(w=w, wf=w * d.ujy).groupby("night")
        nt = pd.DataFrame({"t": g.mjd.mean(), "fl": g.wf.sum() / g.w.sum(), "fe": 1 / np.sqrt(g.w.sum())})
        if not usable(nt.t.values, tpk, 8):
            continue
        s = ratio_series(nt.t.values, nt.fl.values, nt.fe.values, f"ATLAS_{F}_{cam}", tpk)
        if s is not None:
            rows.append(s[(s.f > 0.3) & (s.f < 20)])  # zero-flux dropouts and absurd nights
    z = pd.read_csv(os.path.join(REF, f"ztf_{k}.csv"))
    z = z[(z.catflags == 0) & z.mag.notna() & (z.mjd > WINDOW[0]) & (z.mjd < WINDOW[1])]
    for (fc, fld), d in z.groupby(["filtercode", "field"]):
        if not usable(d.mjd.values, tpk, 3):
            continue
        fl = 10 ** (-0.4 * d.mag.values)
        rows.append(ratio_series(d.mjd.values, fl, fl * d.magerr.values / 1.0857, f"ZTF_{fc[-1]}_{fld}", tpk))
    n = pd.read_csv(os.path.join(REF, f"neowise_{k}.csv"))
    for b in ("w1", "w2"):
        fl = 10 ** (-0.4 * n[b].values)
        rows.append(ratio_series(n.t.values, fl, fl * n[f"{b}_err"].values / 1.0857, f"NEOWISE_{b.upper()}", tpk))
    return pd.concat(rows, ignore_index=True)


def shape_fit(df, kind):
    """A non-lens brightening with an amplitude per series: 'pv7' (symmetric Pearson VII), 'pv7_asym' (separate rise and
    decline widths) or 'fred' (Norris pulse, fast rise and exponential decay)."""
    names = sorted(df.g.unique())
    gi = df.g.map({s: i for i, s in enumerate(names)}).values
    t, f, e = df.t.values, df.f.values, df.e.values
    t0c = float(t[np.argmax(f)])
    nshape = {"pv7": 3, "pv7_asym": 4, "fred": 3}[kind]

    def model(p):
        q, amp = p[:nshape], np.asarray(p[nshape:])[gi]
        if kind == "fred":
            x = np.maximum(t - q[0], 1e-3)
            prof = np.where(t > q[0], np.exp(2 * np.sqrt(q[1] / q[2]) - q[1] / x - x / q[2]), 0.0)
        else:
            w = q[1] if kind == "pv7" else np.where(t < q[0], q[1], q[2])
            prof = (1 + ((t - q[0]) / w) ** 2) ** (-q[-1])
        return 1 + amp * prof

    if kind == "fred":
        starts = [[t0c - d, a, b] for d in (30, 80, 150) for a in (10, 50, 200) for b in (20, 60, 150)]
        lo, hi = [t0c - 600, 0.5, 2], [t0c + 50, 5000, 2000]
    else:
        ws = [[w] if kind == "pv7" else [w, w] for w in (20, 50, 100, 200)]
        starts = [[t0c, *w, m] for w in ws for m in (0.5, 1, 3)]
        lo = [t0c - 150] + [2] * (nshape - 2) + [0.1]
        hi = [t0c + 150] + [2000] * (nshape - 2) + [50]
    best = None
    amp0 = max(float(f.max()) - 1, 0.1)
    for p0 in starts:
        L, H = np.r_[lo, [0.0] * len(names)], np.r_[hi, [50.0] * len(names)]
        x0 = np.clip(np.r_[p0, [amp0] * len(names)], L + 1e-6, H - 1e-6)
        r = least_squares(lambda p: (model(p) - f) / e, x0, bounds=(L, H))
        if best is None or r.cost < best.cost:
            best = r
    return float(2 * best.cost), best.x[:nshape]


def mjd_date(m):
    return Time(m, format="mjd").iso[:10]


def analyse(k):
    name, ra, dec, tpk = TARGETS[k]
    df = series(k)
    out = {"name": name, "n": int(len(df)), "series": {g: int(n) for g, n in df.g.value_counts().sort_index().items()}}
    for par in (False, True):
        prob = Problem(df.t.values, df.f.values, df.e.values, df.g.values, ra=ra, dec=dec, parallax=par, blend=True)
        p, chi2 = prob.fit()
        dof = len(df) - len(p)
        lab = "parallax" if par else "static"
        res = {"chi2": round(chi2, 1), "dof": dof, "t0": round(float(p[0]), 2), "t0_date": mjd_date(p[0]),
               "tE": round(float(p[1]), 1), "u0": round(float(p[2]), 3),
               "fs": {s: round(float(v), 3) for s, v in zip(prob.names, p[prob.nlens:], strict=True)}}
        if par:
            res["piE"] = [round(float(p[3]), 3), round(float(p[4]), 3)]
            res["t0par"] = prob.t0par
        for i, lab_i, hw in ((0, "t0", 30.0), (1, "tE", 0.6 * float(p[1])), (2, "u0", max(0.5 * abs(float(p[2])), 0.1))):
            lo, hi, opn = profile_range(prob, p, chi2, i, hw)
            res[f"{lab_i}_95"] = [round(lo, 3), round(hi, 3)] + (["open"] if opn else [])
        if par:
            for i, lab_i in ((3, "piE_N"), (4, "piE_E")):
                lo, hi, opn = profile_range(prob, p, chi2, i, 1.0)
                res[f"{lab_i}_95"] = [round(lo, 3), round(hi, 3)] + (["open"] if opn else [])
        res["coverage"] = coverage(df.t.values, p[0], p[1], p[2])
        res["Amax_source"] = round(float(magnification(np.array([abs(p[2])]))[0]), 2)
        resid = (df.f.values - prob.model(p)) / df.e.values
        ev = np.abs(df.t.values - p[0]) < 2 * p[1]
        res["event_resid_rms"] = round(float(np.std(resid[ev])), 2)
        out[lab] = res
        if par:
            df.assign(model=prob.model(p)).to_csv(os.path.join(OUT, f"atlas_fit_{k}.csv"), index=False)
    for kind in ("pv7", "pv7_asym", "fred"):
        c, x = shape_fit(df, kind)
        out[kind] = {"chi2": round(c, 1), "params": [round(float(v), 2) for v in x]}
    # colour: the observed flux ratio near the peak, per series (the blend fractions trade off against u0)
    pk = df[np.abs(df.t - out["parallax"]["t0"]) < 10].groupby("g").f.median().round(3).to_dict()
    out["peak_ratio_within_10d"] = pk
    return out


if __name__ == "__main__":
    keys = sys.argv[1:] or list(TARGETS)
    allres = {k: analyse(k) for k in keys}
    print(json.dumps(allres, indent=1, default=str))
    json.dump(allres, open(os.path.join(OUT, "atlas_fits.json"), "w"), indent=1, default=str)
