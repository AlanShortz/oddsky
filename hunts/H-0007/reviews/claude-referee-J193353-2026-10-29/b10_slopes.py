"""b10: empirical null for within-visit slopes: W1/W2 slopes in each baseline visit (same cuts as the event visit), and the slope a
point lens with the b7 best fit predicts across Apr 9-10. Outside the Oddsky tools (pandas/numpy)."""
import numpy as np
import pandas as pd

t = pd.read_parquet("/tmp/j1933ref/target_exp.parquet")
t = t[(t.nb == 1) & (t.qual_frame > 0)]
out = []
for v, g in t.groupby("visit"):
    g = g[g.mjd < g.mjd.min() + 1.2]  # core day of each visit only
    if len(g) < 6:
        continue
    s1 = np.polyfit(g.mjd - g.mjd.mean(), g.w1mpro, 1)[0]
    s2 = np.polyfit(g.mjd - g.mjd.mean(), g.w2mpro, 1)[0]
    out.append(dict(visit=v, n=len(g), s1=s1, s2=s2))
o = pd.DataFrame(out)
print(o.round(3).to_string())
b = o[o.visit != 11]
print(f"baseline visits: W1 slope rms {b.s1.std():.3f} mag/d, max |s1| {b.s1.abs().max():.3f}; event W1 {o[o.visit == 11].s1.iloc[0]:+.3f}"
      f" -> {o[o.visit == 11].s1.iloc[0] / b.s1.std():.1f} sigma; W2 rms {b.s2.std():.3f}")
A = lambda u: (u * u + 2) / (u * np.sqrt(u * u + 4))
for t0, tE, u0 in [(58949.5, 55.6, 0.575), (58930.4, 41.5, 0.337), (58920, 61.3, 0.305)]:
    m = -2.5 * np.log10(A(np.hypot(u0, (np.array([58948.9, 58949.9]) - t0) / tE)))
    print(f"PSPL t0={t0} tE={tE} u0={u0}: model slope over the visit {m[1]-m[0]:+.3f} mag/d")
