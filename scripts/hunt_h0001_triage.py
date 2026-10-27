"""Hunt H-0001, step 2: pull Gaia epoch photometry for every candidate and score its dimming.

For each star (G, BP, RP per transit, 2014-2017):
  depth      how far the faintest real points fall below the star's median (robust)
  n_dim      transits more than 0.1 mag below median
  pairs      dim transits confirmed by the paired field-of-view transit ~2 h apart
  chroma     BP drop / RP drop on dim transits (dust: > 1; grey or geometric: ~1; artifacts: anything)
  periodic   Lomb-Scargle power of the best period (eclipsing binaries the classifier missed)
Writes hunts/H-0001/triage.csv and caches light curves in hunts/H-0001/epoch/.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

from oddsky.data import gaia_epoch

here = Path("hunts/H-0001")
cache = here / "epoch"
cache.mkdir(exist_ok=True)
cand = pd.read_csv(here / "candidates.csv")
cand = cand[cand.gaia_eb.astype(str).str.lower() != "true"]
print(len(cand), "candidates after dropping Gaia eclipsing binaries", flush=True)

todo = [s for s in cand.source_id if not (cache / f"{s}.parquet").exists()]
for i in range(0, len(todo), 50):
    got = gaia_epoch.fetch(todo[i:i + 50])
    for sid, df in got.items():
        df.to_parquet(cache / f"{sid}.parquet", index=False)
    print(f"fetched {min(i + 50, len(todo))}/{len(todo)}", flush=True)


def score(df: pd.DataFrame) -> dict:
    g = df[(df.band == "G") & df.flag.isin(["", "rejected_by_variability"])].sort_values("t_mjd")
    if len(g) < 15:
        return {}
    med = np.median(g.mag)
    mad = 1.4826 * np.median(np.abs(g.mag - med))
    dim = g[g.mag > med + max(0.1, 5 * mad)]
    out = dict(n_g=len(g), g_med=med, g_mad=mad, depth=float(np.percentile(g.mag, 99) - med) if len(g) else 0,
               max_depth=float(g.mag.max() - med), n_dim=len(dim))
    # A paired transit: the other field of view sees the same spot ~106 min later.
    t = g.t_mjd.to_numpy()
    paired = 0
    for td in dim.t_mjd:
        near = g[(np.abs(g.t_mjd - td) < 0.2) & (g.t_mjd != td)]
        if len(near) and (near.mag > med + max(0.05, 3 * mad)).any():
            paired += 1
    out["n_dim_paired"] = paired
    # Distinct dimming episodes (transits more than 10 d apart).
    out["n_episodes"] = int(1 + np.sum(np.diff(np.sort(dim.t_mjd.to_numpy())) > 10)) if len(dim) else 0
    # Colour of the dimming from BP/RP on the same transits.
    bp, rp = df[(df.band == "BP") & (df.flag == "")], df[(df.band == "RP") & (df.flag == "")]
    if len(dim) and len(bp) > 10 and len(rp) > 10:
        bmed, rmed = np.median(bp.mag), np.median(rp.mag)
        db = [bp.mag[np.abs(bp.t_mjd - td) < 0.01].median() - bmed for td in dim.t_mjd]
        dr = [rp.mag[np.abs(rp.t_mjd - td) < 0.01].median() - rmed for td in dim.t_mjd]
        db, dr = np.nanmedian(db), np.nanmedian(dr)
        out.update(d_bp=float(db), d_rp=float(dr), chroma=float(db / dr) if dr and np.isfinite(dr) and dr > 0.02 else np.nan)
    # Periodicity: strong, clean periods mean an eclipsing binary or pulsator, not a dipper.
    try:
        freq = np.linspace(1 / 500, 1 / 0.2, 40000)
        p = LombScargle(t, g.mag.to_numpy()).power(freq, method="fast")
        k = int(np.argmax(p))
        out.update(best_period=float(1 / freq[k]), best_power=float(p[k]))
    except Exception:  # noqa: BLE001
        pass
    out["span_days"] = float(t.max() - t.min())
    return out


rows = []
for sid in cand.source_id:
    f = cache / f"{sid}.parquet"
    if f.exists():
        rows.append({"source_id": sid, **score(pd.read_parquet(f))})
tri = cand.merge(pd.DataFrame(rows), on="source_id", how="left")
tri.to_csv(here / "triage.csv", index=False)
print(len(tri), "scored", flush=True)
sys.exit(0)
