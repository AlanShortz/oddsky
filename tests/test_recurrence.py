"""Recurrent-outburst detector (oddsky.imaging.recurrence) and the Spitzer difference light curve
(oddsky.imaging.spitzer) on synthetic data with the WISE/NEOWISE cadence of the H-0012 light curves."""

import numpy as np
import pytest

from oddsky.imaging import recurrence as rc
from oddsky.imaging import spitzer

# WISE 2010.2, 2010.75, (2011.2), gap, NEOWISE-R 2014.25 ... 2024.2, two visit seasons
T = np.r_[2010.24, 2010.77, 2011.22, 2014.25 + 0.5 * np.arange(21)] + np.r_[0, 0.03, 0, np.tile([0, 0.03], 11)[:21]]
SEASON = np.r_[0, 1, 0, np.tile([0, 1], 11)[:21]]


def make_lc(signal_w1, signal_w2, err=(60.0, 130.0), seed=0, offsets=(0.0, 0.0)):
    rng = np.random.default_rng(seed)
    e = np.array([np.full(T.size, err[0]), np.full(T.size, err[1])])
    y = np.array([signal_w1, signal_w2]) + rng.normal(0, 1, e.shape) * e
    y += np.array(offsets)[:, None] * SEASON[None, :]  # season zero-point offsets (absorbed by the model)
    return rc.LightCurve(T.copy(), SEASON.copy(), y, e, np.arange(T.size))


def outbursts(P, t0, amp, tr=0.3, td=0.7):
    return amp * rc.periodic_template(T, P, t0, tr, td)


def test_train_profile_matches_explicit_sum():
    t = np.linspace(2000, 2030, 400)
    P, t0, tr, td = 4.3, 2003.1, 0.3, 0.9
    explicit = sum(rc.outburst_profile(t - (t0 + k * P), tr, td) for k in range(-40, 40))
    np.testing.assert_allclose(rc.train_profile(t, P, t0, tr, td), explicit, atol=1e-9)
    # time-reversed train: slow rise, fast fall
    rev = rc.train_profile(t, P, t0, tr, td, reverse=True)
    explicit_rev = sum(rc.outburst_profile(-(t - (t0 + k * P)), tr, td) for k in range(-40, 40))
    np.testing.assert_allclose(rev, explicit_rev, atol=1e-9)


def test_periodic_outbursts_recovered():
    lc = make_lc(outbursts(5.3, 2012.4, 400), outbursts(5.3, 2012.4, 1000), offsets=(80, -150))
    a = rc.analyse(lc)
    assert abs(a["P_yr"] / 5.3 - 1) < 0.08
    assert a["n_cycles_det"] >= 2
    assert a["F"] > rc.F_MIN
    assert a["R"] > rc.R_MIN  # the second outburst adds a lot over one
    v, why = rc.light_verdict(a)
    assert v == "recurrent", why
    assert a["colour"] == pytest.approx(-2.5 * np.log10(400 / 1000), abs=0.3)
    null = rc.shuffle_null(lc, 100, seed=1)
    assert rc.p_value(null, a["F"]) < 0.02


def test_single_outburst_is_not_recurrent():
    one = rc.outburst_profile(T - 2018.0, 0.3, 1.0)
    lc = make_lc(400 * one, 1000 * one, seed=2)
    a = rc.analyse(lc)
    v, why = rc.light_verdict(a)
    assert v != "recurrent"
    assert "single-outburst" in why or "no-cycle" in why


def test_mira_sinusoid_vetoed():
    P_d = 420.0
    s = np.sin(2 * np.pi * T * 365.25 / P_d + 0.4)
    lc = make_lc(600 * s, 900 * s, seed=3)
    a = rc.analyse(lc)
    assert a["P_sine_d"] < rc.LPV_P_D
    v, why = rc.light_verdict(a)
    assert v != "recurrent"


def test_noise_is_weak_and_not_significant():
    lc = make_lc(np.zeros(T.size), np.zeros(T.size), seed=4)
    a = rc.analyse(lc)
    assert a["F"] < rc.F_MIN
    null = rc.shuffle_null(lc, 60, seed=5)
    assert rc.p_value(null, a["F"]) > 0.05


def test_one_season_artefact_rejected():
    # bumps only in season 1 (a PSF-orientation artefact): the per-season check fails
    sig = outbursts(4.0, 2015.0, 900) * (SEASON == 1)
    lc = make_lc(0.4 * sig, sig, seed=6)
    a = rc.analyse(lc)
    v, why = rc.light_verdict(a)
    assert v != "recurrent"


def test_injection_into_light_curve():
    lc = make_lc(np.zeros(T.size), np.zeros(T.size), seed=7)
    inj = rc.inject(lc, 6.0, 2015.2, 0.3, 0.8, 300, 800)  # peaks 2015.2, 2021.2 (2009.2, 2027.2 outside)
    a = rc.analyse(inj)
    assert abs(a["P_yr"] / 6.0 - 1) < 0.1
    assert rc.light_verdict(a)[0] == "recurrent"


def test_phase_null_shapes_and_pvalue_floor():
    lc = make_lc(outbursts(5.0, 2012.0, 300), outbursts(5.0, 2012.0, 700), seed=8)
    null = rc.phase_null(lc, 20, seed=0)
    assert null.shape == (20,) and np.isfinite(null).all()
    assert rc.p_value(np.zeros(10), 1.0) == pytest.approx(1 / 11)


def test_fit_series_spitzer_plus_wise_finds_earlier_cycles():
    P, t0 = 5.3, 2007.25
    rng = np.random.default_rng(9)
    ts = np.sort(np.r_[2004.8, 2005.3, 2005.8, 2006.2, 2006.8, 2007.25, 2007.9, 2008.3, 2011.9, 2012.45, 2014.0,
                       2014.5, 2015.1, 2015.5, 2016.0, 2017.0, 2017.5, 2018.0, 2018.5, 2019.2, 2019.5])
    es = np.full(ts.size, 10.0)
    i2 = 240 * rc.periodic_template(ts, P, t0, 0.3, 0.7) + rng.normal(0, 10, ts.size)
    grp = (ts > 2009.5).astype(int)  # cryogenic / warm
    wise = make_lc(outbursts(P, t0, 300), outbursts(P, t0, 800), seed=10)
    ser = rc.series_from_lc(wise) + [rc.Series("I2", ts, i2, es, grp)]
    f = rc.fit_series(ser, return_all=True)
    assert abs(f["params"][0] / P - 1) < 0.03
    scale = max(1.0, f["chi2_fit"] / f["dof"])
    cyc = rc.cycles_series(ser, *f["params"], f["amps"], scale)
    det = [c for c in cyc if c["detected"]]
    assert len(det) >= 4  # 2007, 2012, 2017-18, 2023
    assert any(c["t_peak"] < 2009 and "I2" in c["instruments"] for c in det)
    prof = rc.period_profile(f, scale)
    assert prof["P_lo"] <= f["params"][0] <= prof["P_hi"]


def test_verdict_context_vetoes():
    a = dict(F=200, n_cycles_det=3, S=30, P_sine_d=2000, snr_s0=10, snr_s1=10, amp_w1=1, amp_w2=2, n_cycles_missing=0)
    assert rc.verdict(a, 0.001)[0] == "candidate"
    assert rc.verdict(a, 0.2)[0] == "rejected"
    assert rc.verdict(a, 0.001, ["moving"])[0] == "rejected"
    assert rc.verdict(a, 0.001, ["agn"])[0] == "flagged"


def test_spitzer_difference_lightcurve_recovers_variable():
    n, px = spitzer.N_GRID, spitzer.PX
    yy, xx = np.mgrid[:n, :n]
    rng = np.random.default_rng(11)
    s = 1.66 / 2.355 / px  # IRAC [4.5] FWHM ~1.7"
    psf = np.exp(-0.5 * ((xx - n // 2 - 1) ** 2 + (yy - n // 2) ** 2) / s**2)
    psf /= psf.sum()
    conv = 1e6 * (px / 206265) ** 2 * 1e6  # MJy/sr per px -> uJy
    amps = np.r_[0, 0, 200, 120, 40, 0, 0, 0, 210, 90, 0, 0]  # uJy
    galaxy = 0.5 + 0.002 * xx
    samples = [("I2", 53000.0 + 180 * i, galaxy + a * psf / conv + rng.normal(0, 0.002, (n, n)), f"f{i}")
               for i, a in enumerate(amps)]
    lc = spitzer.difference_lightcurve(samples, "I2")
    d = np.array(lc["dflux"])
    # a Gaussian PSF lies wholly inside the 2.4" aperture, so the result is the flux times the IRAC
    # aperture correction (which is for the real, wider PSF), measured against the median epoch (0 here)
    hi = amps > 100
    np.testing.assert_allclose(d[hi] - np.median(d), amps[hi] * spitzer.APCORR["I2"], rtol=0.1)
    assert lc["var_offset_arcsec"] < 1.0


def test_mira_aliased_to_two_years_is_vetoed():
    # a P = 244 d pulsator sampled every ~half year looks like a 2-yr cycle (2/yr alias family)
    P_d = 244.0
    ph = (T * 365.25 / P_d) % 1
    s = np.where(ph < 0.35, ph / 0.35, np.exp(-(ph - 0.35) / 0.25))  # asymmetric, Mira-like
    lc = make_lc(700 * s, 1000 * s, seed=12)
    a = rc.analyse(lc)
    v, why = rc.light_verdict(a)
    assert v != "recurrent"
    assert "mira-alias" in why or "lpv-sinusoid" in why or "no-cycle" in why or "single-outburst" in why


def test_shape_test_separates_outbursts_from_sinusoid():
    P = 4.0
    burst = make_lc(outbursts(P, 2015.0, 400, tr=0.2, td=0.4), outbursts(P, 2015.0, 1000, tr=0.2, td=0.4), seed=13)
    sine = np.sin(2 * np.pi * (T - 2015.0) / P)
    puls = make_lc(400 * sine, 1000 * sine, seed=14)
    assert rc.shape_test(burst, P)["Z"] > rc.Z_SHARP
    assert rc.shape_test(puls, P)["Z"] < 0
    a = rc.analyse(puls)
    v, why = rc.verdict(a, 0.001)
    if v != "rejected":
        assert "agb-compatible" in why
