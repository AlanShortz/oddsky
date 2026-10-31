"""r13: NEOWISE-only shape fits for the IR-only events J185035 (two-year event, peak visit saturated) and J184240 (two-visit
plateau), point lens (static, parallax) against Pearson VII. With 20 visits and 3-5 in the event these say only whether a lens
shape is possible, not that it is preferred."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitlib import Fitter, build, summary  # noqa: E402
from lib import targets  # noqa: E402

T = targets()
for k, tpk in (("J185035", 58340.0), ("J184240", 59390.0)):
    t = T[k]
    for lab, kw in (("all visits", {}), ("peak visit dropped (saturated)" if k == "J185035" else "fs<=1", {})):
        df, info = build(k, t, tpk, units=("zzz",), ev_dt=400)
        if lab.startswith("peak"):
            df = df[abs(df.t - t["tvis"]) > 3]
        caps = {g: 1.0 for g in info} if lab == "fs<=1" else ({g: 1.0 for g in info} if k == "J185035" else None)
        F = Fitter(df, ra=t["ra"], dec=t["dec"], t0par=round(tpk), fs_cap=caps)
        print(f"== {k} {lab} (fs<=1 for the lens), n {len(df)}")
        for mname in ("static", "parallax", "pv7", "pv7_asym"):
            print("   " + summary(F.fit(mname, tpk), info))
