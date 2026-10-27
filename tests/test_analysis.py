import numpy as np
import pandas as pd

from oddsky.analysis import color, excursions, periodogram, stats


def test_periodogram_recovers_period_and_flags_yearly_alias(rng):
    t = np.sort(rng.uniform(0, 2000, 600))
    t = t[(t % 365.25) < 250]  # seasonal gaps
    y = 10 + 0.5 * np.sin(2 * np.pi * t / 37.3) + rng.normal(0, 0.05, t.size)
    out = periodogram.periodogram(pd.DataFrame(dict(t_mjd=t, mag=y, err=0.05)), min_period=2, max_period=500)
    assert abs(out["peaks"][0]["period_days"] - 37.3) < 0.3
    assert not out["peaks"][0]["alias_flags"]
    assert any(abs(p - 365.25) / 365.25 < 0.1 for p in out["window_peaks_days"])


def test_excursions_finds_the_dip_and_its_shape(rng):
    t = np.arange(0, 1000, 1.0)
    m = 12 + rng.normal(0, 0.01, t.size)
    sel = (t >= 400) & (t <= 430)
    m[sel] += np.interp(t[sel], [400, 405, 430], [0, 0.4, 0])  # fast ingress, slow egress
    ex = excursions.excursions(pd.DataFrame(dict(t_mjd=t, mag=m, err=0.01)), min_depth=0.05)
    ev = ex["events"][0]
    assert ev["direction"] == "fainter"
    assert 0.3 < ev["depth_mag"] < 0.45
    assert 400 <= ev["peak_mjd"] <= 410
    assert ev["asymmetry"] > 0.3  # egress longer than ingress


def test_changepoint_finds_the_step():
    t = np.arange(0, 20.0)
    m = np.where(t < 12, 11.0, 10.5)
    cp = stats.changepoint(pd.DataFrame(dict(t_mjd=t, mag=m, err=0.01)))
    assert 11 <= cp["t_change_mjd"] <= 12
    assert cp["direction"] == "brighter"
    assert abs(cp["step_mag"] + 0.5) < 1e-9


def test_wise_color_reddens_when_brighter(dusty_case):
    out = color.wise_color(dusty_case.series("neowise"))
    assert out["corr_W1_vs_color"] < -0.9
    assert out["w1_minus_w2_range"] > 0.3


def test_cross_band_slope_for_dust(dusty_case):
    a = dusty_case.series("aavso")
    out = color.cross_band(a[a.band == "B"], a[a.band == "V"], "B", "V", tol_days=0.5)
    assert out["pearson_r"] > 0.9
    assert abs(out["slope_dA_dB"] - 1.3) < 0.1


def test_eclipse_period_finds_rare_deep_eclipses(dusty_case, rng):
    import pandas as pd

    from oddsky.tools import Toolbox

    t = np.sort(rng.uniform(58000, 60500, 1500))
    P, T0 = 2.5296, 58001.3
    ph = ((t - T0) / P + 0.5) % 1 - 0.5
    m = 15.0 + rng.normal(0, 0.02, t.size) + np.where(np.abs(ph) < 0.02, 0.9, 0.0)
    dusty_case.write_series("ztf", pd.DataFrame(dict(t_mjd=t, mag=m, err=0.02, band="ZTF_r", survey="ZTF", flag="")))
    out = Toolbox().eclipse_period("OS-0001", ["ZTF:ZTF_r"], p_min=1.0, p_max=10.0)
    assert abs(out["period_days"] - P) < 1e-3
    assert out["frac_dim_within_0.04_phase"] > 0.9
