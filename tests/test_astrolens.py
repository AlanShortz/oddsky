"""Astrometric microlensing (oddsky.analysis.astrolens, lenspop): geometry, conventions and the fitter (hunt H-0015)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from oddsky.analysis import astrolens as al
from oddsky.analysis import lensing, lenspop

ROOT = Path(__file__).resolve().parents[1]
GOST = ROOT / "hunts/H-0009/predictions/work/gost/gost_J124517.csv"   # a committed GOST export (J124517, OS-0022)
RA, DEC = 191.322207, -63.023750


def gost():
    from astropy.time import Time

    g = pd.read_csv(GOST, skipinitialspace=True)
    g.columns = [c.strip() for c in g.columns]
    t = Time(list(g["ObservationTimeAtGaia[UTC]"]), scale="utc").mjd
    return t, g["scanAngle[rad]"].to_numpy(), g["parallaxFactorAlongScan"].to_numpy()


# ---------------------------------------------------------------- geometry
def test_dark_unblended_shift_peaks_at_sqrt2_with_theta_e_over_sqrt8():
    u = np.linspace(0.01, 20, 20001)
    s = al.shift_amplitude(u)
    assert abs(u[np.argmax(s)] - np.sqrt(2)) < 0.01
    assert abs(s.max() - 1 / np.sqrt(8)) < 1e-6
    np.testing.assert_allclose(al.shift_amplitude(np.array([5.0, 10.0])), [5 / 27, 10 / 102], rtol=1e-12)
    assert abs(al.shift_amplitude(np.array([100.0]))[0] * 100 - 1) < 1e-3     # ~1/u far from the lens


def test_shift_points_away_from_the_lens():
    dn, de = al.centroid_shift(np.array([1.0]), np.array([0.0]))     # lens 1 theta_E north of the source
    assert dn[0] < 0 and abs(de[0]) < 1e-15
    dn, de = al.centroid_shift(np.array([0.0]), np.array([-2.0]))    # lens to the west
    assert de[0] > 0


def test_third_light_dilutes_by_A_fs_over_A_fs_plus_blend():
    u = np.array([0.3, 1.0, 3.0])
    fs = 0.4
    a = lensing.magnification(u)
    np.testing.assert_allclose(al.shift_amplitude(u, fs=fs), u / (u**2 + 2) * a * fs / (a * fs + 1 - fs), rtol=1e-12)


def test_luminous_lens_matches_dominik_and_sahu_2000():
    u = np.array([0.2, 1.0, 2.5, 8.0])
    g = 0.7
    r = u * np.sqrt(u**2 + 4)
    ds = u * (1 + g * (u**2 + 3 - r)) / ((1 + g) * (u**2 + 2 + g * r))      # their eq. 98, units of theta_E
    np.testing.assert_allclose(al.shift_amplitude(u, g=g), np.abs(ds), rtol=1e-10)


def test_trajectory_reproduces_the_photometric_parallax_model():
    t = np.linspace(57500, 58500, 400)
    q = [58000.0, 90.0, 0.25, 0.3, -0.2]
    p = lensing.Problem(t, np.ones_like(t), np.ones_like(t), ["x"] * t.size, ra=RA, dec=DEC, parallax=True, t0par=58000)
    dn, de = lensing.sun_offsets(t, RA, DEC, 58000)
    tau = (t - q[0]) / q[1] + q[3] * dn + q[4] * de
    beta = q[2] + (-q[3] * de + q[4] * dn)
    un, ue = al.trajectory(tau, beta, q[3], q[4])
    np.testing.assert_allclose(lensing.magnification(np.hypot(un, ue)), p.model(q), rtol=1e-12)
    # tau is the component along piE (the lens-source relative proper motion)
    pe = np.hypot(q[3], q[4])
    np.testing.assert_allclose((un * q[3] + ue * q[4]) / pe, tau, rtol=1e-10)


def test_gost_scan_angle_convention_and_parallax_factors():
    """GOST's scanAngle is DR4's scan_pos_angle convention: the AL parallax factor is fE sin(theta) + fN cos(theta)."""
    t, theta, plx = gost()
    fn, fe = al.parallax_factors(t, RA, DEC, scale=1.01)
    np.testing.assert_allclose(fe * np.sin(theta) + fn * np.cos(theta), plx, atol=0.005)


def test_along_scan_precision_curve():
    s = al.sigma_al_fov(np.array([13.0, 15.0, 17.0, 19.0, 20.0]))
    assert np.all(np.diff(s) > 0)
    assert 0.05 < s[0] < 0.1 and 0.08 < s[1] < 0.13 and 0.2 < s[2] < 0.3 and 0.7 < s[3] < 0.95 and 1.5 < s[4] < 1.9
    assert np.all(al.sigma_al_fov([15.0, 17.0], "rybicki18") > al.sigma_al_fov([15.0, 17.0]))


# ---------------------------------------------------------------- the fitter
Q = np.array([57900.0, 150.0, 0.2, 0.06, -0.05])


def sim(theta_e, G=16.0, seed=1, **kw):
    t, theta, plx = gost()
    return al.simulate(t, theta, plx, RA, DEC, G, Q, theta_e, fs=0.8, pm=(-3.0, -5.0), parallax=0.3,
                       rng=np.random.default_rng(seed), t0par=57900, **kw)


def test_fit_recovers_theta_e_pie_and_mass():
    ph, ast = sim(4.0)
    r = al.fit_target(ph, ast, RA, DEC, t0par=57900)
    assert r["dchi2"] > 100 and r["p_null_asymptotic"] < 1e-10
    assert abs(r["theta_e"] - 4.0) < 4 * r["sig_theta_e"] and r["sig_theta_e"] < 0.6
    m_true = 4.0 / (al.KAPPA * np.hypot(Q[3], Q[4]))
    assert r["M_16"] < m_true * 1.15 and r["M_84"] > m_true * 0.85
    assert abs(r["pm_ra"] + 3) < 0.3 and abs(r["parallax"] - 0.3) < 0.3
    assert r["theta_e_ul95"] > r["theta_e"]
    # profile-likelihood mass interval brackets the truth and excludes 3 Msun from below only if it should
    assert r["M_lo95"] < m_true < r["M_hi95"] and not r["M_hi95_open"]
    assert r["M_best"] > 3 and r["M_gt3_sigma"] > 2


def test_no_lens_gives_no_detection_and_a_finite_upper_limit():
    ph, ast = sim(0.0, seed=3)
    r = al.fit_target(ph, ast, RA, DEC, t0par=57900)
    assert r["dchi2"] < 16
    assert 0 < r["theta_e_ul95"] < 2.0
    assert r["M_ul95"] < 10 and r["M_gt3_sigma"] < 2     # no lens: a 10 Msun dark lens is excluded here


def test_expected_dchi2_matches_a_noise_free_fit():
    """The fast Asimov Delta chi^2 equals the fitter's Delta chi^2 on noise-free data at the true trajectory."""
    t, theta, plx = gost()
    ph1, a1 = al.simulate(t, theta, plx, RA, DEC, 17.0, Q, 2.0, fs=0.8, rng=np.random.default_rng(4), t0par=57900)
    _, a0 = al.simulate(t, theta, plx, RA, DEC, 17.0, Q, 0.0, fs=0.8, rng=np.random.default_rng(4), t0par=57900)
    nf = al.AstroData(a1.t, a1.theta, a1.w - a0.w, a1.sigma, a1.plx)       # same noise draws: the pure signal remains
    dn, de = lensing.sun_offsets(t, RA, DEC, 57900)
    tau = (t - Q[0]) / Q[1] + Q[3] * dn + Q[4] * de
    beta = Q[2] + (-Q[3] * de + Q[4] * dn)
    f = 0.8 * lensing.magnification(np.hypot(tau, beta)) + 0.2
    prob = al.Problem(al.PhotData(t, f, ph1.e, ph1.group), nf, RA, DEC, t0par=57900)
    d0, d1 = prob.residuals(Q, theta_e=0.0), prob.residuals(Q, theta_e=None)
    lam, sig = al.expected_dchi2(t, theta, a1.sigma, plx, RA, DEC, Q[None], 2.0, 0.8, t0par=57900)
    assert lam[0] > 10
    np.testing.assert_allclose(d0 @ d0 - d1 @ d1, lam[0], rtol=1e-6)
    np.testing.assert_allclose(sig[0], 2.0 / np.sqrt(lam[0]), rtol=1e-9)


def test_blend_offset_terms_absorb_an_offset_blend():
    """A neighbour inside the window pulls the centroid toward the source as it brightens. Without the nuisance terms that
    looks like a deflection; with them it does not."""
    ph, ast = sim(0.0, G=15.0, seed=5, blend_vec=(3.0, 1.0))
    with_terms = al.fit_target(ph, ast, RA, DEC, t0par=57900, upper_limit=False)
    without = al.fit_target(ph, ast, RA, DEC, t0par=57900, upper_limit=False, blend_offset=False, rescale=False, clip=0)
    assert with_terms["dchi2"] < 16
    assert without["dchi2"] > with_terms["dchi2"] + 9 or without["chi2_alt"] > with_terms["chi2_alt"] + 30


def test_detection_probability_is_monotone():
    p = al.detection_probability(np.array([0.0, 10.0, 25.0, 50.0, 100.0]), 25.0)
    assert np.all(np.diff(p) > 0) and p[0] < 1e-5 and p[-1] > 0.99 and 0.4 < p[2] < 0.6


# ---------------------------------------------------------------- the Galactic prior
def test_lens_samples_bulge_sightline():
    s = lenspop.sample_lenses(1.0, -3.0, 268.0, -29.5, 1.0, n=2000, ds=8.0, mu_s=(-3.0, -6.0), te_range=(20, 200),
                              rng=np.random.default_rng(0))
    assert s["n_eff"] > 200
    w = s["weight"]
    assert np.all(s["tE"][w > 0] >= 20) and np.all(s["tE"][w > 0] <= 200)
    prel = 1 / s["D_L"] - 1 / s["D_S"]
    m = prel > 1e-5
    np.testing.assert_allclose(s["theta_E"][m], np.sqrt(al.KAPPA * 1.0 * prel[m]), rtol=1e-12)
    np.testing.assert_allclose((np.hypot(s["piE_N"], s["piE_E"]) * s["theta_E"])[m], prel[m], rtol=1e-9)
    # heavier lenses with the same tE sit closer to the source
    h = lenspop.sample_lenses(1.0, -3.0, 268.0, -29.5, 10.0, n=2000, ds=8.0, mu_s=(-3.0, -6.0), te_range=(20, 200),
                              rng=np.random.default_rng(0))
    assert np.sum(h["weight"] * h["D_L"]) > np.sum(w * s["D_L"])


def test_mass_function_fractions():
    m, kind = lenspop.mass_function_samples(200000, rng=np.random.default_rng(0))
    assert abs((kind == "BH").mean() - 0.0013) < 0.0004 and abs((kind == "WD").mean() - 0.06) < 0.005
    assert m[kind == "star"].max() <= 1.0 and m[kind == "star"].min() >= 0.01
    assert 6.5 < np.median(m[kind == "BH"]) < 9


@pytest.mark.parametrize("model", ["edr3", "rybicki18"])
def test_simulate_shapes(model):
    t, theta, plx = gost()
    ph, ast = al.simulate(t, theta, plx, RA, DEC, 18.0, Q, 1.0, precision=model, rng=np.random.default_rng(0))
    assert len(ph) == len(ast) == len(t) and np.all(ast.sigma > 0) and np.all(ph.e > 0)


# ---------------------------------------------------------------- referee fixes (2026-11-02)
def test_one_wild_outlier_does_not_discard_good_transits():
    """Referee: one 100-mas value at G 15 used to make the fitter clip 64 of 72 good transits."""
    for seed, sizes in ((11, [1000.0]), (12, [300.0, -300.0]), (13, [100.0])):
        ph, ast = sim(0.0, G=15.0, seed=seed)
        n = len(ast)
        idx = np.random.default_rng(seed).choice(n, len(sizes), replace=False)
        ast.w[idx] += np.array(sizes) * ast.sigma[idx]
        r = al.fit_target(ph, ast, RA, DEC, t0par=57900, upper_limit=False, profile_mass=False)
        assert r["n_astro"] >= n - len(sizes) - 2, (sizes, r["n_astro"], n)
        assert r["dchi2"] < 16


def test_final_fit_contains_no_point_beyond_the_clip_and_null_uses_the_same_points():
    """Referee: points flagged on the loop's last pass stayed in the fit and in the null model."""
    ph, ast = sim(0.0, G=16.0, seed=21)
    rng = np.random.default_rng(21)
    idx = rng.choice(len(ast), 6, replace=False)
    ast.w[idx] += rng.choice([-1, 1], 6) * rng.uniform(6, 15, 6) * ast.sigma[idx]
    r = al.fit_target(ph, ast, RA, DEC, t0par=57900, upper_limit=False, profile_mass=False, rescale=False)
    assert r["max_abs_resid"] <= 5.0
    assert r["n_astro"] + r["n_astro_clipped"] == len(ast)


def test_window_class_offsets_absorb_a_calibration_step_at_peak():
    """A source crossing G ~ 13 at peak changes window class; a calibration step between classes follows the
    magnification. With the per-class offset term it is absorbed; without it, it fakes a deflection."""
    t, theta, plx = gost()
    q = np.array([57900.0, 150.0, 0.08, 0.06, -0.05])
    ph, ast = al.simulate(t, theta, plx, RA, DEC, 14.5, q, 0.0, fs=1.0, rng=np.random.default_rng(31), t0par=57900,
                          wclass_step=0.6)
    assert (ast.wclass == "bright").sum() >= 3
    with_term = al.fit_target(ph, ast, RA, DEC, t0par=57900, upper_limit=False, profile_mass=False)
    bare = al.AstroData(ast.t, ast.theta, ast.w, ast.sigma, ast.plx)
    without = al.fit_target(ph, bare, RA, DEC, t0par=57900, upper_limit=False, profile_mass=False)
    assert with_term["n_window_classes"] == 2 and with_term["dchi2"] < 16
    assert without["dchi2"] > with_term["dchi2"] + 9 or without["err_scale"] > 1.5 or without["n_astro_clipped"] >= 3


def test_a_bright_star_with_one_100_mas_value_is_not_a_lens():
    """At G 12 (0.07 mas per transit) a 100-mas value is ~1,400 sigma. The deflection model (a short, strong lens) and the
    blend-offset terms (a tiny bump times a huge offset) can bend to fit one point, so the robust pass picks its candidate
    from a position + proper motion + parallax fit and tests the deleted residual."""
    for seed in (41, 42, 43, 44):
        ph, ast = sim(0.0, G=12.0, seed=seed)
        j = int(np.random.default_rng(seed).integers(len(ast)))
        ast.w[j] += 100.0
        r = al.fit_target(ph, ast, RA, DEC, t0par=57900, upper_limit=False, profile_mass=False)
        assert r["dchi2"] < 16 and r["n_robust_rejected"] >= 1 and r["n_astro_clipped"] <= 2, (seed, r["dchi2"])


def test_a_real_strong_deflection_survives_the_robust_pass():
    ph, ast = sim(8.0, G=13.0, seed=51)
    r = al.fit_target(ph, ast, RA, DEC, t0par=57900, upper_limit=False, profile_mass=False)
    assert r["dchi2"] > 500 and r["n_astro_clipped"] <= 2 and abs(r["theta_e"] - 8.0) < 1.5
