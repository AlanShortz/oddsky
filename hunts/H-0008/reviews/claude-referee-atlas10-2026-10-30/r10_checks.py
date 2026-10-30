"""r10: two small checks.
(a) J191120 late decline colour: ZTF g, r, i fractional excess (flux/baseline - 1) at +61..+116 d. A hot (blackbody) or flat-F_nu
    (free-free / nebular nova) component added to this red star would raise g by ~10x the fractional rise in r; a lens raises
    all bands by the same factor.
(b) The investigators' flux-RATIO series (scripts/hunt_h0008_atlas_fit.ratio_series logic, re-implemented): what the baseline
    medians are for each ATLAS series, and what happens when the median is ~0 or negative (ratio sign flip / blow-up)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, atlas_raw  # noqa: E402

print("(a) J191120 ZTF colour in the decline")
z = pd.read_csv(os.path.join(DATA, "ztf_J191120.csv"))
z = z[z.catflags == 0]
z["fl"] = 10 ** (-0.4 * z.mag)
z["e"] = z.fl * z.magerr / 1.0857
for fc in ("zg", "zr", "zi"):
    d = z[z.filtercode == fc]
    base = d[(d.mjd < 59200) | (d.mjd > 59700)]
    b = np.median(base.fl)
    rob = 1.4826 * np.median(np.abs(base.fl / b - 1))
    w = d[(d.mjd > 59355) & (d.mjd < 59410)]
    ww = 1 / ((w.e / b) ** 2 + rob**2)
    ex = np.sum(ww * (w.fl / b - 1)) / np.sum(ww)
    print(f"  {fc}: baseline {-2.5 * np.log10(b):.2f} mag (n {len(base)}, rob {rob:.3f}); +61..+116 d: n {len(w)}, "
          f"fractional excess {ex:.3f} +- {1 / np.sqrt(np.sum(ww)):.3f} (mean dt {w.mjd.mean() - 59293.7:.0f} d)")

print("(b) baseline medians of the investigators' per-unit ATLAS series (no chi cut, mag5sig>17, dujy>0; |dt|>400 d)")
TPK = {"J191120": 59293.6, "J075219": 58233.3, "J163539": 57977.3, "J173150": 58305.4, "J174440": 60003.1}
for k, tpk in TPK.items():
    r = atlas_raw(k)
    r = r[(r.err == 0) & (r.dujy > 0) & (r.mag5sig > 17.0)]
    r["n"] = np.floor(r.mjd)
    out = []
    for (F, cam), d in r.groupby(["F", "cam"]):
        w = 1 / d.dujy**2
        g = d.assign(w=w, wf=w * d.ujy).groupby("n")
        fl = g.wf.sum() / g.w.sum()
        t = g.mjd.mean()
        base = np.abs(t - tpk) > 400
        if base.sum() < 8 or (np.abs(t - tpk) < 200).sum() < 1:
            continue
        med = np.median(fl[base])
        ev = fl[np.abs(t - tpk) < 60]
        out.append(f"{F}_{cam}: median {med:.0f} uJy" + (f", event max ratio {ev.max() / med:.1f}" if len(ev) else "") +
                   (" <- median <= 0: ratio sign-flipped / undefined" if med <= 0 else ""))
    print(f"  {k}: " + "; ".join(out))
