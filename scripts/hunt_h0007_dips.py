"""H-0007 step 1: mid-infrared dimming events (W1 and W2 both fainter) in quiet photospheres, sky2 NEOWISE pass.

Input: hunts/H-0007/data/quiet_ptp_lc.csv (bq export, see hunts/H-0007/README.md).
For each star: median and robust (MAD) scatter of all visits; a dip visit is W1 and W2 both >= DMIN mag
fainter than the median and >= NSIG sigma. The mirror test (both brighter) is computed the same way.
"""

import sys

import numpy as np
import pandas as pd

DMIN, NSIG = 0.25, 5.0
lc = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "hunts/H-0007/data/quiet_ptp_lc.csv")
lc = lc.sort_values(["allwise_cntr", "t"]).reset_index(drop=True)
g = lc.groupby("allwise_cntr")
for b in ("w1", "w2"):
    lc[f"m{b}"] = g[b].transform("median")
    lc[f"d{b}"] = lc[b] - lc[f"m{b}"]
    mad = lc.groupby("allwise_cntr")[f"d{b}"].transform(lambda x: 1.4826 * np.median(np.abs(x)))
    lc[f"s{b}"] = np.maximum(mad, lc[f"{b}_err"]).clip(lower=0.01)
lc["k"] = g.cumcount()
lc["n"] = g["t"].transform("size")
for sign, name in ((1, "dip"), (-1, "rise")):
    lc[name] = (
        (sign * lc.dw1 >= DMIN)
        & (sign * lc.dw2 >= DMIN)
        & (sign * lc.dw1 >= NSIG * lc.sw1)
        & (sign * lc.dw2 >= NSIG * lc.sw2)
    )
ev = lc[lc.dip | lc.rise].copy()
ev["kind"] = np.where(ev.dip, "dip", "rise")
ev["grey"] = (ev.dw1 - ev.dw2).abs() < 0.35 * ev[["dw1", "dw2"]].abs().max(axis=1)
ev["edge"] = (ev.k == 0) | (ev.k == ev.n - 1)
ev["year"] = 1858.87 + ev.t / 365.25  # MJD -> approx decimal year
nev = ev.groupby(["allwise_cntr", "kind"]).size().unstack(fill_value=0)
print(
    "stars",
    lc.allwise_cntr.nunique(),
    "dip visits",
    int(lc.dip.sum()),
    "rise visits",
    int(lc.rise.sum()),
)
print(
    "stars with >=1 dip",
    int((nev.get("dip", 0) > 0).sum()),
    "with >=1 rise",
    int((nev.get("rise", 0) > 0).sum()),
)
print(
    "dip visits not at the edge",
    int((ev.dip & ~ev.edge).sum()),
    "rise not edge",
    int((ev.rise & ~ev.edge).sum()),
)
print("grey non-edge dips", int((ev.dip & ~ev.edge & ev.grey).sum()))
print("\ndip visits by half-year:")
print(ev[ev.dip & ~ev.edge].groupby((ev.year * 2).round() / 2).size().to_string())
print("\nrise visits by half-year:")
print(ev[ev.rise & ~ev.edge].groupby((ev.year * 2).round() / 2).size().to_string())
ev.to_csv("hunts/H-0007/work/events.csv", index=False)
lc.to_parquet("hunts/H-0007/work/lc.parquet")
