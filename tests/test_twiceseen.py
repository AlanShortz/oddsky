import numpy as np
import pandas as pd

from oddsky.analysis import twiceseen


def _field(n=30000, seed=7, m50=24.0, offset=(0.6, -0.4), blend=0.0):
    """A deep truth catalogue and a shallow test catalogue of the same 100 x 100 arcsec field. The test catalogue is
    shifted, rotated by 0.02 degrees, loses stars along a logistic curve with half-recovery at `m50`, and has 0.04 mag noise."""
    rng = np.random.default_rng(seed)
    x, y = rng.uniform(-50, 50, n), rng.uniform(-50, 50, n)
    mag = 20 + 6.5 * rng.power(3.0, n)                   # rising luminosity function, 20 to 26.5
    dec0 = 30.0
    truth = pd.DataFrame({"ra": 150 + x / 3600 / np.cos(np.radians(dec0)), "dec": dec0 + y / 3600, "mag": mag})
    keep = rng.uniform(size=n) < 1 / (1 + np.exp((mag - m50) / 0.25))
    th = np.radians(0.02)
    xs = x * np.cos(th) - y * np.sin(th) + offset[0] + rng.normal(0, 0.01, n)
    ys = x * np.sin(th) + y * np.cos(th) + offset[1] + rng.normal(0, 0.01, n)
    test = pd.DataFrame({"ra": 150 + xs / 3600 / np.cos(np.radians(dec0)), "dec": dec0 + ys / 3600,
                         "mag": mag + rng.normal(0, 0.04, n) - blend})[keep].reset_index(drop=True)
    return truth, test


def test_the_planted_half_recovery_magnitude_comes_back_despite_an_offset_and_a_rotation():
    truth, test = _field(m50=24.0)
    q = twiceseen.quality(truth, test)
    lim = twiceseen.limit(q["table"])
    assert abs(lim["mag"] - 24.0) < 0.08 and lim["valid"]
    assert q["tie_rms_arcsec"] < 0.03 and q["n_chance"] < 0.08 * q["n_matched"]   # 3 stars per arcsec^2: 4.6% by chance


def test_bright_stars_are_complete_and_the_scatter_is_the_planted_noise():
    truth, test = _field()
    t = twiceseen.quality(truth, test)["table"]
    bright = t[(t.crowding == "all") & (t.mag < 22.5)]
    assert (bright.completeness > 0.97).all()
    assert abs(bright.scatter.median() - 0.04) < 0.01 and abs(bright.offset.median()) < 0.01


def test_a_constant_brightening_is_absorbed_by_the_zero_point_and_reported():
    truth, test = _field(blend=0.10)
    q = twiceseen.quality(truth, test)
    assert abs(q["zero_point"] + 0.10) < 0.01


def test_rows_fainter_than_the_truth_catalogues_horizon_are_marked_invalid():
    truth, test = _field()
    q = twiceseen.quality(truth, test)
    t = q["table"]
    assert q["horizon"] < truth.mag.max() - 0.9
    assert not t[t.mag > q["horizon"] + 0.2].valid.any() and t[t.mag < q["horizon"] - 0.2].valid.all()


def test_catalogues_of_different_fields_are_refused():
    truth, test = _field(n=3000)
    test = test.assign(ra=test.ra + 1.0)
    try:
        twiceseen.quality(truth, test)
    except ValueError:
        return
    raise AssertionError("expected a refusal")


def test_chance_matches_in_a_dense_field_do_not_inflate_completeness_at_the_faint_end():
    truth, test = _field(n=60000, m50=23.0)
    t = twiceseen.quality(truth, test)["table"]
    faint = t[(t.crowding == "all") & (t.mag > 24.5) & (t.mag < 25.3)]
    assert (faint.raw_recovered > faint.completeness).all() and faint.completeness.max() < 0.03


def test_a_mirrored_field_is_refused_because_its_matches_are_no_better_than_chance():
    truth, test = _field(n=20000)
    test = test.assign(ra=2 * 150.0 - test.ra)
    try:
        twiceseen.quality(truth, test)
    except ValueError:
        return
    raise AssertionError("expected a refusal")


def test_a_star_seen_but_moved_is_counted_as_displaced_not_lost():
    truth, test = _field(n=8000, m50=30.0)
    rng = np.random.default_rng(5)
    moved = rng.uniform(size=len(test)) < 0.2
    test.loc[moved, "dec"] += 0.15 / 3600
    t = twiceseen.quality(truth, test)["table"]
    row = t[(t.crowding == "all") & (t.mag < 24)]
    assert abs(np.average(row.displaced, weights=row.n) - 0.2) < 0.04 and abs(np.average(row.completeness, weights=row.n) - 0.8) < 0.04


def test_fainter_truth_stars_still_count_as_neighbours_when_only_bright_ones_are_graded():
    truth, test = _field(n=60000)
    full = twiceseen.quality(truth, test, mag_max=24.5)["stars"]
    cut = twiceseen.quality(truth[truth.mag < 24.5].reset_index(drop=True), test)["stars"]
    assert (full.crowd > 0).mean() > (cut.crowd > 0).mean() + 0.03
