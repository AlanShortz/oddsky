"""Hunt H-0001, step 2b: re-score cached Gaia epoch photometry with artifact-aware features.

Lessons from the first quick-look sheet:
  * single transits 3+ mag below the median are Gaia window artifacts, not stars (a Sun-like star
    does not lose 95% of its light for under two hours): quarantined as `spurious`;
  * repeated dips of identical depth are eclipsing binaries; dippers vary;
  * an event that several consecutive transits sample (a resolved dip) is worth more than a blip.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

here = Path("hunts/H-0001")
cand = pd.read_csv(here / "candidates.csv").set_index("source_id")


def episodes(t, m, med, thr, gap=2.0):
    """Group dim transits into events (gap > 2 d starts a new event)."""
    sel = m > med + thr
    ts, ms = t[sel], m[sel]
    if not len(ts):
        return []
    ev, cur = [], [0]
    for i in range(1, len(ts)):
        if ts[i] - ts[i - 1] > gap:
            ev.append(cur)
            cur = []
        cur.append(i)
    ev.append(cur)
    return [dict(t=float(np.median(ts[e])), depth=float(ms[e].max() - med), n=len(e),
                 dur=float(ts[e].max() - ts[e].min())) for e in ev]


def score(df):
    g = df[(df.band == "G") & df.flag.isin(["", "rejected_by_variability"])].sort_values("t_mjd")
    if len(g) < 15:
        return {}
    t, m = g.t_mjd.to_numpy(), g.mag.to_numpy()
    med = np.median(m)
    mad = 1.4826 * np.median(np.abs(m - med))
    spurious = m > med + 3.0
    t, m = t[~spurious], m[~spurious]
    thr = max(0.08, 5 * mad)
    ev = episodes(t, m, med, thr)
    # Paired-FOV confirmation per event: at least 2 transits in the event.
    confirmed = [e for e in ev if e["n"] >= 2]
    depths = np.array([e["depth"] for e in confirmed])
    out = dict(n_g=len(g), g_med=med, g_mad=mad, n_spurious=int(spurious.sum()), n_events=len(ev),
               n_confirmed=len(confirmed), max_depth=float(depths.max()) if len(depths) else 0.0,
               depth_cv=float(depths.std() / depths.mean()) if len(depths) >= 2 else np.nan,
               max_event_transits=max((e["n"] for e in ev), default=0),
               events=";".join(f"{e['t']:.1f}:{e['depth']:.2f}:{e['n']}" for e in ev[:8]))
    bp, rp = df[(df.band == "BP") & (df.flag == "")], df[(df.band == "RP") & (df.flag == "")]
    dimt = t[m > med + thr]
    if len(dimt) and len(bp) > 10 and len(rp) > 10:
        db = np.nanmedian([bp.mag[np.abs(bp.t_mjd - x) < 0.01].median() for x in dimt]) - np.median(bp.mag)
        dr = np.nanmedian([rp.mag[np.abs(rp.t_mjd - x) < 0.01].median() for x in dimt]) - np.median(rp.mag)
        out.update(d_bp=float(db), d_rp=float(dr), chroma=float(db / dr) if dr > 0.03 else np.nan)
    try:
        freq = np.linspace(1 / 600, 1 / 0.2, 60000)
        p = LombScargle(t, m).power(freq, method="fast")
        k = int(np.argmax(p))
        out.update(best_period=float(1 / freq[k]), best_power=float(p[k]))
    except Exception:  # noqa: BLE001
        pass
    return out


rows = []
for f in sorted((here / "epoch").glob("*.parquet")):
    rows.append({"source_id": int(f.stem), **score(pd.read_parquet(f))})
sc = pd.DataFrame(rows).set_index("source_id").join(cand, how="left")
sc.to_csv(here / "scored.csv")
# Interesting: >= 1 confirmed event of 0.15-3 mag, not a clean periodic signal.
pick = sc[(sc.max_depth >= 0.15) & (sc.n_confirmed >= 1)]
pick = pick.assign(rank=pick.max_depth * (1 + pick.n_confirmed) * (1 + pick.depth_cv.fillna(0.5))
                   * (1 - pick.best_power.fillna(0).clip(0, 0.9)))
pick.sort_values("rank", ascending=False).to_csv(here / "picks.csv")
print(len(sc), "scored;", len(pick), "picks;", int((sc.n_spurious > 0).sum()), "stars with spurious transits")
