"""What does a real blind cascade (gaiamock) say? A, parallax-error ratio and the channel, for fitted solutions, against DR3 data."""
import glob
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

name, ref = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None
d = pd.concat([pd.read_parquet(f) for f in glob.glob(f"{hd.RUNS}/{name}.parquet.parts/batch_*.parquet")], ignore_index=True)
print(name, "fits", len(d), "stars", d.groupby(["plx_true", "G_mag"]).ngroups, d.kind.value_counts().to_dict())
o = d[d.kind == 12].copy()
o["c_plx"] = o.plx / o.s_plx > 20000 / o.P_fit
o["c_a0"] = (o.a0_fit / o.s_a0 > 158 / np.sqrt(o.P_fit)) & (o.a0_fit / o.s_a0 > 5)
o["c_e"] = o.s_e < 0.079 * np.log(o.P_fit) - 0.244
o["c_f2"] = o.F2 < 25
o["acc"] = o.c_plx & o.c_a0 & o.c_e & o.c_f2
o["nop"] = o.c_a0 & o.c_e & o.c_f2
o["recovered"] = np.abs(o.P_fit / o.P - 1) < 0.1
print(f"orbit fits {len(o)}, accepted {o.acc.sum()}; fitted sense = true sense {np.mean(o[o.acc].sense_fit == o[o.acc].sense_true):.3f}; period within 10% {o[o.acc].recovered.mean():.3f}")


def asym(s):
    m = s.mean() if len(s) else np.nan
    return m, np.sqrt((1 - m**2) / max(len(s), 1))


def ratio(x, lo, hi, emin=0, emax=2):
    x = x[(x.P_fit >= lo) & (x.P_fit < hi) & (x.e_fit >= emin) & (x.e_fit < emax)]
    v, w = [], []
    for g in range(12, 16):
        s = x[(x.G_mag >= g) & (x.G_mag < g + 1)]
        p, m = s[s.sense_fit > 0].s_plx, s[s.sense_fit < 0].s_plx
        if min(len(p), len(m)) >= 10:
            v.append(np.median(p) / np.median(m))
            w.append(len(p) + len(m))
    return float(np.average(v, weights=w)) if v else float("nan")


edges = [50, 100, 150, 200, 250, 300, 340, 390, 450, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1600, 3000]
a = o[o.acc]
rows = []
for lo, hi in zip(edges[:-1], edges[1:]):
    s, n = a[(a.P_fit >= lo) & (a.P_fit < hi)], o[o.nop & (o.P_fit >= lo) & (o.P_fit < hi)]
    Aa, Ae = asym(s.sense_fit)
    An, _ = asym(n.sense_fit)
    rows.append(dict(lo=lo, hi=hi, N=len(s), A=Aa, A_se=Ae, A_no_plx_cut=An, ratio=ratio(a, lo, hi)))
t = pd.DataFrame(rows)
if ref:
    h = pd.read_csv(ref)
    t["A_data"], t["ratio_data"] = h.A.values, h.ratio.values
pd.set_option("display.width", 200)
print(t.round(3).to_string(index=False))
if ref:
    ok = t.ratio.notna()
    print(f"against held-out data: A Spearman {stats.spearmanr(t.A, t.A_data).statistic:.3f}; ratio Pearson {np.corrcoef(t.ratio[ok], t.ratio_data[ok])[0, 1]:.3f}, median |diff| {np.median(np.abs(t.ratio[ok] - t.ratio_data[ok])):.3f}")
    w = t.N / t.N.sum()
    print(f"overall A: cascade {asym(a.sense_fit)[0]:+.4f} ± {asym(a.sense_fit)[1]:.4f}, without the parallax cut {asym(o[o.nop].sense_fit)[0]:+.4f}")

print("\nby TRUE period, what becomes of mirror pairs: share of each outcome by true sense, and A at each stage (all draws)")
for lo, hi in [(100, 300), (300, 450), (450, 600), (600, 900), (900, 1100), (1100, 1600), (1600, 3000)]:
    s = d[(d.P >= lo) & (d.P < hi)]
    line = []
    for label, m in [("past RUWE", s.kind != -1), ("7/9-par", s.kind.isin([-7, -9])), ("orbit fit", s.kind == 12)]:
        x = s[m]
        line.append(f"{label} N={len(x)} A={asym(x.sense_true)[0]:+.3f}±{asym(x.sense_true)[1]:.3f}")
    print(f"  {lo}-{hi}: " + "; ".join(line))

print("\nfitted orbits by TRUE period, accepted: A with true sense, and share with fitted period wrong by over 10%")
for lo, hi in [(100, 300), (300, 450), (450, 600), (600, 900), (900, 1100), (1100, 1600), (1600, 3000)]:
    s = a[(a.P >= lo) & (a.P < hi)]
    print(f"  {lo}-{hi}: N={len(s)} A(true)={asym(s.sense_true)[0]:+.3f} wrong P {1 - s.recovered.mean():.3f}")

print("\nby eccentricity, fitted, 700-800 d; and by margin, 600-900 d, sense-blind")
print("  ratio e<0.2, 0.2-0.4, 0.4-0.6, >=0.6:", [round(ratio(a, 700, 800, x, y), 3) for x, y in [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 2)]])
z = a[(a.P_fit >= 600) & (a.P_fit < 900)].copy()
ref_s = z[z.sense_fit < 0].groupby(pd.cut(z[z.sense_fit < 0].G_mag, np.arange(5, 19)), observed=True).s_plx.median()
z["m"] = z.plx / pd.cut(z.G_mag, np.arange(5, 19)).map(ref_s).astype(float) * z.P_fit / 20000
print("  A by margin:", [(l, round(asym(z[(z.m >= l) & (z.m < h_)].sense_fit)[0], 3), int(((z.m >= l) & (z.m < h_)).sum())) for l, h_ in [(0, 1.5), (1.5, 2.5), (2.5, 5), (5, 10), (10, 1e9)]])
if "dr4" in name:
    r = {b: ratio(a, *b) for b in [(340, 390), (600, 700), (700, 800), (800, 900), (1100, 1600)]}
    print("\nForecast statistics, DR3 cuts:", {f"{k[0]}-{k[1]}": round(v, 3) for k, v in r.items()}, "contrast", round(r[(700, 800)] - 0.5 * (r[(600, 700)] + r[(800, 900)]), 3),
          "e<0.2 minus e>=0.4", round(ratio(a, 700, 800, 0, 0.2) - ratio(a, 700, 800, 0.4, 2), 3), "A(340-390)", np.round(asym(a[a.P_fit.between(340, 390)].sense_fit), 3))
    loose = o[(o.a0_fit / o.s_a0 > 15) & (o.plx / o.s_plx > 5) & o.c_f2]
    r = {b: ratio(loose, *b) for b in [(340, 390), (600, 700), (700, 800), (800, 900), (1100, 1600)]}
    print("Same, looser cuts (a0/err > 15, plx/err > 5):", {f"{k[0]}-{k[1]}": round(v, 3) for k, v in r.items()}, "A(340-390)", np.round(asym(loose[loose.P_fit.between(340, 390)].sense_fit), 3))
