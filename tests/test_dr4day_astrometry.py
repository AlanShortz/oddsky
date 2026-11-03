"""The H-0015 release-day stage `astrolens` (oddsky.dr4day.astrometry). Offline: the archive is faked."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from oddsky.dr4day import astrometry as A
from oddsky.dr4day import config, pipeline

ROOT = Path(__file__).resolve().parents[1]
GOST = ROOT / "hunts/H-0015/data/gost_transits.csv.gz"


def transits(sid="OB110462"):
    g = pd.read_csv(GOST, dtype={"source_id": str})
    g = g[g.source_id == sid]
    return g.t_mjd.to_numpy(), g.theta.to_numpy(), g.plx_al.to_numpy()


def test_release_switch_and_stage_order():
    assert not config.release("dr3").has_epoch_astrometry
    dr4 = config.release("dr4")
    assert dr4.has_epoch_astrometry and dr4.retrieval_epoch_astrometry == "EPOCH_ASTROMETRY"
    assert pipeline.STAGES.index("astrolens") == pipeline.STAGES.index("report") - 1
    assert config.release("dr4", {"retrieval_epoch_astrometry": "EPOCH_ASTROMETRY_V2"}).retrieval_epoch_astrometry == "EPOCH_ASTROMETRY_V2"


def test_normalise_reads_the_dr4_draft_layout_back(tmp_path):
    """Per-transit rows with 10-element per-CCD arrays (sky mapper first) written to CSV and read back."""
    t, th, px = transits()
    raw = A.simulated_raw("42", t, th, px, 17.0, np.random.default_rng(0))
    p = tmp_path / "raw.csv"
    raw.to_csv(p, index=False)
    d = A.normalise(pd.read_csv(p, dtype={"source_id": str}))
    assert len(d) == len(t) and (d.n_ccd == 9).all()            # the sky mapper (index 0, used_by_agis_al false) dropped
    np.testing.assert_allclose(d.theta, th, atol=1e-6)            # degrees in, radians out
    np.testing.assert_allclose(d.plx, px)
    assert np.max(np.abs(d.t_mjd - t)) * 86400 < 30                # TCB ns since J2010.0 -> MJD (CCDs 4.4 s apart)
    np.testing.assert_allclose(d.sigma, 0.2386, atol=0.002)       # per-FoV error at G 17 reconstructed (floor included)


def test_normalise_drops_unused_out_of_window_and_reads_a_per_ccd_layout():
    t, th, px = transits()
    raw = A.simulated_raw("42", t[:3], th[:3], px[:3], 15.0, np.random.default_rng(1))
    raw.loc[0, "centroid_pos_al"] = raw.loc[0, "centroid_pos_al"].replace(",", ",1e12,", 1)   # a DR4 out-of-window value
    raw.loc[0, "centroid_pos_al"] = "[" + ",".join(raw.loc[0, "centroid_pos_al"][1:-1].split(",")[:10]) + "]"
    raw.loc[1, "used_by_agis_al"] = "[false,false,false,false,false,false,false,false,false,false]"
    d = A.normalise(raw, per_transit=False)
    assert len(d) == 8 + 0 + 9 and (np.abs(d.w) < 1e6).all()
    # a BH3-like per-CCD table: BJD (TCB), w, sigma_w, scan angle in degrees, parallax factor, outlier flag
    bh3 = pd.DataFrame(dict(source_id="7", transit_id=[1, 1, 2], bjd_tcb=[2457000.1, 2457000.1, 2457100.2], w=[0.1, 0.2, -0.3],
                            sigma_w=[0.2, 0.2, 0.3], scan_angle=[10.0, 10.0, 200.0], parallax_factor=[0.5, 0.5, -0.4],
                            outlier_flag=[False, False, True]))
    d2 = A.normalise(bh3)
    assert len(d2) == 1 and d2.n_ccd.iloc[0] == 2 and abs(d2.t_mjd.iloc[0] - 56999.6) < 1e-6
    assert abs(d2.theta.iloc[0] - np.radians(10)) < 1e-9


def test_normalise_names_missing_columns():
    with pytest.raises(ValueError, match="not found"):
        A.normalise(pd.DataFrame(dict(source_id=["1"], transit_id=[1], g_mag=[15.0])))


class _NoArchive:
    """Stands in for the archive: every request fails, as it would offline or during the archive's closure."""
    errors: list = []
    chunk = 50

    def links(self, sid):
        raise RuntimeError("offline")

    def error(self, *a, **k):
        self.errors.append(a)


def test_dr3_dry_run_says_not_available_and_runs_the_rest_on_simulated_tables(tmp_path):
    run = pipeline.Run(config.release("dr3"), root=ROOT, archive=_NoArchive(), out=tmp_path)
    info = A.stage(run, dry_top=3)
    assert "not available in dr3" in info["epoch_astrometry"]
    n = info["simulated_sources"]
    assert n >= 3 and info["status_counts"] == {"fitted": n}        # 3 targets (+ 1 control once data/controls.csv exists)
    res = pd.read_csv(tmp_path / "astrolens/results.csv", dtype={"release_source_id": str})
    ctl = res[res.release_source_id == info["positive_control"]].iloc[0]
    assert ctl.dchi2 > 25 and 3.0 < ctl.theta_e < 8.0             # the injected 5 mas deflection is found (G 18.3)
    assert (res[res.release_source_id != info["positive_control"]].dchi2 < 25).all()
    assert json.loads((tmp_path / "astrolens/summary.json").read_text())["simulated_sources"] == n


# ---- referee fixes (2026-11-02): format sanity checks make a target ineligible instead of fitting misread data ----------
OB = (267.917458, -29.890639)


def _raw(seed=2, n=None):
    t, th, px = transits()
    if n:
        t, th, px = t[:n], th[:n], px[:n]
    return A.simulated_raw("42", t, th, px, 16.0, np.random.default_rng(seed), ra=OB[0], dec=OB[1]), th


def test_sanity_check_passes_and_carries_quality_columns():
    raw, th = _raw()
    d = A.normalise(raw, ra=OB[0], dec=OB[1])
    assert d.attrs["theta_unit"] == "deg" and d.attrs["plx_deviation"] < 0.01
    np.testing.assert_allclose(d.theta, th, atol=1e-6)
    q = A.quality_summary(d)
    assert q["frac_blended"] == 0 and q["frac_multipeak"] == 0 and q["wclass_counts"] == f"1:{len(d)}"
    assert q["agis_source_excess_noise"] == 0.0 and "gates_counts" in q


def test_time_in_the_wrong_unit_is_refused():
    raw, _ = _raw()
    days = [A._num(A._arr(v)) / A.NS_PER_DAY for v in raw.obs_time_tcb]          # days since J2010.0 instead of ns
    raw["obs_time_tcb"] = ["[" + ",".join(str(x) for x in a) + "]" for a in days]
    with pytest.raises(A.FormatError, match="outside the release span"):
        A.normalise(raw, ra=OB[0], dec=OB[1])


def test_scan_angle_in_radians_is_detected_and_a_wrong_convention_refused():
    raw, th = _raw()
    deg = [A._num(A._arr(v)) for v in raw.scan_pos_angle]
    raw_rad = raw.copy()
    raw_rad["scan_pos_angle"] = ["[" + ",".join(str(x) for x in np.radians(a)) + "]" for a in deg]
    d = A.normalise(raw_rad, ra=OB[0], dec=OB[1])
    assert d.attrs["theta_unit"] == "rad"
    np.testing.assert_allclose(d.theta, th, atol=1e-6)
    raw_east = raw.copy()                                    # measured from east instead of north
    raw_east["scan_pos_angle"] = ["[" + ",".join(str(x) for x in (90.0 - a)) + "]" for a in deg]
    with pytest.raises(A.FormatError, match="parallax_factor_al does not match"):
        A.normalise(raw_east, ra=OB[0], dec=OB[1])


def test_reference_point_must_be_constant():
    raw, _ = _raw(n=5)
    raw.loc[2, "ra0"] = raw.ra0.iloc[0] + 1e-6
    with pytest.raises(A.FormatError, match="ra0"):
        A.normalise(raw, ra=OB[0], dec=OB[1])


def test_a_duplicated_response_uses_each_transit_once():
    raw, _ = _raw(n=20)
    d1 = A.normalise(raw, ra=OB[0], dec=OB[1])
    d2 = A.normalise(pd.concat([raw, raw.iloc[:7]], ignore_index=True), ra=OB[0], dec=OB[1])
    assert len(d2) == len(d1) and (d2.n_ccd == 9).all()
