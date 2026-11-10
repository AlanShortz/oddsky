"""Two points per star: population variability from stars a telescope measured only twice (H-0019).

One pair of visits says almost nothing about one star. Over a population, the distribution of the difference is a
measurement: the fraction of stars above the red-giant tip that change by more than x mag between two visits, minus the
same fraction among stars just below the tip seen in the same two images. The control removes photometric noise that is
shared (crowding, cross-programme systematics) and is itself slightly variable, so a reference built from a monitored
population (OGLE in the Magellanic Clouds) must subtract the same box. `simulate_two_visits` does that.

Nothing here calls the network. Detections come from `oddsky.data.hsc.visits`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CI_RANGE = (0.85, 1.30)   # concentration index of a point source in ACS/WFC
LONG_DAYS, SHORT_DAYS = 100.0, 10.0


def tip_edge(mag: np.ndarray, predicted: float, half_window: float = 0.5, step: float = 0.05) -> tuple[float, float]:
    """Sobel edge of a luminosity function within `half_window` of the predicted tip: (magnitude, significance).
    Returns (nan, 0) with fewer than 200 stars."""
    bins = np.arange(predicted - 1.5, predicted + 1.3, step)
    h, e = np.histogram(mag, bins=bins)
    if h.sum() < 200:
        return float("nan"), 0.0
    hs = np.convolve(h, np.ones(3) / 3, mode="same")
    sob = np.zeros(len(h))
    sob[2:-2] = (hs[4:] + hs[3:-1] - hs[1:-3] - hs[:-4]) / np.sqrt(hs[4:] + hs[3:-1] + hs[1:-3] + hs[:-4] + 1)
    c = (e[:-1] + e[1:]) / 2
    ok = np.abs(c - predicted) <= half_window
    i = int(np.argmax(np.where(ok, sob, -9)))
    return float(c[i]), float(sob[i])


def star_pairs(det: pd.DataFrame, long_days: float = LONG_DAYS, short_days: float = SHORT_DAYS) -> pd.DataFrame:
    """One long pair (first and last clean detection, at least `long_days` apart) and one short pair (the two closest in
    time, under `short_days`) per star. `det` needs MatchID, ImageID, StartMJD, MagAper2, CI, Flags.

    Columns: MatchID, kind ("long" | "short"), img1, img2, mjd1, lag, mag1, mag2, mag (mean), dmag (later minus earlier).
    """
    d = det[(det.CI > CI_RANGE[0]) & (det.CI < CI_RANGE[1]) & (det.Flags == 0)]
    d = d.groupby(["MatchID", "ImageID"], as_index=False).agg(mjd=("StartMJD", "mean"), mag=("MagAper2", "mean"), n=("MagAper2", "size"))
    d = d[d.n == 1].sort_values(["MatchID", "mjd"])
    g = d.groupby("MatchID")
    first, last = g.first(), g.last()
    lp = pd.DataFrame({"img1": first.ImageID, "img2": last.ImageID, "mjd1": first.mjd, "lag": last.mjd - first.mjd,
                       "mag1": first.mag, "mag2": last.mag})
    lp = lp[lp.lag >= long_days]
    d = d.assign(dt=g.mjd.diff(), pmag=g.mag.shift(), pimg=g.ImageID.shift())
    s = d[(d.dt > 0) & (d.dt < short_days)].sort_values("dt").groupby("MatchID").first()
    sp = pd.DataFrame({"img1": s.pimg.astype("int64"), "img2": s.ImageID, "mjd1": s.mjd - s.dt, "lag": s.dt, "mag1": s.pmag, "mag2": s.mag})
    out = []
    for kind, p in (("long", lp), ("short", sp)):
        p = p.assign(kind=kind, mag=(p.mag1 + p.mag2) / 2, dmag=p.mag2 - p.mag1)
        out.append(p.reset_index())
    return pd.concat(out, ignore_index=True)


def remove_zero_points(p: pd.DataFrame, min_stars: int = 30) -> pd.DataFrame:
    """Subtract each image pair's median difference; drop image pairs with fewer than `min_stars`. Adds column `d`."""
    grp = p.groupby(["kind", "img1", "img2"]).dmag
    p = p.assign(d=p.dmag - grp.transform("median"), nimg=grp.transform("size"))
    return p[p.nimg >= min_stars]


def excess(d_target: np.ndarray, d_control: np.ndarray, x: float = 0.3) -> dict:
    """E_x = f_target(|d| > x) - f_control(|d| > x) with its binomial error."""
    n1, n2 = len(d_target), len(d_control)
    if not n1 or not n2:
        return {"E": float("nan"), "se": float("nan"), "n_target": n1, "n_control": n2}
    f1, f2 = float((np.abs(d_target) > x).mean()), float((np.abs(d_control) > x).mean())
    return {"E": f1 - f2, "se": float(np.sqrt(f1 * (1 - f1) / n1 + f2 * (1 - f2) / n2)), "f_target": f1, "f_control": f2,
            "n_target": n1, "n_control": n2}


def simulate_two_visits(mean_mag: np.ndarray, periods: np.ndarray, amplitudes: np.ndarray, lag_days: float, noise: float = 0.03,
                        reps: int = 60, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Two visits `lag_days` apart at random phase for stars with up to k sinusoidal periods.

    `periods` and `amplitudes` (peak to peak, mag) have shape (n_stars, k); a zero amplitude is a constant star.
    Returns (two-visit mean magnitude, difference), each of shape (reps, n_stars), with Gaussian `noise` on the difference.
    """
    rng = np.random.default_rng(seed)
    n = len(mean_mag)
    m1 = np.tile(np.asarray(mean_mag, float), (reps, 1))
    m2 = m1.copy()
    P = np.where(np.isfinite(periods) & (periods > 0), periods, 1.0)
    A = np.nan_to_num(amplitudes)
    for k in range(P.shape[1]):
        ph = rng.uniform(0, 2 * np.pi, (reps, n))
        m1 += A[:, k] / 2 * np.sin(ph)
        m2 += A[:, k] / 2 * np.sin(ph + 2 * np.pi * lag_days / P[:, k])
    m1 += rng.normal(0, noise / np.sqrt(2), m1.shape)
    m2 += rng.normal(0, noise / np.sqrt(2), m2.shape)
    return (m1 + m2) / 2, m2 - m1
