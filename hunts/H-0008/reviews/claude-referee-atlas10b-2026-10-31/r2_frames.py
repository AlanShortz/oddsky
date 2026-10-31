"""r2: frame-level scrutiny.
J175634: every frame within -15..+25 d of the peak (units, positions, mag5sig, chi/N, PSF axes, apfit, sky), frame-to-frame
scatter vs formal errors, and number of distinct detector positions per night.
Saturation: ATLAS o saturates near 12.5 AB in good seeing. Proxy for the peak pixel: flux/(maj*min). Within each unit/band, does
the frame flux relative to the nightly median fall when the PSF is narrow (= higher peak pixel)? Compared between the peak
season and the baseline for J174744 (o 12.9 at peak, 13.7 baseline) and J175634 (o 13.15 at peak)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import atlas_raw, mjd2date, ujy2ab  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
TP = {"J175634": 59661.3, "J174744": 59654.4}


def npos(d):
    cl = []
    for p in d[["x", "y"]].values:
        if not any(np.hypot(*(p - q)) < 50 for q in cl):
            cl.append(p)
    return len(cl)


r = atlas_raw("J175634")
r = r[(r.err == 0) & (r.dujy > 0)]
tp = TP["J175634"]
e = r[(r.mjd > tp - 15) & (r.mjd < tp + 25)].copy()
e["dt"] = (e.mjd - tp).round(3)
e["mag"] = ujy2ab(np.clip(e.ujy, 1, None)).round(2)
print("== J175634: every frame within -15..+25 d")
print(e[["dt", "obs", "F", "ujy", "dujy", "mag", "chi_n", "x", "y", "maj", "min", "apfit", "mag5sig", "sky"]].to_string(index=False))
print("\nPer night: frames, positions, flux scatter / formal error, chi/N, PSF vs unit's season median")
base_seas = r[(np.abs(r.mjd - tp) < 150)]
for (night, cam, F), d in e.groupby(["night", "cam", "F"]):
    s = base_seas[(base_seas.cam == cam) & (base_seas.F == F)]
    print(f"  {mjd2date(d.mjd.mean())} dt {d.mjd.mean() - tp:+6.2f} {F} {cam} nfr {len(d)} npos {npos(d)} med {np.median(d.ujy):7.0f} "
          f"scat/err {np.std(d.ujy, ddof=1) / np.median(d.dujy) if len(d) > 1 else np.nan:5.1f} "
          f"frac.scatter {np.std(d.ujy, ddof=1) / np.median(d.ujy) if len(d) > 1 else np.nan:.3f} chiN {d.chi_n.median():6.1f} "
          f"dmaj {d.maj.median() - s.maj.median():+.2f} dm5 {d.mag5sig.median() - s.mag5sig.median():+.2f} "
          f"dsky {d.sky.median() - s.sky.median():+.2f}  apfit {d.apfit.median():+.3f} (season {s.apfit.median():+.3f})")

print("\n== Saturation tests")
for k in TP:
    r = atlas_raw(k)
    r = r[(r.err == 0) & (r.dujy > 0) & (r.mag5sig > 17.5)].copy()
    r["pk"] = r.ujy / (r.maj * r["min"])  # peak-pixel proxy, uJy per px^2
    # relative flux to the per-night/unit/band median
    r["rel"] = r.ujy / r.groupby(["night", "cam", "F"]).ujy.transform("median")
    r["dmaj"] = r.maj - r.groupby(["night", "cam", "F"]).maj.transform("median")
    print(f"-- {k}: brightest single frames")
    print(r.sort_values("ujy", ascending=False).head(8)[["mjd", "obs", "F", "ujy", "maj", "min", "pk", "chi_n", "apfit"]]
          .round(2).to_string(index=False))
    for F in ("o", "c"):
        d = r[r.F == F]
        for lab, sel in (("peak season |dt|<60", np.abs(d.mjd - TP[k]) < 60), ("baseline |dt|>400", np.abs(d.mjd - TP[k]) > 400)):
            x = d[sel]
            x = x[x.groupby(["night", "cam"]).ujy.transform("size") >= 3]
            if len(x) < 10:
                continue
            # within-night: relative flux vs relative PSF width (positive slope => narrow PSF loses flux => saturation/non-linearity)
            A = np.vstack([np.ones(len(x)), x.dmaj.values]).T
            p, res, *_ = np.linalg.lstsq(A, x.rel.values - 1, rcond=None)
            sig = np.std(x.rel.values - 1 - A @ p)
            cov = np.linalg.inv(A.T @ A) * sig**2
            print(f"  {F} {lab:20s}: n {len(x)}  median peak proxy {x.pk.median():7.0f} uJy/px^2 (max {x.pk.max():7.0f}); "
                  f"within-night d(flux)/d(maj) {p[1] * 100:+.2f} +- {np.sqrt(cov[1, 1]) * 100:.2f} %/px; median chi/N {x.chi_n.median():.1f}")
    # nightly flux vs peak proxy across the peak season: does the flux ratio saturate?
