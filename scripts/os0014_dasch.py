"""OS-0014: what a century of Harvard plates (DASCH DR7) says about a repeat of the 2017 occultation.

Fetches the DASCH DR7 light curve (StarGlass API), then:
  1. every deep plate (limit >= 1 mag fainter than the star) that misses the star: is there a normal
     detection within +/-50 d? (a real ~95-d occultation allows none);
  2. coverage: fraction of 1889-1990 in which a 95-d vanishing would have been caught;
  3. orbital periods (1-130 yr) excluded by DASCH + ASAS-SN + NEOWISE, phased on the 2017 event.
"""
import json
import sys

import httpx
import numpy as np
import pandas as pd

from oddsky.case.store import CaseStore

s = CaseStore.find("OS-0014")
f = s.data / "external" / "dasch_dr7_lightcurve.csv"
if not f.exists() or "--refetch" in sys.argv:
    r = httpx.post("https://api.starglass.cfa.harvard.edu/public/dasch/dr7/lightcurve",
                   json={"refcat": "apass", "gsc_bin_index": 34690085, "ref_number": 418330622360713}, timeout=180)
    f.write_text("\n".join(r.json()))
df = pd.read_csv(f)
df["mjd"] = df.date_jd - 2400000.5
det = df[df.magcal_magdep.notna()]
med = float(det.magcal_magdep.median())
nondet = df[df.magcal_magdep.isna()]
deep = nondet[nondet.limiting_mag_local >= med + 1.0]
normal = np.sort(det.mjd[det.magcal_magdep < med + 0.6].to_numpy())
isolated = [float(p.mjd) for _, p in deep.iterrows() if not ((np.abs(normal - p.mjd) <= 50).any())]
a = s.series("asassn")
a = a[a.flag == ""]
ne = s.series("neowise")
ne = ne[(ne.flag == "") & (ne.band == "W1")]
modern = np.concatenate([a.t_mjd.to_numpy(), ne.t_mjd[np.abs(ne.mag - ne.mag.median()) < 0.3].to_numpy()])
allpts = np.sort(np.concatenate([normal, modern]))
EV, T17 = 95.0, 57839.0


def caught(t0, pts):
    i = np.searchsorted(pts, t0)
    return bool(i < len(pts) and pts[i] <= t0 + EV)


grid = np.arange(normal.min() - EV, normal.max(), 1.0)
coverage = float(np.mean([caught(t, normal) for t in grid]))
periods = np.arange(1.0, 130.01, 0.01) * 365.25
excl = []
for P in periods:
    starts = T17 - np.arange(1, int((T17 - normal.min()) / P) + 2) * P
    starts = starts[starts > normal.min() - EV]
    hit = any(caught(t, allpts) for t in starts) or (T17 + P < allpts.max() and caught(T17 + P, allpts))
    excl.append(hit)
excl = np.array(excl)
allowed = periods[~excl] / 365.25
out = {"plates": int(len(df)), "detections": int(len(det)), "median_mag": round(med, 2),
       "deep_plates_missing_star": int(len(deep)), "of_which_without_normal_detection_within_50d": len(isolated),
       "coverage_1889_1990": round(coverage, 3), "periods_1_130yr_excluded": round(float(excl.mean()), 3),
       "min_allowed_period_yr": round(float(allowed.min()), 2), "allowed_fraction_above_30yr": round(float(np.mean(allowed > 30)), 3)}
print(json.dumps(out, indent=1))
(s.data / "external" / "dasch_constraints.json").write_text(json.dumps(out, indent=1))
