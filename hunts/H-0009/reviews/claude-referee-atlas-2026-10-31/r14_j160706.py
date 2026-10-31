"""r14: the README's headline long event J160706.90-533729.5 (OS-0023; in sky4_classified but not in sky4_strong): same
exposure-level diagnostics (r0 download + framelib.analyse)."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r0_fetch_frames_one as f1  # noqa: E402
from framelib import analyse  # noqa: E402
from lib import W9, frames  # noqa: E402

k = pd.read_csv(os.path.join(W9, "sky4_classified.csv"), dtype={"g_source_id": str})
r = k[k.designation.str.startswith("J160706")].iloc[0]
print(f1.fetch((int(r.allwise_cntr), float(r.ra), float(r.dec))))
fr = frames(int(r.allwise_cntr))
row = r.copy()
row["allwise_cntr"] = int(r.allwise_cntr)
m = analyse(fr, row)[0]
print(r.designation, r["class"], f"dw1 {r.dw1:.2f} dw2 {r.dw2:.2f} nblock {r.nblock} block {r.block_dw1}")
print("  ".join(f"{a}={b:.3g}" if isinstance(b, float) else f"{a}={b}" for a, b in m.items()))
