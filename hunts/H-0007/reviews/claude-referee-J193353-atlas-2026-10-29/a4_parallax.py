"""a4: annual-parallax point-lens fits (MulensModel, Earth-based; NEOWISE treated as geocentric) to the a3 joint set
(/tmp/j1933atl/joint.csv), plus an empirical asymmetric Paczynski (separate tE before/after t0) for comparison.
Outside the Oddsky tools. usage: uv run --with MulensModel python a4_parallax.py"""
import warnings
import numpy as np
import pandas as pd
import MulensModel as mm
from scipy.optimize import least_squares

warnings.filterwarnings("ignore")
D = pd.read_csv("/tmp/j1933atl/joint.csv")
COORDS = "19:33:53.067 -21:18:13.49"
TP = 58925.0
groups = {"ATLAS": ["Ac", "Ao"], "WISE": ["W1", "W2"], "ZTF": ["Zg", "Zr"]}
gi = np.zeros(len(D), int)
for k, g in enumerate(groups.values()):
    gi[D.band.isin(g).values] = k
tt, ff, ee = D.mjd.values + 2400000.5, D.f.values, D.e.values


def mag_par(p):
    t0, u0, tE, pn, pe = p
    m = mm.Model({"t_0": t0 + 2400000.5, "u_0": u0, "t_E": tE, "pi_E_N": pn, "pi_E_E": pe, "t_0_par": TP + 2400000.5}, coords=COORDS)
    return m.get_magnification(tt)


def run(blend, par, starts):
    best = None
    for s in starts:
        def res(p):
            q = p[:5] if par else list(p[:3]) + [0, 0]
            a = mag_par(q) if par else mag_par(list(p[:3]) + [0.0, 0.0])
            fs = p[5 if par else 3:] if blend else np.ones(3)
            return (fs[gi] * a + 1 - fs[gi] - ff) / ee
        p0 = list(s[:5] if par else s[:3]) + ([0.8] * 3 if blend else [])
        lo = [58880, -3, 5] + ([-5, -5] if par else []) + ([0.02] * 3 if blend else [])
        hi = [58960, 3, 600] + ([5, 5] if par else []) + ([1.05] * 3 if blend else [])
        try:
            r = least_squares(res, p0, bounds=(lo, hi), x_scale="jac")
        except Exception as ex:
            continue
        if best is None or r.cost < best.cost:
            best = r
    return best


def report(lab, r, par, blend):
    p = r.x
    q = list(p[:5]) if par else list(p[:3]) + [0, 0]
    a = mag_par(q)
    fs = p[5 if par else 3:] if blend else np.ones(3)
    mod = fs[gi] * a + 1 - fs[gi]
    res = ff - mod
    npar = len(p)
    am = mag_par(q)  # not used
    print(f"\n[{lab}] chi2 {2 * r.cost:.0f}/{len(D) - npar}  t0 {q[0]:.1f}  u0 {q[1]:+.3f}  tE {q[2]:.1f}  piEN {q[3]:+.3f}  piEE {q[4]:+.3f}"
          f"  |piE| {np.hypot(q[3], q[4]):.3f}  fs {np.round(fs, 3)}")
    for wl, w0, w1 in [("2019 Sep 15-Nov 15", 58741, 58803), ("2020 Mar 11", 58919, 58920), ("Apr 8-12", 58946, 58952),
                       ("Jun 10-30", 59010, 59031), ("Jul", 59031, 59062), ("Aug-Sep", 59062, 59123), ("Oct", 59123, 59154)]:
        s = (D.mjd > w0) & (D.mjd < w1)
        print(f"   {wl}: " + ", ".join(f"{b} {res[s & (D.band == b)].mean():+.3f}" for b in sorted(D[s].band.unique())))
    # observed-flux peak (ATLAS fs) on a fine grid
    g = np.arange(58880, 58980, 0.5) + 2400000.5
    m = mm.Model({"t_0": q[0] + 2400000.5, "u_0": q[1], "t_E": q[2], "pi_E_N": q[3], "pi_E_E": q[4], "t_0_par": TP + 2400000.5}, coords=COORDS) \
        if par else mm.Model({"t_0": q[0] + 2400000.5, "u_0": q[1], "t_E": q[2]})
    A = m.get_magnification(g)
    F = fs[0] * A + 1 - fs[0]
    k = F.argmax()
    print(f"   ATLAS observed-flux peak x{F[k]:.2f} on MJD {g[k] - 2400000.5:.1f}; source A_max {A.max():.2f}; "
          f"Gaia transits Feb 28/Mar 12/Apr 17: " + ", ".join(f"{-2.5 * np.log10(fs[0] * mm_ + 1 - fs[0]):+.2f}" for mm_ in
                                                             m.get_magnification(np.array([58907.5, 58920.5, 58956.5]) + 2400000.5)))
    return 2 * r.cost


starts = [(58926, su * u0, tE, pn, pe) for su in (1, -1) for u0 in (0.2, 0.45) for tE in (60, 90) for pn, pe in ((0, 0), (0.5, 0.5), (-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5))]
c_static = report("static, fs=1", run(False, False, [(58926, 0.43, 63, 0, 0)]), False, False)
c_staticb = report("static, fs free", run(True, False, [(58926, 0.43, 63, 0, 0), (58928, 0.2, 90, 0, 0)]), False, True)
c_par = report("parallax, fs=1", run(False, True, starts), True, False)
c_parb = report("parallax, fs free", run(True, True, starts), True, True)


# empirical asymmetric Paczynski: tE_rise before t0, tE_fall after, fs=1
def Aasym(t, t0, u0, t1, t2):
    tE = np.where(t < t0, t1, t2)
    u = np.sqrt(u0 ** 2 + ((t - t0) / tE) ** 2)
    return (u ** 2 + 2) / (u * np.sqrt(u ** 2 + 4))


r = least_squares(lambda p: (Aasym(D.mjd.values, *p) - ff) / ee, [58926, 0.43, 60, 65], bounds=([58880, 0.01, 5, 5], [58960, 3, 600, 600]))
print(f"\n[asymmetric Paczynski, fs=1] chi2 {2 * r.cost:.0f}/{len(D) - 4}  t0 {r.x[0]:.1f}  u0 {r.x[1]:.3f}  tE_rise {r.x[2]:.1f}  tE_fall {r.x[3]:.1f}")
