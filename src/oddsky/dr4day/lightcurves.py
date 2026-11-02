"""What one Gaia epoch light curve says: the blind per-source analysis of the DR4-day searches.

The method is H-0010's (hunts/H-0010/scripts/s3_lightcurves.py, refereed 2026-11-01), made release-agnostic:
  * clean: drop rejected_by_photometry and non-finite values; drop BP/RP points that depart from the same transit's G by more
    than max(1 mag, 5 sigma), window contamination from a neighbour (BP/RP integrate 3.5" x 2.1", G a ~0.7" PSF);
  * per-band iterative quiet baseline and robust scatter; flux ratios with an error floor from the excess scatter;
  * brightening and fading episodes in G (>= 2 transits beyond max(4 sigma, 0.08 mag), split by a quiet transit and > 30 d);
  * colour at significantly brightened transits: Delta(BP-RP) and k = (f_BP - 1)/(f_RP - 1), 1 for a lens on an unblended star;
  * point-lens fits (oddsky.analysis.lensing.Problem, blend per band; static, and with annual parallax on request) against
    non-lens Pearson VII and FRED shapes, compared by BIC;
  * at a NEOWISE event time, the sealed ensemble rule (hunts/H-0009/predictions/dr4_ensemble_grade.py `grade_series`),
    imported unchanged, so the discovery search and the forecast judge an event the same way.

Labels are computed descriptions for triage, never claims. Anything ranked high goes to a referee before it is called new.
"""

from __future__ import annotations

import importlib.util
import warnings
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from ..analysis.lensing import Problem, magnification

ENSEMBLE_GRADER = Path("hunts/H-0009/predictions/dr4_ensemble_grade.py")
MIN_G = 10


@lru_cache(maxsize=1)
def ensemble_rule():
    """The sealed ensemble grader as a module (read-only use of its `grade_series`, `judge` and `RULE`)."""
    spec = importlib.util.spec_from_file_location("dr4_ensemble_grade", ENSEMBLE_GRADER.resolve())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean(df: pd.DataFrame, clip_bp_rp: bool = True) -> pd.DataFrame:
    d = df[(df.flag.astype(str) != "rejected_by_photometry") & np.isfinite(df.mag.astype(float))
           & np.isfinite(df.t_mjd.astype(float))].copy()
    d["camera"] = d["camera"].astype(str) if "camera" in d else np.arange(len(d)).astype(str)
    if clip_bp_rp and len(d):
        med = d.groupby("band").mag.median()
        d["dm0"] = d.mag - d.band.map(med)
        g = d[d.band == "G"].drop_duplicates("camera").set_index("camera").dm0
        x = d[d.band != "G"]
        gd = x.camera.map(g)
        tol = np.maximum(1.0, 5 * x.err.astype(float))
        bad = np.where(gd.notna(), (x.dm0 - gd).abs() > tol, x.dm0.abs() > 1.0)
        d = d.drop(index=x.index[bad]).drop(columns="dm0")
    return d.sort_values("t_mjd").reset_index(drop=True)


def baseline(m, e, nit: int = 5):
    """Iterative quiet baseline: median and robust scatter of transits not significantly brighter (3 sigma)."""
    m, e = np.asarray(m, float), np.asarray(e, float)
    keep = np.ones(len(m), bool)
    base = float(np.median(m))
    sig = 0.005
    for _ in range(nit):
        sig = max(1.4826 * float(np.median(np.abs(m[keep] - base))), float(np.median(e[keep])), 0.005)
        keep = m > base - 3 * sig
        if not keep.any():
            keep = np.ones(len(m), bool)
        base = float(np.median(m[keep]))
    return base, sig, keep


def ratio_series(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out, base = [], {}
    for b in ("G", "BP", "RP"):
        x = d[d.band == b]
        if len(x) < 5:
            continue
        m, e = x.mag.to_numpy(float), x.err.to_numpy(float)
        bl, sig, keep = baseline(m, e)
        floor = float(np.sqrt(max(sig**2 - np.median(e[keep]) ** 2, 0.0)))
        f = 10 ** (-0.4 * (m - bl))
        base[b] = {"mag": round(bl, 4), "sig": round(sig, 4), "floor": round(floor, 4), "n": int(len(x))}
        out.append(pd.DataFrame(dict(t=x.t_mjd.to_numpy(float), f=f, e=f * 0.921 * np.sqrt(e**2 + floor**2), g=b, dm=m - bl,
                                     err=e, sig=sig, camera=x.camera.to_numpy())))
    if not out:
        return pd.DataFrame(columns=["t", "f", "e", "g", "dm", "err", "sig", "camera"]), base
    return pd.concat(out, ignore_index=True), base


def episodes(g: pd.DataFrame, sign: int = -1) -> list[dict]:
    """Clusters of >= 2 transits brighter (sign -1) or fainter (+1) than max(4 sigma, 0.08 mag)."""
    if g.empty:
        return []
    sig = float(g.sig.iloc[0])
    thr = max(4 * sig, 0.08)
    t, dm = g.t.to_numpy(float), g.dm.to_numpy(float)
    hit = (sign * dm) > thr
    quiet = np.abs(dm) < 2 * max(sig, 0.03)
    eps, cur = [], []
    for i in np.flatnonzero(hit):
        if cur and quiet[(t > t[cur[-1]]) & (t < t[i])].any() and t[i] - t[cur[-1]] > 30:
            eps.append(cur)
            cur = []
        cur.append(i)
    if cur:
        eps.append(cur)
    res = []
    for ep in eps:
        if len(ep) < 2:
            continue
        ip = ep[int(np.argmin(dm[ep]))] if sign == -1 else ep[int(np.argmax(dm[ep]))]
        t1, t2 = t[ep[0]], t[ep[-1]]
        qb, qa = t[quiet & (t < t1)], t[quiet & (t > t2)]
        te = np.sort(t[ep])
        res.append(dict(n=len(ep), n_dates=int(1 + (np.diff(te) > 5).sum()), t_first=float(t1), t_last=float(t2),
                        t_peak=float(t[ip]), dm_peak=float(dm[ip]), quiet_before=float(qb.max()) if len(qb) else None,
                        quiet_after=float(qa.min()) if len(qa) else None, trunc_start=len(qb) == 0, trunc_end=len(qa) == 0))
    return res


def colour(df: pd.DataFrame) -> dict:
    g = df[df.g == "G"].drop_duplicates("camera").set_index("camera")
    hot = g[((g.f - 1) / g.e > 5) & (g.f > 1.1)]
    bp = df[df.g == "BP"].drop_duplicates("camera").set_index("camera")
    rp = df[df.g == "RP"].drop_duplicates("camera").set_index("camera")
    cams = [c for c in hot.index if c in bp.index and c in rp.index]
    if not cams:
        return {"n_colour": 0}
    B, R, G = bp.loc[cams], rp.loc[cams], hot.loc[cams]
    dc = B.dm.to_numpy() - R.dm.to_numpy()
    ec = np.hypot(np.hypot(B.err, B.sig), np.hypot(R.err, R.sig)).to_numpy()
    w = 1 / ec**2
    mean = float((w * dc).sum() / w.sum())
    emean = float(1 / np.sqrt(w.sum()))
    x, y = (R.f - 1).to_numpy(), (B.f - 1).to_numpy()
    eB, eR = B.e.to_numpy(), R.e.to_numpy()
    kk = float((x * y / eB**2).sum() / max((x * x / eB**2).sum(), 1e-12))
    ey2 = eB**2
    for _ in range(3):
        ey2 = eB**2 + (kk * eR) ** 2
        kk = float((x * y / ey2).sum() / max((x * x / ey2).sum(), 1e-12))
    ek = float(1 / np.sqrt(max((x * x / ey2).sum(), 1e-12)))
    return {"n_colour": len(cams), "dcol_mean": round(mean, 3), "dcol_err": round(emean, 3), "k_bp_rp": round(kk, 3),
            "k_err": round(ek, 3), "peak_fG": round(float(G.f.max()), 3)}


def colour_verdict(c: dict, base_bp: float | None) -> str:
    """Delta(BP-RP) at the bright transits (the ensemble's 0.10 mag / 0.05 error), or H-0010's excess-flux ratio k."""
    if not c.get("n_colour") or base_bp is None or base_bp > 20.5:
        return "untested"
    dcol, edcol, k, ek = c["dcol_mean"], c["dcol_err"], c["k_bp_rp"], c["k_err"]
    if (abs(dcol) > 0.10 and abs(dcol) > 3 * edcol) or (ek <= 0.25 and abs(k - 1) > 3 * ek):
        return "chromatic"
    if (abs(dcol) <= 0.10 and edcol <= 0.05) or (ek <= 0.25 and abs(k - 1) <= 2 * ek):
        return "achromatic"
    return "untested"


def shape_fit(df: pd.DataFrame, kind: str) -> tuple[float, int]:
    """A non-lens brightening with one amplitude per band: 'pv7' (Pearson VII) or 'fred' (fast rise, exponential decay).
    From scripts/hunt_h0008_atlas_fit.py via H-0010, so the comparison matches the refereed hunts."""
    names = sorted(df.g.unique())
    gi = df.g.map({s: i for i, s in enumerate(names)}).to_numpy()
    t, f, e = df.t.to_numpy(float), df.f.to_numpy(float), df.e.to_numpy(float)
    t0c = float(t[np.argmax(f)])
    nshape = 3

    def model(p):
        q, amp = p[:nshape], np.asarray(p[nshape:])[gi]
        if kind == "fred":
            x = np.maximum(t - q[0], 1e-3)
            prof = np.where(t > q[0], np.exp(np.clip(2 * np.sqrt(q[1] / q[2]) - q[1] / x - x / q[2], -50, 50)), 0.0)
        else:
            prof = (1 + ((t - q[0]) / q[1]) ** 2) ** (-q[2])
        return 1 + amp * prof

    if kind == "fred":
        starts = [[t0c - d, a, b] for d in (30, 80) for a in (10, 50, 200) for b in (20, 60, 150)]
        lo, hi = [t0c - 600, 0.5, 2], [t0c + 50, 5000, 2000]
    else:
        starts = [[t0c, w, m] for w in (20, 50, 100, 200) for m in (0.5, 1, 3)]
        lo, hi = [t0c - 150, 2, 0.1], [t0c + 150, 2000, 50]
    amp0 = max(float(f.max()) - 1, 0.1)
    L, H = np.r_[lo, [0.0] * len(names)], np.r_[hi, [50.0] * len(names)]
    best = None
    for p0 in starts:
        x0 = np.clip(np.r_[p0, [amp0] * len(names)], L + 1e-6, H - 1e-6)
        r = least_squares(lambda p: (model(p) - f) / e, x0, bounds=(L, H))
        if best is None or r.cost < best.cost:
            best = r
    return float(2 * best.cost), nshape + len(names)


def lens_fit(df: pd.DataFrame, ra: float, dec: float, parallax: bool = False) -> dict:
    prob = Problem(df.t.to_numpy(), df.f.to_numpy(), df.e.to_numpy(), df.g.to_numpy(), ra=ra, dec=dec, parallax=parallax,
                   blend=True)
    gmask = df.g.to_numpy() == "G"
    tb = float(df.t.to_numpy()[np.argmax(np.where(gmask, df.f.to_numpy(), -np.inf))])
    p, chi2 = None, np.inf
    for dt in (0.0, -30.0, 30.0):
        q, c = prob.fit(t0c=tb + dt)
        if c < chi2:
            p, chi2 = q, c
    k, n = len(p), len(df)
    out = {"chi2": round(chi2, 1), "k": k, "bic": round(chi2 + k * np.log(n), 1), "t0": round(float(p[0]), 2),
           "tE": round(float(p[1]), 1), "u0": round(float(p[2]), 4),
           "fs": {s: round(float(v), 3) for s, v in zip(prob.names, p[prob.nlens:], strict=True)},
           "Amax_source": round(float(magnification(np.array([abs(p[2])]))[0]), 2)}
    out["fs_at_bound"] = any(v <= 0.021 or v >= 1.49 for v in out["fs"].values())
    if parallax:
        out["piE"] = [round(float(p[3]), 3), round(float(p[4]), 3)]
    return out


def analyse(df: pd.DataFrame, ra: float = np.nan, dec: float = np.nan, t_event: float = np.nan, fit: bool = True,
            parallax: bool = False) -> dict:
    """Metrics and a triage label for one source's epoch photometry (gaia_epoch.to_series format)."""
    rec: dict = {"n_raw": int(len(df))}
    d = clean(df)
    rs, base = ratio_series(d)
    g = rs[rs.g == "G"].sort_values("t")
    rec["n_G"] = int(len(g))
    rec["t_first"] = round(float(g.t.min()), 1) if len(g) else np.nan
    rec["t_last"] = round(float(g.t.max()), 1) if len(g) else np.nan
    if len(g) < MIN_G:
        rec["label"] = "too few G transits"
        return rec
    rec.update(base_G=base["G"]["mag"], sig_G=base["G"]["sig"], base_BP=base.get("BP", {}).get("mag"),
               base_RP=base.get("RP", {}).get("mag"))
    br, fa = episodes(g, -1), episodes(g, +1)
    # periodicity of what remains outside the strongest brightening and fading episodes (+-30 d): one big event in a
    # 2-5 year light curve otherwise gives high power at long periods (the dry run labelled 18 lens candidates periodic)
    keep = np.ones(len(g), bool)
    for ep in [e for e in (min(br, key=lambda e: e["dm_peak"]) if br else None,
                           max(fa, key=lambda e: e["dm_peak"]) if fa else None) if e]:
        keep &= ~((g.t.to_numpy() >= ep["t_first"] - 30) & (g.t.to_numpy() <= ep["t_last"] + 30))
    rec.update(periodicity(g[keep]))
    rec["amp_5_95"] = round(float(np.percentile(g.dm, 95) - np.percentile(g.dm, 5)), 3)
    rec["n_bright_ep"], rec["n_fade_ep"] = len(br), len(fa)
    rec["bright_eps"] = ";".join(f"{e['t_peak']:.0f}:{e['dm_peak']:+.2f}:{e['n']}" for e in br)
    rec["fade_eps"] = ";".join(f"{e['t_peak']:.0f}:{e['dm_peak']:+.2f}:{e['n']}" for e in fa)
    main = min(br, key=lambda e: e["dm_peak"]) if br else None
    deep = max(fa, key=lambda e: e["dm_peak"]) if fa else None
    if np.isfinite(t_event):
        r = ensemble_rule().grade_series(df, float(t_event))
        rec.update(ev_status=r["status"].split(":")[0], ev_n_win=r["n_win"], ev_n_up=r["n_up"],
                   ev_r_max=round(r["r_max"], 3) if np.isfinite(r["r_max"]) else np.nan,
                   ev_dt_rmax=round(r["dt_rmax"], 1) if np.isfinite(r["dt_rmax"]) else np.nan,
                   ev_colour=r.get("colour", ""))
    if main:
        rec.update(t_peak=round(main["t_peak"], 2), dG_peak=round(main["dm_peak"], 3),
                   A_obs_G=round(10 ** (-0.4 * main["dm_peak"]), 3), ep_n=main["n"], ep_n_dates=main["n_dates"],
                   ep_dur_min=round(main["t_last"] - main["t_first"], 1), ep_trunc=main["trunc_start"] or main["trunc_end"],
                   other_bright_max_dG=round(max([e["dm_peak"] for e in br if e is not main], default=0.0), 3))
        col = colour(rs)
        rec.update(col)
        rec["colour"] = colour_verdict(col, rec.get("base_BP"))
        if fit and main["dm_peak"] <= -0.15:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fdf = rs[["t", "f", "e", "g"]]
                n = len(fdf)
                lf = lens_fit(fdf, ra, dec, parallax=False)
                rec.update(lens_t0=lf["t0"], lens_tE=lf["tE"], lens_u0=lf["u0"], lens_bic=lf["bic"],
                           lens_fs_at_bound=lf["fs_at_bound"])
                if parallax and np.isfinite(ra):
                    pf = lens_fit(fdf, ra, dec, parallax=True)
                    rec.update(par_bic=pf["bic"], par_tE=pf["tE"], par_piE=str(pf["piE"]))
                shapes = {}
                for kind in ("pv7", "fred"):
                    c, k = shape_fit(fdf, kind)
                    shapes[kind] = c + k * np.log(n)
                best_lens = min(lf["bic"], rec.get("par_bic", np.inf))
                rec["dbic_shape_minus_lens"] = round(min(shapes.values()) - best_lens, 1)
    if deep:
        rec.update(t_fade=round(deep["t_peak"], 2), dG_fade=round(deep["dm_peak"], 3), fade_n=deep["n"],
                   fade_n_dates=deep["n_dates"], fade_dur_min=round(deep["t_last"] - deep["t_first"], 1))
    rec["label"] = label(rec)
    return rec


def periodicity(g: pd.DataFrame) -> dict:
    """Strongest Lomb-Scargle period of G between 20 d and the span (at most 1,000 d). Added after the DR3 dry run: 33 of 45
    "deep declines" among H-0004's R CrB candidates were Miras and semiregulars (power >= 0.6, Gaia class LPV)."""
    from astropy.timeseries import LombScargle

    t, m = g.t.to_numpy(float), g.dm.to_numpy(float)
    if len(t) < 15:
        return {"n_rest": int(len(t))}
    span = float(t.max() - t.min())
    rest = {"n_rest": int(len(t)), "amp_rest": round(float(np.percentile(m, 95) - np.percentile(m, 5)), 3)}
    if span < 100:
        return rest
    f, p = LombScargle(t, m).autopower(minimum_frequency=1 / min(1000.0, span / 2), maximum_frequency=1 / 20.0,
                                       samples_per_peak=10)
    i = int(np.argmax(p))
    return {**rest, "ls_period": round(float(1 / f[i]), 1), "ls_power": round(float(p[i]), 3)}


def is_periodic(r: dict) -> bool:
    """A periodic large-amplitude variable: strong periodogram peak AND >= 0.3 mag (5-95%) outside the strongest episodes,
    on >= 20 transits. With Gaia's clustered sampling ~20 points give LS power 0.6-0.8 by chance (dry run); a lensed star is
    flat outside its event, a Mira is not."""
    return r.get("ls_power", 0) >= 0.6 and r.get("amp_rest", 0) >= 0.3 and r.get("n_rest", 0) >= 20


def label(r: dict) -> str:
    """A triage label. Order matters: the first that applies wins."""
    tags = []
    if r.get("dG_peak") is not None and r["dG_peak"] <= -0.15:
        single = r.get("other_bright_max_dG", 0.0) > -0.3
        chrom = r.get("colour") == "chromatic"
        lens_ok = r.get("dbic_shape_minus_lens", -99) >= -10
        dates = r.get("ep_n_dates", 1) >= 2
        periodic = is_periodic(r)
        if single and not chrom and lens_ok and dates and not periodic:
            tags.append("lens-like brightening")
        elif not single:
            tags.append("repeating brightenings")
        elif chrom:
            tags.append("chromatic brightening")
        elif not dates:
            tags.append("one-date brightening (scan-angle artifact possible)")
        elif periodic:
            tags.append("periodic large-amplitude variable")
            return "; ".join(tags)
        else:
            tags.append("brightening, not lens-shaped")
    if r.get("dG_fade") is not None and r["dG_fade"] >= 0.3:
        if is_periodic(r):
            tags.append("periodic large-amplitude variable")
        else:
            tags.append("deep decline" if r["dG_fade"] >= 1.0 and r.get("fade_n_dates", 1) >= 2 else "dip")
    if not tags and is_periodic(r):
        tags.append("periodic large-amplitude variable")  # the 4-sigma episode threshold scales with the variability itself
    elif not tags and r.get("sig_G", 0) >= 0.1:
        tags.append("high-scatter variable")
    return "; ".join(tags) or "quiet"


PRIORITY = {"lens-like brightening": 1, "deep decline": 2, "dip": 3, "brightening, not lens-shaped": 4,
            "chromatic brightening": 5, "repeating brightenings": 6, "one-date brightening (scan-angle artifact possible)": 7,
            "periodic large-amplitude variable": 8, "high-scatter variable": 8, "quiet": 9, "too few G transits": 10}


def priority(lbl: str, ev_status: str | None = None, at_event: bool = False, other_class: bool = False) -> int:
    """Lower is first. `other_class`: the release's classifier puts the source in a variable class other than
    microlensing (e.g. LPV), which explains most brightenings and declines."""
    p = min((PRIORITY.get(x.strip(), 8) for x in str(lbl).split(";")), default=9)
    if ev_status == "pass" or at_event:
        p = max(p - 1, 0)  # Gaia agrees with a second instrument (NEOWISE) on the time: worth a look first
    if other_class:
        p += 2
    return p
