"""Gaia epoch photometry asks for DR4 first and falls back to DR3 without changing DR3 results."""
import pandas as pd

from oddsky.data import gaia_epoch


def test_falls_back_when_newest_release_fails(monkeypatch):
    calls = []

    def fake(ids, chunk, release):
        calls.append(release)
        if release == "Gaia DR4":
            raise RuntimeError("500")
        return {i: pd.DataFrame({"t_mjd": [57000.0]}) for i in ids}

    monkeypatch.setattr(gaia_epoch, "_fetch_release", fake)
    out = gaia_epoch.fetch([1, 2])
    assert calls == ["Gaia DR4", "Gaia DR3"]
    assert set(out) == {1, 2}


def test_newest_release_wins_and_older_only_fills_gaps(monkeypatch):
    def fake(ids, chunk, release):
        if release == "Gaia DR4":
            return {1: pd.DataFrame({"t_mjd": [58000.0]})}
        return {i: pd.DataFrame({"t_mjd": [57000.0]}) for i in ids}

    monkeypatch.setattr(gaia_epoch, "_fetch_release", fake)
    out = gaia_epoch.fetch([1, 2])
    assert out[1].t_mjd.iloc[0] == 58000.0
    assert out[2].t_mjd.iloc[0] == 57000.0


def test_prediction_on_unreleased_series_is_allowed(tmp_path, monkeypatch):
    """A case with no Gaia epoch photometry yet can still register a check on GAIA:G (graded once DR4 is out),
    but not on an archive the grader cannot fetch."""
    import pytest

    from oddsky.case.model import Case, Target
    from oddsky.case.store import CaseStore
    from oddsky.tools import Toolbox

    monkeypatch.chdir(tmp_path)
    (tmp_path / "cases" / "OS-9999").mkdir(parents=True)
    store = CaseStore(tmp_path / "cases" / "OS-9999")
    store.save(Case(id="OS-9999", title="t", target=Target(name="x", ra=1.0, dec=2.0)))
    tb = Toolbox(mode="open", author="test")
    monkeypatch.setattr(tb, "store", lambda case: store)
    out = tb.register_prediction("OS-9999", "s", 0.8, "GAIA:G", 57955, 58020, "<", -1.0, statistic="brightest",
                                 baseline_start=56800, baseline_end=57900)
    assert out["prediction"] == "P1"
    with pytest.raises(FileNotFoundError):
        tb.register_prediction("OS-9999", "s", 0.8, "NOSUCH:X", 1, 2, "<", 0.0)
