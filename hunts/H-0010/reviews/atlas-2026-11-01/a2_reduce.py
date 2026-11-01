"""a2: reduce the 8 ATLAS files (reduced-image forced photometry, full history).
Cuts c/o, err==0, dujy>0, mag5sig>17.5, NO chi/N cut. Nightly per (band, unit, local night) weighted means, 4-sigma clip.
dt = night - Gaia t0 (static lens t0 from work/gaia_ml_unpub.csv). Per (band, unit):
  * baseline nights |dt| > 400 d: median, robust scatter, detection S/N (median / robust scatter), PSF maj median;
  * PSF-width slope of the baseline (robust line in maj), so a 2015-17 night can be compared at matched PSF;
  * matched-PSF baseline for the event era: baseline nights of the same unit with |maj - maj_event| < 0.3 px, where maj_event is
    the median PSF of that unit's nights within 90 d of t0.
Coverage: nights within +-30 and +-90 d of t0, per band/unit. Yearly medians per unit/band (PSF era check). Writes
data/a2_nightly_<k>.csv (one row per night, with dt, baseline, PSF-corrected excess) and data/a2_summary.json.
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a2_reduce.py"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, atlas_raw, clean, mjd2date, nightly, targets, ujy2ab  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 400)
T = targets()
SH = json.load(open(os.path.join(DATA, "a1_shares.json")))
summ = {}


def robust_line(x, y, nit=4):
    keep = np.ones(len(y), bool)
    p = np.array([np.median(y), 0.0])
    for _ in range(nit):
        if keep.sum() < 8:
            break
        A = np.vstack([np.ones(keep.sum()), x[keep]]).T
        p, *_ = np.linalg.lstsq(A, y[keep], rcond=None)
        res = y - (p[0] + p[1] * x)
        s = 1.4826 * np.median(np.abs(res[keep]))
        keep = np.abs(res) < 4 * max(s, 1e-9)
    res = y - (p[0] + p[1] * x)
    s = 1.4826 * np.median(np.abs(res[keep]))
    # slope error from the scatter
    xe = x[keep] - x[keep].mean()
    se = s / np.sqrt(np.sum(xe**2)) if np.sum(xe**2) > 0 else np.nan
    return float(p[0]), float(p[1]), float(se), float(s)


for k in KEYS:
    t = T[k]
    t0 = t["t0"]
    raw = atlas_raw(k)
    rc = clean(raw)
    nt = nightly(rc)
    nt["dt"] = nt.t - t0
    nt["base"] = nt.dt.abs() > 400
    print("=" * 40, k, t["name"], f"G {t['G']:.2f}; Gaia t0 {t0:.1f} ({mjd2date(t0)}), brightest transit {mjd2date(t['tpk'])} x{t['Apk']:.2f}; "
          f"Gaia event transits {mjd2date(t['ep_first'])} .. {mjd2date(t['ep_last'])}")
    print(f"raw c/o frames {len(raw)} ({raw.year.min():.2f}-{raw.year.max():.2f}); after cuts {len(rc)}; nights {len(nt)}")
    print(f"Gaia-predicted target flux: c {SH[k]['fc_star']:.0f} uJy, o {SH[k]['fo_star']:.0f} uJy; target share of ATLAS PSF flux "
          f"(maj 3.8/2.6 px): c {SH[k]['share']['3.8']['c']:.2f}/{SH[k]['share']['2.6']['c']:.2f}, o {SH[k]['share']['3.8']['o']:.2f}/{SH[k]['share']['2.6']['o']:.2f}")
    # yearly medians
    rc["yr"] = np.floor(rc.year).astype(int)
    yt = rc.groupby(["F", "cam", "yr"]).agg(n=("ujy", "size"), ujy=("ujy", "median"), maj=("maj", "median"), m5=("mag5sig", "median"),
                                             chi=("chi_n", "median")).reset_index()
    print("yearly frame medians per band/unit (uJy, PSF maj px):")
    for (F, cam), d in yt.groupby(["F", "cam"]):
        print(f"  {F} {cam}: " + "  ".join(f"{r.yr}:{r.ujy:.0f}({r.maj:.1f},n{r.n})" for r in d.itertuples()))
    st = {}
    nt["ubase"] = np.nan
    nt["ubase_psf"] = np.nan
    nt["floor"] = np.nan
    nt["exc_psf"] = np.nan
    for (F, cam), d in nt.groupby(["F", "cam"]):
        b = d[d.base]
        ev = d[d.dt.abs() <= 90]
        if len(b) < 10:
            st[f"{F}_{cam}"] = dict(n=len(b), n30=int((d.dt.abs() <= 30).sum()), n90=len(ev), usable=False, why="< 10 baseline nights")
            continue
        med = float(np.median(b.ujy))
        rob = float(1.4826 * np.median(np.abs(b.ujy - med)))
        a0, slope, slope_e, rres = robust_line(b.maj.values - b.maj.median(), b.ujy.values)
        extra = float(np.sqrt(max(rres**2 - np.median(b.ujy_err) ** 2, 0)))
        majev = float(ev.maj.median()) if len(ev) else np.nan
        bm = b[np.abs(b.maj - majev) < 0.3] if len(ev) else b.iloc[:0]
        medm = float(np.median(bm.ujy)) if len(bm) >= 5 else np.nan
        robm = float(1.4826 * np.median(np.abs(bm.ujy - medm))) if len(bm) >= 5 else np.nan
        # PSF-corrected baseline value at the event PSF (from the line)
        base_at_ev = a0 + slope * (majev - b.maj.median()) if len(ev) else np.nan
        snr = med / max(rob, 1e-9)
        usable = bool(med > 0 and snr >= 3)
        st[f"{F}_{cam}"] = dict(n=len(b), med=med, rob=rob, snr=snr, maj_base=float(b.maj.median()), slope=slope, slope_e=slope_e,
                                extra=extra, n30=int((d.dt.abs() <= 30).sum()), n90=len(ev), maj_ev=majev, n_matched=len(bm),
                                med_matched=medm, rob_matched=robm, base_at_ev=base_at_ev, usable=usable,
                                why="" if usable else ("baseline <= 0" if med <= 0 else f"baseline S/N {snr:.1f} < 3"))
        idx = d.index
        nt.loc[idx, "ubase"] = med
        nt.loc[idx, "floor"] = extra
        nt.loc[idx, "ubase_psf"] = a0 + slope * (d.maj - b.maj.median())
        nt.loc[idx, "exc_psf"] = d.ujy - (a0 + slope * (d.maj - b.maj.median()))
    print("per band/unit: baseline (|dt|>400 d) | PSF slope | event-era coverage | matched-PSF baseline")
    for key, v in sorted(st.items()):
        if "med" not in v:
            print(f"  {key}: baseline nights {v['n']} -> {v['why']}; event nights +-30 {v['n30']}, +-90 {v['n90']}")
            continue
        fl = "" if v["usable"] else f"   ** NOT USABLE: {v['why']}"
        print(f"  {key}: n {v['n']:4d} med {v['med']:7.1f} uJy ({ujy2ab(v['med']) if v['med'] > 0 else np.nan:.2f} AB) rob {v['rob']:6.1f} "
              f"S/N {v['snr']:5.1f} maj {v['maj_base']:.2f} | slope {v['slope']:+7.1f} +- {v['slope_e']:.1f} uJy/px | "
              f"+-30 d {v['n30']:2d}, +-90 d {v['n90']:2d} nights (maj {v['maj_ev']:.2f}) | matched n {v['n_matched']} med "
              f"{v['med_matched']:.1f} rob {v['rob_matched']:.1f}; line at event PSF {v['base_at_ev']:.1f}{fl}")
    nt["e2"] = np.hypot(nt.ujy_err, nt.floor)
    nt["sig_psf"] = nt.exc_psf / nt.e2
    ev = nt[nt.dt.abs() <= 120].sort_values("t").copy()
    ev["date"] = [mjd2date(x) for x in ev.t]
    print("nights within 120 d of t0:")
    if len(ev):
        print(ev[["date", "dt", "F", "cam", "n", "nraw", "ujy", "ujy_err", "ubase", "ubase_psf", "exc_psf", "sig_psf", "maj", "m5", "chi"]]
              .round(2).to_string(index=False))
    else:
        print("  NONE")
    summ[k] = dict(t0=t0, series=st, first_night=float(nt.t.min()), first_date=mjd2date(nt.t.min()),
                   n30=int((nt.dt.abs() <= 30).sum()), n90=int((nt.dt.abs() <= 90).sum()))
    print(f"coverage: first ATLAS night {mjd2date(nt.t.min())}; nights within +-30 d: {summ[k]['n30']}, +-90 d: {summ[k]['n90']}")
    nt.to_csv(os.path.join(DATA, f"a2_nightly_{k}.csv"), index=False)
json.dump(summ, open(os.path.join(DATA, "a2_summary.json"), "w"), indent=1, default=float)
