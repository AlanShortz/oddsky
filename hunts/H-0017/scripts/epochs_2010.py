"""H-0017: were the nuclei already changing during 2010-11? Per-epoch medians from the AllWISE Multiepoch Photometry Table
(frames grouped into visits separated by more than 60 days; qi_fact > 0, saa_sep > 0, both bands measured), and the change
between the first and the last AllWISE visit, next to the change across the gap.
usage: epochs_2010.py NUCLEI_CSV(allwise_cntr, designation, side) MEP_CSV FEATURES_CSV OUT_CSV"""
import sys

import numpy as np
import pandas as pd

n = pd.read_csv(sys.argv[1])
m = pd.read_csv(sys.argv[2])
f = pd.read_csv(sys.argv[3])
missing = set(n.allwise_cntr) - set(m.cntr_mf)
print(len(n), "nuclei;", len(missing), "with no multi-epoch rows")
m = m[(m.qi_fact > 0) & (m.saa_sep > 0) & m.w1sigmpro_ep.notna() & m.w2sigmpro_ep.notna()]
rows = []
for cntr, g in m.sort_values("mjd").groupby("cntr_mf"):
    ep = (g.mjd.diff() > 60).cumsum()
    e = g.groupby(ep).agg(t=("mjd", "median"), n=("mjd", "size"), w1=("w1mpro_ep", "median"), w2=("w2mpro_ep", "median"),
                          s1=("w1mpro_ep", lambda v: 1.4826 * (v - v.median()).abs().median() / np.sqrt(len(v))),
                          s2=("w2mpro_ep", lambda v: 1.4826 * (v - v.median()).abs().median() / np.sqrt(len(v))))
    e = e[e.n >= 5]
    if len(e) < 2:
        rows.append(dict(allwise_cntr=cntr, n_ep=len(e)))
        continue
    a, b = e.iloc[0], e.iloc[-1]
    rows.append(dict(allwise_cntr=cntr, n_ep=len(e), dt_days=b.t - a.t, t0=a.t, t1=b.t, w1_0=a.w1, w1_1=b.w1, w2_0=a.w2, w2_1=b.w2,
                     dw1_2010=b.w1 - a.w1, dw2_2010=b.w2 - a.w2, e_dw1=np.hypot(a.s1, b.s1), e_dw2=np.hypot(a.s2, b.s2)))
o = n.merge(pd.DataFrame(rows), on="allwise_cntr", how="left").merge(f, on="allwise_cntr", how="left")
o["dcolor_2010"] = o.dw1_2010 - o.dw2_2010
o["sig_dw2"] = o.dw2_2010 / o.e_dw2.clip(lower=0.02)
o.to_csv(sys.argv[4], index=False)
for side, g in o.groupby("side"):
    k = g[g.n_ep >= 2]
    print(f"{side}: {len(g)} nuclei, {len(k)} with two or more AllWISE visits (median {k.dt_days.median():.0f} d apart)")
    print(f"  W2 change within 2010-11: median {k.dw2_2010.median():+.3f} mag; fading by > 3 sigma and > 0.1 mag: "
          f"{int(((k.sig_dw2 > 3) & (k.dw2_2010 > 0.1)).sum())}; brightening likewise: {int(((k.sig_dw2 < -3) & (k.dw2_2010 < -0.1)).sum())}")
    print(f"  W1 change: median {k.dw1_2010.median():+.3f}; colour (W1-W2) change: median {k.dcolor_2010.median():+.3f}")
