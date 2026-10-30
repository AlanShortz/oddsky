"""Microlensing fits recover planted events, and the lens_fit tool reports asymmetry and an unsampled peak honestly."""

import numpy as np
import pandas as pd
from conftest import make_series

from oddsky.analysis import lensing
from oddsky.case.model import Case, Target
from oddsky.case.store import CaseStore
from oddsky.tools import Toolbox

RA, DEC = 60.1, 32.6


def planted(t, t0=58000.0, te=40.0, u0=0.3, pin=0.0, pie=0.0):
    prob = lensing.Problem(t, np.ones_like(t), np.ones_like(t), ["x"] * len(t), ra=RA, dec=DEC, parallax=True, t0par=round(t0))
    return prob.model([t0, te, u0, pin, pie])


def test_static_fit_recovers_a_planted_event(rng):
    t = np.arange(57850, 58150, 2.0)
    f = lensing.magnification(np.hypot((t - 58000) / 40.0, 0.3)) + rng.normal(0, 0.01, t.size)
    prob = lensing.Problem(t, f, np.full_like(t, 0.01), ["x"] * t.size)
    p, chi2 = prob.fit()
    assert abs(p[0] - 58000) < 0.5 and abs(p[1] - 40) < 1.5 and abs(abs(p[2]) - 0.3) < 0.02
    assert chi2 / (t.size - 3) < 1.5


def test_parallax_fit_recovers_parallax_and_the_static_fit_is_worse(rng):
    t = np.arange(57850, 58150, 2.0)
    f = planted(t, pin=0.5, pie=0.6) + rng.normal(0, 0.01, t.size)
    e = np.full_like(t, 0.01)
    p_s, chi_s = lensing.Problem(t, f, e, ["x"] * t.size).fit()
    prob = lensing.Problem(t, f, e, ["x"] * t.size, ra=RA, dec=DEC, parallax=True)
    p, chi_p = prob.fit()
    assert chi_s - chi_p > 25
    assert abs(np.hypot(p[3], p[4]) - np.hypot(0.5, 0.6)) < 0.15


def test_profile_range_brackets_the_truth(rng):
    t = np.arange(57850, 58150, 3.0)
    f = lensing.magnification(np.hypot((t - 58000) / 40.0, 0.3)) + rng.normal(0, 0.01, t.size)
    prob = lensing.Problem(t, f, np.full_like(t, 0.01), ["x"] * t.size)
    p, chi2 = prob.fit()
    lo, hi, open_ = lensing.profile_range(prob, p, chi2, 1, 20.0)
    assert lo < 40 < hi and hi - lo < 6 and not open_


def test_lens_fit_tool_flags_an_unsampled_peak(tmp_path, monkeypatch, rng):
    monkeypatch.setenv("ODDSKY_HOME", str(tmp_path))
    (tmp_path / "cases").mkdir()
    store = CaseStore(tmp_path / "cases" / "OS-0001")
    store.save(Case(id="OS-0001", title="lens", target=Target(name="L", ra=RA, dec=DEC)))
    t = np.arange(57000, 59000, 1.0)
    t = t[(np.abs(t - 58000) > 12)]  # a gap over the peak
    f = lensing.magnification(np.hypot((t - 58000) / 40.0, 0.3))
    mag = 15.0 - 2.5 * np.log10(f) + rng.normal(0, 0.01, t.size)
    store.write_series("atlas", pd.concat([make_series(t, mag, "ATLAS_o", "ATLAS", 0.01),
                                           make_series(t, mag + 0.6, "ATLAS_c", "ATLAS", 0.01)]))
    r = Toolbox(mode="open", author="t").lens_fit("OS-0001", ["ATLAS:ATLAS_o", "ATLAS:ATLAS_c"], 57800, 58200)
    assert abs(r["parallax"]["tE_days"] - 40) < 5
    assert any("peak" in w for w in r["warnings"])
    assert r["ranges_95"]["tE_days"][0] < 40 < r["ranges_95"]["tE_days"][1]
