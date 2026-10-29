"""Referee 2: follow-ups to r4 (unit-scale values, sat-13 case, acceleration vs parallax in restricted windows,
residuals of the parallax fit by night and unit). uv run python .../r5_extra.py"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L
from r4_fits import fit, par_both, RAW
pd.set_option("display.width", 200)
base = L.nightly(RAW)
r = min(par_both(base, scale_units=("02a",)).values(), key=lambda q: q["chi2"])
print(f"02a scale free: scale = {r['p'][5]:.4f} +- {r['err'][5]:.4f}, chi2 {r['chi2']:.1f}, piE ({r['p'][3]:.3f}, {r['p'][4]:.3f})")
s = fit(base, "static", scale_units=("02a",)); print(f"   static with 02a scale: {s['p'][3]:.4f}, chi2 {s['chi2']:.1f}")
# only scale during the event season: 2017 Jul-2018 Mar 02a offset (zero point of the 2017 season)
d13 = L.nightly(RAW, sat=13.0)
print("sat 13 points in event:", d13[(d13.mjd > 57950) & (d13.mjd < 58090)][["mjd", "f", "e", "band", "unit"]].round(3).values.tolist())
for kind in ("static", "acc"):
    q = fit(d13, kind, starts=[[58011, 47, 0.14], [58011, 47, -0.14], [58005, 40, 0.3]])
    print(f"sat13 {kind}: chi2 {q['chi2']:.1f}, p {np.round(q['p'], 3).tolist()}")
pb = par_both(d13)
for k, q in pb.items():
    print(f"sat13 par u0sign {k}: chi2 {q['chi2']:.1f}, p {np.round(q['p'], 3).tolist()}")
# acceleration vs parallax by window
for tag, w in (("57700-58300", (57700, 58300)), ("57900-58200", (57900, 58200)), ("57940-58090 + no baseline", (57940, 58090))):
    d = L.nightly(RAW, window=w)
    p = min(par_both(d).values(), key=lambda q: q["chi2"]); a = fit(d, "acc"); aj = fit(d, "accjerk"); st = fit(d, "static")
    print(f"window {tag}: N {len(d)}  static {st['chi2']:.1f}  parallax {p['chi2']:.1f}  acc {a['chi2']:.1f}  acc+jerk {aj['chi2']:.1f}")
# residuals of the parallax fit, by night
p = min(par_both(base).values(), key=lambda q: q["chi2"])
a = fit(base, "acc")
R = base.assign(par=p["model"], acc=a["model"], r_par=(base.f - p["model"]) / base.e, r_acc=(base.f - a["model"]) / base.e)
print(R[(R.mjd > 57940) & (R.mjd < 58200)].round(3).to_string())
off = R[(R.mjd < 57940) | (R.mjd > 58200)]
print(f"off-event chi2 par {np.sum(off.r_par**2):.1f} acc {np.sum(off.r_acc**2):.1f} for {len(off)} pts; on-event par {np.sum(R.r_par**2)-np.sum(off.r_par**2):.1f} acc {np.sum(R.r_acc**2)-np.sum(off.r_acc**2):.1f} for {len(R)-len(off)}")
# runs test / lag-1 autocorrelation of residuals in time order (event season)
ev = R[(R.mjd > 57940) & (R.mjd < 58200) & R.band.isin(["o"])].sort_values("mjd")
x = ev.r_par.values; print(f"event-season o residuals: lag-1 autocorr {np.corrcoef(x[:-1], x[1:])[0,1]:.2f}, n {len(x)}, sign runs {1+np.sum(np.sign(x[1:])!=np.sign(x[:-1]))}")
x = R[(R.mjd < 57940) | (R.mjd > 58200)].sort_values("mjd").r_par.values
print(f"off-event residuals: lag-1 autocorr {np.corrcoef(x[:-1], x[1:])[0,1]:.2f}, n {len(x)}")
# acceleration vs parallax when the 02a zero point is free
a2 = fit(base, "acc", scale_units=("02a",)); p2 = min(par_both(base, scale_units=("02a",)).values(), key=lambda q: q["chi2"])
print(f"with 02a scale free: acc chi2 {a2['chi2']:.1f} (scale {a2['p'][5]:.4f}); parallax chi2 {p2['chi2']:.1f}")
