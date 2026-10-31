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


def test_grading_keeps_gaia_variability_outliers(tmp_path, monkeypatch):
    """A lens peak can be exactly what Gaia rejects as a variability outlier: grading keeps those transits (but not
    photometry rejections); the analysis tools still drop them."""
    from oddsky.case.model import Case, Target
    from oddsky.case.store import CaseStore
    from oddsky.tools import Toolbox

    monkeypatch.chdir(tmp_path)
    (tmp_path / "cases" / "OS-9999").mkdir(parents=True)
    store = CaseStore(tmp_path / "cases" / "OS-9999")
    store.save(Case(id="OS-9999", title="t", target=Target(name="x", ra=1.0, dec=2.0)))
    store.write_series("gaia_epoch", pd.DataFrame({
        "t_mjd": [57000.0, 57001.0, 57002.0, 57003.0], "mag": [15.0, 13.2, 13.0, 9.0], "err": [0.01] * 4, "band": ["G"] * 4,
        "survey": ["GAIA"] * 4, "flag": ["", "rejected_by_variability", "rejected_by_variability", "rejected_by_photometry"]}))
    tb = Toolbox(mode="open", author="test")
    assert len(tb._frame(store, "GAIA:G")) == 1
    graded = tb._frame(store, "GAIA:G", grading=True)
    assert sorted(graded.mag) == [13.0, 13.2, 15.0]


def test_report_records_a_failed_release_and_the_source_release(monkeypatch):
    """A DR4 failure falls back silently in `fetch`; `fetch_report` must say what failed and where each source came from."""
    def fake(ids, chunk, release):
        if release == "Gaia DR4":
            raise KeyError("g_transit_time")
        return {i: pd.DataFrame({"t_mjd": [57000.0]}) for i in ids}

    monkeypatch.setattr(gaia_epoch, "_fetch_release", fake)
    out, rep = gaia_epoch.fetch_report([7])
    assert set(out) == {7}
    assert rep["releases"][0]["release"] == "Gaia DR4" and not rep["releases"][0]["ok"]
    assert "KeyError" in rep["releases"][0]["error"]
    assert rep["source_release"] == {7: "Gaia DR3"}
