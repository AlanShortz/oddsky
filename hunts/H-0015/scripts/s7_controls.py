"""H-0015 s7: the false-positive control sample (referee requirement 6), fetched before the Gaia archive closes.

For each F1 target (predictions/dr4_astrometric_sample.csv), three Gaia DR3 stars within 6' (so the same scanning law and a
similar crowding), with |G - G_target| <= 0.3, a five- or six-parameter solution, RUWE <= 1.4, not flagged VARIABLE, and
more than 10" from every target; chosen by DR3's `random_index` (reproducible), then three of up to 20 by a seeded draw.
Each control gets a fake event hint (t0, tE range) drawn from a different F1 target, so that on release day it goes
through exactly the same stage as the targets with nothing to find. Its rate of significant deflections is forecast F5.

Small async TAP jobs through the polite H-0014 client, one cone per target; every failure is recorded in
data/controls_errors.jsonl (a failed cone means fewer controls for that target, never a silent empty result).
Output: data/controls.csv. Run: uv run python -I hunts/H-0015/scripts/s7_controls.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, HUNT  # noqa: E402

from oddsky.dr4day.archive import Archive  # noqa: E402
from oddsky.dr4day.config import release  # noqa: E402

PER_TARGET = 3
RADIUS_DEG = 0.1
DG = 0.3


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    smp = pd.read_csv(HUNT / "predictions/dr4_astrometric_sample.csv", dtype={"source_id": str})
    f1 = smp[smp.forecast.str.contains("F1")]
    R = pd.read_csv(DATA / "ranked_targets.csv", dtype={"source_id": str})
    allt = R[["source_id", "ra", "dec"]]
    tgt = f1.merge(R[["source_id", "ra", "dec"]], on="source_id", how="left")
    arc = Archive(release("dr3"))
    rng = np.random.default_rng(20261102)
    rows, errors = [], []
    for r in tgt.itertuples():
        q = (f"SELECT TOP 20 source_id, ra, dec, phot_g_mean_mag, bp_rp, parallax, parallax_error, pmra, pmdec, pmra_error, "
             f"pmdec_error, ruwe, astrometric_params_solved, astrometric_excess_noise, ipd_frac_multi_peak, phot_variable_flag, "
             f"l, b, random_index FROM gaiadr3.gaia_source WHERE 1 = CONTAINS(POINT(ra, dec), CIRCLE({r.ra!r}, {r.dec!r}, "
             f"{RADIUS_DEG})) AND phot_g_mean_mag BETWEEN {r.G - DG:.3f} AND {r.G + DG:.3f} AND ruwe <= 1.4 "
             f"AND astrometric_params_solved > 3 AND source_id <> {r.source_id} ORDER BY random_index")
        try:
            d = arc.tap(q, sync=True)
        except Exception as e:  # noqa: BLE001
            errors.append({"target": r.source_id, "error": f"{type(e).__name__}: {e}"[:400]})
            continue
        if d.empty:
            errors.append({"target": r.source_id, "error": "no star passes the cuts within 6'"})
            continue
        d = d[d.phot_variable_flag.astype(str) != "VARIABLE"]
        # more than 10" from every target
        far = np.ones(len(d), bool)
        for x in allt.itertuples():
            sep = np.hypot((d.ra - x.ra) * np.cos(np.radians(x.dec)), d.dec - x.dec) * 3600
            far &= sep.to_numpy() > 10
        d = d[far]
        pick = d.iloc[rng.choice(len(d), size=min(PER_TARGET, len(d)), replace=False)] if len(d) else d
        for c in pick.itertuples():
            h = tgt.iloc[rng.integers(len(tgt))]          # a fake hint from another F1 target
            while h.source_id == r.source_id and len(tgt) > 1:
                h = tgt.iloc[rng.integers(len(tgt))]
            rows.append(dict(source_id=str(c.source_id), matched_target=r.source_id, ra=c.ra, dec=c.dec, G=c.phot_g_mean_mag,
                             bp_rp=c.bp_rp, parallax=c.parallax, pmra=c.pmra, pmdec=c.pmdec, ruwe=c.ruwe,
                             astrometric_params_solved=c.astrometric_params_solved,
                             astrometric_excess_noise=c.astrometric_excess_noise, ipd_frac_multi_peak=c.ipd_frac_multi_peak,
                             l=c.l, b=c.b, hint_from=h.source_id, t0=h.t0, tE_lo=h.tE_lo, tE_hi=h.tE_hi))
    out = pd.DataFrame(rows).drop_duplicates("source_id")
    out.insert(0, "name", ["CTRL-" + s for s in out.source_id])
    out.to_csv(DATA / "controls.csv", index=False, float_format="%.10g")
    with open(DATA / "controls_errors.jsonl", "w") as f:
        for e in errors + arc.errors:
            f.write(json.dumps(e, default=str) + "\n")
    print(f"{len(out)} controls for {out.matched_target.nunique()} of {len(tgt)} targets; {len(errors)} errors")


if __name__ == "__main__":
    main()
