"""Copied from claude-referee-atlas10-2026-10-30/fitlib.py and extended for this pass (fs_min floor; reviewed line by line).

Fits in EXCESS-flux space (referee's own code; magnification and the parallax geometry come from oddsky.analysis.lensing).

Every series g is modelled as  d_g(t) = F_g * P(t; theta) [+ c_g],  d = flux - baseline median.  P = A(u) - 1 for a point lens
(F_g = source flux), or a non-lens profile.  F_g (and optional offsets c_g) are linear and solved exactly for every theta
(variable projection), so every model gets the same per-series freedom.  Working in excess flux is needed because several
ATLAS c (and some o) baselines are ~0 or negative in these crowded fields: a flux RATIO to such a baseline is meaningless.
The blend fraction fs_g = F_g / baseline_g is reported only where the baseline is clearly positive.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, atlas_raw, clean, neowise, nightly, to_excess  # noqa: E402

from oddsky.analysis.lensing import magnification, sun_offsets  # noqa: E402


# ----------------------------------------------------------------------------------------------------------- data
def psf_slopes(nt, tpk, base_dt=400):
    """Per band: baseline flux vs PSF major axis, zero point per unit; slope in fractional flux per px."""
    out = {}
    for F, d in nt[np.abs(nt.t - tpk) > base_dt].groupby("F"):
        X, y, w = [], [], []
        cams = sorted(d.cam.unique())
        for _, r in d.iterrows():
            row = [0.0] * len(cams) + [r.maj - 2.4]
            row[cams.index(r.cam)] = 1.0
            X.append(row)
            y.append(r.ujy)
            w.append(1 / max(r.ujy_err, 1.0))
        X, y, w = np.array(X), np.array(y), np.array(w)
        if len(y) < 20:
            continue
        # robust: two passes with 4-sigma clipping
        keep = np.ones(len(y), bool)
        for _ in range(3):
            p, *_ = np.linalg.lstsq(X[keep] * w[keep, None], y[keep] * w[keep], rcond=None)
            res = y - X @ p
            s = 1.4826 * np.median(np.abs(res[keep]))
            keep = np.abs(res) < 4 * s
        zp = np.median(p[:-1])
        out[F] = (p[-1], zp)  # uJy per px (additive), typical zero point
    return out


def build(k, T, tpk, chi_mode="rel", m5min=17.5, base_dt=400, floor="mad", psf_corr=False, maj_max=None, window=None,
          extra=None, use_neowise=True, min_base=8, min_event=3, ev_dt=150, units=None, bands=("c", "o"), clip=4.0):
    """Series in excess flux. extra: list of DataFrames (t, fl, fl_err, g) of other surveys (relative flux)."""
    r = clean(atlas_raw(k), m5min=m5min, chi_mode=chi_mode, maj_max=maj_max)
    if window is not None:
        r = r[(r.mjd > window[0]) & (r.mjd < window[1])]
    if units is not None:
        r = r[r.cam.isin(units)]
    nt = nightly(r, clip=clip)
    if psf_corr:
        sl = psf_slopes(nt, tpk, base_dt)
        for F, (s, _) in sl.items():
            m = nt.F == F
            nt.loc[m, "ujy"] = nt.loc[m, "ujy"] - s * (nt.loc[m, "maj"] - 2.4)
    parts, info = [], {}
    for (F, cam), d in nt.groupby(["F", "cam"]):
        if F not in bands:
            continue
        base = (np.abs(d.t - tpk) > base_dt).values
        nev = int((np.abs(d.t - tpk) < ev_dt).sum())
        if base.sum() < min_base or nev < min_event:
            continue
        s = to_excess(d.t.values, d.ujy.values, d.ujy_err.values, f"ATLAS_{F}_{cam}", base, floor=floor)
        rob = 1.4826 * np.median(np.abs(s.d[base] - np.median(s.d[base])))
        info[f"ATLAS_{F}_{cam}"] = dict(base=float(s.base.iloc[0]), rob=float(rob), nev=nev, unit="uJy")
        parts.append(s.drop(columns="base"))
    if use_neowise:
        n = neowise(k, T)
        for b, d in n.groupby("band"):
            base = (np.abs(d.t - tpk) > base_dt).values
            s = to_excess(d.t.values, d.fl.values / np.median(d.fl.values[base]), d.fl_err.values / np.median(d.fl.values[base]),
                          f"NEOWISE_{b}", base, floor=floor)
            info[f"NEOWISE_{b}"] = dict(base=1.0, rob=float(1.4826 * np.median(np.abs(s.d[base]))),
                                        nev=int((np.abs(d.t - tpk) < ev_dt).sum()), unit="rel")
            parts.append(s.drop(columns="base"))
    for ex in extra or []:
        for g, d in ex.groupby("g"):
            base = (np.abs(d.t - tpk) > base_dt).values
            if base.sum() < 3:
                continue
            med = np.median(d.fl.values[base])
            s = to_excess(d.t.values, d.fl.values / med, d.fl_err.values / med, g, base, floor=floor)
            info[g] = dict(base=1.0, rob=float(1.4826 * np.median(np.abs(s.d[base]))), nev=int((np.abs(d.t - tpk) < ev_dt).sum()),
                           unit="rel")
            parts.append(s.drop(columns="base"))
    return pd.concat(parts, ignore_index=True), info


def gaia_alert_series(name):
    p = os.path.join(DATA, f"gsa_{name}.csv")
    g = pd.read_csv(p, skiprows=1)
    g.columns = ["date", "jd", "mag"]
    g = g[pd.to_numeric(g.mag, errors="coerce").notna()].copy()
    g["mag"] = g.mag.astype(float)
    g["t"] = g.jd.astype(float) - 2400000.5
    g["night"] = np.floor(g.t)
    rows = []
    for _, d in g.groupby("night"):
        fl = 10 ** (-0.4 * d.mag.values)
        rows.append((d.t.mean(), fl.mean(), len(d)))
    out = pd.DataFrame(rows, columns=["t", "fl", "n"])
    # per-transit noise from the out-of-event scatter of single transits ~0.02-0.03 mag; per night / sqrt(n)
    out["fl_err"] = out.fl * 0.025 / np.sqrt(out.n)
    out["g"] = "GAIA_G"
    return out


def ztf_series(path, flags=(0,)):
    z = pd.read_csv(path)
    z = z[z.catflags.isin(flags) & z.mag.notna()].copy()
    z["night"] = np.floor(z.mjd)
    rows = []
    for (fc, fld, n), d in z.groupby(["filtercode", "field", "night"]):
        fl = 10 ** (-0.4 * d.mag.values)
        e = fl * d.magerr.values / 1.0857
        w = 1 / e**2
        rows.append((d.mjd.mean(), np.sum(w * fl) / np.sum(w), 1 / np.sqrt(np.sum(w)), f"ZTF_{fc[-1]}_{fld}"))
    return pd.DataFrame(rows, columns=["t", "fl", "fl_err", "g"])


# ----------------------------------------------------------------------------------------------------------- models
class Fitter:
    def __init__(self, df, ra=None, dec=None, t0par=None, offsets=False, fs_cap=None, fs_min=None):
        """fs_cap: dict series -> max F (e.g. the baseline flux: no negative blend). offsets: free constant per series."""
        self.t, self.d, self.e = df.t.values.astype(float), df.d.values.astype(float), df.e.values.astype(float)
        self.names = sorted(df.g.unique())
        self.gi = df.g.map({s: i for i, s in enumerate(self.names)}).values
        self.idx = [np.where(self.gi == i)[0] for i in range(len(self.names))]
        self.offsets, self.fs_cap, self.fs_min = offsets, fs_cap or {}, fs_min or {}
        self.ra, self.dec, self.t0par = ra, dec, t0par
        self._par = None

    def par_offsets(self):
        if self._par is None:
            self._par = sun_offsets(self.t, self.ra, self.dec, self.t0par)
        return self._par

    def linear(self, P):
        """Best amplitudes (and offsets) per series for profile P; returns model and coefficients."""
        m = np.zeros_like(self.d)
        coef = []
        for i, ix in enumerate(self.idx):
            w = 1 / self.e[ix] ** 2
            p, y = P[ix], self.d[ix]
            if self.offsets:
                A = np.vstack([p, np.ones_like(p)]).T
                c = np.linalg.solve(A.T @ (A * w[:, None]) + 1e-12 * np.eye(2), A.T @ (w * y))
            else:
                c = np.array([np.sum(w * p * y) / max(np.sum(w * p * p), 1e-30), 0.0])
            cap = self.fs_cap.get(self.names[i])
            if cap is not None and c[0] > cap:  # refit offset with amplitude pinned at the cap
                c[0] = cap
                if self.offsets:
                    c[1] = np.sum(w * (y - cap * p)) / np.sum(w)
            c[0] = max(c[0], 0.0) if cap is not None else c[0]
            lo_ = self.fs_min.get(self.names[i])
            if lo_ is not None and c[0] < lo_:  # amplitude floor (e.g. Gaia-based minimum source flux)
                c[0] = lo_
                if self.offsets:
                    c[1] = np.sum(w * (y - lo_ * p)) / np.sum(w)
            m[ix] = c[0] * p + c[1]
            coef.append(c)
        return m, coef

    # profiles
    def lens(self, q, parallax=False):
        t0, te, u0 = q[0], q[1], q[2]
        tau = (self.t - t0) / te
        beta = np.full_like(self.t, u0)
        if parallax:
            dn, de = self.par_offsets()
            tau = tau + q[3] * dn + q[4] * de
            beta = beta + (-q[3] * de + q[4] * dn)
        return magnification(np.hypot(tau, beta)) - 1

    def lens_asym(self, q):
        te = np.where(self.t < q[0], q[1], q[2])
        return magnification(np.hypot((self.t - q[0]) / te, q[3])) - 1

    def pv7(self, q):
        return (1 + ((self.t - q[0]) / q[1]) ** 2) ** (-q[2])

    def pv7_asym(self, q):
        w = np.where(self.t < q[0], q[1], q[2])
        return (1 + ((self.t - q[0]) / w) ** 2) ** (-q[3])

    def fred(self, q):  # Norris pulse, peak normalised to 1
        ts, t1, t2 = q
        x = np.maximum(self.t - ts, 1e-3)
        return np.where(self.t > ts, np.exp(2 * np.sqrt(t1 / t2) - t1 / x - x / t2), 0.0)

    def nova(self, q):  # exponential rise (tau_r) to a cusp at t0, power-law decline (1 + dt/tau_d)^-alpha
        t0, tr, td, al = q
        dt = self.t - t0
        return np.where(dt < 0, np.exp(np.clip(dt / tr, -50, 0)), (1 + np.maximum(dt, 0) / td) ** (-al))

    def resid(self, P):
        m, _ = self.linear(P)
        return (m - self.d) / self.e

    def fit(self, kind, t0c, fixed=None):
        fixed = fixed or {}
        spec = {
            "static": (lambda q: self.lens(q), [[t0c, te, u0] for te in (10, 30, 80, 200) for u0 in (0.01, 0.1, 0.3, 0.8)],
                       [t0c - 150, 1, 1e-4], [t0c + 150, 3000, 3]),
            "parallax": (lambda q: self.lens(q, True),
                         [[t0c, te, s * u0, pn, pe] for te in (30, 100, 250) for u0 in (0.03, 0.15, 0.5) for s in (1, -1)
                          for pn, pe in ((0, 0), (0.3, 0.1), (-0.3, 0.1), (0.1, -0.3))],
                         [t0c - 150, 1, -3, -5, -5], [t0c + 150, 3000, 3, 5, 5]),
            "lens_asym": (self.lens_asym, [[t0c, te, te, u0] for te in (20, 80, 200) for u0 in (0.01, 0.1, 0.4)],
                          [t0c - 150, 1, 1, 1e-4], [t0c + 150, 3000, 3000, 3]),
            "pv7": (self.pv7, [[t0c, w, m] for w in (2, 10, 40, 120) for m in (0.5, 1, 3)],
                    [t0c - 150, 0.2, 0.05], [t0c + 150, 3000, 50]),
            "pv7_asym": (self.pv7_asym, [[t0c, w, w, m] for w in (2, 10, 40, 120) for m in (0.5, 1, 3)],
                         [t0c - 150, 0.2, 0.2, 0.05], [t0c + 150, 3000, 3000, 50]),
            "fred": (self.fred, [[t0c - d, a, b] for d in (5, 30, 100) for a in (1, 20, 200) for b in (5, 30, 150)],
                     [t0c - 600, 0.01, 0.5], [t0c + 50, 5000, 3000]),
            "nova": (self.nova, [[t0c, tr, td, al] for tr in (1, 10, 40) for td in (1, 10, 50) for al in (1, 2, 4)],
                     [t0c - 150, 0.05, 0.05, 0.05], [t0c + 150, 1000, 3000, 20]),
        }
        prof, starts, lo, hi = spec[kind]
        lo, hi = np.array(lo, float), np.array(hi, float)
        free = [i for i in range(len(lo)) if i not in fixed]
        best = None
        for p0 in starts:
            p0 = np.array(p0, float)

            def full(q):
                p = p0.copy()
                p[free] = q
                for i, v in fixed.items():
                    p[i] = v
                return p
            q0 = np.clip(p0[free], lo[free] + 1e-6, hi[free] - 1e-6)
            try:
                r = least_squares(lambda q: self.resid(prof(full(q))), q0, bounds=(lo[free], hi[free]), x_scale="jac",
                                  max_nfev=4000)
            except Exception:  # noqa: BLE001
                continue
            if best is None or r.cost < best[1].cost:
                best = (full(r.x), r)
        p = best[0]
        m, coef = self.linear(prof(p))
        chi2 = float(np.sum(((m - self.d) / self.e) ** 2))
        npar = len(lo) - len(fixed) + len(self.names) * (2 if self.offsets else 1)
        return dict(kind=kind, p=[float(x) for x in p], chi2=chi2, npar=npar, n=len(self.d),
                    amp={n: float(c[0]) for n, c in zip(self.names, coef, strict=True)},
                    off={n: float(c[1]) for n, c in zip(self.names, coef, strict=True)}, model=m)


def summary(res, info):
    p = res["p"]
    s = f"{res['kind']:9s} chi2 {res['chi2']:9.1f} (n {res['n']}, k {res['npar']}, BIC {res['chi2'] + res['npar'] * np.log(res['n']):9.1f})"
    if res["kind"] in ("static", "parallax"):
        s += f"  t0 {p[0]:.2f} tE {p[1]:.1f} u0 {p[2]:+.4f} Amax {float(magnification(np.array([abs(p[2])]))[0]):.1f}"
        if res["kind"] == "parallax":
            s += f" piEN {p[3]:+.3f} piEE {p[4]:+.3f}"
        fs = []
        for g, F in res["amp"].items():
            b = info.get(g, {}).get("base", np.nan)
            rob = info.get(g, {}).get("rob", np.nan)
            if info.get(g, {}).get("unit") == "uJy":
                fs.append(f"{g}:F={F:.0f}uJy" + (f"(fs={F / b:.2f})" if b > 5 * max(rob, 1) / np.sqrt(20) and b > 0 else
                                                 f"(base {b:.0f})"))
            else:
                fs.append(f"{g}:fs={F:.2f}")
        s += "\n             " + " ".join(fs)
    elif res["kind"] == "lens_asym":
        s += f"  t0 {p[0]:.2f} tE_rise {p[1]:.1f} tE_fall {p[2]:.1f} ratio {p[1] / p[2]:.2f} u0 {p[3]:.4f}"
    else:
        s += "  shape " + " ".join(f"{x:.3g}" for x in p)
    return s
