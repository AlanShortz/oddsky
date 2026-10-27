import numpy as np
import pandas as pd
import pytest

from oddsky.case.model import Case, Target
from oddsky.case.store import CaseStore


def make_series(t, mag, band, survey, err=0.01, **extra):
    df = pd.DataFrame(dict(t_mjd=t, mag=mag, err=err, band=band, survey=survey, flag="", **extra))
    return df


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def dusty_case(tmp_path, rng, monkeypatch):
    """A synthetic star: flat optical with one deep 60-day dip; NEOWISE brightening + reddening."""
    monkeypatch.setenv("ODDSKY_HOME", str(tmp_path))
    (tmp_path / "cases").mkdir()
    store = CaseStore(tmp_path / "cases" / "OS-0001")
    store.save(Case(id="OS-0001", title="Synthetic dusty star", target=Target(name="Synth-1", ra=10.0, dec=-20.0)))
    t = np.arange(59000, 60000, 1.0)
    v = 12.0 + rng.normal(0, 0.01, t.size)
    dip = (t > 59500) & (t < 59560)
    v[dip] += 0.5 * np.sin(np.pi * (t[dip] - 59500) / 60)
    a = pd.concat([
        make_series(t, v, "V", "AAVSO", observer=np.where(t % 2 == 0, "AAA", "BBB")),
        make_series(t, v + 0.6 + 0.3 * (v - 12), "B", "AAVSO", observer="AAA"),
    ])
    store.write_series("aavso", a)
    tw = np.arange(56800, 60400, 182.6)
    w1 = np.where(tw > 58200, 10.6, 11.0) + rng.normal(0, 0.005, tw.size)
    w2 = np.where(tw > 58200, 10.2, 11.0) + rng.normal(0, 0.005, tw.size)
    store.write_series("neowise", pd.concat([make_series(tw, w1, "W1", "NEOWISE", 0.01),
                                             make_series(tw, w2, "W2", "NEOWISE", 0.01)]))
    store.write_context({
        "gaia": {"G": 11.9, "bp_rp": 0.8, "ruwe": 1.0, "abs_G": 4.5},
        "neighbors": [{"source_id": 1, "sep_arcsec": 4.0, "phot_g_mean_mag": 13.0, "bp_rp": 2.5, "dG": 1.1,
                       "flux_ratio_G": 0.36, "parallax": 1.0, "ruwe": 1.0}],
    })
    return store
