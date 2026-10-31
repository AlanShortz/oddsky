"""p1: NEOWISE visit light curves of the six targets (visit medians), relative to the median of all visits."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import LC_DIRS, T  # noqa: E402

for k, t in T.items():
    for d in LC_DIRS:
        p = os.path.join(d, f"pixel={t['pixel']}.parquet")
        if os.path.exists(p):
            lc = pd.read_parquet(p)
            lc = lc[lc.allwise_cntr == np.int64(t["cntr"])].sort_values("t")
            if len(lc):
                break
    med1, med2 = np.median(lc.w1), np.median(lc.w2)
    print(f"== {k} {t['name']} ({os.path.basename(d)}), {len(lc)} visits, W1 median {med1:.3f}")
    for _, r in lc.iterrows():
        print(f"   {r.t:9.1f}  dW1 {r.w1 - med1:+.3f} ±{r.w1_err:.3f} (n{int(r.w1_n):2d})  dW2 {r.w2 - med2:+.3f} ±{r.w2_err:.3f} (n{int(r.w2_n):2d})"
              f"  rchi {r.rchi:5.2f} cc {r.ccfrac:.2f} hd {r.hdfrac:.2f}" + ("   <==" if abs(r.t - t["t_nw"]) < 200 else ""))
