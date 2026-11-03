"""H-0016 fades: frame-level test of a one-visit NEOWISE fade. For each star, fetch the single exposures (IRSA, Oddsky quality
cuts), take the event visit (frames within 3 d of t), and report: frames in the visit, the fraction of frames fainter than the
star's median by > half the visit depth, the W1-vs-W2 frame-to-frame correlation inside the visit, and the shape (monotonic
ingress/egress vs scattered). usage: fade_frames.py IN_CSV OUT_CSV"""
import sys

import numpy as np
import pandas as pd

from oddsky.data.neowise import exposures

x = pd.read_csv(sys.argv[1])
rows = []
for s in x.itertuples():
    rec = dict(cntr=s.cntr)
    try:
        e, prov = exposures(float(s.ra), float(s.dec))
    except Exception as ex:  # noqa: BLE001
        rec["frames_status"] = f"error {str(ex)[:60]}"
        rows.append(rec)
        continue
    if not len(e):
        rec["frames_status"] = "none"
        rows.append(rec)
        continue
    for band, d in (("W1", s.dw1), ("W2", s.dw2)):
        b = e[e.band == band]
        med = b.mag.median()
        v = b[(b.t_mjd - s.t).abs() < 3].sort_values("t_mjd")
        o = b[(b.t_mjd - s.t).abs() >= 3]
        rec[f"{band}_n_vis"], rec[f"{band}_n_other"] = len(v), len(o)
        if len(v):
            dv = v.mag - med
            rec[f"{band}_vis_med"] = float(dv.median())
            rec[f"{band}_vis_min"] = float(dv.min())
            rec[f"{band}_vis_max"] = float(dv.max())
            rec[f"{band}_frac_deep"] = float((dv > 0.5 * d).mean())
            rec[f"{band}_vis_mad"] = float(1.4826 * (dv - dv.median()).abs().median())
            rec[f"{band}_other_mad"] = float(1.4826 * (o.mag - o.mag.median()).abs().median()) if len(o) else np.nan
    v1 = e[(e.band == "W1") & ((e.t_mjd - s.t).abs() < 3)]
    v2 = e[(e.band == "W2") & ((e.t_mjd - s.t).abs() < 3)]
    if len(v1) >= 4 and len(v2) >= 4:
        m = pd.merge_asof(v1.sort_values("t_mjd"), v2.sort_values("t_mjd"), on="t_mjd", tolerance=0.01, suffixes=("1", "2")).dropna(subset=["mag2"])
        rec["frame_corr"] = float(np.corrcoef(m.mag1, m.mag2)[0, 1]) if len(m) >= 4 else np.nan
        rec["n_pairs"] = len(m)
    rec["frames_status"] = "ok"
    rows.append(rec)
    print(s.designation, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in rec.items() if k != "cntr"}, flush=True)
pd.DataFrame(rows).to_csv(sys.argv[2], index=False)
