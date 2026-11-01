"""s8: what NEOWISE saw during each Gaia event, and whether it saw other brightenings (repeats) in 2014-2024.

Only sources whose NEOWISE detections are associated with an AllWISE source within 1.5" of the Gaia position (s4,
"allwise_cntr" match with >= 10 exposures) are used; for the rest NEOWISE does not resolve the star (crowded bulge fields).
Per source:
  * baseline: median of visits ("long" cuts) more than max(2 tE, 100 d) from the Gaia event (static-lens t0, tE);
  * visits within that window: date, dW1, dW2, and the Gaia G-band lens model's flux ratio at the visit (the same model
    including the fitted G blend; NEOWISE's 6" beam dilutes more, so a lens predicts NEOWISE <= Gaia's source magnification);
  * repeats: visits outside the window brighter than max(0.25 mag, 5 x baseline rms) in both bands.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s8_neowise_event.py
Writes hunts/H-0010/data/neowise_event.csv."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, NW, mjd2date, targets  # noqa: E402

from oddsky.analysis.lensing import Problem  # noqa: E402


def main():
    T = targets()
    lc = pd.read_csv(os.path.join(DATA, "lc_metrics.csv"), dtype={"source_id": str}).set_index("source_id")
    aw = pd.read_csv(os.path.join(DATA, "allwise.csv"), dtype={"source_id": str}).set_index("source_id")
    ev = pd.read_csv(os.path.join(DATA, "neowise_events.csv"), dtype={"source_id": str}).set_index("source_id")
    rows = []
    for r in T.itertuples():
        sid = r.source_id
        rec = {"source_id": sid}
        ok = ev.loc[sid, "match"] == "allwise_cntr" and ev.loc[sid, "n_exp"] >= 10 and aw.loc[sid, "aw_sep"] < 1.5
        if not ok:
            rec["nw_status"] = "no NEOWISE source on the star" if ev.loc[sid, "n_exp"] < 10 or aw.loc[sid, "n_allwise_3as"] == 0 \
                else f"AllWISE source {aw.loc[sid, 'aw_sep']}\" away or unmatched"
            rows.append(rec)
            continue
        v = pd.read_csv(os.path.join(NW, f"{sid}_visits.csv"))
        v = v[v["mode"] == "long"]
        w1 = v[v.band == "W1"].set_index("visit")
        w2 = v[v.band == "W2"].set_index("visit")
        vv = w1[["t", "mag", "err"]].join(w2[["mag", "err"]], rsuffix="2", how="inner")
        m = lc.loc[sid]
        t0, te = float(m.static_t0), float(m.static_tE)
        if not np.isfinite(t0) or te > 1500:
            t0, te = float(m.t_peak), 60.0
        win = max(2 * te, 100.0)
        inw = np.abs(vv.t - t0) < win
        base = vv[~inw]
        if len(base) < 4:
            rec["nw_status"] = "too few baseline visits"
            rows.append(rec)
            continue
        vv["d1"] = vv.mag - base.mag.median()
        vv["d2"] = vv.mag2 - base.mag2.median()
        rms1 = 1.4826 * np.median(np.abs(base.mag - base.mag.median()))
        rms2 = 1.4826 * np.median(np.abs(base.mag2 - base.mag2.median()))
        fj = json.load(open(os.path.join(DATA, "fits", f"{sid}.json")))
        st = fj["fit"]["static"]
        prob = Problem(vv.t.values, np.ones(len(vv)), np.ones(len(vv)), np.array(["G"] * len(vv)), blend=True)
        pred = prob.model([st["t0"], st["tE"], st["u0"], st["fs"].get("G", 1.0)])
        vv["gaia_model"] = pred
        lines = []
        for x in vv[inw].itertuples():
            lines.append(f"{mjd2date(x.t)}: W1 {x.d1:+.2f} W2 {x.d2:+.2f} (x{10 ** (-0.4 * x.d1):.2f}/x{10 ** (-0.4 * x.d2):.2f}; "
                         f"Gaia lens model x{x.gaia_model:.2f})")
        thr1, thr2 = max(0.25, 5 * rms1), max(0.25, 5 * rms2)
        rep = vv[~inw & (vv.d1 < -thr1) & (vv.d2 < -thr2)]
        best = vv[inw].sort_values("d1").head(1)
        rec.update(nw_status="ok", nw_n_visits=len(vv), nw_rms_W1=round(rms1, 3), nw_rms_W2=round(rms2, 3),
                   nw_in_event=" | ".join(lines) if lines else "no visit in the event window",
                   nw_best_dW1=round(float(best.d1.iloc[0]), 3) if len(best) else None,
                   nw_best_dW2=round(float(best.d2.iloc[0]), 3) if len(best) else None,
                   nw_best_date=mjd2date(best.t.iloc[0]) if len(best) else None,
                   nw_best_gaia_model=round(float(best.gaia_model.iloc[0]), 3) if len(best) else None,
                   nw_repeats=";".join(f"{mjd2date(x.t)}:{x.d1:+.2f}/{x.d2:+.2f}" for x in rep.itertuples()),
                   nw_max_other_dW1=round(float(vv[~inw].d1.min()), 3))
        rows.append(rec)
        print(sid, rec["nw_in_event"], "| repeats:", rec["nw_repeats"] or "-", "| rms", rec["nw_rms_W1"], flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "neowise_event.csv"), index=False)


if __name__ == "__main__":
    main()
