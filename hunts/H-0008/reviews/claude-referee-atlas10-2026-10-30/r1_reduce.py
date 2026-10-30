"""r1: re-reduce the seven ATLAS light curves. Per target:
 - what the cuts remove (overall, and within 60 d of the event),
 - per (band, unit) baseline (>400 d from the peak) median flux, scatter, PSF width; yearly medians (zero-point / PSF steps),
 - the event: brightest nightly points, and every frame of the brightest nights (mag5sig, chi/N, x, y, maj, min, sky, apfit),
 - c vs o at the peak.
Writes data/r1_nightly_<k>.csv (clean nightly table, chi 'rel').
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, atlas_raw, clean, mjd2date, nightly, targets  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
T = targets()


def find_peak(nt, tvis):
    """Brightest o-band 3-night rolling median (relative to the unit's median) within 200 d of the NEOWISE visit."""
    nt = nt.copy()
    nt["rel"] = nt.ujy - nt.groupby(["F", "cam"]).ujy.transform("median")
    nt["rel"] /= nt.groupby(["F", "cam"]).ujy_err.transform("median")
    o = nt[(nt.F == "o") & (np.abs(nt.t - tvis) < 200)].sort_values("t")
    sm = o.rel.rolling(3, center=True, min_periods=1).median()
    return float(o.t.iloc[int(np.argmax(sm.values))])


for k, t in T.items():
    print("=" * 110)
    print(k, t["name"], f"G={t['G']:.2f} BP-RP={t['bprp']:.2f} l={t['l']:.2f} b={t['b']:.2f} NEOWISE visit {mjd2date(t['tvis'])}"
          f" dW1={t['dw1']:.2f} dW2={t['dw2']:.2f}")
    raw = atlas_raw(k)
    c = clean(raw, chi_mode="rel")
    nt = nightly(c)
    tpk = find_peak(nt, t["tvis"])
    print(f"peak (o, rolling) {tpk:.1f} = {mjd2date(tpk)}")
    near = np.abs(raw.mjd - tpk) < 60
    for mode in ("rel", "abs", "none"):
        cc = clean(raw, chi_mode=mode)
        nn = np.abs(cc.mjd - tpk) < 60
        print(f"  chi {mode:4s}: kept {len(cc)}/{len(raw)} overall; within 60 d {nn.sum()}/{near.sum()}")
    bm = raw[near]
    print(f"  near-peak rows failing: err!=0 {int((bm.err != 0).sum())}, dujy<=0 {int((bm.dujy <= 0).sum())}, "
          f"m5<17.5 {int((bm.mag5sig <= 17.5).sum())}, chi/N>=10 {int((bm.chi_n >= 10).sum())}")
    nt.to_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"), index=False)
    # baseline
    nt["base"] = np.abs(nt.t - tpk) > 400
    rows = []
    for (F, cam), d in nt.groupby(["F", "cam"]):
        b = d[d.base]
        if len(b) < 3:
            rows.append((F, cam, len(d), len(b), np.nan, np.nan, np.nan, np.nan, (np.abs(d.t - tpk) < 60).sum()))
            continue
        med = np.median(b.ujy)
        rob = 1.4826 * np.median(np.abs(b.ujy - med))
        rows.append((F, cam, len(d), len(b), med, rob, np.median(b.ujy_err), np.median(b.maj), (np.abs(d.t - tpk) < 60).sum()))
    print(pd.DataFrame(rows, columns=["F", "cam", "nights", "nbase", "base_ujy", "rob_sd", "med_err", "maj", "n<60d"]).round(1)
          .to_string(index=False))
    # yearly medians per unit, o and c (steps)
    nt["yr"] = np.floor(2000 + (nt.t - 51544.5) / 365.25).astype(int)
    y = nt[nt.base].groupby(["F", "cam", "yr"]).agg(ujy=("ujy", "median"), maj=("maj", "median"), n=("ujy", "size"))
    y = y[y.n >= 5]
    print("  yearly baseline medians (uJy / PSF major px):")
    for (F, cam), d in y.groupby(level=[0, 1]):
        print(f"   {F} {cam}: " + "  ".join(f"{yr}:{r.ujy:.0f}/{r.maj:.2f}" for (_, _, yr), r in d.iterrows()))
    # event
    ev = nt[np.abs(nt.t - tpk) < 120].copy()
    ev["bmed"] = ev.groupby(["F", "cam"]).ujy.transform(lambda s: 0) + ev.apply(
        lambda r: np.median(nt[(nt.F == r.F) & (nt.cam == r.cam) & nt.base].ujy) if ((nt.F == r.F) & (nt.cam == r.cam)
                                                                                      & nt.base).sum() else np.nan, axis=1)
    ev["exc"] = ev.ujy - ev.bmed
    ev["snr"] = ev.exc / ev.ujy_err
    ev["date"] = [mjd2date(x) for x in ev.t]
    print("  nights within 120 d of the peak (excess = nightly - baseline median, uJy):")
    print(ev.sort_values("t")[["date", "t", "F", "cam", "n", "nraw", "ujy", "ujy_err", "bmed", "exc", "snr", "maj", "mnr", "m5",
                               "chi", "sky"]].round(2).to_string(index=False))
    # frames of the 3 brightest nights (by S/N excess)
    top = ev.sort_values("snr", ascending=False).head(3)
    print("  frames on the 3 most significant nights (all frames, no cuts):")
    for _, r in top.iterrows():
        fr = raw[(raw.night == r.night) & (raw.cam == r.cam)]
        print(f"   night {r.night} {r.date} unit {r.cam}: {len(fr)} frames in all bands")
        print(fr[["mjd", "F", "ujy", "dujy", "err", "chi_n", "x", "y", "maj", "min", "phi", "apfit", "mag5sig", "sky", "obs"]]
              .to_string(index=False))
    # other units same night +-1
    for _, r in top.head(1).iterrows():
        fr = raw[(np.abs(raw.mjd - r.t) < 2.0)]
        print(f"   all frames within +-2 d of the most significant night ({r.date}), any unit:")
        print(fr[["mjd", "F", "ujy", "dujy", "chi_n", "x", "y", "maj", "min", "mag5sig", "sky", "obs"]].to_string(index=False))
