"""H-0007 step 2: achromatic, isolated mid-infrared brightenings (microlensing-like) in every stored sky2 light curve.

Stored light curves (gs://oddsky-sky-br3c3-data/runs/sky2/lightcurves) = stars with W1_base < 13 and W2 peak-to-peak >= 0.3,
or a W2 rise (see oddsky.sky.neowise_pixel.process). For each star: baseline = median of all visits; robust scatter =
1.4826 * MAD. An event is a run of 1-3 consecutive visits brighter in BOTH bands by >= max(DMIN, 6 sigma), achromatic
(|dW1 - dW2| <= 0.08 + 0.12 |dW|), with every other visit within 4 sigma (or 0.1 mag) of the baseline.
The mirror run (fainter instead of brighter) is the control.
usage: hunt_h0007_lens.py LC_DIR OUT_CSV
"""

import glob
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

DMIN = 0.15
files = sorted(glob.glob(f"{sys.argv[1]}/*.parquet"))
lc = pd.concat([pq.read_table(f).to_pandas() for f in files], ignore_index=True)
lc = lc.dropna(subset=["w1", "w2"]).sort_values(["allwise_cntr", "t"]).reset_index(drop=True)
g = lc.groupby("allwise_cntr")
lc["n"] = g.t.transform("size")
lc = lc[lc.n >= 10].copy()
g = lc.groupby("allwise_cntr")
lc["k"] = g.cumcount()
for b in ("w1", "w2"):
    lc[f"d{b}"] = lc[b] - g[b].transform("median")
    lc[f"s{b}"] = np.maximum(
        1.4826 * lc.groupby("allwise_cntr")[f"d{b}"].transform(lambda x: np.median(np.abs(x))), 0.01
    )
rows = []
for sign, kind in ((-1, "brighten"), (1, "fade")):
    hit = (
        (sign * lc.dw1 >= np.maximum(DMIN, 6 * lc.sw1))
        & (sign * lc.dw2 >= np.maximum(DMIN, 6 * lc.sw2))
        & ((lc.dw1 - lc.dw2).abs() <= 0.08 + 0.12 * lc[["dw1", "dw2"]].abs().max(axis=1))
    )
    calm = (lc.dw1.abs() <= np.maximum(0.1, 4 * lc.sw1)) & (
        lc.dw2.abs() <= np.maximum(0.1, 4 * lc.sw2)
    )
    lc["hit"], lc["calm"] = hit, calm
    s = lc.groupby("allwise_cntr").agg(nhit=("hit", "sum"), ncalm=("calm", "sum"), n=("n", "first"))
    # hits must be one consecutive run of 1-3 visits, everything else calm
    first = lc[lc.hit].groupby("allwise_cntr").k.agg(["min", "max"])
    s = s.join(first)
    s = s[
        (s.nhit >= 1)
        & (s.nhit <= 3)
        & (s["max"] - s["min"] + 1 == s.nhit)
        & (s.ncalm + s.nhit == s.n)
    ]
    for cntr, r in s.iterrows():
        e = lc[(lc.allwise_cntr == cntr) & lc.hit]
        rows.append(
            {
                "allwise_cntr": cntr,
                "kind": kind,
                "n": int(r.n),
                "nhit": int(r.nhit),
                "k0": int(r["min"]),
                "edge": bool(r["min"] == 0 or r["max"] == r.n - 1),
                "dw1": float(e.dw1.iloc[np.argmax(np.abs(e.dw1.values))]),
                "dw2": float(e.dw2.iloc[np.argmax(np.abs(e.dw2.values))]),
                "sw1": float(e.sw1.iloc[0]),
                "t_peak": float(e.t.iloc[np.argmax(np.abs(e.dw1.values))]),
                "w1_med": float((lc.loc[lc.allwise_cntr == cntr, "w1"]).median()),
                "w1w2": float(
                    (
                        lc.loc[lc.allwise_cntr == cntr, "w1"]
                        - lc.loc[lc.allwise_cntr == cntr, "w2"]
                    ).median()
                ),
                "pixel": int(e.pixel.iloc[0]),
            }
        )
out = pd.DataFrame(rows)
out["year"] = 1858.87 + out.t_peak / 365.25
out.to_csv(sys.argv[2], index=False)
print("stars searched", lc.allwise_cntr.nunique())
print(out.groupby(["kind", "edge"]).size())
print(out[~out.edge].sort_values(["kind", "dw1"]).to_string())
