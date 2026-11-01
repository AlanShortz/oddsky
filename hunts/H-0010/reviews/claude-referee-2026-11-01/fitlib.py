"""Referee's fitting code (own; only magnification and the parallax geometry come from oddsky.analysis.lensing).
Data: Gaia DR3 per-transit G/BP/RP flux ratios (flux / band baseline). Baseline per band = median of transits outside the event
window; error = formal flux error (1/flux_over_error) in quadrature with the band's excess baseline scatter. No BP/RP point is
removed for disagreeing with G (the investigators' lib.epoch() did that; it biases an achromaticity test). Points with
rejected_by_photometry are dropped; NaN fluxes dropped; BP/RP points with |dm| > 3 mag from baseline are dropped as gross
window-contamination outliers (listed).
Models (flux ratio per band b):
  lens:   F_b = fs_b * A(u(t)) + 1 - fs_b; static or with annual parallax; fs_b in (0.02, fs_max]
  shapes: F_b = 1 + amp_b * S(t): Gaussian, symmetric Pearson VII, asymmetric Pearson VII, FRED (Norris), asymmetric Gaussian
Also NEOWISE visit ratios can be added as extra series ('W1','W2')."""
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from oddsky.analysis.lensing import magnification, sun_offsets

GT0 = 55197.0


def load_gaia(path, win, band_list=("G", "BP", "RP")):
    r = pd.read_csv(path)
    r = r[~r.rejected_by_photometry.astype(str).str.lower().eq("true")]
    rows, dropped, base = [], [], {}
    for b, p, tc in (("G", "g_transit", "g_transit_time"), ("BP", "bp", "bp_obs_time"), ("RP", "rp", "rp_obs_time")):
        if b not in band_list:
            continue
        x = pd.DataFrame(dict(t=r[tc] + GT0, flux=r[f"{p}_flux"], foe=r[f"{p}_flux_over_error"], tid=r.transit_id,
                              vrej=r[f"variability_flag_{b.lower()}_reject"].astype(str).str.lower().eq("true"), g=b))
        x = x[np.isfinite(x.flux) & (x.flux > 0) & np.isfinite(x.t)]
        out = (x.t < win[0]) | (x.t > win[1])
        fb = float(np.median(x.flux[out]))
        f = x.flux / fb
        dm = -2.5 * np.log10(f)
        gross = np.abs(dm) > 3
        dropped += [(b, round(t, 2), round(d, 2)) for t, d in zip(x.t[gross], dm[gross])]
        x = x[~gross]
        f = f[~gross]
        e_form = 1 / x.foe.clip(lower=1)
        o2 = out[~gross]
        sc = 1.4826 * np.median(np.abs(f[o2] - np.median(f[o2])))
        floor = np.sqrt(max(sc ** 2 - np.median(e_form[o2]) ** 2, 0.0))
        x = x.assign(f=f.values, e=np.sqrt(e_form ** 2 + floor ** 2).values * f.values)
        base[b] = dict(n=int(len(x)), n_base=int(o2.sum()), scatter=round(float(sc), 4), floor=round(float(floor), 4),
                       med_formal=round(float(np.median(e_form[o2])), 4), mag=round(float(-2.5 * np.log10(fb) + 25.6874), 3))
        rows.append(x)
    return pd.concat(rows, ignore_index=True), base, dropped


class Lens:
    def __init__(self, df, ra, dec, parallax=False, fs_max=1.0, t0par=None, fs_fixed=None):
        self.t, self.f, self.e = df.t.values, df.f.values, df.e.values
        self.names = sorted(df.g.unique())
        self.gi = np.array([self.names.index(g) for g in df.g])
        self.par = parallax
        self.fs_max = fs_max
        self.fs_fixed = fs_fixed or {}
        self.t0par = t0par if t0par is not None else float(self.t[np.argmax(self.f)])
        if parallax:
            self.dn, self.de = sun_offsets(self.t, ra, dec, self.t0par)
        self.free_fs = [n for n in self.names if n not in self.fs_fixed]
        self.nl = 5 if parallax else 3

    def model(self, p, t=None, dn=None, de=None, which=None):
        t = self.t if t is None else t
        tau = (t - p[0]) / p[1]
        beta = np.full_like(t, p[2], dtype=float)
        if self.par:
            dn = self.dn if dn is None else dn
            de = self.de if de is None else de
            tau = tau + p[3] * dn + p[4] * de
            beta = beta + (-p[3] * de + p[4] * dn)
        a = magnification(np.hypot(tau, beta))
        fsd = dict(zip(self.free_fs, p[self.nl:]))
        fsd.update(self.fs_fixed)
        if which is not None:
            return fsd[which] * a + 1 - fsd[which]
        fs = np.array([fsd[n] for n in self.names])[self.gi]
        return fs * a + 1 - fs

    def fit(self, t0c, t0range=300, starts_te=(10, 25, 60, 150, 400), fixed=None):
        fixed = fixed or {}
        lo = [t0c - t0range, 1.0, -3 if self.par else 1e-4] + ([-5, -5] if self.par else []) + [0.02] * len(self.free_fs)
        hi = [t0c + t0range, 3000.0, 3.0] + ([5, 5] if self.par else []) + [self.fs_max] * len(self.free_fs)
        lo, hi = np.array(lo, float), np.array(hi, float)
        free = [i for i in range(len(lo)) if i not in fixed]
        best = None
        amax = max(self.f.max(), 1.05)
        import os as _os
        fast = _os.environ.get("REFEREE_FAST") == "1"  # r3d: coarser start grid (48 starts) for the parallax model
        if fast:
            starts_te = (15, 40, 100, 300)
        for te in starts_te:
            for u0 in ((0.1, 0.5) if fast else (0.05, 0.2, 0.5, 1.0)):
                for s in ((1, -1) if self.par else (1,)):
                    for pi in (((0, 0), (0.3, 0.3), (-0.3, 0.3), (0.5, -0.5)) if self.par else ((),)):
                        for dt in ((0,) if fast else (0, -20, 20)):
                            p0 = np.array([t0c + dt, te, s * u0, *pi] + [min(0.9, self.fs_max)] * len(self.free_fs), float)
                            for i, v in fixed.items():
                                p0[i] = v

                            def full(q):
                                p = p0.copy(); p[free] = q; return p
                            q0 = np.clip(p0[free], lo[free] + 1e-6, hi[free] - 1e-6)
                            r = least_squares(lambda q: (self.model(full(q)) - self.f) / self.e, q0, bounds=(lo[free], hi[free]))
                            if best is None or r.cost < best[1]:
                                best = (full(r.x), r.cost)
        p = best[0]
        return p, float(2 * best[1])


def shape(df, kind, t0c):
    names = sorted(df.g.unique())
    gi = np.array([names.index(g) for g in df.g])
    t, f, e = df.t.values, df.f.values, df.e.values
    ns = {"gauss": 2, "pv7": 3, "pv7_asym": 4, "fred": 3, "gauss_asym": 3}[kind]

    def prof(q):
        if kind == "gauss":
            return np.exp(-0.5 * ((t - q[0]) / q[1]) ** 2)
        if kind == "gauss_asym":
            w = np.where(t < q[0], q[1], q[2])
            return np.exp(-0.5 * ((t - q[0]) / w) ** 2)
        if kind == "fred":
            x = np.maximum(t - q[0], 1e-3)
            return np.where(t > q[0], np.exp(2 * np.sqrt(q[1] / q[2]) - q[1] / x - x / q[2]), 0.0)
        w = q[1] if kind == "pv7" else np.where(t < q[0], q[1], q[2])
        return (1 + ((t - q[0]) / w) ** 2) ** (-q[-1])

    def model(p):
        return 1 + np.asarray(p[ns:])[gi] * prof(p[:ns])

    if kind == "fred":
        starts = [[t0c - d, a, b] for d in (10, 30, 80, 150) for a in (10, 50, 200) for b in (10, 30, 60, 150)]
        lo, hi = [t0c - 600, 0.5, 2], [t0c + 100, 5000, 2000]
    elif kind in ("gauss", "gauss_asym"):
        starts = [[t0c + d] + [w] * (ns - 1) for d in (-20, 0, 20) for w in (5, 15, 40, 100)]
        lo, hi = [t0c - 300] + [1] * (ns - 1), [t0c + 300] + [2000] * (ns - 1)
    else:
        ws = [[w] if kind == "pv7" else [w, w] for w in (5, 15, 40, 100, 250)]
        starts = [[t0c + d, *w, m] for d in (-20, 0, 20) for w in ws for m in (0.5, 1, 3)]
        lo = [t0c - 300] + [1] * (ns - 2) + [0.1]
        hi = [t0c + 300] + [3000] * (ns - 2) + [50]
    best = None
    amp0 = max(float(f.max()) - 1, 0.1)
    L, H = np.r_[lo, [0.0] * len(names)], np.r_[hi, [200.0] * len(names)]
    for p0 in starts:
        x0 = np.clip(np.r_[p0, [amp0] * len(names)], L + 1e-6, H - 1e-6)
        r = least_squares(lambda p: (model(p) - f) / e, x0, bounds=(L, H))
        if best is None or r.cost < best.cost:
            best = r
    return float(2 * best.cost), best.x, (lambda tt, p=best.x: None)


def bic(chi2, k, n):
    return chi2 + k * np.log(n)
