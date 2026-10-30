"""r4: point-lens refits of the four new events and the Zhai+2024 sanity check, on my own re-fetch (ZTF catflags=0 nightly,
NEOWISE sky3lens visits; ATLAS nightly o/c added when data/atlas_<k>.txt exists). Fitter: oddsky.analysis.lensing.Problem
(the Oddsky tool), on flux ratios with a per-series error floor from that series' own baseline scatter (> 200 d from the event).
Variants: (a) no blending, (b) blend per series, (c) blend + annual parallax (both u0 signs, built into Problem).
Also: asymmetry (separate tE before/after t0, my own model, scipy) and per-series amplitude at matched epochs (colour).
usage: r4_fits.py [keys]"""
import json, os, sys
import numpy as np, pandas as pd
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import ztf, neowise, D
from targets import TARGETS
from oddsky.analysis.lensing import Problem, magnification, coverage
from oddsky.data import atlas

HERE = os.path.dirname(os.path.abspath(__file__))


def series_for(k, use_atlas=True, cat0=True):
    name, ra, dec, t, pix = TARGETS[k]
    rows = []
    z = ztf(k, cat0=cat0)
    for s, d in z.groupby("series"):
        base = d[(d.mjd - t).abs() > 200]
        if len(base) < 5:
            continue
        med = base.mag.median()
        fr = 10 ** (-0.4 * (d.mag - med)); fe = fr * d.magerr / 1.0857
        bfr = 10 ** (-0.4 * (base.mag - med)); floor = 1.4826 * np.median(np.abs(bfr - 1))
        fe = np.sqrt(fe ** 2 + max(floor ** 2 - np.median(fe[(d.mjd - t).abs() > 200]) ** 2, 0) + 0.005 ** 2)
        rows.append(pd.DataFrame({"t": d.mjd, "f": fr, "e": fe, "g": s}))
    n = neowise(k)
    nb = n[(n.t - t).abs() > 100]
    for b in ("w1", "w2"):
        med = nb[b].median(); fr = 10 ** (-0.4 * (n[b] - med)); fe = fr * n[f"{b}_err"] / 1.0857
        floor = 1.4826 * np.median(np.abs(10 ** (-0.4 * (nb[b] - med)) - 1))
        fe = np.sqrt(fe ** 2 + floor ** 2)
        rows.append(pd.DataFrame({"t": n.t, "f": fr, "e": fe, "g": "NEOWISE_" + b.upper()}))
    a = f"{D}/atlas_{k}.txt"
    if use_atlas and os.path.exists(a) and os.path.getsize(a) > 1000:
        raw = atlas.parse(open(a).read())
        raw = raw[(raw.err == 0) & (raw.chi_n < 10) & (raw.dujy > 0) & (raw.dujy < 0.3 * raw.ujy.abs().median() + 1e3)]
        raw["night"] = np.floor(raw.mjd)
        for (F, cam), d in raw.groupby(["F", raw.obs.str[:3]]):
            w = 1 / d.dujy ** 2
            g = d.assign(w=w, wf=w * d.ujy).groupby("night")
            nt = pd.DataFrame({"t": g.mjd.mean(), "fl": g.wf.sum() / g.w.sum(), "fe": 1 / np.sqrt(g.w.sum())})
            base = nt[(nt.t - t).abs() > 200]
            if len(base) < 10 or base.fl.median() <= 0:
                continue
            med = base.fl.median()
            floor = 1.4826 * np.median(np.abs(base.fl / med - 1))
            fr = nt.fl / med; fe = np.sqrt((nt.fe / med) ** 2 + floor ** 2)
            ok = (fr - 1).abs() < 20 * floor + 10  # drop absurd nights
            rows.append(pd.DataFrame({"t": nt.t[ok], "f": fr[ok], "e": fe[ok], "g": f"ATLAS_{F}_{cam}"}))
    return pd.concat(rows, ignore_index=True)


def fit_variants(k, df, window=None):
    name, ra, dec, t, pix = TARGETS[k]
    if window:
        df = df[(df.t - t).abs() < window]
    out = {}
    t0c = float(df.t[df.f.idxmax()]) if len(df) else t
    for lab, kw in (("static_noblend", dict(blend=False)), ("static_blend", dict(blend=True)),
                    ("parallax_blend", dict(blend=True, parallax=True, ra=ra, dec=dec))):
        p = Problem(df.t.values, df.f.values, df.e.values, df.g.values, **kw)
        best, chi2 = p.fit(t0c=t0c)
        dof = len(df) - len(best)
        res = {"chi2": round(chi2, 1), "n": len(df), "dof": dof, "t0": round(best[0], 2), "tE": round(best[1], 2),
               "u0": round(best[2], 4), "Amax": round(float(magnification(best[2])), 2)}
        if kw.get("parallax"):
            res["piEN"], res["piEE"] = round(best[3], 3), round(best[4], 3)
        if kw.get("blend"):
            res["fs"] = {g: round(float(v), 3) for g, v in zip(p.names, best[p.nlens:])}
        # per-series chi2
        m = p.model(best)
        res["chi2_by_series"] = {g: [round(float((((m - p.f) / p.e) ** 2)[p.group == g].sum()), 1), int((p.group == g).sum())] for g in p.names}
        out[lab] = res
        if lab == "static_blend":
            out["coverage"] = coverage(df.t.values, best[0], best[1], best[2])
            out["_best_blend"] = best.tolist()
    return out


def asym(df, t0, te, u0):
    """Symmetric vs asymmetric (tE_rise, tE_fall) unblended point lens, my own code."""
    def model(p, tt):
        tau = np.where(tt < p[0], (tt - p[0]) / p[1], (tt - p[0]) / p[2])
        return magnification(np.hypot(tau, p[3]))
    r = least_squares(lambda p: (model(p, df.t.values) - df.f.values) / df.e.values, [t0, te, te, max(u0, 1e-3)],
                      bounds=([t0 - 100, 1, 1, 1e-4], [t0 + 100, 1000, 1000, 3]))
    return {"t0": round(r.x[0], 2), "tE_rise": round(r.x[1], 2), "tE_fall": round(r.x[2], 2), "u0": round(r.x[3], 4), "chi2": round(2 * r.cost, 1)}


if __name__ == "__main__":
    keys = sys.argv[1:] or list(TARGETS)
    allres = {}
    for k in keys:
        df = series_for(k)
        df.to_csv(f"{D}/fitinput_{k}.csv", index=False)
        res = fit_variants(k, df)
        sb = res["static_noblend"]
        res["asym_noblend"] = asym(df, sb["t0"], sb["tE"], sb["u0"])
        res["series_counts"] = df.g.value_counts().to_dict()
        allres[k] = res
        print(k, json.dumps({kk: vv for kk, vv in res.items() if not kk.startswith("_")}, indent=1), flush=True)
    prev = json.load(open(f"{HERE}/r4_fits.json")) if os.path.exists(f"{HERE}/r4_fits.json") else {}
    prev.update(allres)
    json.dump(prev, open(f"{HERE}/r4_fits.json", "w"), indent=1)
