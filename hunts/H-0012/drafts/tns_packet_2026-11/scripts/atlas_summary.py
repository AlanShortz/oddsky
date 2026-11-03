"""TNS packet 2026-11: optical limits from the ATLAS forced photometry the H-0012 triage referee retrieved
(reviews/claude-referee-triage-2026-11-01/atlas_{NGC4945_obs3,M81_obs9}.txt; jobs 5280888/5280889, forced at
196.4697 -49.4162 and 148.7390 +69.1468, within 0.7" of the packet positions). No new ATLAS job was queued.

Per filter, error-weighted mean difference flux in +-30 d windows around the WISE epochs, after dropping
placeholder rows (chi/N = 0) and points with duJy > 3x the median error (cloud/bright-sky frames); a 3-sigma upper limit in AB mag is given when the
mean is consistent with zero.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/atlas_summary.py
Output: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/atlas_summary.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

REV = Path(__file__).resolve().parents[3] / "reviews/claude-referee-triage-2026-11-01"
OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11"
SETS = {
    "NGC4945_obs3": ("atlas_NGC4945_obs3.txt", {"last_nondet 2018-07-07": 58306.61, "discovery 2019-01-27": 58510.74,
                                                 "2019-07-07": 58671.09, "2020-01-28": 58876.25,
                                                 "peak 2022-07-07": 59767.39, "2023-01-27": 59971.68}),
    "M81_OS-0035": ("atlas_M81_obs9.txt", {"last_nondet 2023-03-27": 60030.76, "discovery 2023-10-23": 60240.24,
                                            "2024-03-28": 60397.56}),
}
res = {}
for lab, (fn, ep) in SETS.items():
    d = pd.read_csv(REV / fn, sep=r"\s+")
    d = d.rename(columns={"###MJD": "MJD"})
    d = d[(d.duJy > 0) & (d["chi/N"].abs() > 0)]  # rows with chi/N = 0 and uJy = 0 are placeholders, not measurements
    d = d[d.duJy < 3 * d.duJy.median()]
    rec = {"file": fn, "n_points_kept": int(len(d)), "mjd_range": [float(d.MJD.min()), float(d.MJD.max())]}
    for name, m in ep.items():
        for f in ("c", "o"):
            g = d[(d.F == f) & (np.abs(d.MJD - m) < 30)]
            if len(g) == 0:
                rec[f"{name} {f}"] = "no ATLAS data within +-30 d"
                continue
            w = 1 / g.duJy ** 2
            mu = float((g.uJy * w).sum() / w.sum())
            e = float(1 / np.sqrt(w.sum()))
            lim = -2.5 * np.log10(max(mu, 0) + 3 * e) + 23.9
            rec[f"{name} {f}"] = dict(n=int(len(g)), mean_uJy=round(mu, 1), err_uJy=round(e, 1),
                                      ab_3sig_limit=round(float(lim), 2))
    res[lab] = rec
    print(lab, json.dumps(rec, indent=1))
(OUT / "atlas_summary.json").write_text(json.dumps(res, indent=1))
