"""r8b: which source brightened? The NEOWISE centroid of the event frames moves toward the source that brightened by
  shift = f_ex x (position of that source - quiet centroid),   f_ex = excess W1 flux / W1 flux at the event.
For every Gaia DR3 and 2MASS source within 8" of the quiet-visit centroid, the predicted shift vector is compared with the
observed one (event-visit median position minus quiet-visit median position, associated frames only). Positions are matched
in each catalogue's own epoch (Gaia 2016, 2MASS ~1999); proper motions of these distant stars are < 10 mas/yr."""
import io
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framelib import analyse  # noqa: E402
from lib import KEYS, frames, targets  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
T = targets()


def viz(cat, ra, dec, r, cols):
    q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r, "-out": cols,
                     "-out.max": 500, "-c.u": "arcsec"}, headers=UA, timeout=240)
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 3:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        if c not in ("Source", "2MASS"):
            df[c] = pd.to_numeric(df[c].str.strip(), errors="coerce")
    return df


for k in KEYS:
    t = T[k]
    fr = frames(t["cntr"])
    if fr is None:
        print(f"== {k}: no frames")
        continue
    res = analyse(fr, t["row"])
    if res is None:
        continue
    m, d, ev, blk = res
    q, e = d[~d.vis.isin(blk)], d[d.vis == ev]
    ra0, de0 = q.ra.median(), q.dec.median()
    c = np.cos(np.radians(de0))
    ox, oy = ((e.ra - ra0) * c * 3600).median(), ((e.dec - de0) * 3600).median()
    rW = 10 ** (-0.4 * m["d_all"])
    fex = (rW - 1) / rW
    print(f"== {k}: observed shift ({ox:+.2f}, {oy:+.2f})\" = {np.hypot(ox, oy):.2f}\" at PA {np.degrees(np.arctan2(ox, oy)) % 360:.0f} "
          f"({m['shift_sig']:.1f} sigma); W1 x{rW:.2f}, f_ex {fex:.2f}; quiet centroid vs AllWISE "
          f"({(ra0 - t['ra']) * c * 3600:+.2f}, {(de0 - t['dec']) * 3600:+.2f})\"")
    rows = []
    g = viz("I/355/gaiadr3", ra0, de0, 8, "Source,RA_ICRS,DE_ICRS,Gmag,BP-RP")
    for _, s in g.iterrows():
        rows.append(("Gaia " + str(s.Source) + (" (matched)" if str(s.Source) == t["gaia"] else ""), s.RA_ICRS, s.DE_ICRS, f"G {s.Gmag:.2f}"))
    m2 = viz("II/246/out", ra0, de0, 8, "2MASS,RAJ2000,DEJ2000,Jmag,Kmag")
    for _, s in m2.iterrows():
        rows.append(("2MASS " + str(s["2MASS"]), s.RAJ2000, s.DEJ2000, f"J {s.Jmag:.2f} K {s.Kmag:.2f}"))
    out = []
    for name, ra, dec, mag in rows:
        sx, sy = (ra - ra0) * c * 3600, (dec - de0) * 3600
        px, py = fex * sx, fex * sy
        out.append((name, mag, np.hypot(sx, sy), px, py, np.hypot(px - ox, py - oy)))
    o = pd.DataFrame(out, columns=["source", "mag", "sep_from_centroid", "pred_dx", "pred_dy", "miss"]).sort_values("miss")
    print(o.head(6).round(2).to_string(index=False))
