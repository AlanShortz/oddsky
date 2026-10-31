"""H-0008: ATLAS follow-up of the strongest lens-like unclassified events that ZTF cannot check (work/atlas/queue.csv).

For each returned light curve (~/oddsky-runs/h0008/atlas10/atlas_<J>.txt, copied to work/atlas/): ATLAS nightly series per band
and unit, built exactly as in hunt_h0008_atlas_fit.py (no chi/N cut, baseline > 400 d from the peak, error floor from the
baseline's excess scatter), plus the star's NEOWISE W1/W2 visits from the sky3lens light curves. Fits: point lens with blending
per series, static and with annual parallax (oddsky.analysis.lensing), and the non-lens shapes (Pearson VII symmetric and
two-sided, fast-rise exponential decay). Reports the ATLAS coverage of the event (nights within 60 d of the peak), the largest
excursion elsewhere, and a figure per star (figures/atlas10.png).

This is a first pass. The referee (reviews/claude-referee-atlas10-2026-10-30.md) supersedes its parameters: ratios to a faint
ATLAS baseline exaggerate amplitudes (J191120's "x110" is x30-50 of the Gaia star), series with an undetected baseline are now
skipped, and blend fractions at their bounds (0.02, 1.5) mean the fit is not constrained.
usage: uv run python scripts/hunt_h0008_atlas10.py [--hunt H-0009]
"""

import json
import os
import shutil
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from astropy.time import Time  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hunt_h0008_atlas_fit import BASE_DT, ratio_series, shape_fit  # noqa: E402

from oddsky.analysis.lensing import Problem, magnification  # noqa: E402
from oddsky.data import atlas  # noqa: E402

# H-0008 by default; `--hunt H-0009` runs the same analysis on hunt H-0009's ATLAS follow-up (its queue, strong table, sky4long
# light curves), writing work/atlas10.json and figures/atlas10.png inside that hunt.
HUNT = sys.argv[sys.argv.index("--hunt") + 1] if "--hunt" in sys.argv else "H-0008"
CFG = {"H-0008": ("atlas10", "h0008/lightcurves", "sky3_strong.csv"),
       "H-0009": ("atlas", "h0009/lightcurves", "sky4_strong.csv")}[HUNT]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hunts", HUNT)
WORK = os.path.join(ROOT, "work")
RAW = os.path.expanduser(f"~/oddsky-runs/{HUNT.lower().replace('-', '')}/{CFG[0]}")
LC = os.path.expanduser(f"~/oddsky-runs/{CFG[1]}")


def atlas_series(path, tpk_guess):
    raw = atlas.parse(open(path).read())
    raw = raw[(raw.err == 0) & (raw.dujy > 0) & (raw.mag5sig > 17.0) & raw.F.isin(["c", "o"])].copy()
    raw["night"] = np.floor(raw.mjd)
    nights = []
    for (F, cam), d in raw.groupby(["F", raw.obs.str[:3]]):
        w = 1 / d.dujy**2
        g = d.assign(w=w, wf=w * d.ujy).groupby("night")
        nights.append(pd.DataFrame({"t": g.mjd.mean(), "fl": g.wf.sum() / g.w.sum(), "fe": 1 / np.sqrt(g.w.sum()),
                                    "F": F, "cam": cam}))
    nt = pd.concat(nights, ignore_index=True)
    # the peak: the brightest 20-day median in o within 150 d of the NEOWISE visit, relative to each unit's median
    nt["rel"] = nt.fl / nt.groupby(["F", "cam"]).fl.transform("median")
    o = nt[(nt.F == "o") & (np.abs(nt.t - tpk_guess) < 150)].sort_values("t")
    tpk = float(o.t.iloc[int(np.argmax(o.rel.rolling(5, center=True, min_periods=1).median()))]) if len(o) else tpk_guess
    rows = []
    for (F, cam), d in nt.groupby(["F", "cam"]):
        base = np.abs(d.t - tpk) > BASE_DT
        if base.sum() < 8 or (np.abs(d.t - tpk) < 200).sum() < 1:
            continue
        s = ratio_series(d.t.values, d.fl.values, d.fe.values, f"ATLAS_{F}_{cam}", tpk)
        if s is not None:
            rows.append(s[(s.f > -5) & (s.f < 500)])
    return (pd.concat(rows, ignore_index=True) if rows else None), tpk


def neowise_series(pixel, cntr, tpk):
    lc = pd.read_parquet(f"{LC}/pixel={int(pixel)}.parquet")
    n = lc[lc.allwise_cntr == int(cntr)]
    rows = []
    for b in ("w1", "w2"):
        fl = 10 ** (-0.4 * n[b].values)
        rows.append(ratio_series(n.t.values, fl, fl * n[f"{b}_err"].values / 1.0857, f"NEOWISE_{b.upper()}", tpk))
    return pd.concat(rows, ignore_index=True)


def main():
    q = pd.read_csv(os.path.join(WORK, "atlas", "queue.csv"))
    strong = pd.read_csv(os.path.join(WORK, CFG[2]), dtype={"g_source_id": str})
    out, panels = {}, []
    for _, r in q.iterrows():
        key = r.designation.split(".")[0]
        path = os.path.join(RAW, f"atlas_{key}.txt")
        if not os.path.exists(path):
            out[r.designation] = {"status": "ATLAS not returned yet", "task": r.task}
            continue
        shutil.copy(path, os.path.join(WORK, "atlas", f"atlas_{key}.txt"))
        s = strong[strong.designation == r.designation].iloc[0]
        a, tpk = atlas_series(path, r.t_neowise)
        if a is None:
            out[r.designation] = {"status": "ATLAS baseline not detected in any band/unit: no flux ratios (see the referee)"}
            print(r.designation, out[r.designation], flush=True)
            continue
        df = pd.concat([a, neowise_series(s.pixel, s.allwise_cntr, tpk)], ignore_index=True)
        ev = df[np.abs(df.t - tpk) < 60]
        res = {"t_peak_guess": round(tpk, 1), "t_peak_date": Time(tpk, format="mjd").iso[:10], "n": int(len(df)),
               "atlas_nights_within_60d": int(ev.g.str.startswith("ATLAS").sum()),
               "peak_ratio_atlas_o": round(float(ev[ev.g.str.startswith("ATLAS_o")].f.max()), 2) if len(ev) else None,
               "max_ratio_elsewhere_o": round(float(df[(np.abs(df.t - tpk) > BASE_DT) & df.g.str.startswith("ATLAS_o")]
                                                   .f.quantile(0.995)), 2),
               "gaia_G": s.g_phot_g_mean_mag, "l": round(s.l, 2), "b": round(s.b, 2)}
        if res["atlas_nights_within_60d"] >= 5:
            fit = df[np.abs(df.t - tpk) < 1500]
            for par in (False, True):
                prob = Problem(fit.t.values, fit.f.values, fit.e.values, fit.g.values, ra=s.ra, dec=s.dec, parallax=par,
                               blend=True, t0par=round(tpk))
                p, chi2 = prob.fit(t0c=tpk)
                res["parallax" if par else "static"] = {
                    "chi2": round(chi2, 1), "dof": int(len(fit) - len(p)), "t0": round(float(p[0]), 2),
                    "t0_date": Time(p[0], format="mjd").iso[:10], "tE": round(float(p[1]), 1), "u0": round(float(p[2]), 3),
                    "Amax": round(float(magnification(np.array([abs(p[2])]))[0]), 2),
                    "fs": {g: round(float(v), 3) for g, v in zip(prob.names, p[prob.nlens:], strict=True)}}
                if not par:
                    model = prob.model(p)
            for kind in ("pv7", "pv7_asym", "fred"):
                c, x = shape_fit(fit, kind)
                res[kind] = round(c, 1)
            panels.append((r.designation, df, fit.assign(model=model), tpk))
        else:
            panels.append((r.designation, df, None, tpk))
        out[r.designation] = res
        print(r.designation, json.dumps(res, default=str)[:900], flush=True)
    json.dump(out, open(os.path.join(WORK, "atlas10.json"), "w"), indent=1, default=str)
    n = len(panels)
    fig, axes = plt.subplots((n + 1) // 2, 2, figsize=(12, 2.8 * ((n + 1) // 2)), squeeze=False)
    for ax, (name, df, fit, tpk) in zip(axes.flat, panels, strict=False):
        win = df[np.abs(df.t - tpk) < 400]
        for g, d in win.groupby("g"):
            c = "#e08a2c" if "_o_" in g else "#2aa1b3" if "_c_" in g else "#2836d9" if "W1" in g else "#d6338a"
            ax.errorbar(Time(d.t, format="mjd").datetime, d.f, d.e, fmt="o", ms=2.5 if "ATLAS" in g else 6, lw=0.4, c=c,
                        alpha=0.7)
        if fit is not None:
            o = fit[fit.g.str.startswith("ATLAS_o") & (np.abs(fit.t - tpk) < 400)].sort_values("t")
            ax.plot(Time(o.t, format="mjd").datetime, o.model, c="k", lw=0.6, alpha=0.6)
        ax.set_title(name, fontsize=9)
        ax.set_ylabel("flux / baseline", fontsize=8)
        ax.tick_params(labelsize=7)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle(f"{HUNT} ATLAS follow-up: ATLAS o (orange), c (cyan), NEOWISE W1 (blue), W2 (pink); line: static lens, ATLAS o",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "figures", "atlas10.png"), dpi=120)


if __name__ == "__main__":
    main()
