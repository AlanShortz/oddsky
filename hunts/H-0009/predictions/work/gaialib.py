"""Shared helpers: GOST transit times (barycentric MJD, the time system of Gaia epoch photometry) and a replica of the
Oddsky grader (oddsky.tools.evaluate) for Monte Carlo."""
import os

import numpy as np
import pandas as pd
from targets import HERE

DR4 = (56863.44, 58868.0)  # 2014-07-25 .. 2020-01-20


def gost(k):
    g = pd.read_csv(os.path.join(HERE, "gost", f"gost_{k}.csv"), skipinitialspace=True)
    t = g["ObservationTimeAtBarycentre[BarycentricJulianDateInTCB]"].astype(float).to_numpy() - 2400000.5
    t = np.sort(t)
    return t[(t >= DR4[0]) & (t <= DR4[1])]


def nightly(t, m):
    """stats.daily_bins(win, 1.0): bins on floor(t_mjd), median mag per bin."""
    key = np.floor(t)
    return pd.Series(m).groupby(key).median().to_numpy()


def grade(t, m, c):
    """c: dict(start, end, statistic, baseline (tuple|None), op, value). Returns 'true'/'false'/'unresolvable'."""
    s = (t >= c["start"]) & (t <= c["end"])
    if s.sum() < 3:
        return "unresolvable"
    w = m[s]
    nm = nightly(t[s], w)
    val = {"median": np.median(w), "faintest": nm.max(), "brightest": nm.min(), "amplitude": nm.max() - nm.min()}[c["statistic"]]
    if c.get("baseline"):
        b = (t >= c["baseline"][0]) & (t <= c["baseline"][1])
        if b.sum() < 3:
            return "unresolvable"
        if c["statistic"] != "amplitude":
            val = val - np.median(m[b])
    ok = val > c["value"] if c["op"] == ">" else val < c["value"]
    return "true" if ok else "false"


def sigma_G(G):
    """Per-transit G scatter (mag) for a constant star, from the DR3 epoch-photometry noise floor (Riello+2021,
    Fig. 9-ish): ~1 mmag at 13, 3 mmag at 15, 8 at 17, 13 at 18, 20 at 18.5, 30 at 19. Conservative x1.5 for crowding."""
    g = np.array([12, 13, 15, 16, 17, 18, 18.5, 19, 20])
    s = np.array([0.0012, 0.0015, 0.003, 0.005, 0.008, 0.013, 0.020, 0.030, 0.06])
    return 1.5 * float(np.interp(G, g, s))


def simulate(t_all, dm, G, rng, loss=0.10, out_rate=0.02, flag_bright=None):
    """One realisation of the observed Gaia G series: dm (mag offset from baseline at every GOST transit; dm may be
    brighter than G so noise is evaluated at the transit's own magnitude), 10% of transits lost, per-transit noise,
    2% outliers of +-0.2..1 mag, timing jitter 0.1 d (GOST times good to ~hours)."""
    keep = rng.random(len(t_all)) > loss
    t = t_all[keep] + rng.normal(0, 0.05, keep.sum())
    mag = G + dm[keep]
    sig = np.array([sigma_G(x) for x in mag])
    m = mag + rng.normal(0, 1, keep.sum()) * sig
    o = rng.random(len(t)) < out_rate
    m[o] += rng.choice([-1, 1], o.sum()) * rng.uniform(0.2, 1.0, o.sum())
    if flag_bright is not None:  # photometry-reject drop of the brightest transits (pessimistic case)
        ok = m - np.median(m) > flag_bright
        t, m = t[ok], m[ok]
    return t, m
