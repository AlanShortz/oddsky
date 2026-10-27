import numpy as np
import pandas as pd
from conftest import make_series

from oddsky.analysis import fades


def sparse(rng, t0=58200.0, span=3000.0, every=3.0):
    """ATLAS-like sampling: roughly one night in three, with seasonal gaps."""
    t = np.arange(t0, t0 + span, every) + rng.uniform(0, 1, int(span / every))
    phase = (t % 365.25) / 365.25
    return t[(phase < 0.65) | (phase > 0.9)]


def rcb_curve(t, t_decline=59000.0):
    m = np.full(t.size, 12.0)
    d = t - t_decline
    fall = (d >= 0) & (d < 40)
    m[fall] += 3.5 * d[fall] / 40
    rec = d >= 40
    m[rec] += 3.5 * np.exp(-(d[rec] - 40) / 200)
    return m


def test_rcb_like_decline(rng):
    t = sparse(rng)
    m = rcb_curve(t) + rng.normal(0, 0.02, t.size)
    df = make_series(t, m, "ATLAS_o", "ATLAS", err=0.02)
    f = fades.rcb_features(df)
    assert f["band"] == "ATLAS_o"
    assert f["depth"] > 2.5
    assert f["decline_rate_mag_per_day"] > 0.05
    assert f["asymmetry"] is not None and f["asymmetry"] > 3
    assert f["max_frac"] > 0.5
    assert fades.classify_fade(f) == "rcb_like"


def test_ongoing_decline_counts(rng):
    t = sparse(rng, span=1500)
    m = rcb_curve(t, t_decline=t.max() - 60) + rng.normal(0, 0.02, t.size)
    f = fades.rcb_features(make_series(t, m, "ZTF_r", "ZTF", err=0.02))
    assert f["ongoing"] is True
    assert fades.classify_fade(f) == "rcb_like"


def test_mira(rng):
    t = sparse(rng)
    m = 13.0 + 2.0 * np.sin(2 * np.pi * t / 330.0) + rng.normal(0, 0.03, t.size)
    f = fades.rcb_features(make_series(t, m, "ATLAS_o", "ATLAS", err=0.03))
    assert f["ls_power"] > 0.6
    assert 300 < f["ls_period"] < 360
    assert fades.classify_fade(f) == "mira_like"


def test_symmetric_grey_eclipse(rng):
    t = sparse(rng, every=1.0)
    m = np.full(t.size, 12.0)
    d = np.abs(t - 59300)
    m[d < 30] += 1.5 * (1 - d[d < 30] / 30)
    m += rng.normal(0, 0.02, t.size)
    df = pd.concat([make_series(t, m, "ZTF_g", "ZTF", err=0.02), make_series(t, m - 0.5, "ZTF_r", "ZTF", err=0.02)])
    f = fades.rcb_features(df)
    assert fades.classify_fade(f) == "eclipse_like"
    col = fades.colour_during_fade(df, "ZTF_g", "ZTF_r", f["events"])
    assert col is not None and abs(col["delta_colour"]) < 0.05
    d = fades.disk_eclipse_features(df)
    assert d["candidate"] is True


def test_single_night_glitch_is_artifact(rng):
    t = sparse(rng)
    m = 12.0 + rng.normal(0, 0.02, t.size)
    m[len(m) // 2] = 15.5
    f = fades.rcb_features(make_series(t, m, "ATLAS_o", "ATLAS", err=0.02))
    # a lone night that disagrees with both neighbours is dropped before scoring, so nothing remains
    assert fades.classify_fade(f) in ("no_event", "artifact")
    assert f["depth"] == 0.0


def test_flat_star_has_no_event(rng):
    t = sparse(rng)
    m = 12.0 + rng.normal(0, 0.02, t.size)
    f = fades.rcb_features(make_series(t, m, "ATLAS_c", "ATLAS", err=0.02))
    assert f["depth"] == 0.0
    assert fades.classify_fade(f) == "no_event"


def test_limits_are_censored_depth(rng):
    t = sparse(rng)
    m = rcb_curve(t) + rng.normal(0, 0.02, t.size)
    df = make_series(t, m, "ATLAS_o", "ATLAS", err=0.02)
    deep = df.mag > 14.5
    df.loc[deep, "flag"] = "upper_limit"
    df.loc[deep, "mag"] = 14.5
    f = fades.rcb_features(df)
    assert f["depth_censored"] is True
    assert f["n_limits"] > 0
    assert fades.classify_fade(f) == "rcb_like"
