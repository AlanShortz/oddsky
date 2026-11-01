"""s3: light-curve analysis of the 67 sources' Gaia DR3 epoch photometry.

Per source:
  * baseline per band (iterative median of transits not significantly brighter) and its robust scatter;
  * brightening episodes in G (>= 2 transits brighter than max(4 sigma, 0.08 mag); episodes split by a quiet transit and a
    gap > 30 d), their peak, amplitude, duration bounds (last quiet transit before, first after) and whether the window edge
    truncates them; fading episodes the same way;
  * fits to the G, BP and RP flux ratios jointly: point-source point-lens with blending per band (static, and with annual
    parallax; src/oddsky/analysis/lensing.py), and non-lens shapes (symmetric and asymmetric Pearson VII, FRED) with an
    amplitude per band; chi2, BIC, tE 95% profile ranges;
  * colour: at transits where G is significantly brightened, Delta(BP-RP) and the excess-flux ratio
    k = (f_BP - 1)/(f_RP - 1) (a lens on an unblended star gives k = 1).

Run from the repo root: uv run python -I hunts/H-0010/scripts/s3_lightcurves.py
Writes hunts/H-0010/data/lc_metrics.csv and data/fits/<source_id>.json."""
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, DR3_END, DR3_START, baseline, epoch, mjd2date, shape_fit, targets  # noqa: E402

from oddsky.analysis.lensing import Problem, coverage, magnification, profile_range  # noqa: E402

warnings.filterwarnings("ignore")
FITS = os.path.join(DATA, "fits")
os.makedirs(FITS, exist_ok=True)


def ratio_series(d):
    """Flux ratios per band against the quiet baseline, errors with a floor from the baseline's excess scatter."""
    out, base = [], {}
    for b in ("G", "BP", "RP"):
        x = d[d.band == b]
        if len(x) < 5:
            continue
        m, e = x.mag.values, x.err.values
        bl, sig, keep = baseline(x.t_mjd.values, m, e)
        floor = np.sqrt(max(sig**2 - np.median(e[keep]) ** 2, 0.0))
        f = 10 ** (-0.4 * (m - bl))
        ef = f * 0.921 * np.sqrt(e**2 + floor**2)
        base[b] = {"mag": round(bl, 4), "sig": round(sig, 4), "floor": round(float(floor), 4), "n": int(len(x)),
                   "median_err": round(float(np.median(e)), 4)}
        out.append(pd.DataFrame(dict(t=x.t_mjd.values, f=f, e=ef, g=b, dm=m - bl, err=e, sig=sig, camera=x.camera.values,
                                     flag=x.flag.values)))
    return pd.concat(out, ignore_index=True), base


def episodes(g, sign=-1):
    """Clusters of >= 2 transits brighter (sign -1) or fainter (+1) than max(4 sigma, 0.08 mag)."""
    sig = float(g.sig.iloc[0])
    thr = max(4 * sig, 0.08)
    t, dm = g.t.values, g.dm.values
    hit = (sign * dm) > thr
    quiet = np.abs(dm) < 2 * max(sig, 0.03)
    eps, cur = [], []
    for i in np.where(hit)[0]:
        if cur:
            between = quiet[(t > t[cur[-1]]) & (t < t[i])]
            if between.any() and t[i] - t[cur[-1]] > 30:
                eps.append(cur)
                cur = []
        cur.append(i)
    if cur:
        eps.append(cur)
    res = []
    for ep in eps:
        ip = ep[int(np.argmin(sign * -dm[ep]))] if sign == -1 else ep[int(np.argmax(dm[ep]))]
        ip = ep[int(np.argmin(dm[ep]))] if sign == -1 else ep[int(np.argmax(dm[ep]))]
        t1, t2 = t[ep[0]], t[ep[-1]]
        qb = t[quiet & (t < t1)]
        qa = t[quiet & (t > t2)]
        te = np.sort(t[ep])
        n_dates = int(1 + (np.diff(te) > 5).sum())
        res.append(dict(n=len(ep), n_dates=n_dates, t_first=float(t1), t_last=float(t2), t_peak=float(t[ip]), dm_peak=float(dm[ip]),
                        quiet_before=float(qb.max()) if len(qb) else None, quiet_after=float(qa.min()) if len(qa) else None,
                        trunc_start=len(qb) == 0, trunc_end=len(qa) == 0, thr=thr))
    return res


def fit_all(df, ra, dec):
    n = len(df)
    out = {"n": n, "bands": sorted(df.g.unique().tolist())}
    out["chi2_flat"] = round(float((((df.f - 1) / df.e) ** 2).sum()), 1)
    models = {}
    for par in (False, True):
        prob = Problem(df.t.values, df.f.values, df.e.values, df.g.values, ra=ra, dec=dec, parallax=par, blend=True)
        # several t0 starting points: events cut by the window edge peak away from the brightest transit
        tb = float(df.t.values[np.argmax(np.where(df.g.values == "G", df.f.values, -np.inf))])
        p, chi2 = None, np.inf
        for dt in (0.0, -30.0, 30.0, 80.0, -80.0):
            q, c = prob.fit(t0c=tb + dt)
            if c < chi2:
                p, chi2 = q, c
        k = len(p)
        lab = "parallax" if par else "static"
        res = {"chi2": round(chi2, 1), "k": k, "bic": round(chi2 + k * np.log(n), 1), "t0": round(float(p[0]), 2),
               "t0_date": mjd2date(p[0]), "tE": round(float(p[1]), 1), "u0": round(float(p[2]), 4),
               "fs": {s: round(float(v), 3) for s, v in zip(prob.names, p[prob.nlens:], strict=True)},
               "Amax_source": round(float(magnification(np.array([abs(p[2])]))[0]), 2)}
        if par:
            res["piE"] = [round(float(p[3]), 3), round(float(p[4]), 3)]
        try:
            lo, hi, opn = profile_range(prob, p, chi2, 1, 0.6 * float(p[1]), n=7, iters=4)
            res["tE_95"] = [round(lo, 1), round(hi, 1)] + (["open"] if opn else [])
        except Exception as e:  # noqa: BLE001
            res["tE_95"] = f"error {e}"
        res["coverage"] = coverage(df.t.values, p[0], p[1], p[2])
        tt = np.linspace(DR3_START - 50, DR3_END + 50, 1500)
        mod = {}
        for b in prob.names:
            pp = Problem(tt, np.ones_like(tt), np.ones_like(tt), np.array([b] * len(tt)), ra=ra, dec=dec, parallax=par,
                         blend=True, t0par=prob.t0par)
            q = np.r_[p[:prob.nlens], [p[prob.nlens + prob.names.index(b)]]]
            mod[b] = pp.model(q).round(5).tolist()
        models[lab] = {"t": tt.round(2).tolist(), **mod}
        out[lab] = res
    for kind in ("pv7", "pv7_asym", "fred"):
        c, x, amp = shape_fit(df, kind)
        k = len(x) + len(amp)
        out[kind] = {"chi2": round(c, 1), "k": k, "bic": round(c + k * np.log(n), 1),
                     "params": [round(float(v), 2) for v in x], "amp": [round(float(v), 3) for v in amp]}
    best_lens = min(out["static"]["bic"], out["parallax"]["bic"])
    best_shape = min(out[k]["bic"] for k in ("pv7", "pv7_asym", "fred"))
    out["dbic_shape_minus_lens"] = round(best_shape - best_lens, 1)
    return out, models


def colour(df):
    """Same-transit comparison of BP and RP at transits where G is significantly brightened."""
    g = df[df.g == "G"].set_index("camera")
    sig = (g.f - 1) / g.e
    hot = g[(sig > 5) & (g.f > 1.1)]
    rows = []
    for cam, r in hot.iterrows():
        bp = df[(df.g == "BP") & (df.camera == cam)]
        rp = df[(df.g == "RP") & (df.camera == cam)]
        if len(bp) and len(rp):
            rows.append(dict(fG=r.f, fBP=bp.f.iloc[0], eBP=bp.e.iloc[0], fRP=rp.f.iloc[0], eRP=rp.e.iloc[0],
                             dBP=bp.dm.iloc[0], dRP=rp.dm.iloc[0], errBP=np.hypot(bp.err.iloc[0], bp.sig.iloc[0]),
                             errRP=np.hypot(rp.err.iloc[0], rp.sig.iloc[0])))
    if not rows:
        return {"n_colour": 0}
    c = pd.DataFrame(rows)
    dc = c.dBP - c.dRP
    ec = np.hypot(c.errBP, c.errRP)
    w = 1 / ec**2
    mean = float((w * dc).sum() / w.sum())
    emean = float(1 / np.sqrt(w.sum()))
    chi = float((((dc - mean) / ec) ** 2).sum())
    # excess-flux ratio k through the origin, errors on both axes folded into y
    x, y = c.fRP - 1, c.fBP - 1
    kk = float((x * y / c.eBP**2).sum() / (x * x / c.eBP**2).sum())
    for _ in range(3):
        ey2 = c.eBP**2 + (kk * c.eRP) ** 2
        kk = float((x * y / ey2).sum() / (x * x / ey2).sum())
    ek = float(1 / np.sqrt((x * x / ey2).sum()))
    kg = float(((c.fG - 1) * x / c.eRP**2).sum() / (x * x / c.eRP**2).sum())
    return {"n_colour": len(c), "dcol_mean": round(mean, 3), "dcol_err": round(emean, 3), "dcol_chi2": round(chi, 1),
            "k_bp_rp": round(kk, 3), "k_err": round(ek, 3), "k_g_rp": round(kg, 3), "peak_fG": round(float(c.fG.max()), 3)}


def main():
    T = targets()
    only = sys.argv[1:]
    rows = []
    for r in T.itertuples():
        if only and r.source_id not in only:
            continue
        d, info = epoch(r.source_id)
        df, base = ratio_series(d)
        g = df[df.g == "G"].sort_values("t")
        br = episodes(g, -1)
        fa = episodes(g, +1)
        main_ep = min(br, key=lambda e: e["dm_peak"]) if br else None
        fit, models = fit_all(df[["t", "f", "e", "g"]], r.ra, r.dec)
        col = colour(df)
        nG = len(g)
        rec = dict(source_id=r.source_id, n_G=nG, base_G=base["G"]["mag"], sig_G=base["G"]["sig"],
                   floor_G=base["G"]["floor"], medErr_G=base["G"]["median_err"],
                   base_BP=base.get("BP", {}).get("mag"), base_RP=base.get("RP", {}).get("mag"),
                   n_rej_var=info["n_rej_var"], n_rej_var_G=info["n_rej_var_G"], n_clip_bprp=info["n_clip_bprp"],
                   n_rej_phot=info["n_rej_phot"],
                   n_bright_ep=len(br), n_fade_ep=len(fa),
                   bright_eps=";".join(f"{mjd2date(e['t_peak'])}:{e['dm_peak']:+.2f}:{e['n']}" for e in br),
                   fade_eps=";".join(f"{mjd2date(e['t_peak'])}:{e['dm_peak']:+.2f}:{e['n']}" for e in fa))
        if main_ep:
            rec.update(t_peak=round(main_ep["t_peak"], 2), t_peak_date=mjd2date(main_ep["t_peak"]),
                       dG_peak=round(main_ep["dm_peak"], 3), A_obs_G=round(10 ** (-0.4 * main_ep["dm_peak"]), 3),
                       ep_n=main_ep["n"], ep_n_dates=main_ep["n_dates"], ep_first=round(main_ep["t_first"], 1), ep_last=round(main_ep["t_last"], 1),
                       dur_min=round(main_ep["t_last"] - main_ep["t_first"], 1),
                       dur_max=(round(main_ep["quiet_after"] - main_ep["quiet_before"], 1)
                                if main_ep["quiet_before"] and main_ep["quiet_after"] else None),
                       trunc_start=main_ep["trunc_start"], trunc_end=main_ep["trunc_end"],
                       other_bright_max_dG=round(max([e["dm_peak"] for e in br if e is not main_ep], default=0.0), 3))
        rec.update({f"static_{k}": fit["static"][k] for k in ("chi2", "bic", "t0", "t0_date", "tE", "u0", "Amax_source")})
        rec["static_tE95"] = str(fit["static"]["tE_95"])
        rec["static_fs"] = json.dumps(fit["static"]["fs"])
        rec.update({f"par_{k}": fit["parallax"][k] for k in ("chi2", "bic", "t0", "tE", "u0")})
        rec["par_tE95"] = str(fit["parallax"]["tE_95"])
        rec["par_piE"] = str(fit["parallax"]["piE"])
        rec["par_fs"] = json.dumps(fit["parallax"]["fs"])
        for kind in ("pv7", "pv7_asym", "fred"):
            rec[f"{kind}_chi2"] = fit[kind]["chi2"]
            rec[f"{kind}_bic"] = fit[kind]["bic"]
        rec["chi2_flat"] = fit["chi2_flat"]
        rec["n_fit"] = fit["n"]
        rec["dbic_shape_minus_lens"] = fit["dbic_shape_minus_lens"]
        rec.update(col)
        rows.append(rec)
        with open(os.path.join(FITS, f"{r.source_id}.json"), "w") as f:
            json.dump({"fit": fit, "base": base, "info": info, "bright": br, "fade": fa, "colour": col, "models": models}, f)
        print(f"{r.source_id} G{base['G']['mag']:.2f} sig{base['G']['sig']:.3f} eps {rec['bright_eps']} | fades {rec['fade_eps']} | "
              f"static tE {fit['static']['tE']} chi2 {fit['static']['chi2']} par {fit['parallax']['chi2']} "
              f"pv7 {fit['pv7']['chi2']} asym {fit['pv7_asym']['chi2']} fred {fit['fred']['chi2']} flat {fit['chi2_flat']} n {fit['n']} "
              f"| k {col.get('k_bp_rp')}±{col.get('k_err')} dcol {col.get('dcol_mean')}±{col.get('dcol_err')}", flush=True)
    out = pd.DataFrame(rows)
    path = os.path.join(DATA, "lc_metrics.csv")
    if only and os.path.exists(path):  # re-run of a subset: replace those rows
        old = pd.read_csv(path, dtype={"source_id": str})
        out = pd.concat([old[~old.source_id.isin(out.source_id)], out], ignore_index=True)
    out.to_csv(path, index=False)
    print("wrote", path, len(out))


if __name__ == "__main__":
    main()
