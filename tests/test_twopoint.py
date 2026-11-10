import numpy as np
import pandas as pd

from oddsky.analysis import twopoint
from oddsky.data import hsc


def _detections(n_stars=400, seed=3):
    """Three visits (day 0, day 2, day 500); a quarter of the stars brighten by 0.6 mag at the last one."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_stars):
        base = rng.uniform(20, 22)
        for img, mjd in ((1, 55000.0), (2, 55002.0), (3, 55500.0)):
            jump = -0.6 if (i % 4 == 0 and img == 3) else 0.0
            rows.append(dict(MatchID=i, SourceID=i * 10 + img, ImageID=img, StartMJD=mjd, MagAper2=base + jump + rng.normal(0, 0.02),
                             CI=1.05, Flags=0, Detector="ACS/WFC", Filter="F814W", MatchRA=10.0, MatchDec=20.0, PropID=1))
    return pd.DataFrame(rows)


def test_star_pairs_gives_one_long_and_one_short_pair_per_star():
    p = twopoint.star_pairs(_detections())
    assert set(p.kind) == {"long", "short"}
    assert (p[p.kind == "long"].groupby("MatchID").size() == 1).all()
    assert np.allclose(p[p.kind == "long"].lag, 500.0) and np.allclose(p[p.kind == "short"].lag, 2.0)


def test_excess_recovers_the_injected_fraction_and_short_pairs_are_quiet():
    p = twopoint.remove_zero_points(twopoint.star_pairs(_detections()))
    long, short = p[p.kind == "long"], p[p.kind == "short"]
    e = twopoint.excess(long.d.values, short.d.values, 0.3)
    assert abs(e["E"] - 0.25) < 0.03 and e["f_control"] == 0.0


def test_bad_detections_are_dropped():
    det = _detections(50)
    det.loc[det.ImageID == 3, "Flags"] = 5     # every late detection flagged: no long pair survives
    p = twopoint.star_pairs(det)
    assert (p.kind == "short").all()


def test_tip_edge_finds_a_step_in_the_luminosity_function():
    rng = np.random.default_rng(1)
    mag = np.concatenate([rng.uniform(22.0, 24.0, 300), rng.uniform(23.0, 24.0, 6000)])
    edge, sig = twopoint.tip_edge(mag, predicted=23.1)
    assert abs(edge - 23.0) < 0.1 and sig > 4


def test_simulated_constant_stars_show_only_noise_and_miras_show_changes():
    mean = np.full(500, 14.0)
    const = twopoint.simulate_two_visits(mean, np.ones((500, 1)), np.zeros((500, 1)), 400.0)[1]
    mira = twopoint.simulate_two_visits(mean, np.full((500, 1), 300.0), np.full((500, 1), 2.0), 400.0)[1]
    assert (np.abs(const) > 0.3).mean() < 1e-3 and (np.abs(mira) > 0.3).mean() > 0.7


def test_hsc_pairs_averages_split_detections_and_orders_by_time():
    det = _detections(5)
    p = hsc.pairs(det, min_lag_days=100)
    assert len(p) == 10 and (p.lag > 100).all() and (p.mjd2 > p.mjd1).all()
