"""(e): data-side tests of the sense statistic."""
import numpy as np
import pandas as pd

d = pd.read_pickle("/tmp/repro_h18/d.pkl")
A, B, F, G = d.a_thiele_innes.values, d.b_thiele_innes.values, d.f_thiele_innes.values, d.g_thiele_innes.values
u = 0.5 * (A**2 + B**2 + F**2 + G**2)
v = A * G - B * F
a2 = u + np.sqrt(u**2 - v**2)
d["a0"] = np.sqrt(a2)
d["cosi"] = v / a2
det = B * F - A * G
sdet = np.sqrt((F * d.b_thiele_innes_error) ** 2 + (B * d.f_thiele_innes_error) ** 2 + (G * d.a_thiele_innes_error) ** 2 + (A * d.g_thiele_innes_error) ** 2).values
d["detsnr"] = np.abs(det) / sdet
d["poe"] = d.parallax / d.parallax_error
d["poe_margin"] = d.poe * d.period / 20000
d["sig_margin"] = d.significance * np.sqrt(d.period) / 158
d["beta_abs"] = d.ecl_lat.abs()

def me(x):
    m = x.mean(); return f"{m:+.4f}+-{np.sqrt((1-m*m)/len(x)):.4f} (N={len(x)})"

print("cut sharpness: quantiles of poe*P/20000 and significance*sqrt(P)/158")
for t in ["Orbital", "AstroSpectroSB1"]:
    g = d[d.nss_solution_type == t]
    print(t, "poe_margin min/q0.1%/q1%/q50:", np.round(np.nanquantile(g.poe_margin, [0, 0.001, 0.01, 0.5]), 3), "frac<1:", (g.poe_margin < 1).mean(),
          "| sig_margin min/q0.1%/q1%/q50:", np.round(np.nanquantile(g.sig_margin.dropna(), [0, 0.001, 0.01, 0.5]), 3), "frac<1", (g.sig_margin < 1).mean())

o = d[d.nss_solution_type == "Orbital"]
print("\nA vs parallax-cut margin, Orbital (poe*P/20000), P in [300,1100)")
g = o[(o.period >= 300) & (o.period < 1100)]
for lo, hi in [(0, 1.2), (1.2, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 10), (10, 1e9)]:
    k = g[(g.poe_margin >= lo) & (g.poe_margin < hi)]
    print(f"  [{lo},{hi}) {me(k.sense)}")
print("A vs significance margin, Orbital, P in [300,1100)")
for lo, hi in [(0, 1.1), (1.1, 1.3), (1.3, 1.6), (1.6, 2), (2, 3), (3, 1e9)]:
    k = g[(g.sig_margin >= lo) & (g.sig_margin < hi)]
    print(f"  [{lo},{hi}) {me(k.sense)}")
print("A vs det SNR, all")
for lo, hi in [(0, 1), (1, 3), (3, 5), (5, 10), (10, 30), (30, 1e9)]:
    k = d[(d.detsnr >= lo) & (d.detsnr < hi)]
    print(f"  [{lo},{hi}) {me(k.sense)}")
print("A vs |cos i|")
for lo, hi in np.array([(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, .9), (.9, 1.0001)]):
    k = d[(d.cosi.abs() >= lo) & (d.cosi.abs() < hi)]
    print(f"  [{lo:.1f},{hi:.1f}) {me(k.sense)}")
print("A vs |beta| band")
for lo, hi in [(0, 5), (5, 15), (15, 30), (30, 45), (45, 60), (60, 90)]:
    k = d[(d.beta_abs >= lo) & (d.beta_abs < hi)]
    print(f"  [{lo},{hi}) {me(k.sense)}   N-only {me(k[k.ecl_lat>0].sense)}  S-only {me(k[k.ecl_lat<0].sense)}")
print("A vs G, Orbital")
for lo, hi in [(0, 10), (10, 11), (11, 12), (12, 13), (13, 14), (14, 15), (15, 16), (16, 25)]:
    k = o[(o.phot_g_mean_mag >= lo) & (o.phot_g_mean_mag < hi)]
    if len(k):
        print(f"  [{lo},{hi}) {me(k.sense)}")
print("A vs fine period around 1/2 yr and 1/4 yr, 1 yr, 2 yr")
for lo, hi in [(80, 88), (88, 95), (95, 110), (160, 172), (172, 178), (178, 188), (188, 200), (345, 355), (355, 375), (375, 390), (690, 720), (720, 745), (745, 780)]:
    k = d[(d.period >= lo) & (d.period < hi)]
    print(f"  [{lo},{hi}) {me(k.sense)}")

print("\nby sense medians per P bin, Orbital: ruwe+/-, significance+/-, poe+/-, a0+/-, a0*(mas)/parallax+/-, gof+/-, parallax+/-, ecc+/-")
BINS = [100, 200, 300, 340, 390, 450, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1600, 3000]
o = d[(d.nss_solution_type == "Orbital")].copy()
o["pb2"] = pd.cut(o.period, BINS, right=False)
for b, g in o.groupby("pb2", observed=False):
    p, q = g[g.sense > 0], g[g.sense < 0]
    print(f"  {str(b):14s} n+/n-={len(p)/len(q):.3f} "
          + " ".join(f"{c}={np.nanmedian(p[c])/np.nanmedian(q[c]):.3f}" for c in ["ruwe", "significance", "parallax", "a0", "goodness_of_fit", "eccentricity", "parallax_error", "phot_g_mean_mag", "period_error"]))

print("\nfixed-G (13-14), Orbital, P[600,800): counts by parallax decile, sense asymmetry")
g = o[(o.period >= 600) & (o.period < 800) & (o.phot_g_mean_mag >= 13) & (o.phot_g_mean_mag < 14)]
g = g.assign(pd_=pd.qcut(g.parallax, 5))
for b, h in g.groupby("pd_", observed=True):
    print(f"  plx {str(b):22s} {me(h.sense)}  err_ratio={np.median(h.parallax_error[h.sense>0])/np.median(h.parallax_error[h.sense<0]):.3f}")

print("\nsense asymmetry and parallax_error ratio vs |beta|, Orbital 12<=G<16, P in [600,800) (parallax_error normalised to G bin)")
g = o[(o.period >= 600) & (o.period < 800) & (o.phot_g_mean_mag >= 12) & (o.phot_g_mean_mag < 16)]
for lo, hi in [(0, 15), (15, 30), (30, 45), (45, 60), (60, 90)]:
    h = g[(g.beta_abs >= lo) & (g.beta_abs < hi)]
    print(f"  [{lo},{hi}) {me(h.sense)}  err_ratio={np.median(h.parallax_error[h.sense>0])/np.median(h.parallax_error[h.sense<0]):.3f}")

print("\nflags bits vs A")
print(d.groupby("flags").sense.agg(["mean", "size"]).sort_values("size", ascending=False).head(8).to_string())

print("\nparallax-leak test, P in [340,390): |cos i| vs |sin beta| correlation by sense")
g = d[(d.period >= 340) & (d.period < 390)]
sb = np.abs(np.sin(np.radians(g.ecl_lat)))
for sg in [1, -1]:
    k = g.sense == sg
    print(f"  sense={sg:+d} N={k.sum()} corr(|cos i|,|sin beta|)={np.corrcoef(g.cosi.abs()[k], sb[k])[0,1]:+.3f}")
