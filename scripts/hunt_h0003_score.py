"""Hunt H-0003, step 3: score each Gaia light curve for R CrB-likeness.

An R CrB decline: from a steady maximum the star drops by magnitudes within days to weeks (soot
condensing in the line of sight), then claws back over months. A Mira swings smoothly and
periodically; an Algol dips briefly and periodically; a young star's fades are shallow and frequent.

Features (Gaia G, rejected_by_variability points kept: the deepest decline points are often the ones
Gaia's own pipeline rejected):
  bright      5th-percentile magnitude (the maximum light level)
  depth       faintest minus bright
  frac_max    fraction of transits within 0.4 mag of maximum (R CrB: high)
  fade_rate   steepest fade between transits 1-60 d apart (mag/day)
  rise_rate   steepest brightening on the same terms (R CrB: slower than fade_rate)
  ls_power    strongest Lomb-Scargle peak 20-1000 d (Mira: high)
"""
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

here = Path("hunts/H-0003")
cand = pd.read_csv(here / "candidates.csv").set_index("source_id")


def score(df):
    g = df[(df.band == "G") & df.flag.isin(["", "rejected_by_variability"])].sort_values("t_mjd")
    g = g.groupby(g.t_mjd.round(1)).agg(t_mjd=("t_mjd", "median"), mag=("mag", "median")).reset_index(drop=True)
    if len(g) < 12:
        return {}
    t, m = g.t_mjd.to_numpy(), g.mag.to_numpy()
    bright = np.percentile(m, 5)
    depth = m.max() - bright
    frac_max = float(np.mean(m < bright + 0.4))
    fade, rise = 0.0, 0.0
    for i in range(len(t)):
        dt = t[i + 1:] - t[i]
        dm = m[i + 1:] - m[i]
        ok = (dt >= 1) & (dt <= 60)
        if ok.any():
            fade = max(fade, float(np.max(dm[ok] / dt[ok])))
            rise = max(rise, float(np.max(-dm[ok] / dt[ok])))
    try:
        f = np.linspace(1 / 1000, 1 / 20, 5000)
        p = LombScargle(t, m).power(f)
        k = int(np.argmax(p))
        lsp, lsper = float(p[k]), float(1 / f[k])
    except Exception:  # noqa: BLE001
        lsp, lsper = np.nan, np.nan
    deep = t[m > bright + 1.0]
    n_deep, deep_span = len(deep), float(deep.max() - deep.min()) if len(deep) else 0.0
    bp = df[(df.band == "BP") & (df.flag == "")].mag
    rp = df[(df.band == "RP") & (df.flag == "")].mag
    return dict(n=len(g), bright=bright, depth=depth, n_deep=n_deep, deep_span=deep_span, frac_max=frac_max, fade_rate=fade, rise_rate=rise,
                ls_power=lsp, ls_period=lsper, bp_rp_bright=float(np.percentile(bp, 5) - np.percentile(rp, 5))
                if len(bp) > 5 and len(rp) > 5 else np.nan)


rows = [{"source_id": int(f.stem), **score(pd.read_parquet(f))} for f in sorted((here / "epoch").glob("*.parquet"))]
sc = pd.DataFrame(rows).set_index("source_id").join(cand, how="left")
# A real decline lasts months: several deep transits spread over weeks, not one deep blip.
sc["rcb_like"] = ((sc.depth >= 2.0) & (sc.n_deep >= 4) & (sc.deep_span >= 20) & (sc.frac_max >= 0.3)
                  & (sc.fade_rate >= 0.05) & (sc.ls_power < 0.5) & (sc.fade_rate > sc.rise_rate))
sc.to_csv(here / "scored.csv")
print(len(sc), "scored;", int(sc.rcb_like.sum()), "R CrB-like")
