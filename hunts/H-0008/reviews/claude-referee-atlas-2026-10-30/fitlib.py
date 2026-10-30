"""Fit inputs under switchable reduction choices, and non-lens comparison shapes (referee's own code; the point-lens model is
the Oddsky tool oddsky.analysis.lensing.Problem)."""
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import TARGETS, atlas_raw, clean, neowise, nightly, to_ratio, ztf  # noqa: E402

PSF_SLOPE = {"J180624": {"c": -0.25, "o": -0.134}, "J183040": {"c": -0.076, "o": -0.019}}  # mag per px, from r2


def build(k, window=(58480, 61500), chi="rel", m5min=17.5, base_dt=400, floor="mad", per_unit=True, psf_corr=False,
          ztf_flags=(0,), use_ztf=True, use_neowise=True, min_base=8, units=None, bands=("c", "o"), clip=4.0):
    T = TARGETS[k]
    tpk = T["tpk"]
    r = clean(atlas_raw(k), m5min=m5min, chi=chi)
    r = r[(r.mjd > window[0]) & (r.mjd < window[1])]
    if units is not None:
        r = r[r.cam.isin(units)]
    nt = nightly(r, clip=clip)
    if psf_corr:
        s = nt.F.map(PSF_SLOPE[k]).values
        corr = 10 ** (-0.4 * s * (nt.maj.values - 2.4))  # slope<0: wider PSF -> fainter; divide that out
        nt["ujy"] = nt.ujy / corr
        nt["ujy_err"] = nt.ujy_err / corr
    parts = []
    if per_unit:
        groups = nt.groupby(["F", "cam"])
    else:
        # normalise each unit to its own baseline first, then merge per band
        tmp = []
        for (F, cam), d in nt.groupby(["F", "cam"]):
            base = np.abs(d.t - tpk) > base_dt
            if base.sum() < min_base:
                continue
            med = np.median(d.ujy[base])
            tmp.append(d.assign(ujy=d.ujy / med, ujy_err=d.ujy_err / med, cam="all"))
        nt = pd.concat(tmp)
        groups = nt.groupby(["F", "cam"])
    for (F, cam), d in groups:
        if F not in bands:
            continue
        base = (np.abs(d.t - tpk) > base_dt).values
        if base.sum() < min_base:
            continue
        s = to_ratio(d.t, d.ujy, d.ujy_err, f"ATLAS_{F}_{cam}", base, floor=floor)
        parts.append(s[(s.f > 0.3) & (s.f < 20)])
    if use_ztf:
        z = ztf(k, flags=ztf_flags)
        z = z[(z.t > window[0]) & (z.t < window[1])]
        for (b, fld), d in z.groupby(["band", "field"]):
            base = (np.abs(d.t - tpk) > base_dt).values
            ev = (np.abs(d.t - tpk) < 200).sum()
            if base.sum() < 3 or ev < 1:
                continue
            parts.append(to_ratio(d.t, d.fl, d.fl_err, f"ZTF_{b}_{fld}", base, floor=floor))
    if use_neowise:
        n = neowise(k)
        for b, d in n.groupby("band"):
            base = (np.abs(d.t - tpk) > base_dt).values
            parts.append(to_ratio(d.t, d.fl, d.fl_err, f"NEOWISE_{b}", base, floor=floor))
    return pd.concat(parts, ignore_index=True)


# ------------------------------------------------------------------ comparison shapes, same per-series freedom as the lens
def _fit(df, model, p0s, lo, hi):
    names = sorted(df.g.unique())
    gi = df.g.map({s: i for i, s in enumerate(names)}).values
    t, f, e = df.t.values, df.f.values, df.e.values
    best = None
    for p0 in p0s:
        p0 = np.r_[p0, [1.0] * len(names)]
        L = np.r_[lo, [0.0] * len(names)]
        H = np.r_[hi, [50.0] * len(names)]
        r = least_squares(lambda p: (model(p, t, gi) - f) / e, np.clip(p0, L + 1e-6, H - 1e-6), bounds=(L, H))
        if best is None or r.cost < best.cost:
            best = r
    return float(2 * best.cost), best.x


def shape_fits(df, t0c):
    """Each returns chi2 and the shape parameters. amplitude per series is free, baseline fixed at 1 (as for the lens)."""
    out = {}

    def gauss(p, t, gi):
        w = np.where(t < p[0], p[1], p[2])
        return 1 + p[3:][gi] * np.exp(-0.5 * ((t - p[0]) / w) ** 2)

    def pv7(p, t, gi):  # Pearson VII / generalised Lorentzian, separate widths, free power m
        w = np.where(t < p[0], p[1], p[2])
        return 1 + p[4:][gi] * (1 + ((t - p[0]) / w) ** 2) ** (-p[3])

    def fred(p, t, gi):  # Norris pulse: exp(-tau1/(t-ts) - (t-ts)/tau2), peak normalised to 1
        ts, t1, t2 = p[0], p[1], p[2]
        x = np.maximum(t - ts, 1e-3)
        prof = np.where(t > ts, np.exp(2 * np.sqrt(t1 / t2) - t1 / x - x / t2), 0.0)
        return 1 + p[3:][gi] * prof

    def lens_asym(p, t, gi):  # point lens shape with separate tE on the rise and the decline (u0 shared), fs per series
        te = np.where(t < p[0], p[1], p[2])
        u = np.hypot((t - p[0]) / te, p[3])
        a = (u**2 + 2) / (u * np.sqrt(u**2 + 4))
        fs = p[4:][gi]
        return fs * a + 1 - fs

    ws = (20, 50, 100, 200)
    c, x = _fit(df, lambda p, t, gi: gauss(np.r_[p[0], p[1], p[1], p[2:]], t, gi),
                [[t0c, w] for w in ws], [t0c - 150, 2], [t0c + 150, 800])
    out["gaussian"] = (c, x[:2])
    out["gaussian_asym"] = _fit(df, gauss, [[t0c, w, w] for w in ws], [t0c - 150, 2, 2], [t0c + 150, 800, 800])
    c, x = _fit(df, lambda p, t, gi: pv7(np.r_[p[0], p[1], p[1], p[2:]], t, gi),
                [[t0c, w, m] for w in ws for m in (0.5, 1, 3)], [t0c - 150, 2, 0.1], [t0c + 150, 2000, 50])
    out["pv7_sym"] = (c, x[:3])
    out["pv7_asym"] = _fit(df, pv7, [[t0c, w, w, m] for w in ws for m in (0.5, 1, 3)], [t0c - 150, 2, 2, 0.1], [t0c + 150, 2000, 2000, 50])
    out["fred"] = _fit(df, fred, [[t0c - d, a, b] for d in (30, 80, 150) for a in (10, 50, 200) for b in (20, 60, 150)],
                       [t0c - 600, 0.5, 2], [t0c + 50, 5000, 2000])

    def lens_asym_fit():
        names = sorted(df.g.unique())
        gi = df.g.map({s: i for i, s in enumerate(names)}).values
        t, f, e = df.t.values, df.f.values, df.e.values
        best = None
        for te in (40, 100, 200):
            for u0 in (0.1, 0.3, 0.6):
                p0 = np.r_[t0c, te, te, u0, [0.7] * len(names)]
                L = np.r_[t0c - 150, 1, 1, 1e-3, [0.02] * len(names)]
                H = np.r_[t0c + 150, 2000, 2000, 3, [1.5] * len(names)]
                r = least_squares(lambda p: (lens_asym(p, t, gi) - f) / e, p0, bounds=(L, H))
                if best is None or r.cost < best.cost:
                    best = r
        return float(2 * best.cost), best.x
    out["lens_asym"] = lens_asym_fit()
    return {k: (round(v[0], 1), [round(float(q), 3) for q in v[1][:5]]) for k, v in out.items()}
