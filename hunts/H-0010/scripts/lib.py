"""Shared helpers for H-0010: load the 67 sources, clean Gaia DR3 epoch photometry, build flux-ratio series,
and fit non-lens shapes (copied from scripts/hunt_h0008_atlas_fit.py shape_fit so the comparison is identical)."""
import os

import numpy as np
import pandas as pd
from astropy.time import Time
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(ROOT, "work")
FIG = os.path.join(ROOT, "figures")
EP = os.path.join(DATA, "epoch")
NW = os.path.join(DATA, "neowise")
DR3_START, DR3_END = 56863.0, 57901.0  # 2014-07-25 .. 2017-05-28
CASES = {"5959812622743175552": "OS-0026", "4143495279954502016": "OS-0027", "4145977633638478336": "OS-0029"}


def mjd2date(m):
    return Time(float(m), format="mjd").iso[:10]


def targets() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA, "unpub.csv"), dtype={"source_id": str})


def short_name(ra, dec):
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    c = SkyCoord(ra * u.deg, dec * u.deg)
    s = c.to_string("hmsdms", sep="", precision=2, pad=True).replace(" ", "")
    h, d = s.split("+") if "+" in s else s.split("-")
    sign = "+" if "+" in s else "-"
    return "J" + h[:9] + sign + d[:8]


def epoch(sid: str, clip_bp_rp: bool = True) -> tuple[pd.DataFrame, dict]:
    """Gaia DR3 epoch photometry for one source. Drops rejected_by_photometry and non-finite magnitudes; keeps
    rejected_by_variability (flag column says so). If clip_bp_rp, BP/RP points that depart from the same transit's G
    by more than max(1 mag, 5 sigma) relative to each band's median are dropped as window contamination: G is a
    PSF fit in a ~0.7" window, BP/RP integrate a 3.5" x 2.1" window that catches neighbours at some scan angles."""
    d = pd.read_csv(os.path.join(EP, f"{sid}.csv"), dtype={"camera": str})
    info = {"n_raw": len(d), "n_rej_phot": int((d.flag == "rejected_by_photometry").sum())}
    d = d[(d.flag != "rejected_by_photometry") & np.isfinite(d.mag)].copy()
    info["n_rej_var"] = int((d.flag == "rejected_by_variability").sum())
    info["n_rej_var_G"] = int(((d.flag == "rejected_by_variability") & (d.band == "G")).sum())
    med = d.groupby("band").mag.median()
    d["dm"] = d.mag - d.band.map(med)
    info["n_clip_bprp"] = 0
    if clip_bp_rp:
        g = d[d.band == "G"].set_index("camera").dm
        drop = []
        for i, r in d[d.band != "G"].iterrows():
            if r.camera in g.index:
                gd = g.loc[r.camera]
                gd = float(gd.iloc[0]) if hasattr(gd, "iloc") else float(gd)
                if abs(r.dm - gd) > max(1.0, 5 * r.err):
                    drop.append(i)
            elif abs(r.dm) > 1.0:
                drop.append(i)
        info["n_clip_bprp"] = len(drop)
        d = d.drop(index=drop)
    return d.sort_values("t_mjd").reset_index(drop=True), info


def baseline(t, m, e, nit: int = 5):
    """Iterative quiet baseline: median and robust scatter of transits not significantly brighter (3 sigma)."""
    keep = np.ones(len(m), bool)
    base, sig = np.median(m), 1.4826 * np.median(np.abs(m - np.median(m)))
    for _ in range(nit):
        sig = max(1.4826 * np.median(np.abs(m[keep] - base)), np.median(e[keep]), 0.005)
        keep = m > base - 3 * sig
        base = np.median(m[keep])
    return float(base), float(sig), keep


def shape_fit(df, kind):
    """A non-lens brightening with an amplitude per series: 'pv7' (symmetric Pearson VII), 'pv7_asym' (separate rise and
    decline widths) or 'fred' (Norris pulse, fast rise and exponential decay). From scripts/hunt_h0008_atlas_fit.py."""
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
    return float(2 * best.cost), best.x[:nshape], best.x[nshape:]
