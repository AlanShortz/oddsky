"""Handedness predicted by the forward model, as A = (N_plus - N_minus) / (N_plus + N_minus), by cut and by period."""
import sys

import numpy as np
import pandas as pd

d = pd.read_parquet(sys.argv[1])
edges = [30, 100, 150, 200, 250, 300, 340, 390, 450, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1600, 3000]


def a(p, m):
    np_, nm = p.sum(), m.sum()
    return (np_ - nm) / max(np_ + nm, 1), np_ + nm


rows = []
for lo, hi in zip(edges[:-1], edges[1:]):
    s = d[(d.P >= lo) & (d.P < hi)]
    r = [a(s.pass_ruwe_plus, s.pass_ruwe_minus)[0], a(s.pass_a0_plus, s.pass_a0_minus)[0], a(s.pass_plx_plus, s.pass_plx_minus)[0], *a(s.acc_plus, s.acc_minus)]
    acc = s[s.acc_plus | s.acc_minus]
    ratio = np.nanmedian(s.s_plx_plus) / np.nanmedian(s.s_plx_minus)
    ratio = (ratio, np.nanmedian(acc.s_plx_plus) / np.nanmedian(acc.s_plx_minus), a(s.pass_e_plus, s.pass_e_minus)[0])
    rows.append((lo, hi, *r, ratio))
print("P range      A(RUWE)  A(a0)   A(plx)   A(all)  N_acc  sig_plx(+)/sig_plx(-) all, accepted; A(e cut)")
for x in rows:
    print(f"{x[0]:>5}-{x[1]:<5} {x[2]:+.3f}  {x[3]:+.3f}  {x[4]:+.3f}  {x[5]:+.3f} {int(x[6]):>7}  {x[7][0]:.3f} {x[7][1]:.3f}  {x[7][2]:+.3f}")
print("overall", a(d.acc_plus, d.acc_minus))


def tab(name, col, edges, x=d):
    print(f"\nby {name}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = x[(x[col] >= lo) & (x[col] < hi)]
        A, n = a(s.acc_plus, s.acc_minus)
        print(f"  {lo:>7.3g} - {hi:<7.3g} A={A:+.3f}  N={int(n)}")


w = d[(d.P > 300) & (d.P < 900)]
tab("parallax (300<P<900)", "plx", [0, 0.5, 1, 1.5, 2, 3, 5, 10, 20, 50, 1000], w)
tab("G (300<P<900)", "G", [0, 10, 11, 12, 13, 14, 15, 16, 17, 18, 22], w)
tab("ecc (300<P<900)", "ecc", [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1], w)
tab("|cos i| (300<P<900)", "ac", np.linspace(0, 1, 11), w.assign(ac=np.abs(w.cosi)))
tab("|sin beta| (300<P<900)", "asb", np.linspace(0, 1, 11), w.assign(asb=np.abs(np.sin(np.radians(w.beta)))))
