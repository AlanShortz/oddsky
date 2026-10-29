"""a6: (i) c vs o achromaticity on near-simultaneous nights; (ii) 01a vs 02a agreement during the event (residuals from the
a4 parallax fs=1 model, refit here); (iii) chi/N vs flux in baseline and event; (iv) the investigators' >x1.15 nights outside 2020.
usage: uv run --with MulensModel python a6_checks.py ATLAS_TXT (run a2 first)"""
import sys, warnings
import numpy as np
import pandas as pd
import MulensModel as mm
from oddsky.data import atlas

warnings.filterwarnings("ignore")
n = pd.read_csv("/tmp/j1933atl/nightly_ref.csv")
print("nights with A < 0.5 dropped (dropouts):", n[n.A < 0.5][["date", "F", "unit", "A", "k", "m5"]].to_string(index=False))
n = n[n.A > 0.5]
J = 2400000.5
P = dict(t_0=58928.8 + J, u_0=-0.390, t_E=44.1, pi_E_N=-0.068, pi_E_E=0.533, t_0_par=58925.0 + J)   # a4 parallax fs=1
M = mm.Model(P, coords="19:33:53.067 -21:18:13.49")
ev = n[(n.mjd > 58900) & (n.mjd < 59140)].copy()
ev["mod"] = M.get_magnification(ev.mjd.values + J)
ev["res"] = ev.A / ev["mod"] - 1
print("(i) c vs o: each c night against o nights within 2.5 d, excess ratio (A_c-1)/(A_o-1) after scaling o to the c epoch by the model")
c, o = ev[ev.F == "c"], ev[ev.F == "o"]
rat = []
for _, x in c.iterrows():
    y = o[(o.mjd - x.mjd).abs() < 2.5]
    if len(y) and x["mod"] > 1.08:
        ao = np.mean(1 + (y.A - 1) * (x["mod"] - 1) / (y["mod"] - 1))
        rat.append((x.A - 1) / (ao - 1))
        print(f"   {x.date} c {x.A:.3f} ({x.unit}) | o scaled {ao:.3f} from {len(y)} night(s) -> ratio {rat[-1]:.3f}")
rat = np.array(rat)
print(f"   weighted by excess: c/o excess ratio median {np.median(rat):.3f}, mean {rat.mean():.3f} +- {rat.std(ddof=1) / np.sqrt(len(rat)):.3f} (N={len(rat)})")
print("   model-residual means in event (A>1.08): c %+.4f (N=%d), o %+.4f (N=%d)" % (
    ev[(ev.F == 'c') & (ev['mod'] > 1.08)].res.mean(), ((ev.F == 'c') & (ev['mod'] > 1.08)).sum(),
    ev[(ev.F == 'o') & (ev['mod'] > 1.08)].res.mean(), ((ev.F == 'o') & (ev['mod'] > 1.08)).sum()))
print("\n(ii) per-unit residuals (event, model > 1.03):")
print(ev[ev["mod"] > 1.03].groupby(["F", "unit"]).res.agg(["mean", "std", "size"]).round(4).to_string())
r = atlas.parse(open(sys.argv[1]).read())
r = r[r.F.isin(["c", "o"]) & (r.dujy > 0)].copy()
r["unit"] = r.obs.str[:3]
good = (r.dujy < 150) & (r.mag5sig >= 17.5)
print("\n(iii) chi/N: median by unit, baseline vs event (good frames, o band)")
r["evt"] = (r.mjd > 58900) & (r.mjd < 59000)
print(r[good & (r.F == "o") & r.unit.isin(["01a", "02a"])].groupby(["unit", "evt"]).chi_n.describe()[["count", "25%", "50%", "75%"]].round(2).to_string())
print("\n(iv) investigators' nightly medians (all frames, dujy<2000) > 1.15 outside 2020: frames that night")
q = r[(r.dujy < 2000)].copy()
base = q[(q.mjd < 58800) | (q.mjd > 59200)].groupby("F").ujy.median()
q["A"] = q.ujy / q.F.map(base)
q["night"] = np.floor(q.mjd - 0.3)
nn = q.groupby(["F", "night"]).A.median()
hi = nn[(nn > 1.15)].reset_index()
hi = hi[(hi.night < 58880) | (hi.night > 59140)]
for _, h in hi.iterrows():
    f = q[(q.night == h.night)]
    print(f"   {pd.Timestamp(h.night - 40587, unit='D').date()} {h.F}: " + "; ".join(
        f"{x.F}{x.unit} A={x.A:.2f} m5={x.mag5sig:.1f} d={x.dujy:.0f}" for _, x in f.iterrows()))
