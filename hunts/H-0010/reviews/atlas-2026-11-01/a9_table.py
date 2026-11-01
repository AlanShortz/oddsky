"""a9: one row per candidate from the a1-a8 outputs (no new measurement): neighbours and target share of the ATLAS PSF flux,
coverage (+-30 / +-90 d of the Gaia t0, all nights and PSF-matched ones), the same-era event excess per band in units of the Gaia
star's band flux (a7), the Gaia G excess at the same nights (fs = 1 lens), the joint-fit ATLAS scales s_o, s_c and the lens-vs-shape
BIC (a8), and the repeat search (a4). Writes data/a9_table.csv.
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a9_table.py"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, targets  # noqa: E402

T = targets()
J = {n: json.load(open(os.path.join(DATA, f"{n}.json"))) for n in ("a1_shares", "a2_summary", "a4_summary", "a6_summary", "a7_summary",
                                                                     "a8_summary")}
rows = []
for k in KEYS:
    sh = J["a1_shares"][k]
    a2 = J["a2_summary"][k]
    a4 = J["a4_summary"][k]
    a7 = J["a7_summary"].get(k, {})
    a8 = J["a8_summary"].get(k, {})
    n4 = os.path.join(DATA, f"a4_nights_{k}.csv")
    nt = pd.read_csv(n4)
    good = nt[nt.kd < 1.0]
    row = dict(cand=k, G=round(T[k]["G"], 2), n_gaia_8as=sh["n8"], share_o=f"{sh['share']['3.8']['o']:.2f}-{sh['share']['2.6']['o']:.2f}",
               share_c=f"{sh['share']['3.8']['c']:.2f}-{sh['share']['2.6']['c']:.2f}", n30=a2["n30"], n90=a2["n90"],
               n30_matched=int((np.abs(good.dt) <= 30).sum()), n90_matched=int((np.abs(good.dt) <= 90).sum()))
    for F in ("o", "c"):
        if F in a7:
            Fb = sh["fo_star" if F == "o" else "fc_star"]
            row[f"{F}_exc_over_star"] = f"{a7[F]['exc'] / Fb:+.2f} +- {a7[F]['err'] / Fb:.2f} ({a7[F]['nights']} n)"
    for kind in ("lens_fs1", "lens"):
        f = a8.get(kind + "_free_s") or a8.get(kind)
        if f:
            row[f"s_{kind}"] = ", ".join(f"{a} {b:.2f}" for a, b in f["s"].items())
    if a8:
        bl = min(a8["lens"]["bic"], a8["lens_fs1"]["bic"])
        bs = min(a8["pv7a"]["bic"], a8["gauss_a"]["bic"])
        row["dBIC_shape_minus_lens"] = round(bs - bl, 1)
    rp = a4.get("repeat", {})
    row["repeat"] = "; ".join(f"{F}: {v['years']}, max {v['max_sig']:+.1f} sig (x{1 + v['max_in_star']:.2f} raw), >4 sig {v['n_gt4']}"
                              for F, v in rp.items())
    rows.append(row)
D = pd.DataFrame(rows)
D.to_csv(os.path.join(DATA, "a9_table.csv"), index=False)
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 30)
print(D.T.to_string())
