"""r7: ATLAS frame-level checks at the event nights (|dt| <= 30 d of the NEOWISE peak visit): frames, distinct detector positions,
frame-to-frame scatter against the formal errors, chi/N, PSF width, mag5sig and sky against the unit's season medians.
Saturation test for the two bright stars (J025145 o 12.2 AB, J064439 o 12.9 AB): within a night, does the frame flux fall when the
PSF is narrow (higher peak pixel)? Compared between the event window and the baseline. Also the per-night chi/N against flux."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import KEYS, atlas_raw, mjd2date, targets  # noqa: E402

pd.set_option("display.width", 250)
T = targets()


def npos(d):
    cl = []
    for p in d[["x", "y"]].values:
        if not any(np.hypot(*(p - q)) < 50 for q in cl):
            cl.append(p)
    return len(cl)


for k in KEYS:
    t = T[k]
    r = atlas_raw(k)
    r = r[(r.err == 0) & (r.dujy > 0) & (r.mag5sig > 17.5)]
    tv = t["tvis"]
    e = r[np.abs(r.mjd - tv) <= 30]
    if e.empty:
        print(f"== {k}: no ATLAS frame within 30 d")
        continue
    seas = r[np.abs(r.mjd - tv) < 150]
    print(f"== {k}: {len(e)} frames within 30 d of {mjd2date(tv)}")
    for (night, cam, F), d in e.groupby(["night", "cam", "F"]):
        s = seas[(seas.cam == cam) & (seas.F == F)]
        print(f"  {mjd2date(d.mjd.mean())} dt {d.mjd.mean() - tv:+6.1f} {F} {cam} nfr {len(d)} npos {npos(d)} med {np.median(d.ujy):8.0f} "
              f"scat/err {np.std(d.ujy, ddof=1) / np.median(d.dujy) if len(d) > 1 else np.nan:5.1f} chiN {d.chi_n.median():7.1f} "
              f"maj {d.maj.median():.2f} (season {s.maj.median():.2f}) dm5 {d.mag5sig.median() - s.mag5sig.median():+.2f} "
              f"dsky {d.sky.median() - s.sky.median():+.2f} apfit {d.apfit.median():+.3f} (season {s.apfit.median():+.3f})")

print("\n== Saturation tests (within-night flux vs PSF width)")
for k in ("J025145", "J064439"):
    t = T[k]
    r = atlas_raw(k)
    r = r[(r.err == 0) & (r.dujy > 0) & (r.mag5sig > 17.5)].copy()
    r["rel"] = r.ujy / r.groupby(["night", "cam", "F"]).ujy.transform("median")
    r["dmaj"] = r.maj - r.groupby(["night", "cam", "F"]).maj.transform("median")
    r["pk"] = r.ujy / (r.maj * r["min"])
    for F in ("o", "c"):
        d = r[r.F == F]
        for lab, sel in (("event +-30 d", np.abs(d.mjd - t["tvis"]) <= 30), ("baseline >400 d", np.abs(d.mjd - t["tvis"]) > 400)):
            x = d[sel]
            x = x[x.groupby(["night", "cam"]).ujy.transform("size") >= 3]
            if len(x) < 8:
                continue
            A = np.vstack([np.ones(len(x)), x.dmaj.values]).T
            p, *_ = np.linalg.lstsq(A, x.rel.values - 1, rcond=None)
            sig = np.std(x.rel.values - 1 - A @ p)
            cov = np.linalg.inv(A.T @ A) * sig**2
            print(f"  {k} {F} {lab:16s}: n {len(x):4d} median peak proxy {x.pk.median():8.0f} uJy/px^2; d(flux)/d(maj) within night "
                  f"{p[1] * 100:+.2f} +- {np.sqrt(cov[1, 1]) * 100:.2f} %/px; chi/N median {x.chi_n.median():.0f}")
    # does the nightly flux depend on the PSF width across nights (season)? and chi/N vs flux
    o = r[(r.F == "o")]
    b = o[np.abs(o.mjd - t["tvis"]) > 400]
    for lab, sel in (("narrow PSF maj<2.2", b.maj < 2.2), ("2.2-2.6", (b.maj >= 2.2) & (b.maj < 2.6)), ("maj>=2.6", b.maj >= 2.6)):
        print(f"  {k} o baseline frames {lab:18s}: n {sel.sum():4d} median flux {b.ujy[sel].median():8.0f} chi/N {b.chi_n[sel].median():6.0f}")
    ev = o[np.abs(o.mjd - t["tvis"]) <= 15]
    print(f"  {k} o event frames (+-15 d): n {len(ev)} median maj {ev.maj.median():.2f} median flux {ev.ujy.median():.0f} chi/N {ev.chi_n.median():.0f}")
