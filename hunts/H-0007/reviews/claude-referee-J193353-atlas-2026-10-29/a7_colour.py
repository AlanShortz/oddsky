"""a7: is the c-band excess really ~10% larger than o? Fit A_c = b_c * (1 + k (A_model - 1)) on 2020 c nights with the a4 parallax
model shape (fs=1) fixed, b_c (c baseline offset) and k free; same for o. Also the c 02a nightly zero point by season.
usage: uv run --with MulensModel python a7_colour.py (run a2 first)"""
import warnings
import numpy as np
import pandas as pd
import MulensModel as mm

warnings.filterwarnings("ignore")
n = pd.read_csv("/tmp/j1933atl/nightly_ref.csv"); n = n[n.A > 0.5]
J = 2400000.5
M = mm.Model(dict(t_0=58928.8 + J, u_0=-0.390, t_E=44.1, pi_E_N=-0.068, pi_E_E=0.533, t_0_par=58925.0 + J), coords="19:33:53.067 -21:18:13.49")
s = n[(n.mjd > 58900) & (n.mjd < 59160)].copy()
s["mod"] = M.get_magnification(s.mjd.values + J)
for F, U in [("c", ["02a"]), ("o", ["01a", "02a"]), ("o", ["01a"]), ("o", ["02a"])]:
    x = s[(s.F == F) & s.unit.isin(U)]
    X = np.vstack([np.ones(len(x)), x["mod"] - 1]).T
    (b, bk), res, *_ = np.linalg.lstsq(X, x.A.values, rcond=None)
    sig = np.sqrt(res[0] / (len(x) - 2)) if len(res) else np.nan
    cov = sig ** 2 * np.linalg.inv(X.T @ X)
    print(f"{F} {'+'.join(U)}: N={len(x)}  baseline b={b:.4f}+-{np.sqrt(cov[0, 0]):.4f}  excess scale k=bk/b={bk / b:.3f}+-{np.sqrt(cov[1, 1]) / b:.3f}  rms {sig:.4f}")
n["yr"] = pd.to_datetime(n.date).dt.year
n["mo"] = pd.to_datetime(n.date).dt.month
print("\nc 02a and o 01a/02a nightly median A by season (Apr-Oct only), excluding 2020:")
w = n[(n.mo >= 4) & (n.mo <= 10) & (n.yr != 2020)]
print(w[w.unit.isin(["01a", "02a"])].groupby(["yr", "F", "unit"]).A.median().unstack(["F", "unit"]).round(3).to_string())
