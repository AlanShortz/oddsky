"""H-0016: per-epoch AllWISE 2010-11 medians from the multi-epoch table, quality-cut like NEOWISE (qi_fact>0, saa_sep>0,
moon_masked 00, cc_flags 00 in W1/W2, nb=1), compared with the NEOWISE baseline and 2MASS K.
usage: mep_epochs.py STEPS_CSV MEP_CSV OUT_CSV"""
import sys

import numpy as np
import pandas as pd

s = pd.read_csv(sys.argv[1])
m = pd.read_csv(sys.argv[2])
m["cc"] = m.cc_flags.fillna("0000").astype(str).str.zfill(4)
m["mm"] = m.moon_masked.fillna("0000").astype(str).str.zfill(4)
ok = (m.qi_fact > 0) & (m.saa_sep > 0) & (m.mm.str[:2] == "00") & (m.cc.str[:2] == "00") & (m.nb.fillna(1) == 1)
m = m[ok].sort_values(["cntr_mf", "mjd"])
rows = []
for cntr, g in m.groupby("cntr_mf"):
    gap = np.r_[True, np.diff(g.mjd.to_numpy()) > 30]
    g = g.assign(ep=np.cumsum(gap))
    eps = []
    for _e, h in g.groupby("ep"):
        w1 = h.w1mpro_ep.dropna()
        w2 = h.w2mpro_ep.dropna()
        eps.append(dict(t=float(h.mjd.median()), n1=len(w1), w1=float(w1.median()) if len(w1) else np.nan, w1s=float(1.4826 * (w1 - w1.median()).abs().median()) if len(w1) else np.nan,
                        n2=len(w2), w2=float(w2.median()) if len(w2) else np.nan, w2s=float(1.4826 * (w2 - w2.median()).abs().median()) if len(w2) else np.nan))
    rec = dict(allwise_cntr=cntr, n_ep=len(eps), n_frames=len(g))
    for k, e in enumerate(eps[:4]):
        for key, v in e.items():
            rec[f"ep{k}_{key}"] = v
    w1s = [e["w1"] for e in eps if np.isfinite(e["w1"])]
    w2s = [e["w2"] for e in eps if np.isfinite(e["w2"])]
    rec["mep_w1_min"], rec["mep_w1_max"] = (min(w1s), max(w1s)) if w1s else (np.nan, np.nan)
    rec["mep_w2_min"], rec["mep_w2_max"] = (min(w2s), max(w2s)) if w2s else (np.nan, np.nan)
    rows.append(rec)
e = pd.DataFrame(rows)
x = s.merge(e, on="allwise_cntr", how="left")
x["mep_ptp_w1"] = x.mep_w1_max - x.mep_w1_min
# does every 2010 epoch sit on the AllWISE catalogue side of the step (>= 60% of the way from NEOWISE to AllWISE)?
x["step_frac_min"] = (x.w1_base - x.mep_w1_max) / (x.w1_base - x.w1mpro_allwise)
x["step_frac_max"] = (x.w1_base - x.mep_w1_min) / (x.w1_base - x.w1mpro_allwise)
x["mep_verdict"] = np.select([x.n_ep.isna(), x.n_ep < 2, (x[["step_frac_min", "step_frac_max"]].min(axis=1) > 0.6), (x[["step_frac_min", "step_frac_max"]].max(axis=1) < 0.4)],
                             ["no_mep", "one_epoch", "all_2010_epochs_off", "2010_frames_agree_with_neowise"], "mixed_2010")
x.to_csv(sys.argv[3], index=False)
print(pd.crosstab([x.direction, x.nflags == 0], x.mep_verdict))
c = x[(x.nflags == 0)]
cols = ["designation", "direction", "epoch3", "w1mpro_allwise", "w1_base", "k_m_2mass", "d1", "d2", "n_ep", "ep0_t", "ep0_w1", "ep0_n1", "ep1_t", "ep1_w1", "ep1_n1", "ep2_w1", "mep_ptp_w1", "mep_verdict"]
pd.set_option("display.width", 250)
print(c[cols].sort_values("d1").to_string())
