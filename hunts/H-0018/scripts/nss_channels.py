"""Which DR3 acceptance cut carries the handedness? Development split (HELD-OUT with --heldout, once frozen)."""
import argparse
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402
from nss_rv_test import load  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--heldout", action="store_true")
args = ap.parse_args()
d = load(args.heldout)
d = d[d.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])].copy()
d["m_plx"] = d.parallax / d.parallax_error * d.period / 20000
d["m_a0"] = d.significance * np.sqrt(d.period) / 158
d["sn_plx"] = d.parallax / d.parallax_error


def line(x, label):
    if len(x) < 40:
        return
    m = x.sense.mean()
    print(f"    {label:<14} N={len(x):6d} A={m:+.3f}±{np.sqrt((1 - m**2) / len(x)):.3f}")


for lo, hi in [(100, 300), (300, 450), (450, 600), (600, 900), (900, 3000)]:
    s = d[(d.period >= lo) & (d.period < hi)]
    print(f"P {lo}-{hi} N={len(s)} A={s.sense.mean():+.3f}  min m_plx={s.m_plx.min():.3f} min m_a0={s.m_a0.min():.3f}")
    print("   margin over parallax cut, (plx/err) / (20000/P)")
    for a, b in [(1, 1.2), (1.2, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 10), (10, 1e9)]:
        line(s[(s.m_plx >= a) & (s.m_plx < b)], f"[{a},{b:.3g})")
    print("   margin over a0 cut, significance / (158/sqrt P)")
    for a, b in [(1, 1.2), (1.2, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 10), (10, 1e9)]:
        line(s[(s.m_a0 >= a) & (s.m_a0 < b)], f"[{a},{b:.3g})")
    print("   median parallax_error, ratio +NEP / -NEP in G bins (Orbital only)")
    o = s[s.nss_solution_type == "Orbital"]
    for a, b in [(10, 12), (12, 13), (13, 14), (14, 15), (15, 16.5)]:
        x = o[(o.phot_g_mean_mag >= a) & (o.phot_g_mean_mag < b)]
        p, n = x[x.sense > 0], x[x.sense < 0]
        if min(len(p), len(n)) < 30:
            continue
        rng = np.random.default_rng(1)
        boots = [np.median(rng.choice(p.parallax_error.values, len(p))) / np.median(rng.choice(n.parallax_error.values, len(n))) for _ in range(200)]
        sn_p, sn_n = np.median(p.sn_plx), np.median(n.sn_plx)
        print(f"    G {a}-{b}: err ratio {np.median(p.parallax_error) / np.median(n.parallax_error):.3f} ± {np.std(boots):.3f};"
              f" plx ratio {np.median(p.parallax) / np.median(n.parallax):.3f}; S/N {sn_p:.0f} vs {sn_n:.0f}; signif {np.median(p.significance):.1f} vs {np.median(n.significance):.1f}; a0 {np.median(p.a0):.3f} vs {np.median(n.a0):.3f}; N {len(p)} {len(n)}")
    print("   RV amplitude / 2 K_pred, G_RVS stars with >=8 transits (Orbital)")
    r = o[o.rv_amplitude_robust.notna() & (o.rv_nb_transits >= 8) & (o.kpred > 5)]
    p, n = r[r.sense > 0], r[r.sense < 0]
    if min(len(p), len(n)) > 30:
        print(f"    +NEP N={len(p)} median {np.median(p.rv_amplitude_robust / (2 * p.kpred)):.3f}   -NEP N={len(n)} median {np.median(n.rv_amplitude_robust / (2 * n.kpred)):.3f}")
